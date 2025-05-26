import os
from typing import Literal

from pydantic import BaseModel

from fast_pypi.storage import AbstractStorageInterface


class FastPypiEnvConfig(BaseModel):
    """Configuration for the local file system storage environment."""

    allow_overwrite: bool
    backend: Literal['localfs']

    @classmethod
    def from_env(cls) -> 'FastPypiEnvConfig':
        """Create a LocalFSEnvConfig instance from environment variables."""
        return FastPypiEnvConfig.model_validate(
            {
                'allow_overwrite': os.getenv('FAST_PYPI_ALLOW_OVERWRITE', 'false').lower() == 'true',
                'backend': os.getenv('FAST_PYPI_BACKEND', 'localfs'),
            }
        )

    def get_backend(self) -> AbstractStorageInterface:
        """Get the storage backend based on the configuration."""
        if self.backend == 'localfs':
            from fast_pypi.storage.localfs import LocalFSEnvConfig, LocalFSInterface

            local_fs_env = LocalFSEnvConfig.from_env()

            return LocalFSInterface(
                root_path=local_fs_env.root_path,
                allow_overwrite=self.allow_overwrite,
            )

        msg = f"Backend '{self.backend}' is not implemented."
        raise NotImplementedError(msg)
