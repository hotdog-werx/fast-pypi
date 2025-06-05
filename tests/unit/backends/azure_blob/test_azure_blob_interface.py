import hashlib

import pytest
from azure.storage.blob.aio import ContainerClient
from testcontainers.azurite import AzuriteContainer  # pyright: ignore[reportMissingTypeStubs]

from fast_pypi.backend.azure_blob.interface import AzureBlobBackend


@pytest.mark.asyncio
async def test_azure_blob_get_file_contents_missing_sha256(
    azurite_container: AzuriteContainer,
    azure_blob_backend: AzureBlobBackend,
):
    """Test the case where the file exists but the SHA256 digest metadata is missing."""
    # Test data
    project = 'testproj'
    version = '0.1.0'
    filename = 'example-0.1.0-py3-none-any.whl'
    content = b'fake wheel content'
    expected_sha256 = hashlib.sha256(content).hexdigest()

    _, container_name, base_path = azure_blob_backend.config.parse_destination_path()

    # Upload file directly to blob storage without SHA256 metadata
    async with ContainerClient.from_connection_string(
        conn_str=azurite_container.get_connection_string(),
        container_name=container_name,
    ) as container_client:
        blob_name = f'{base_path}{project}/{version}/{filename}'
        blob_client = container_client.get_blob_client(blob_name)
        _ = await blob_client.upload_blob(
            data=content,
            overwrite=True,
            metadata={},  # Explicitly empty metadata
        )

        # First get_file_contents should compute and store SHA256
        fc1 = await azure_blob_backend.get_file_contents(project, version, filename)
        assert fc1 is not None
        assert fc1.content == content
        assert fc1.sha256_digest == expected_sha256

        # Second get_file_contents should find stored SHA256
        fc2 = await azure_blob_backend.get_file_contents(project, version, filename)
        assert fc2 is not None
        assert fc2.content == content
        assert fc2.sha256_digest == expected_sha256

        # Verify metadata was actually stored
        props = await blob_client.get_blob_properties()
        assert props.metadata.get('sha256') == expected_sha256
