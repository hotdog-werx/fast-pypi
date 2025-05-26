import os
from pathlib import Path

from pydantic import BaseModel


class LocalFSConfig(BaseModel):
    """Configuration for the local file system backend."""

    root_path: Path

    @classmethod
    def from_env(cls) -> 'LocalFSConfig':
        """Create a LocalFSConfig instance from environment variables."""
        return LocalFSConfig.model_validate(
            {
                'root_path': os.getenv('FAST_PYPI_LOCALFS_ROOT_PATH'),
            }
        )
