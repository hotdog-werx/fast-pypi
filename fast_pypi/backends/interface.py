from abc import ABC, abstractmethod
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import datetime

from pydantic import BaseModel

from fast_pypi.config import FastPypiConfig


class ProjectFileInfo(BaseModel):
    """Model for project file information."""

    project_name: str
    version: str
    filename: str
    last_modified: datetime
    size: int


class AbstractBackendInterface(ABC):
    """Abstract base class for backend interfaces.

    This class defines the interface for backend storage operations, such as listing projects,
    listing files for a project, getting file contents, and saving files.

    Attributes:
        general_config: General FastPypi configuration.
    """

    general_config: FastPypiConfig

    def __init__(self, *, general_config: FastPypiConfig) -> None:
        """Initialize the backend interface.

        Args:
            general_config: General FastPypi configuration.
        """
        self.general_config = general_config

    @abstractmethod
    async def list_projects(self) -> Sequence[str]:
        """List all projects in the backend.

        Returns:
            A sequence of project names.
        """

    @abstractmethod
    async def list_project_versions(self, project_name: str) -> Sequence[str]:
        """Get the available versions of a project.

        Args:
            project_name: The name of the project.

        Returns:
            A sequence of version strings for the specified project.
        """

    @abstractmethod
    async def list_files_for_project(self, project_name: str) -> Sequence[ProjectFileInfo]:
        """List all files for a given project.

        Args:
            project_name: The name of the project.

        Returns:
            A sequence of ProjectFileInfo objects for the specified project.
        """

    @abstractmethod
    async def get_file_contents(self, project_name: str, version: str, filename: str) -> 'FileContents | None':
        """Get the contents of a file for a specific project.

        Args:
            project_name: The name of the project.
            version: The version of the project.
            filename: The name of the file.

        Returns:
            An instance of FileContents containing the file's content and its
                SHA256 digest.
        """

    @abstractmethod
    async def upload_file(
        self,
        project_name: str,
        version: str,
        filename: str,
        file_content: bytes,
        sha256_digest: str | None,
    ) -> None:
        """Upload a file for a specific project.

        Args:
            project_name: The name of the project.
            version: The version of the project.
            filename: The name of the file to save.
            file_content: The content of the file as bytes.
            sha256_digest: The SHA256 digest of the file content. If not
                provided, it will be calculated automatically.

        Raises:
            ProjectFileExistsError: If the file already exists and overwriting is not allowed.
        """

    @abstractmethod
    async def delete_project_version(
        self,
        project_name: str,
        version: str,
    ) -> bool:
        """Delete a specific project version for a project.

        Args:
            project_name: The name of the project.
            version: The version of the project to delete.

        Returns:
            bool: True if the version was successfully deleted, False
                otherwise.
        """

    @abstractmethod
    async def delete_project_version_file(
        self,
        project_name: str,
        version: str,
        filename: str,
    ) -> bool:
        """Delete a specific file for a project version.

        Args:
            project_name: The name of the project.
            version: The version of the project.
            filename: The name of the file to delete.

        Returns:
            bool: True if the file was successfully deleted, False otherwise.
        """


@dataclass(frozen=True)
class FileContents:
    """Dataclass to hold file contents and its SHA256 digest."""

    filename: str
    content: bytes
    sha256_digest: str


class ProjectFileExistsError(FileExistsError):
    """Custom exception raised when a project file already exists.

    Attributes:
        filename: The name of the file that already exists.
        project_name: The name of the project to which the file belongs.
    """

    filename: str
    project_name: str

    def __init__(self, filename: str, project_name: str) -> None:
        super().__init__(
            f'File {filename} for project {project_name} already exists.',
        )
        self.filename = filename
        self.project_name = project_name
