import tempfile

import pytest

from fast_pypi.backends.azure_blob.interface import AzureBlobBackend
from fast_pypi.backends.localfs.interface import LocalFSBackend
from fast_pypi.get_backend import get_backend_from_env


def test_get_backend_default_is_localfs(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Test that LocalFSBackend is used by default."""
    with tempfile.TemporaryDirectory() as temp_dir:
        monkeypatch.setenv('FAST_PYPI_LOCALFS_ROOT_PATH', temp_dir)
        backend = get_backend_from_env()
        assert isinstance(backend, LocalFSBackend)


def test_get_backend_explicit_localfs(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Test that LocalFSBackend is used when explicitly configured."""
    with tempfile.TemporaryDirectory() as temp_dir:
        monkeypatch.setenv('FAST_PYPI_BACKEND', 'localfs')
        monkeypatch.setenv('FAST_PYPI_LOCALFS_ROOT_PATH', temp_dir)
        backend = get_backend_from_env()
        assert isinstance(backend, LocalFSBackend)


def test_get_backend_azure_blob(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Test that AzureBlobBackend is used when configured."""
    monkeypatch.setenv('FAST_PYPI_BACKEND', 'azure_blob')
    monkeypatch.setenv(
        'FAST_PYPI_AZURE_BLOB_DESTINATION_PATH',
        'https://test.blob.core.windows.net/test-container/pypi/',
    )
    monkeypatch.setenv(
        'FAST_PYPI_AZURE_BLOB_CONNECTION_STRING',
        'DefaultEndpointsProtocol=https;AccountName=test;AccountKey=key==;EndpointSuffix=core.windows.net',
    )
    backend = get_backend_from_env()
    assert isinstance(backend, AzureBlobBackend)
