from dataclasses import dataclass

import pytest
from pydantic import SecretStr

from fast_pypi.backends.azure_blob.config import AzureBlobConfig


@dataclass
class AzureBlobConfigFromEnvTestCase:
    env: dict[str, str]
    expected: AzureBlobConfig


@pytest.mark.parametrize(
    'test_case',
    [
        AzureBlobConfigFromEnvTestCase(
            env={
                'FAST_PYPI_AZURE_BLOB_DESTINATION_PATH': 'https://account.blob.core.windows.net/container/path/',
                'FAST_PYPI_AZURE_BLOB_CONNECTION_STRING': (
                    'DefaultEndpointsProtocol=https;AccountName=devstoreaccount1;'
                ),
                'FAST_PYPI_AZURE_BLOB_CONNECTION_METHOD': 'default',
            },
            expected=AzureBlobConfig(
                destination_path='https://account.blob.core.windows.net/container/path/',
                connection_string=SecretStr('DefaultEndpointsProtocol=https;AccountName=devstoreaccount1;'),
                connection_method='default',
            ),
        ),
        AzureBlobConfigFromEnvTestCase(
            env={
                'FAST_PYPI_AZURE_BLOB_DESTINATION_PATH': 'http://localhost:10000/devstoreaccount1/container/path/',
                'FAST_PYPI_AZURE_BLOB_CONNECTION_METHOD': 'managed_identity',
            },
            expected=AzureBlobConfig(
                destination_path='http://localhost:10000/devstoreaccount1/container/path/',
                connection_string=None,
                connection_method='managed_identity',
            ),
        ),
        # Test with default connection_method
        AzureBlobConfigFromEnvTestCase(
            env={
                'FAST_PYPI_AZURE_BLOB_DESTINATION_PATH': 'https://account.blob.core.windows.net/container/path/',
            },
            expected=AzureBlobConfig(
                destination_path='https://account.blob.core.windows.net/container/path/',
                connection_string=None,
                connection_method='default',
            ),
        ),
    ],
)
def test_azure_blob_config_from_env(test_case: AzureBlobConfigFromEnvTestCase, monkeypatch: pytest.MonkeyPatch):
    """Test AzureBlobConfig.from_env with various environment configurations.

    Args:
        test_case: The test case containing environment variables and expected config
        monkeypatch: pytest fixture for modifying environment variables
    """
    # Set up environment variables
    for key, value in test_case.env.items():
        monkeypatch.setenv(key, value)

    # Clear any variables not in test case
    for key in [
        'FAST_PYPI_AZURE_BLOB_DESTINATION_PATH',
        'FAST_PYPI_AZURE_BLOB_CONNECTION_STRING',
        'FAST_PYPI_AZURE_BLOB_CONNECTION_METHOD',
    ]:
        if key not in test_case.env:
            monkeypatch.delenv(key, raising=False)

    # Create config from environment
    config = AzureBlobConfig.from_env()

    # Assert all fields match
    assert config.destination_path == test_case.expected.destination_path
    assert config.connection_method == test_case.expected.connection_method

    # Compare connection string if present, otherwise assert both are None
    if test_case.expected.connection_string is None:
        assert config.connection_string is None
    else:
        assert config.connection_string is not None
        assert config.connection_string.get_secret_value() == test_case.expected.connection_string.get_secret_value()


def test_parse_destination_path():
    """Test parsing the destination path into account URL, container name, and base path."""
    config = AzureBlobConfig(
        destination_path='https://hotdogaccount.blob.core.windows.net/container/path/to/storage/',
        connection_string=None,
        connection_method='default',
    )
    account_url, container_name, base_path = config.parse_destination_path()

    assert account_url == 'https://hotdogaccount.blob.core.windows.net'
    assert container_name == 'container'
    assert base_path == 'path/to/storage/'
