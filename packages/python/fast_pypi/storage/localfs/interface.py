import hashlib
from collections.abc import Sequence
from logging import getLogger
from pathlib import Path

import aiofiles
from aiofiles import os as aiofiles_os
from typing_extensions import override

from fast_pypi.pypi import pypi_normalize
from fast_pypi.storage import AbstractStorageInterface, FileContents, ProjectFileExistsError

logger = getLogger(__name__)


class LocalFSInterface(AbstractStorageInterface):
    """Interface for local file system storage."""

    root_path: Path

    def __init__(self, root_path: Path, *, allow_overwrite: bool = False) -> None:
        self.root_path = root_path
        super().__init__(allow_overwrite=allow_overwrite)

    @override
    async def list_projects(self) -> Sequence[str]:
        """List all projects in the local file system.

        Returns:
            A sequence of project names.
        """
        projects: list[str] = []
        for project in await aiofiles_os.listdir(self.root_path):
            project_path = self.root_path / project
            if await aiofiles_os.path.isdir(project_path) and not project.startswith('.'):
                projects.append(project)
        return projects

    @override
    async def list_files_for_project(
        self,
        project_name: str,
    ) -> Sequence[str]:
        """List all files for a given project in the local file system.

        Args:
            project_name: The name of the project.

        Returns:
            A sequence of filenames for the specified project.
        """
        project_path = self.root_path / pypi_normalize(project_name)

        if not await aiofiles_os.path.exists(project_path):
            logger.warning(
                'list_files_for_project_not_found',
                extra={
                    'project_name': project_name,
                    'project_path': str(project_path),
                },
            )
            return []

        return [
            f.name
            for f in await aiofiles_os.scandir(project_path)
            if f.is_file() and not f.name.startswith('.') and not f.name.endswith('.sha256')
        ]

    @override
    async def get_file_contents(
        self,
        project_name: str,
        filename: str,
    ) -> FileContents | None:
        """Get the contents of a file from the local file system.

        Args:
            project_name: The name of the project.
            filename: The name of the file to retrieve.

        Returns:
            A FileContents object containing the file's contents and SHA256 digest, or None if the file does not exist.
        """
        project_path = self.root_path / pypi_normalize(project_name)
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

        async with aiofiles.open(file_path, mode='rb') as f:  # pyright: ignore[reportUnknownMemberType]
            content = await f.read()

        # Check if the SHA256 digest file exists
        if await aiofiles_os.path.exists(sha256_path):
            # Read the SHA256 digest from the file
            async with aiofiles.open(sha256_path, 'rb') as f:  # pyright: ignore[reportUnknownMemberType]
                sha256_digest = (await f.read()).decode('utf-8').strip()
        else:
            # Calculate the SHA256 digest if the file does not exist and
            # save it for future use
            sha256_digest = hashlib.sha256(content).hexdigest()
            async with aiofiles.open(sha256_path, 'wb') as f:  # pyright: ignore[reportUnknownMemberType]
                _ = await f.write(sha256_digest.encode('utf-8'))
            logger.warning(
                'sha256_digest_file_does_not_exist',
                extra={
                    'project_name': project_name,
                    'file_name': filename,
                    'sha256_path': str(sha256_path),
                },
            )

        return FileContents(
            filename=filename,
            content=content,
            sha256_digest=sha256_digest,
        )

    @override
    async def save_file(
        self,
        project_name: str,
        filename: str,
        file_content: bytes,
        sha256_digest: str,
    ) -> None:
        """Save a file to the local file system.

        Args:
            project_name: The name of the project.
            filename: The name of the file to save.
            file_content: The content of the file to save.
            sha256_digest: The SHA256 digest of the file content.
        """
        project_path = self.root_path / pypi_normalize(project_name)
        await aiofiles_os.makedirs(project_path, exist_ok=True)

        file_path = project_path / filename
        if not self.allow_overwrite and await aiofiles_os.path.exists(file_path):
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

        async with aiofiles.open(project_path / filename, 'wb') as f:  # pyright: ignore[reportUnknownMemberType]
            _ = await f.write(file_content)

        async with aiofiles.open(project_path / f'{filename}.sha256', 'wb') as f:  # pyright: ignore[reportUnknownMemberType]
            _ = await f.write(sha256_digest.encode('utf-8'))
