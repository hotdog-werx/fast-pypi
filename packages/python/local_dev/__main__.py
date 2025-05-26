import os
import tempfile

import uvicorn
from azure.core.utils import parse_connection_string
from fastapi import FastAPI
from testcontainers.azurite import AzuriteContainer  # pyright: ignore[reportMissingTypeStubs]

from fast_pypi.router import pep503_router

app = FastAPI()
app.include_router(pep503_router, prefix='/hot/dog', tags=['hotdog'])


if __name__ == '__main__':
    with AzuriteContainer() as azurite, tempfile.TemporaryDirectory() as temp_dir:
        print(f'Azurite is running at {azurite.get_connection_string()}')
        print('parse', parse_connection_string(azurite.get_connection_string()))
        print(f'Setting FAST_PYPI_LOCALFS_ROOT_PATH to {temp_dir}')
        os.environ['FAST_PYPI_LOCALFS_ROOT_PATH'] = temp_dir
        uvicorn.run(
            app,
            host='0.0.0.0',  # noqa: S104
        )
