from collections.abc import Iterator
from dataclasses import dataclass

import pytest
from fastapi import FastAPI
from fastapi.responses import PlainTextResponse
from fastapi.testclient import TestClient
from pytest_mock import MockerFixture

from fast_pypi.pypi.package_rbac import (
    ProjectRBACDecisionInput,
    package_rbac_dependency,
    reset_project_rbac_decision_func,
    set_project_rbac_decision_func,
)


@pytest.fixture
def fast_pypi_rbac_test_app(fast_pypi_test_app: FastAPI) -> FastAPI:
    @fast_pypi_test_app.get(
        '/fast-pypi/rbac-test-read/',
        dependencies=[package_rbac_dependency('read')],
    )
    async def _rbac_test_read() -> PlainTextResponse:  # pyright: ignore[reportUnusedFunction]
        """A test endpoint to verify RBAC read access."""
        return PlainTextResponse('ok')

    @fast_pypi_test_app.post(
        '/fast-pypi/rbac-test-write/',
        dependencies=[package_rbac_dependency('write')],
    )
    async def _rbac_test_write() -> PlainTextResponse:  # pyright: ignore[reportUnusedFunction]
        """A test endpoint to verify RBAC write access."""
        return PlainTextResponse('ok')

    @fast_pypi_test_app.delete(
        '/fast-pypi/rbac-test-delete/',
        dependencies=[package_rbac_dependency('delete')],
    )
    async def _rbac_test_delete() -> PlainTextResponse:  # pyright: ignore[reportUnusedFunction]
        """A test endpoint to verify RBAC delete access."""
        return PlainTextResponse('ok')

    return fast_pypi_test_app


@pytest.fixture
def fast_pypi_rbac_testclient(
    fast_pypi_rbac_test_app: FastAPI,
) -> TestClient:
    """Fixture to create a TestClient for the FastAPI app with RBAC endpoints."""
    return TestClient(fast_pypi_rbac_test_app)


@dataclass
class RBACTestCase:
    """Dataclass to hold RBAC test case parameters."""

    method: str
    path: str
    request_headers: dict[str, str]
    project_name: str
    expected_status_code: int


@pytest.mark.parametrize(
    'test_case',
    [
        RBACTestCase(
            method='GET',
            path='/fast-pypi/rbac-test-read/',
            request_headers={},
            project_name='hotdog',
            expected_status_code=200,
        ),
        RBACTestCase(
            method='POST',
            path='/fast-pypi/rbac-test-write/',
            request_headers={},
            project_name='hotdog',
            expected_status_code=200,
        ),
        RBACTestCase(
            method='DELETE',
            path='/fast-pypi/rbac-test-delete/',
            request_headers={},
            project_name='hotdog',
            expected_status_code=200,
        ),
    ],
)
def test_rbac_default_noop(
    test_case: RBACTestCase,
    fast_pypi_rbac_testclient: TestClient,
    mocker: MockerFixture,
) -> None:
    """Test that the RBAC default noop works."""
    _ = mocker.patch(
        'fast_pypi.pypi.package_rbac.infer_project_name_from_request',
        return_value=test_case.project_name,
    )

    response = fast_pypi_rbac_testclient.request(
        method=test_case.method,
        url=test_case.path,
    )

    assert response.status_code == test_case.expected_status_code, (
        f'Expected status code {test_case.expected_status_code}, '
        f'but got {response.status_code} for {test_case.method} {test_case.path}'
    )


async def package_rbac_test_func(
    rbac_input: ProjectRBACDecisionInput,
) -> bool:
    """Function to use for testing custom RBAC logic.

    Allows a request iff:
    - The project name is 'hotdog'
    - The header "x-user-id" is "hotdog-vendor"
    - The operation type is 'read' or 'write'

    Args:
        rbac_input: The RBAC input data.

    Returns:
        True if access is allowed, False otherwise.
    """
    if rbac_input.project_name != 'hotdog':
        return False
    if rbac_input.request.headers.get('x-user-id') != 'hotdog-vendor':
        return False
    return rbac_input.operation_type in ('read', 'write')


@pytest.fixture
def set_package_rbac_test_func() -> Iterator[None]:
    """Fixture to set the package RBAC test function."""
    set_project_rbac_decision_func(package_rbac_test_func)
    yield
    reset_project_rbac_decision_func()


@pytest.mark.usefixtures('set_package_rbac_test_func')
@pytest.mark.parametrize(
    'test_case',
    [
        # Allowed cases - correct project, header, and allowed operations
        RBACTestCase(
            method='GET',
            path='/fast-pypi/rbac-test-read/',
            request_headers={'x-user-id': 'hotdog-vendor'},
            project_name='hotdog',
            expected_status_code=200,
        ),
        RBACTestCase(
            method='POST',
            path='/fast-pypi/rbac-test-write/',
            request_headers={'x-user-id': 'hotdog-vendor'},
            project_name='hotdog',
            expected_status_code=200,
        ),
        # Wrong project name
        RBACTestCase(
            method='GET',
            path='/fast-pypi/rbac-test-read/',
            request_headers={'x-user-id': 'hotdog-vendor'},
            project_name='pizza',
            expected_status_code=403,
        ),
        # Missing required header
        RBACTestCase(
            method='GET',
            path='/fast-pypi/rbac-test-read/',
            request_headers={},
            project_name='hotdog',
            expected_status_code=403,
        ),
        # Wrong header value
        RBACTestCase(
            method='GET',
            path='/fast-pypi/rbac-test-read/',
            request_headers={'x-user-id': 'pizza-vendor'},
            project_name='hotdog',
            expected_status_code=403,
        ),
        # Delete operation not allowed even with correct project and header
        RBACTestCase(
            method='DELETE',
            path='/fast-pypi/rbac-test-delete/',
            request_headers={'x-user-id': 'hotdog-vendor'},
            project_name='hotdog',
            expected_status_code=403,
        ),
        # Multiple failures - wrong project and missing header
        RBACTestCase(
            method='GET',
            path='/fast-pypi/rbac-test-read/',
            request_headers={},
            project_name='pizza',
            expected_status_code=403,
        ),
        # Multiple failures - wrong project and wrong header
        RBACTestCase(
            method='POST',
            path='/fast-pypi/rbac-test-write/',
            request_headers={'x-user-id': 'pizza-vendor'},
            project_name='pizza',
            expected_status_code=403,
        ),
    ],
)
def test_rbac_custom_function(
    test_case: RBACTestCase,
    fast_pypi_rbac_testclient: TestClient,
    mocker: MockerFixture,
) -> None:
    """Test that the custom RBAC function enforces all rules correctly.

    Rules being tested:
    - Project name must be 'hotdog'
    - Header 'x-user-id' must be 'hotdog-vendor'
    - Only 'read' and 'write' operations are allowed
    """
    _ = mocker.patch(
        'fast_pypi.pypi.package_rbac.infer_project_name_from_request',
        return_value=test_case.project_name,
    )

    response = fast_pypi_rbac_testclient.request(
        method=test_case.method,
        url=test_case.path,
        headers=test_case.request_headers,
    )

    assert response.status_code == test_case.expected_status_code, (
        f'Expected status code {test_case.expected_status_code}, '
        f'but got {response.status_code} for {test_case.method} {test_case.path}'
    )
