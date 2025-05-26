from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from azure.core.credentials import AzureNamedKeyCredential, AzureSasCredential
from azure.core.credentials_async import AsyncTokenCredential
from azure.identity.aio import DefaultAzureCredential, ManagedIdentityCredential
from azure.storage.blob._shared.base_client_async import parse_connection_str
from azure.storage.blob.aio import BlobClient, ContainerClient

from .env import AzureBlobConfig


class InvalidConnectionStringError(ValueError):
    """Raised when the connection string is invalid or missing credentials."""

    def __init__(self) -> None:
        super().__init__('Invalid connection string provided. Ensure it contains a valid credential.')


@asynccontextmanager
async def azure_credential(
    config: AzureBlobConfig,
) -> AsyncIterator[
    (
        DefaultAzureCredential
        | ManagedIdentityCredential
        | str
        | dict[str, str]
        | AzureNamedKeyCredential
        | AzureSasCredential
        | AsyncTokenCredential
    )
]:
    """Get the Azure credential to use for authentication."""
    if config.connection_string:
        _, __, credential = parse_connection_str(
            conn_str=config.connection_string.get_secret_value(),
            credential=None,
            service='blob',
        )
        if credential is None:
            raise InvalidConnectionStringError
        yield credential

    connection_method_map = {
        'default': DefaultAzureCredential(),
        'managed_identity': ManagedIdentityCredential(),
    }
    async with connection_method_map[config.connection_method] as credential:
        yield credential


@asynccontextmanager
async def azure_blob_container_client(
    config: AzureBlobConfig,
) -> AsyncIterator[tuple[ContainerClient, str]]:
    """Get the Azure Blob Container Client."""
    account_url, container_name, base_path = config.parse_destination_path()
    async with (
        azure_credential(config) as cred,
        ContainerClient(
            account_url=account_url,
            container_name=container_name,
            credential=cred,
        ) as client,
    ):
        yield client, base_path


@asynccontextmanager
async def azure_blob_client(
    config: AzureBlobConfig,
    blob_name: str,
) -> AsyncIterator[BlobClient]:
    """Get the Azure Blob Client."""
    account_url, container_name, base_path = config.parse_destination_path()
    async with (
        azure_credential(config) as cred,
        BlobClient(
            account_url=account_url,
            container_name=container_name,
            blob_name=f'{base_path}{blob_name}',
            credential=cred,
        ) as client,
    ):
        yield client
