from datetime import UTC, datetime
from unittest.mock import AsyncMock

from fastapi import status
from fastapi.testclient import TestClient
from pytest_mock import MockerFixture

from fast_pypi.backends import FileContents
from fast_pypi.backends.interface import ProjectFileInfo
from fast_pypi.pypi.package_rbac import ProjectRBACDecisionInput


def test_get_simple_index(
    fast_pypi_testclient: TestClient,
    mocker: MockerFixture,
    check_rbac_mock: AsyncMock,
) -> None:
    # Mock the backend to return a list of project names
    mock_backend = mocker.patch('fast_pypi.pypi.router.get_backend_from_env')
    mock_backend.return_value.list_projects = mocker.AsyncMock(
        return_value=['testproj1', 'testproj2'],
    )

    response = fast_pypi_testclient.get('/fast-pypi/simple/')

    assert response.status_code == status.HTTP_200_OK

    assert '<li><a href="testproj1/">testproj1</a></li>' in response.text
    assert '<li><a href="testproj2/">testproj2</a></li>' in response.text

    check_rbac_mock.assert_awaited_once_with(
        rbac_input=ProjectRBACDecisionInput(
            operation_type='read',
            project_name=None,
            request=mocker.ANY,
        ),
    )


def test_get_project_simple_index(
    fast_pypi_testclient: TestClient,
    mocker: MockerFixture,
    check_rbac_mock: AsyncMock,
) -> None:
    version_files = [
        ('0.1.0', 'testproj1-0.1.0-py3-none-any.whl'),
        ('0.1.0', 'testproj1-0.1.0.tar.gz'),
        ('0.2.0', 'testproj1-0.2.0-py3-none-any.whl'),
        ('0.2.0', 'testproj1-0.2.0.tar.gz'),
        ('0.2.0a1', 'testproj1-0.2.0a1-py3-none-any.whl'),
        ('0.2.0a1', 'testproj1-0.2.0a1.tar.gz'),
    ]

    # Mock the backend to return a list of files for the project
    mock_backend = mocker.patch('fast_pypi.pypi.router.get_backend_from_env')
    mock_backend.return_value.list_files_for_project = mocker.AsyncMock(
        return_value=[
            ProjectFileInfo(
                project_name='testproj1',
                version=version,
                filename=filename,
                size=1234,
                last_modified=datetime(2023, 1, 1, tzinfo=UTC),
            )
            for version, filename in version_files
        ]
    )

    response = fast_pypi_testclient.get('/fast-pypi/simple/testproj1/')

    assert response.status_code == status.HTTP_200_OK

    line_template = '<a href="http://testserver/fast-pypi/artifacts/testproj1/{version}/{filename}">{filename}</a><br>'

    for version, filename in version_files:
        assert line_template.format(version=version, filename=filename) in response.text

    check_rbac_mock.assert_awaited_once_with(
        rbac_input=ProjectRBACDecisionInput(
            operation_type='read',
            project_name='testproj1',
            request=mocker.ANY,
        ),
    )


def test_get_project_simple_index_not_found(
    fast_pypi_testclient: TestClient,
    mocker: MockerFixture,
    check_rbac_mock: AsyncMock,
) -> None:
    """Test getting a project simple index that does not exist."""
    # Mock the backend to return an empty list for project files
    mock_backend = mocker.patch('fast_pypi.pypi.router.get_backend_from_env')
    mock_backend.return_value.list_files_for_project = mocker.AsyncMock(return_value=[])

    response = fast_pypi_testclient.get('/fast-pypi/simple/nonexistent-project/')

    assert response.status_code == status.HTTP_404_NOT_FOUND
    assert response.json()['detail'] == 'Project nonexistent-project not found.'

    check_rbac_mock.assert_awaited_once_with(
        rbac_input=ProjectRBACDecisionInput(
            operation_type='read',
            project_name='nonexistent-project',
            request=mocker.ANY,
        ),
    )


def test_get_project_artifact(
    fast_pypi_testclient: TestClient,
    mocker: MockerFixture,
    check_rbac_mock: AsyncMock,
) -> None:
    """Test getting a project artifact."""
    # Test data
    project = 'testproj1'
    version = '0.1.0'
    filename = 'testproj1-0.1.0-py3-none-any.whl'
    content = b'fake wheel content'
    sha256_digest = 'fake_sha256'

    # Mock the backend to return file contents
    mock_backend = mocker.patch('fast_pypi.pypi.router.get_backend_from_env')
    mock_backend.return_value.get_file_contents = mocker.AsyncMock(
        return_value=FileContents(
            filename=filename,
            content=content,
            sha256_digest=sha256_digest,
        ),
    )

    response = fast_pypi_testclient.get(f'/fast-pypi/artifacts/{project}/{version}/{filename}')

    assert response.status_code == status.HTTP_200_OK
    assert response.content == content
    assert response.headers['Content-Type'] == 'application/octet-stream'
    assert response.headers['Content-Disposition'] == f'attachment; filename="{filename}"'

    check_rbac_mock.assert_awaited_once_with(
        rbac_input=ProjectRBACDecisionInput(
            operation_type='read',
            project_name=project,
            request=mocker.ANY,
        ),
    )


def test_get_project_artifact_not_found(
    fast_pypi_testclient: TestClient,
    mocker: MockerFixture,
    check_rbac_mock: AsyncMock,
) -> None:
    """Test getting a non-existent project artifact."""
    # Test data
    project = 'testproj1'
    version = '0.1.0'
    filename = 'nonexistent.whl'

    # Mock the backend to return None for file contents
    mock_backend = mocker.patch('fast_pypi.pypi.router.get_backend_from_env')
    mock_backend.return_value.get_file_contents = mocker.AsyncMock(return_value=None)

    response = fast_pypi_testclient.get(f'/fast-pypi/artifacts/{project}/{version}/{filename}')

    assert response.status_code == status.HTTP_404_NOT_FOUND
    assert response.json()['detail'] == f'File {filename} for project {project} not found.'

    check_rbac_mock.assert_awaited_once_with(
        rbac_input=ProjectRBACDecisionInput(
            operation_type='read',
            project_name=project,
            request=mocker.ANY,
        ),
    )
