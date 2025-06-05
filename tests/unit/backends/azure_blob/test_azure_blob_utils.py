from typing import Literal

import pytest
from pydantic import SecretStr
from pytest_mock import MockerFixture

from fast_pypi.backend.azure_blob.azure_blob_utils import (
    azure_blob_container_client,
)
from fast_pypi.backend.azure_blob.env import AzureBlobConfig


@pytest.mark.asyncio
async def test_azure_blob_container_client_connection_string(
    mocker: MockerFixture,
):
    # Arrange
    config = AzureBlobConfig(
        destination_path='https://hotdogcart.blob.core.windows.net/hotdogcontainer/path/to/storage/',
        connection_string=SecretStr('this-is-a-connection-string'),
    )

    from_conn_str_mock = mocker.patch(
        'azure.storage.blob.aio.ContainerClient.from_connection_string',
        return_value=mocker.MagicMock(),
    )

    # Act
    async with azure_blob_container_client(config=config) as (container_client, base_path):
        # Assert
        from_conn_str_mock.assert_called_once_with(
            conn_str='this-is-a-connection-string',
            container_name='hotdogcontainer',
        )
        assert container_client == from_conn_str_mock.return_value.__aenter__.return_value  # pyright: ignore[reportAny]
        assert base_path == 'path/to/storage/'


@pytest.mark.asyncio
@pytest.mark.parametrize('connection_method', ['default', 'managed_identity'])
async def test_azure_blob_container_client_credential(
    connection_method: Literal['default', 'managed_identity'],
    mocker: MockerFixture,
):
    # Arrange
    config = AzureBlobConfig(
        destination_path='https://hotdogcart.blob.core.windows.net/hotdogcontainer/path/to/storage/',
        connection_method=connection_method,
    )

    credential_class = (
        'azure.identity.aio._credentials.default.DefaultAzureCredential'
        if connection_method == 'default'
        else 'azure.identity.aio._credentials.managed_identity.ManagedIdentityCredential'
    )
    credential_aenter_mock = mocker.patch(
        f'{credential_class}.__aenter__',
        return_value=mocker.MagicMock(),
    )

    container_client_aenter_mock = mocker.patch(
        'azure.storage.blob.aio.ContainerClient.__aenter__',
        return_value=mocker.MagicMock(),
    )

    # Act
    async with azure_blob_container_client(config=config) as (container_client, base_path):
        # Assert
        credential_aenter_mock.assert_called_once()
        assert container_client == container_client_aenter_mock.return_value  # pyright: ignore[reportAny]
        assert base_path == 'path/to/storage/'
