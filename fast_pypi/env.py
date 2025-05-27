import os
from typing import Literal

from pydantic import BaseModel


class FastPypiConfig(BaseModel):
    """Configuration for the local file system storage environment."""

    allow_overwrite: bool
    backend: Literal['localfs', 'azure_blob']

    @classmethod
    def from_env(cls) -> 'FastPypiConfig':
        """Create a LocalFSConfig instance from environment variables."""
        return FastPypiConfig.model_validate(
            {
                'allow_overwrite': os.getenv('FAST_PYPI_ALLOW_OVERWRITE', 'false').lower() == 'true',
                'backend': os.getenv('FAST_PYPI_BACKEND', 'localfs'),
            }
        )
