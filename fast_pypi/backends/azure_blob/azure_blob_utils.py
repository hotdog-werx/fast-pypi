from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from azure.identity.aio import DefaultAzureCredential, ManagedIdentityCredential
from azure.storage.blob.aio import ContainerClient

from .config import AzureBlobConfig


@asynccontextmanager
async def azure_blob_container_client(
    config: AzureBlobConfig,
) -> AsyncIterator[tuple[ContainerClient, str]]:
    """Get the Azure Blob Container Client."""
    account_url, container_name, base_path = config.parse_destination_path()
    if config.connection_string:
        async with ContainerClient.from_connection_string(
            conn_str=config.connection_string.get_secret_value(),
            container_name=container_name,
        ) as client:
            yield client, base_path
            return

    connection_method_map = {
        'default': DefaultAzureCredential(),
        'managed_identity': ManagedIdentityCredential(),
    }
    async with (
        connection_method_map[config.connection_method] as credential,
        ContainerClient(
            account_url=account_url,
            container_name=container_name,
            credential=credential,
        ) as client,
    ):
        yield (client, base_path)
