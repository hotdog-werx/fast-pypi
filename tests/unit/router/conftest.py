from unittest.mock import AsyncMock

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from pytest_mock import MockerFixture

from fast_pypi import pep503_router


@pytest.fixture
def fast_pypi_test_app() -> FastAPI:
    """Fixture to create a FastAPI app with the pep503 router for testing."""
    app = FastAPI()
    app.include_router(pep503_router, prefix='/fast-pypi')
    return app


@pytest.fixture
def fast_pypi_testclient(fast_pypi_test_app: FastAPI) -> TestClient:
    """Fixture to create a TestClient for the FastAPI app."""
    return TestClient(fast_pypi_test_app)


@pytest.fixture
def check_rbac_mock(mocker: MockerFixture) -> AsyncMock:
    """Fixture to mock the RBAC check function."""
    return mocker.patch('fast_pypi.pypi.package_rbac.check_and_raise_project_rbac')
