from unittest.mock import AsyncMock

from fastapi import status
from fastapi.testclient import TestClient
from pytest_mock import MockerFixture

from fast_pypi.pypi.package_rbac import ProjectRBACDecisionInput


def test_list_all_projects(
    fast_pypi_testclient: TestClient,
    check_rbac_mock: AsyncMock,
    mocker: MockerFixture,
) -> None:
    """Test listing all projects."""
    # Mock the backend to return a list of projects
    mock_backend = mocker.patch('fast_pypi.pypi.router.get_backend_from_env')
    mock_backend.return_value.list_projects = mocker.AsyncMock(
        return_value=['project1', 'project2', 'project3'],
    )

    response = fast_pypi_testclient.get('/fast-pypi/projects/')

    assert response.status_code == status.HTTP_200_OK
    assert response.json() == ['project1', 'project2', 'project3']

    # Verify RBAC check
    check_rbac_mock.assert_awaited_once_with(
        rbac_input=ProjectRBACDecisionInput(
            operation_type='read',
            project_name=None,
            request=mocker.ANY,
        ),
    )


def test_list_project_versions(
    fast_pypi_testclient: TestClient,
    check_rbac_mock: AsyncMock,
    mocker: MockerFixture,
) -> None:
    """Test listing versions for a specific project."""
    # Mock the backend to return list of versions
    mock_backend = mocker.patch('fast_pypi.pypi.router.get_backend_from_env')
    mock_backend.return_value.list_project_versions = mocker.AsyncMock(
        return_value=['1.0.0', '2.0.0'],
    )

    response = fast_pypi_testclient.get('/fast-pypi/projects/project1/versions/')

    assert response.status_code == status.HTTP_200_OK
    # The response should be a dict with versions list
    assert response.json() == ['1.0.0', '2.0.0']

    # Verify RBAC check
    check_rbac_mock.assert_awaited_once_with(
        rbac_input=ProjectRBACDecisionInput(
            operation_type='read',
            project_name='project1',
            request=mocker.ANY,
        ),
    )


def test_list_project_versions_not_found(
    fast_pypi_testclient: TestClient,
    check_rbac_mock: AsyncMock,
    mocker: MockerFixture,
) -> None:
    """Test listing versions for a non-existent project."""
    # Mock the backend to return empty list (project not found)
    mock_backend = mocker.patch('fast_pypi.pypi.router.get_backend_from_env')
    mock_backend.return_value.list_project_versions = mocker.AsyncMock(return_value=[])

    response = fast_pypi_testclient.get('/fast-pypi/projects/nonexistent/versions/')

    assert response.status_code == status.HTTP_404_NOT_FOUND
    assert response.json() == {'detail': 'Project nonexistent not found.'}

    # Verify RBAC check still happens even for non-existent projects
    check_rbac_mock.assert_awaited_once_with(
        rbac_input=ProjectRBACDecisionInput(
            operation_type='read',
            project_name='nonexistent',
            request=mocker.ANY,
        ),
    )
