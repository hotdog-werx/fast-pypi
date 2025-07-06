from unittest.mock import AsyncMock, MagicMock

import pytest
from fastapi import Request
from starlette.datastructures import URL

from fast_pypi.pypi.utils import infer_project_name_from_request


@pytest.fixture
def mock_request() -> MagicMock:
    """Create a mock request with a configurable URL."""
    request = MagicMock(spec=Request)

    # These can be overridden in tests
    request.url = URL('')
    request.form = AsyncMock(side_effect=lambda: None)

    return request


@pytest.fixture
def mock_form_request(mock_request: Request) -> Request:
    """Create a mock request that returns form data."""

    async def mock_form() -> dict[str, str]:
        return {'name': 'test-project'}

    mock_request.form = AsyncMock(side_effect=mock_form)
    return mock_request


@pytest.mark.asyncio
@pytest.mark.parametrize(
    'path_prefix',
    ['', '/prefix', '/prefix/sub'],
)
@pytest.mark.parametrize(
    ('method', 'path', 'expected_name'),
    [
        # Root simple index
        ('GET', '/simple/', None),
        ('GET', '/simple', None),  # No trailing slash
        # Simple project index
        ('GET', '/simple/test-project/', 'test-project'),
        ('GET', '/simple/test-project', 'test-project'),  # No trailing slash
        # Artifacts
        ('GET', '/artifacts/test-project/1.0.0/file.whl', 'test-project'),
        # List versions
        ('GET', '/projects/test-project/versions/', 'test-project'),
        # Delete versions
        ('POST', '/projects/test-project/delete-versions/', 'test-project'),
    ],
)
async def test_infer_project_name_from_path(
    mock_request: MagicMock,
    method: str,
    path_prefix: str,
    path: str,
    expected_name: str | None,
) -> None:
    """Test project name inference from various URL paths."""
    mock_request.method = method
    mock_request.url = URL(f'{path_prefix}{path}')

    result = await infer_project_name_from_request(mock_request)
    assert result == expected_name


@pytest.mark.asyncio
async def test_infer_project_name_from_upload_form(
    mock_form_request: MagicMock,
) -> None:
    """Test project name inference from upload form data."""
    mock_form_request.method = 'POST'
    mock_form_request.url = URL('/upload/')
    # Don't override form here, it's already set in the fixture

    result = await infer_project_name_from_request(mock_form_request)
    assert result == 'test-project'


@pytest.mark.asyncio
@pytest.mark.parametrize(
    'path',
    [
        '/upload/',
        '/prefix/upload/',
        '/prefix/sub/upload/',
    ],
)
async def test_infer_project_name_from_upload_form_missing(
    mock_request: MagicMock,
    path: str,
) -> None:
    """Test upload form handling when form data is missing or invalid."""
    mock_request.method = 'POST'
    mock_request.url = URL(path)

    # Mock form() to return empty data
    async def mock_form() -> dict[str, str]:
        return {}

    mock_request.form = AsyncMock(side_effect=mock_form)
    result = await infer_project_name_from_request(mock_request)
    assert result is None


@pytest.mark.asyncio
@pytest.mark.parametrize(
    'path',
    [
        '/upload/',
        '/prefix/upload/',
        '/prefix/sub/upload/',
    ],
)
async def test_infer_project_name_from_upload_form_error(
    mock_request: MagicMock,
    path: str,
) -> None:
    """Test upload form handling when form() raises RuntimeError."""
    mock_request.method = 'POST'
    mock_request.url = URL(path)
    # Mock form() to raise RuntimeError (e.g. already consumed)
    mock_request.form = AsyncMock(side_effect=RuntimeError)
    result = await infer_project_name_from_request(mock_request)
    assert result is None


@pytest.mark.asyncio
@pytest.mark.parametrize(
    'path_prefix',
    ['', '/prefix', '/prefix/sub'],
)
@pytest.mark.parametrize(
    ('method', 'path'),
    [
        # Invalid paths
        ('GET', '/'),
        ('POST', '/'),
        ('GET', '/invalid/'),
        ('POST', '/invalid/'),
        # Extra segments after project name
        ('GET', '/simple/test-project/extra'),
        ('GET', '/simple/test-project/1.0.0/extra'),
        # Wrong methods for endpoints
        ('POST', '/simple/'),
        ('POST', '/simple/test-project/'),
        ('POST', '/artifacts/test-project/1.0.0/file.whl'),
        ('GET', '/delete/test-project/1.0.0'),
        ('POST', '/delete/test-project/1.0.0'),
        # Missing required segments
        ('GET', '/artifacts/'),
        ('GET', '/artifacts/test-project/'),
        ('DELETE', '/delete/'),
        ('DELETE', '/delete/test-project'),
    ],
)
async def test_infer_project_name_from_invalid_paths(
    mock_request: MagicMock,
    method: str,
    path_prefix: str,
    path: str,
) -> None:
    """Test project name inference returns None for invalid paths and methods."""
    mock_request.method = method
    mock_request.url = URL(f'{path_prefix}{path}')

    with pytest.raises(ValueError, match='Unable to infer project name from request'):
        _ = await infer_project_name_from_request(mock_request)
