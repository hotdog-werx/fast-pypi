import tempfile
from collections.abc import Iterator
from pathlib import Path

import pytest
from azure.storage.blob import ContainerClient
from pydantic import SecretStr
from testcontainers.azurite import AzuriteContainer  # pyright: ignore[reportMissingTypeStubs]

from fast_pypi.backend.azure_blob.env import AzureBlobConfig
from fast_pypi.backend.azure_blob.interface import AzureBlobBackend
from fast_pypi.backend.localfs.env import LocalFSConfig
from fast_pypi.backend.localfs.interface import LocalFSBackend
from fast_pypi.env import FastPypiConfig


@pytest.fixture
def localfs_backend() -> Iterator[LocalFSBackend]:
    """Fixture to set up a local file system backend for testing."""
    with tempfile.TemporaryDirectory() as temp_dir:
        localfs_path = Path(temp_dir) / 'fast_pypi' / 'localfs-tests'
        local_fs_backend = LocalFSBackend(
            config=LocalFSConfig(
                root_path=localfs_path,
            ),
            general_config=FastPypiConfig(
                allow_overwrite=False,
                backend='localfs',
            ),
        )

        yield local_fs_backend


@pytest.fixture(scope='session')
def azure_blob_backend() -> Iterator[AzureBlobBackend]:
    """Fixture to set up a azure blob backend for testing."""
    container_name = 'blobbackendtest'
    base_path = '/fast_pypi/azureblob_tests/'

    with AzuriteContainer() as azurite:
        azurite_url = f'http://{azurite.get_container_host_ip()}:{azurite.get_exposed_port(10000)}'

        _ = ContainerClient.from_connection_string(
            conn_str=azurite.get_connection_string(),
            container_name=container_name,
        ).create_container()

        azure_blob_backend = AzureBlobBackend(
            config=AzureBlobConfig(
                destination_path=f'{azurite_url}/{container_name}{base_path}',
                connection_string=SecretStr(azurite.get_connection_string()),
            ),
            general_config=FastPypiConfig(
                allow_overwrite=False,
                backend='azure_blob',
            ),
        )

        yield azure_blob_backend
