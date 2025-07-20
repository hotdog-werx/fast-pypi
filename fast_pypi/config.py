import os
from typing import Literal

from pydantic import BaseModel


class FastPypiConfig(BaseModel):
    """Configuration for the local file system storage environment."""

    allow_overwrite: bool
    backend: Literal['localfs', 'azure_blob']
    fallback_enabled: bool = False
    fallback_url: str = 'https://pypi.org/simple/'

    @classmethod
    def from_env(cls) -> 'FastPypiConfig':
        """Create a LocalFSConfig instance from environment variables."""
        env_dict = {
            'allow_overwrite': os.getenv('FAST_PYPI_ALLOW_OVERWRITE', 'false').lower() == 'true',
            'backend': os.getenv('FAST_PYPI_BACKEND', 'localfs'),
            'fallback_enabled': os.getenv('FAST_PYPI_FALLBACK_ENABLED', 'false').lower() == 'true',
            'fallback_url': os.getenv('FAST_PYPI_FALLBACK_URL'),
        }
        return FastPypiConfig.model_validate({key: val for key, val in env_dict.items() if val is not None})
