import hashlib
from collections.abc import Sequence

from typing_extensions import override

from fast_pypi.backends import (
    AbstractBackendInterface,
    FileContents,
    ProjectFileExistsError,
    ProjectFileInfo,
)
from fast_pypi.config import FastPypiConfig
from fast_pypi.logger import logger

from .azure_blob_utils import azure_blob_container_client
from .config import AzureBlobConfig


class AzureBlobBackend(AbstractBackendInterface):
    """Interface for the azure blob backend."""

    config: AzureBlobConfig

    def __init__(self, config: AzureBlobConfig, general_config: FastPypiConfig) -> None:
        self.config = config
        super().__init__(general_config=general_config)

    @override
    async def list_projects(self) -> Sequence[str]:
        """List all projects in the azure blob backend.

        Returns:
            A sequence of project names.
        """
        async with azure_blob_container_client(config=self.config) as (container_client, base_path):
            blob_props = [
                blob_prop async for blob_prop in container_client.walk_blobs(name_starts_with=base_path, delimiter='/')
            ]

            return sorted(
                [
                    blob_prop.name.removeprefix(base_path).removesuffix('/')
                    for blob_prop in blob_props
                    if '/' in blob_prop.name
                ]
            )

    @override
    async def list_project_versions(self, project_name: str) -> Sequence[str]:
        """Get the available versions of a project in the azure blob backend.

        Args:
            project_name: The name of the project.

        Returns:
            A sequence of version strings for the specified project.
        """
        async with azure_blob_container_client(config=self.config) as (container_client, base_path):
            name_prefix = f'{base_path}{project_name}/'
            blob_props = [
                blob_prop
                async for blob_prop in container_client.walk_blobs(
                    name_starts_with=name_prefix,
                    delimiter='/',
                )
            ]

            return sorted(
                [
                    blob_prop.name.removeprefix(name_prefix).removesuffix('/')
                    for blob_prop in blob_props
                    if '/' in blob_prop.name
                ]
            )

    @override
    async def list_files_for_project(
        self,
        project_name: str,
    ) -> Sequence[ProjectFileInfo]:
        """List all files for a given project in the azure blob backend.

        Args:
            project_name: The name of the project.

        Returns:
            A sequence of ProjectFileInfo objects for the specified project.
        """
        async with azure_blob_container_client(config=self.config) as (container_client, base_path):
            name_prefix = f'{base_path}{project_name}/'
            blob_props = sorted(
                [
                    blob_name
                    async for blob_name in container_client.list_blobs(
                        name_starts_with=name_prefix,
                    )
                ],
                key=lambda x: x.name,
            )

            return [
                ProjectFileInfo(
                    project_name=project_name,
                    version=blob_prop.name.removeprefix(name_prefix).split('/', maxsplit=1)[0],
                    filename=blob_prop.name.removeprefix(name_prefix).split('/', maxsplit=1)[1],
                    last_modified=blob_prop.last_modified,
                    size=blob_prop.size,
                )
                for blob_prop in blob_props
                if not blob_prop.name.endswith('.sha256') and blob_prop.name.endswith(('.whl', '.tar.gz'))
            ]

    @override
    async def get_file_contents(
        self,
        project_name: str,
        version: str,
        filename: str,
    ) -> FileContents | None:
        """Get the contents of a file from the azure blob backend.

        Args:
            project_name: The name of the project.
            version: The version of the project.
            filename: The name of the file to retrieve.

        Returns:
            A FileContents object containing the file's contents and SHA256
                digest, or None if the file does not exist.
        """
        async with azure_blob_container_client(config=self.config) as (container_client, base_path):
            blob_name = f'{base_path}{project_name}/{version}/{filename}'
            blob_client = container_client.get_blob_client(blob_name)

            if not await blob_client.exists():
                logger.warning(
                    'get_file_contents_file_not_found',
                    extra={
                        'project_name': project_name,
                        'file_name': filename,
                        'blob_name': blob_name,
                    },
                )
                return None

            file_content = await (await blob_client.download_blob()).readall()
            blob_props = await blob_client.get_blob_properties()
            sha256_digest = blob_props.metadata.get('sha256', None)

            if sha256_digest is None:
                logger.warning(
                    'sha256_digest_metadata_does_not_exist',
                    extra={
                        'project_name': project_name,
                        'file_name': filename,
                    },
                )

                # Update the blob metadata with the computed SHA256 digest
                sha256_digest = hashlib.sha256(file_content).hexdigest()
                _ = await blob_client.set_blob_metadata(metadata={'sha256': sha256_digest})

            return FileContents(
                filename=filename,
                content=file_content,
                sha256_digest=sha256_digest,
            )

    @override
    async def upload_file(
        self,
        project_name: str,
        version: str,
        filename: str,
        file_content: bytes,
        sha256_digest: str | None,
    ) -> None:
        """Upload a file to the azure blob backend for a specific project.

        Args:
            project_name: The name of the project.
            version: The version of the project.
            filename: The name of the file to save.
            file_content: The content of the file to save.
            sha256_digest: The SHA256 digest of the file content.
        """
        async with azure_blob_container_client(config=self.config) as (container_client, base_path):
            blob_name = f'{base_path}{project_name}/{version}/{filename}'
            blob_client = container_client.get_blob_client(blob_name)

            if not self.general_config.allow_overwrite and await blob_client.exists():
                raise ProjectFileExistsError(
                    project_name=project_name,
                    filename=filename,
                )

            _ = await blob_client.upload_blob(
                data=file_content,
                overwrite=self.general_config.allow_overwrite,
                metadata={'sha256': sha256_digest or hashlib.sha256(file_content).hexdigest()},
            )
            logger.info(
                'azure_blob_backend_file_saved',
                extra={
                    'project_name': project_name,
                    'file_name': filename,
                    'sha256': sha256_digest,
                },
            )

    @override
    async def delete_project_version(
        self,
        project_name: str,
        version: str,
    ) -> bool:
        """Delete a specific project version from the azure blob backend.

        Args:
            project_name: The name of the project.
            version: The version of the project to delete.

        Returns:
            True if the version was deleted, False if it did not exist.
        """
        async with azure_blob_container_client(config=self.config) as (container_client, base_path):
            blob_name_prefix = f'{base_path}{project_name}/{version}/'

            blob_props = [
                blob
                async for blob in container_client.list_blobs(
                    name_starts_with=blob_name_prefix,
                )
            ]

            if not blob_props:
                logger.warning(
                    'delete_project_version_not_found',
                    extra={
                        'project_name': project_name,
                        'version': version,
                    },
                )
                return False

            for blob in blob_props:
                await container_client.get_blob_client(blob.name).delete_blob()
            logger.info(
                'azure_blob_backend_version_deleted',
                extra={
                    'project_name': project_name,
                    'version': version,
                },
            )
            return True

    @override
    async def delete_project_version_file(
        self,
        project_name: str,
        version: str,
        filename: str,
    ) -> bool:
        """Delete a specific file for a project version in the azure blob backend.

        Args:
            project_name: The name of the project.
            version: The version of the project.
            filename: The name of the file to delete.

        Returns:
            True if the file was deleted, False if it did not exist.
        """
        async with azure_blob_container_client(config=self.config) as (container_client, base_path):
            blob_name = f'{base_path}{project_name}/{version}/{filename}'
            blob_client = container_client.get_blob_client(blob_name)

            if not await blob_client.exists():
                logger.warning(
                    'delete_project_version_file_not_found',
                    extra={
                        'project_name': project_name,
                        'version': version,
                        'file_name': filename,
                    },
                )
                return False

            await blob_client.delete_blob()
            logger.info(
                'azure_blob_backend_file_deleted',
                extra={
                    'project_name': project_name,
                    'version': version,
                    'file_name': filename,
                },
            )
            return True
