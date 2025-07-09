import hashlib

import aiofiles
import pytest

from fast_pypi.backends.localfs.interface import LocalFSBackend


@pytest.mark.asyncio
async def test_localfs_get_file_contents_missing_sha256(
    localfs_backend: LocalFSBackend,
):
    """Test the case where the file exists but the SHA256 file is missing."""
    # Test data
    project = 'testproj'
    version = '0.1.0'
    filename = 'example-0.1.0-py3-none-any.whl'
    content = b'fake wheel content'
    expected_sha256 = hashlib.sha256(content).hexdigest()

    # Create project version directory
    project_version_path = localfs_backend.config.root_path / project / version
    project_version_path.mkdir(parents=True, exist_ok=True)

    # Create wheel file directly without SHA256 file
    wheel_path = project_version_path / filename
    async with aiofiles.open(str(wheel_path), 'wb') as f:
        _ = await f.write(content)

    # First get_file_contents should compute and create SHA256 file
    fc1 = await localfs_backend.get_file_contents(project, version, filename)
    assert fc1 is not None
    assert fc1.content == content
    assert fc1.sha256_digest == expected_sha256

    # Second get_file_contents should read existing SHA256 file
    fc2 = await localfs_backend.get_file_contents(project, version, filename)
    assert fc2 is not None
    assert fc2.content == content
    assert fc2.sha256_digest == expected_sha256

    # Verify SHA256 file was actually created and contains correct hash
    sha256_path = project_version_path / f'{filename}.sha256'
    assert sha256_path.exists()
    async with aiofiles.open(str(sha256_path), 'rb') as f:
        stored_sha256 = (await f.read()).decode('utf-8').strip()
        assert stored_sha256 == expected_sha256


@pytest.mark.asyncio
async def test_list_files_for_project_os_error(localfs_backend: LocalFSBackend):
    """Test list_files_for_project handles OS errors gracefully."""
    # Create a project directory
    project_path = localfs_backend.config.root_path / 'test-project'
    project_path.mkdir(parents=True, exist_ok=True)

    # Create a file in the project dir that isn't a directory - it should be
    # ignored by the scandir logic
    test_file = project_path / 'test-file.whl'
    _ = test_file.write_text('dummy content')

    result = await localfs_backend.list_files_for_project('test-project')

    # Should return empty list when OS error occurs
    assert result == []
