from .backends import AbstractBackendInterface
from .config import FastPypiConfig


def get_backend_from_env() -> AbstractBackendInterface:
    """Get the storage backend based on the configuration."""
    general_env = FastPypiConfig.from_env()

    if general_env.backend == 'localfs':
        from fast_pypi.backends.localfs.config import LocalFSConfig
        from fast_pypi.backends.localfs.interface import LocalFSBackend

        return LocalFSBackend(
            config=LocalFSConfig.from_env(),
            general_config=general_env,
        )
    if general_env.backend == 'azure_blob':
        from fast_pypi.backends.azure_blob.config import AzureBlobConfig
        from fast_pypi.backends.azure_blob.interface import AzureBlobBackend

        return AzureBlobBackend(
            config=AzureBlobConfig.from_env(),
            general_config=general_env,
        )

    # Not actually possible to hit this branch
    msg = f"Backend '{general_env.backend}' is not implemented."
    raise NotImplementedError(msg)
