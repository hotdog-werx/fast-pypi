from typing import TYPE_CHECKING, cast

import pytest

from fast_pypi.backend import ProjectFileExistsError
from tests.helpers import UploadTestFile

if TYPE_CHECKING:
    from fast_pypi.backend import AbstractBackendInterface


@pytest.mark.parametrize(
    'backend_fixture',
    [
        'localfs_backend',
        'azure_blob_backend',
    ],
)
class TestBackendE2E:
    """Test class for PyPI backend implementations."""

    @pytest.mark.asyncio
    async def test_backend_e2e(
        self,
        backend_fixture: str,
        request: pytest.FixtureRequest,
    ) -> None:
        """Test the complete upload/list/download workflow for a backend.

        Args:
            backend_fixture: Name of the backend fixture to use
            request: The pytest request object
        """
        # Get the backend fixture
        backend = cast(
            'AbstractBackendInterface',
            request.getfixturevalue(backend_fixture),
        )

        upload_files = [
            UploadTestFile(
                project_name='testproj',
                version='0.1.0',
                content=b'fake wheel content',
            ),
            UploadTestFile(
                project_name='testproj',
                version='0.2.0a1',
                content=b'another fake wheel content',
            ),
            UploadTestFile(
                project_name='anotherproj',
                version='1.0.0',
                content=b'yet another fake wheel content',
            ),
        ]

        # Upload the files
        for upload_file in upload_files:
            await backend.upload_file(
                project_name=upload_file.project_name,
                version=upload_file.version,
                filename=upload_file.wheel_filename,
                file_content=upload_file.content,
                sha256_digest=upload_file.sha256_digest,
            )

        # List projects
        projects = await backend.list_projects()
        assert projects == [
            'anotherproj',
            'testproj',
        ]

        # List files for project
        files = await backend.list_files_for_project('testproj')
        assert files == [
            ('0.1.0', 'testproj-0.1.0-py3-none-any.whl'),
            ('0.2.0a1', 'testproj-0.2.0a1-py3-none-any.whl'),
        ]

        # Get file contents and sha256
        fc = await backend.get_file_contents(
            project_name='testproj',
            version='0.1.0',
            filename='testproj-0.1.0-py3-none-any.whl',
        )
        assert fc is not None
        assert fc.content == upload_files[0].content
        assert fc.sha256_digest == upload_files[0].sha256_digest

    @pytest.mark.asyncio
    async def test_backend_list_files_nonexistent_project(
        self,
        backend_fixture: str,
        request: pytest.FixtureRequest,
    ) -> None:
        """Test listing files for a project that does not exist in the backend.

        Args:
            backend_fixture: Name of the backend fixture to use
            request: The pytest request object
        """
        # Get the backend fixture
        backend = cast(
            'AbstractBackendInterface',
            request.getfixturevalue(backend_fixture),
        )

        # Attempt to list files for a nonexistent project
        assert not await backend.list_files_for_project('nonexistentproj')

    @pytest.mark.asyncio
    async def test_backend_get_nonexistent_file(
        self,
        backend_fixture: str,
        request: pytest.FixtureRequest,
    ) -> None:
        """Test getting a file that does not exist in the backend.

        Args:
            backend_fixture: Name of the backend fixture to use
            request: The pytest request object
        """
        # Get the backend fixture
        backend = cast(
            'AbstractBackendInterface',
            request.getfixturevalue(backend_fixture),
        )

        # Attempt to get a file that does not exist
        fc = await backend.get_file_contents(
            project_name='nonexistentproj',
            version='0.1.0',
            filename='nonexistentfile.whl',
        )
        assert fc is None

    @pytest.mark.asyncio
    @pytest.mark.parametrize('allow_overwrite', [True, False])
    async def test_backend_upload_existing_file(
        self,
        backend_fixture: str,
        request: pytest.FixtureRequest,
        *,
        allow_overwrite: bool,
    ) -> None:
        """Test uploading a file that already exists in the backend.

        If allow_overwrite is True, the file should be overwritten.
        If allow_overwrite is False, a ProjectFileExistsError should be raised.

        Args:
            backend_fixture: Name of the backend fixture to use
            request: The pytest request object
            allow_overwrite: Whether to allow overwriting existing files
        """
        # Get the backend fixture
        backend = cast(
            'AbstractBackendInterface',
            request.getfixturevalue(backend_fixture),
        )

        backend.general_config.allow_overwrite = allow_overwrite

        upload_file = UploadTestFile(
            project_name='testproj',
            version='0.1.0',
            content=b'new fake wheel content',
        )

        # Upload the file
        await backend.upload_file(
            project_name=upload_file.project_name,
            version=upload_file.version,
            filename=upload_file.wheel_filename,
            file_content=upload_file.content,
            sha256_digest=upload_file.sha256_digest,
        )

        # Verify the file was overwritten
        fc = await backend.get_file_contents(
            project_name=upload_file.project_name,
            version=upload_file.version,
            filename=upload_file.wheel_filename,
        )
        assert fc is not None
        assert fc.content == upload_file.content
        assert fc.sha256_digest == upload_file.sha256_digest

        # Attempt to upload the same file again
        if allow_overwrite:
            await backend.upload_file(
                project_name=upload_file.project_name,
                version=upload_file.version,
                filename=upload_file.wheel_filename,
                file_content=upload_file.content,
                sha256_digest=upload_file.sha256_digest,
            )
        else:
            with pytest.raises(ProjectFileExistsError):
                await backend.upload_file(
                    project_name=upload_file.project_name,
                    version=upload_file.version,
                    filename=upload_file.wheel_filename,
                    file_content=upload_file.content,
                    sha256_digest=upload_file.sha256_digest,
                )

    @pytest.mark.asyncio
    async def test_backend_delete_project_version(
        self,
        backend_fixture: str,
        request: pytest.FixtureRequest,
    ) -> None:
        """Test deleting a project version from the backend.

        Args:
            backend_fixture: Name of the backend fixture to use
            request: The pytest request object
        """
        # Get the backend fixture
        backend = cast(
            'AbstractBackendInterface',
            request.getfixturevalue(backend_fixture),
        )

        upload_file = UploadTestFile(
            project_name='testproj',
            version='0.1.0',
            content=b'fake wheel content',
        )

        # Upload the file
        await backend.upload_file(
            project_name=upload_file.project_name,
            version=upload_file.version,
            filename=upload_file.wheel_filename,
            file_content=upload_file.content,
            sha256_digest=upload_file.sha256_digest,
        )

        # Check the file exists
        assert (
            await backend.get_file_contents(
                project_name=upload_file.project_name,
                version=upload_file.version,
                filename=upload_file.wheel_filename,
            )
            is not None
        )

        # Delete the project version
        deleted = await backend.delete_project_version(
            project_name=upload_file.project_name,
            version=upload_file.version,
        )
        assert deleted is True

        # Verify the file no longer exists
        fc = await backend.get_file_contents(
            project_name=upload_file.project_name,
            version=upload_file.version,
            filename=upload_file.wheel_filename,
        )
        assert fc is None

        # Deleting the version again should return False
        assert (
            await backend.delete_project_version(
                project_name=upload_file.project_name,
                version=upload_file.version,
            )
            is False
        )

    @pytest.mark.asyncio
    async def test_backend_delete_project_version_file(
        self,
        backend_fixture: str,
        request: pytest.FixtureRequest,
    ) -> None:
        """Test deleting a specific file from a project version in the backend.

        Args:
            backend_fixture: Name of the backend fixture to use
            request: The pytest request object
        """
        # Get the backend fixture
        backend = cast(
            'AbstractBackendInterface',
            request.getfixturevalue(backend_fixture),
        )

        upload_file = UploadTestFile(
            project_name='testproj',
            version='0.1.0',
            content=b'fake wheel content',
        )

        # Upload the file
        await backend.upload_file(
            project_name=upload_file.project_name,
            version=upload_file.version,
            filename=upload_file.wheel_filename,
            file_content=upload_file.content,
            sha256_digest=upload_file.sha256_digest,
        )

        # Check the file exists
        assert (
            await backend.get_file_contents(
                project_name=upload_file.project_name,
                version=upload_file.version,
                filename=upload_file.wheel_filename,
            )
            is not None
        )

        # Delete the specific file
        deleted = await backend.delete_project_version_file(
            project_name=upload_file.project_name,
            version=upload_file.version,
            filename=upload_file.wheel_filename,
        )
        assert deleted is True

        # Verify the file no longer exists
        fc = await backend.get_file_contents(
            project_name=upload_file.project_name,
            version=upload_file.version,
            filename=upload_file.wheel_filename,
        )
        assert fc is None

        # Deleting the file again should return False
        assert (
            await backend.delete_project_version_file(
                project_name=upload_file.project_name,
                version=upload_file.version,
                filename=upload_file.wheel_filename,
            )
            is False
        )

    @pytest.mark.asyncio
    async def test_backend_handle_missing_sha256(
        self,
        backend_fixture: str,
        request: pytest.FixtureRequest,
    ) -> None:
        """Test handling of missing SHA256 digest file in the backend.

        Args:
            backend_fixture: Name of the backend fixture to use
            request: The pytest request object
        """
        # Get the backend fixture
        backend = cast(
            'AbstractBackendInterface',
            request.getfixturevalue(backend_fixture),
        )

        upload_file = UploadTestFile(
            project_name='testproj',
            version='0.1.0',
            content=b'fake wheel content',
        )

        # Upload the file
        await backend.upload_file(
            project_name=upload_file.project_name,
            version=upload_file.version,
            filename=upload_file.wheel_filename,
            file_content=upload_file.content,
            sha256_digest=None,
        )

        # Verify the file was uploaded and SHA256 was calculated
        fc = await backend.get_file_contents(
            project_name=upload_file.project_name,
            version=upload_file.version,
            filename=upload_file.wheel_filename,
        )
        assert fc is not None
        assert fc.content == upload_file.content
        assert fc.sha256_digest == upload_file.sha256_digest
