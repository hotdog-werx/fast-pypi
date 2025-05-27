import hashlib
from dataclasses import dataclass


@dataclass
class UploadTestFile:
    """Data class representing a file to be uploaded for testing purposes."""

    project_name: str
    version: str
    content: bytes

    @property
    def wheel_filename(self) -> str:
        """Generate the wheel filename based on project name and version."""
        return f'{self.project_name}-{self.version}-py3-none-any.whl'

    @property
    def sha256_digest(self) -> str:
        """Calculate the SHA256 digest of the file content."""
        return hashlib.sha256(self.content).hexdigest()
