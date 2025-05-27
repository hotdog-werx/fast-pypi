import hashlib
from typing import TYPE_CHECKING, cast

import pytest

if TYPE_CHECKING:
    from fast_pypi.backend import AbstractBackendInterface


class TestBackendE2E:
    """Test class for PyPI backend implementations."""

    @pytest.mark.asyncio
    @pytest.mark.parametrize(
        'backend_fixture',
        [
            'localfs_backend',
            'azure_blob_backend',
        ],
    )
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

        # Test data
        project = 'testproj'
        version = '0.1.0'
        filename = f'{project}-{version}-py3-none-any.whl'
        content = b'fake wheel content'
        digest = hashlib.sha256(content).hexdigest()

        # Upload the file
        await backend.upload_file(
            project_name=project,
            version=version,
            filename=filename,
            file_content=content,
            sha256_digest=digest,
        )

        # List projects
        projects = await backend.list_projects()
        assert project in projects

        # List files for project
        files = await backend.list_files_for_project(project)
        assert (version, filename) in files

        # Get file contents and sha256
        fc = await backend.get_file_contents(project, version, filename)
        assert fc is not None
        assert fc.content == content
        assert fc.sha256_digest == digest
