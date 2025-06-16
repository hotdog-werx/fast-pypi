from io import BytesIO
from unittest.mock import ANY, AsyncMock

import pytest
from fastapi import status
from fastapi.testclient import TestClient
from pytest_mock import MockerFixture

from fast_pypi.backends import ProjectFileExistsError
from fast_pypi.pypi.package_rbac import ProjectRBACDecisionInput


@pytest.fixture
def upload_form_data() -> dict[str, str]:
    """Fixture to provide test upload form data."""
    return {
        ':action': 'file_upload',
        'protocol_version': '1',
        'metadata_version': '2.1',
        'name': 'testproj',
        'version': '0.1.0',
        'filetype': 'bdist_wheel',
        'description': 'A test project',
        'description_content_type': 'text/markdown',
    }


def test_upload_project_file(
    fast_pypi_testclient: TestClient,
    check_rbac_mock: AsyncMock,
    upload_form_data: dict[str, str],
    mocker: MockerFixture,
) -> None:
    """Test uploading a project file."""
    # Mock the backend
    mock_backend = mocker.patch('fast_pypi.pypi.router.get_backend_from_env')
    mock_backend.return_value.upload_file = mocker.AsyncMock()

    files = {
        'content': (
            'testproj-0.1.0-py3-none-any.whl',
            BytesIO(b'fake wheel content'),
        ),
    }
    response = fast_pypi_testclient.post(
        '/fast-pypi/upload/',
        files=files,
        data=upload_form_data,
    )

    assert response.status_code == status.HTTP_201_CREATED

    # Verify backend call
    mock_backend.return_value.upload_file.assert_awaited_once_with(
        project_name='testproj',
        version='0.1.0',
        filename='testproj-0.1.0-py3-none-any.whl',
        file_content=ANY,  # Can't easily compare bytes objects
        sha256_digest=None,
    )

    # Verify RBAC check
    check_rbac_mock.assert_awaited_once_with(
        rbac_input=ProjectRBACDecisionInput(
            operation_type='write',
            project_name='testproj',
            request=mocker.ANY,
        ),
    )


def test_upload_project_file_exists(
    fast_pypi_testclient: TestClient,
    check_rbac_mock: AsyncMock,
    upload_form_data: dict[str, str],
    mocker: MockerFixture,
) -> None:
    """Test uploading a file that already exists."""
    # Mock the backend to raise ProjectFileExistsError
    mock_backend = mocker.patch('fast_pypi.pypi.router.get_backend_from_env')
    mock_backend.return_value.upload_file.side_effect = ProjectFileExistsError(
        filename='testproj-0.1.0-py3-none-any.whl',
        project_name='testproj',
    )

    files = {
        'content': (
            'testproj-0.1.0-py3-none-any.whl',
            BytesIO(b'fake wheel content'),
        ),
    }
    response = fast_pypi_testclient.post(
        '/fast-pypi/upload/',
        files=files,
        data=upload_form_data,
    )

    assert response.status_code == status.HTTP_409_CONFLICT
    assert response.json()['detail'] == 'File testproj-0.1.0-py3-none-any.whl for project testproj already exists.'

    # Verify RBAC check still happened
    check_rbac_mock.assert_awaited_once()


def test_delete_project_version(
    fast_pypi_testclient: TestClient,
    check_rbac_mock: AsyncMock,
    mocker: MockerFixture,
) -> None:
    """Test deleting a project version."""
    # Mock the backend to return success
    mock_backend = mocker.patch('fast_pypi.pypi.router.get_backend_from_env')
    mock_backend.return_value.delete_project_version = mocker.AsyncMock(return_value=True)

    response = fast_pypi_testclient.delete('/fast-pypi/delete/testproj/0.1.0')

    assert response.status_code == status.HTTP_204_NO_CONTENT
    assert response.content == b''  # No content for 204

    # Verify backend call
    mock_backend.return_value.delete_project_version.assert_awaited_once_with(
        project_name='testproj',
        version='0.1.0',
    )

    # Verify RBAC check
    check_rbac_mock.assert_awaited_once_with(
        rbac_input=ProjectRBACDecisionInput(
            operation_type='delete',
            project_name='testproj',
            request=mocker.ANY,
        ),
    )


def test_delete_project_version_not_found(
    fast_pypi_testclient: TestClient,
    check_rbac_mock: AsyncMock,
    mocker: MockerFixture,
) -> None:
    """Test deleting a non-existent project version."""
    # Mock the backend to return not found
    mock_backend = mocker.patch('fast_pypi.pypi.router.get_backend_from_env')
    mock_backend.return_value.delete_project_version = mocker.AsyncMock(return_value=False)

    response = fast_pypi_testclient.delete('/fast-pypi/delete/testproj/0.1.0')

    assert response.status_code == status.HTTP_404_NOT_FOUND
    assert response.json()['detail'] == 'Project testproj version 0.1.0 not found.'

    # Verify RBAC check still happened
    check_rbac_mock.assert_awaited_once_with(
        rbac_input=ProjectRBACDecisionInput(
            operation_type='delete',
            project_name='testproj',
            request=mocker.ANY,
        ),
    )
