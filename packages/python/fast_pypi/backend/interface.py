from abc import ABC, abstractmethod
from collections.abc import Sequence
from dataclasses import dataclass


class AbstractBackendInterface(ABC):
    """Abstract base class for backend interfaces.

    This class defines the interface for backend storage operations, such as listing projects,
    listing files for a project, getting file contents, and saving files.

    Attributes:
        allow_overwrite: Whether to allow overwriting existing files.
    """

    allow_overwrite: bool

    def __init__(self, *, allow_overwrite: bool = False) -> None:
        """Initialize the backend interface.

        Args:
            allow_overwrite: Whether to allow overwriting existing files.
        """
        self.allow_overwrite = allow_overwrite

    @abstractmethod
    async def list_projects(self) -> Sequence[str]:
        """List all projects in the backend.

        Returns:
            A sequence of project names.
        """
        ...

    @abstractmethod
    async def list_files_for_project(self, project_name: str) -> Sequence[str]:
        """List all files for a given project.

        Args:
            project_name: The name of the project.

        Returns:
            A sequence of filenames for the specified project.
        """
        ...

    @abstractmethod
    async def get_file_contents(self, project_name: str, filename: str) -> 'FileContents | None':
        """Get the contents of a file for a specific project.

        Args:
            project_name: The name of the project.
            filename: The name of the file.

        Returns:
            An instance of FileContents containing the file's content and its SHA256 digest.
        """
        ...

    @abstractmethod
    async def save_file(
        self,
        project_name: str,
        filename: str,
        file_content: bytes,
        sha256_digest: str,
    ) -> None:
        """Save a file for a specific project.

        Args:
            project_name: The name of the project.
            filename: The name of the file to save.
            file_content: The content of the file as bytes.
            sha256_digest: The SHA256 digest of the file content.

        Raises:
            ProjectFileExistsError: If the file already exists and overwriting is not allowed.
        """
        ...


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
