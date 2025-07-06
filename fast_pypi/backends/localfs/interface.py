import hashlib
from collections.abc import Sequence

import aiofiles
import aioshutil
from aiofiles import os as aiofiles_os
from typing_extensions import override

from fast_pypi.backends import AbstractBackendInterface, FileContents, ProjectFileExistsError
from fast_pypi.config import FastPypiConfig
from fast_pypi.logger import logger
from fast_pypi.pypi import pypi_normalize

from .config import LocalFSConfig


class LocalFSBackend(AbstractBackendInterface):
    """Interface for the local file system backend."""

    config: LocalFSConfig

    def __init__(self, config: LocalFSConfig, general_config: FastPypiConfig) -> None:
        self.config = config
        super().__init__(general_config=general_config)

    @override
    async def list_projects(self) -> Sequence[str]:
        """List all projects in the local file system.

        Returns:
            A sequence of project names.
        """
        projects: list[str] = []
        for project in await aiofiles_os.listdir(self.config.root_path):
            project_path = self.config.root_path / project
            if await aiofiles_os.path.isdir(project_path) and not project.startswith('.'):
                projects.append(project)
        return sorted(projects)

    @override
    async def list_project_versions(self, project_name: str) -> Sequence[str]:
        """Get the available versions of a project in the local file system.

        Args:
            project_name: The name of the project.

        Returns:
            A sequence of version strings for the specified project.
        """
        project_path = self.config.root_path / pypi_normalize(project_name)
        if not await aiofiles_os.path.exists(project_path):
            logger.warning(
                'list_project_versions_not_found',
                extra={
                    'project_name': project_name,
                    'project_path': str(project_path),
                },
            )
            return []

        version_names = [
            d
            for d in await aiofiles_os.listdir(project_path)
            if await aiofiles_os.path.isdir(project_path / d) and not d.startswith('.')
        ]
        return sorted(version_names)

    @override
    async def list_files_for_project(
        self,
        project_name: str,
    ) -> Sequence[tuple[str, str]]:
        """List all files for a given project in the local file system.

        Args:
            project_name: The name of the project.

        Returns:
            A sequence of tuples of (version, filename) for the specified project.
        """
        project_path = self.config.root_path / pypi_normalize(project_name)
        files: list[tuple[str, str]] = []

        if not await aiofiles_os.path.exists(project_path):
            logger.warning(
                'list_files_for_project_not_found',
                extra={
                    'project_name': project_name,
                    'project_path': str(project_path),
                },
            )
            return []

        version_names = [
            d
            for d in await aiofiles_os.listdir(project_path)
            if await aiofiles_os.path.isdir(project_path / d) and not d.startswith('.')
        ]

        for version in version_names:
            version_path = project_path / version
            file_names = [
                f
                for f in await aiofiles_os.listdir(version_path)
                if (
                    await aiofiles_os.path.isfile(version_path / f)
                    and not f.startswith('.')
                    and not f.endswith('.sha256')
                )
            ]
            files.extend((version, file_name) for file_name in file_names)

        return sorted(files)

    @override
    async def get_file_contents(
        self,
        project_name: str,
        version: str,
        filename: str,
    ) -> FileContents | None:
        """Get the contents of a file from the local file system.

        Args:
            project_name: The name of the project.
            version: The version of the project.
            filename: The name of the file to retrieve.

        Returns:
            A FileContents object containing the file's contents and SHA256 digest, or None if the file does not exist.
        """
        project_path = self.config.root_path / pypi_normalize(project_name) / version
        file_path = project_path / filename
        sha256_path = project_path / f'{filename}.sha256'

        if not await aiofiles_os.path.exists(file_path):
            logger.warning(
                'get_file_contents_file_not_found',
                extra={
                    'project_name': project_name,
                    'file_name': filename,
                    'file_path': str(file_path),
                },
            )
            return None

        async with aiofiles.open(file_path, mode='rb') as f:
            content = await f.read()

        # Check if the SHA256 digest file exists
        if await aiofiles_os.path.exists(sha256_path):
            # Read the SHA256 digest from the file
            async with aiofiles.open(sha256_path, 'rb') as f:
                sha256_digest = (await f.read()).decode('utf-8').strip()
        else:
            logger.warning(
                'sha256_digest_file_does_not_exist',
                extra={
                    'project_name': project_name,
                    'file_name': filename,
                    'sha256_path': str(sha256_path),
                },
            )

            # Calculate the SHA256 digest if the file does not exist and
            # save it for future use
            sha256_digest = hashlib.sha256(content).hexdigest()
            async with aiofiles.open(sha256_path, 'wb') as f:
                _ = await f.write(sha256_digest.encode('utf-8'))

        return FileContents(
            filename=filename,
            content=content,
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
        """Upload a file to the local file system for a specific project.

        Args:
            project_name: The name of the project.
            version: The version of the project
            filename: The name of the file to save.
            file_content: The content of the file to save.
            sha256_digest: The SHA256 digest of the file content.
        """
        project_version_path = self.config.root_path / pypi_normalize(project_name) / version
        await aiofiles_os.makedirs(project_version_path, exist_ok=True)

        file_path = project_version_path / filename
        if not self.general_config.allow_overwrite and await aiofiles_os.path.exists(file_path):
            logger.error(
                'file_already_exists',
                extra={
                    'project_name': project_name,
                    'file_name': filename,
                    'file_path': str(file_path),
                },
            )
            raise ProjectFileExistsError(
                filename=filename,
                project_name=project_name,
            )

        async with aiofiles.open(project_version_path / filename, 'wb') as f:
            _ = await f.write(file_content)

        set_sha256_digest = sha256_digest or hashlib.sha256(file_content).hexdigest()
        async with aiofiles.open(project_version_path / f'{filename}.sha256', 'wb') as f:
            _ = await f.write(set_sha256_digest.encode('utf-8'))

    @override
    async def delete_project_version(
        self,
        project_name: str,
        version: str,
    ) -> bool:
        """Delete a specific project version from the local file system.

        Args:
            project_name: The name of the project.
            version: The version of the project to delete.

        Returns:
            bool: True if the version was successfully deleted, False otherwise.
        """
        project_path = self.config.root_path / pypi_normalize(project_name) / version

        if not await aiofiles_os.path.exists(project_path):
            logger.warning(
                'delete_project_version_not_found',
                extra={
                    'project_name': project_name,
                    'version': version,
                    'project_path': str(project_path),
                },
            )
            return False

        await aioshutil.rmtree(project_path, ignore_errors=True)
        logger.info(
            'project_version_deleted',
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
        """Delete a specific file for a project version from the local file system.

        Args:
            project_name: The name of the project.
            version: The version of the project.
            filename: The name of the file to delete.

        Returns:
            bool: True if the file was deleted, False if it did not exist.
        """
        project_path = self.config.root_path / pypi_normalize(project_name) / version
        file_path = project_path / filename
        sha256_path = project_path / f'{filename}.sha256'

        if not await aiofiles_os.path.exists(file_path):
            logger.warning(
                'delete_project_version_file_not_found',
                extra={
                    'project_name': project_name,
                    'version': version,
                    'file_name': filename,
                    'file_path': str(file_path),
                },
            )
            return False

        await aiofiles_os.remove(file_path)
        await aiofiles_os.remove(sha256_path)
        logger.info(
            'project_version_file_deleted',
            extra={
                'project_name': project_name,
                'version': version,
                'file_name': filename,
            },
        )
        return True
