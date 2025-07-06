from unittest.mock import AsyncMock

from fastapi import status
from fastapi.testclient import TestClient
from pytest_mock import MockerFixture

from fast_pypi.pypi.package_rbac import ProjectRBACDecisionInput


def test_delete_project_version(
    fast_pypi_testclient: TestClient,
    check_rbac_mock: AsyncMock,
    mocker: MockerFixture,
) -> None:
    """Test deleting a project version."""
    # Mock the backend to return success
    mock_backend = mocker.patch('fast_pypi.pypi.router.get_backend_from_env')
    mock_delete = mock_backend.return_value.delete_project_version = mocker.AsyncMock()
    mock_delete.side_effect = [True, False, True]

    response = fast_pypi_testclient.post(
        '/fast-pypi/projects/testproj/delete-versions/',
        json=['0.1.0', '0.2.0', '0.3.0'],
    )

    assert response.status_code == status.HTTP_200_OK
    assert response.json() == ['0.1.0', '0.3.0']

    # Verify each call individually
    assert mock_delete.await_count == 3
    await_args_list = mock_delete.await_args_list
    assert await_args_list[0] == mocker.call(project_name='testproj', version='0.1.0')
    assert await_args_list[1] == mocker.call(project_name='testproj', version='0.2.0')
    assert await_args_list[2] == mocker.call(project_name='testproj', version='0.3.0')

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

    response = fast_pypi_testclient.post('/fast-pypi/projects/testproj/delete-versions/', json=['0.1.0'])

    assert response.status_code == status.HTTP_200_OK
    assert response.json() == []

    # Verify RBAC check still happened
    check_rbac_mock.assert_awaited_once_with(
        rbac_input=ProjectRBACDecisionInput(
            operation_type='delete',
            project_name='testproj',
            request=mocker.ANY,
        ),
    )
