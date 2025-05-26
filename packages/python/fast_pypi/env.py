import os
from typing import Literal

from pydantic import BaseModel

from fast_pypi.backend import AbstractBackendInterface


class FastPypiConfig(BaseModel):
    """Configuration for the local file system storage environment."""

    allow_overwrite: bool
    backend: Literal['localfs']

    @classmethod
    def from_env(cls) -> 'FastPypiConfig':
        """Create a LocalFSConfig instance from environment variables."""
        return FastPypiConfig.model_validate(
            {
                'allow_overwrite': os.getenv('FAST_PYPI_ALLOW_OVERWRITE', 'false').lower() == 'true',
                'backend': os.getenv('FAST_PYPI_BACKEND', 'localfs'),
            }
        )

    def get_backend(self) -> AbstractBackendInterface:
        """Get the storage backend based on the configuration."""
        if self.backend == 'localfs':
            from fast_pypi.backend.localfs import LocalFSBackend, LocalFSConfig

            return LocalFSBackend(
                config=LocalFSConfig.from_env(),
                allow_overwrite=self.allow_overwrite,
            )

        msg = f"Backend '{self.backend}' is not implemented."
        raise NotImplementedError(msg)
