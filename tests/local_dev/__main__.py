import os
import pprint as pp
import tempfile

import uvicorn
from azure.storage.blob import ContainerClient
from fastapi import FastAPI
from testcontainers.azurite import AzuriteContainer  # pyright: ignore[reportMissingTypeStubs]

from fast_pypi.pypi.router import pep503_router

app = FastAPI()
app.include_router(pep503_router, prefix='/hot/dog', tags=['hotdog'])


def run_with_localfs_backend() -> None:
    os.environ['FAST_PYPI_BACKEND'] = 'localfs'
    with tempfile.TemporaryDirectory() as temp_dir:
        pp.pp(f'Setting FAST_PYPI_LOCALFS_ROOT_PATH to {temp_dir}/hot/dog/storage')
        os.environ['FAST_PYPI_LOCALFS_ROOT_PATH'] = f'{temp_dir}/hot/dog/storage'
        uvicorn.run(
            app,
            host='0.0.0.0',  # noqa: S104
        )


def run_with_azure_backend() -> None:
    os.environ['FAST_PYPI_BACKEND'] = 'azure_blob'
    with AzuriteContainer() as azurite:
        env_settings = {
            'FAST_PYPI_AZURE_BLOB_DESTINATION_PATH': f'http://{azurite.get_container_host_ip()}:{azurite.get_exposed_port(10000)}/hotdogcontainer/hot/dog/storage/',
            'FAST_PYPI_AZURE_BLOB_CONNECTION_STRING': azurite.get_connection_string(),
        }

        _ = ContainerClient.from_connection_string(
            conn_str=env_settings['FAST_PYPI_AZURE_BLOB_CONNECTION_STRING'],
            container_name='hotdogcontainer',
        ).create_container()

        for key, value in env_settings.items():
            os.environ[key] = value
            pp.pp(f'Setting {key} to {value}')

        uvicorn.run(
            app,
            host='0.0.0.0',  # noqa: S104
        )


if __name__ == '__main__':
    run_with_azure_backend()
