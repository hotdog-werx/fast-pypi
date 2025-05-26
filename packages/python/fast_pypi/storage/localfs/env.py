import os
from pathlib import Path

from pydantic import BaseModel


class LocalFSEnvConfig(BaseModel):
    """Configuration for the local file system storage environment."""

    root_path: Path

    @classmethod
    def from_env(cls) -> 'LocalFSEnvConfig':
        """Create a LocalFSEnvConfig instance from environment variables."""
        return LocalFSEnvConfig.model_validate(
            {
                'root_path': os.getenv('FAST_PYPI_LOCALFS_ROOT_PATH'),
            }
        )
