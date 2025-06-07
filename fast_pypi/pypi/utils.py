import re
from re import Pattern

from fastapi import Request

# Pattern for normalizing package names
__NORMALIZE_PATTERN = re.compile(r'[-_.]+', re.ASCII)

# Path patterns for different endpoints
__UPLOAD_PATTERN = re.compile(r'.*/upload/?$')
__SIMPLE_ROOT_PATTERN = re.compile(r'.*/simple/?$')
__SIMPLE_PROJECT_PATTERN = re.compile(r'.*/simple/([^/]+)/?$')
__ARTIFACTS_PATTERN = re.compile(r'.*/artifacts/([^/]+)/.+')
__DELETE_PATTERN = re.compile(r'.*/delete/([^/]+)/.+')


def pypi_normalize(name: str) -> str:
    """Normalize a PyPI package name.

    This function replaces any sequence of hyphens, underscores, or dots
    with a single hyphen and converts the name to lowercase.

    Args:
        name: The name of the package to normalize.

    Returns:
        The normalized package name.
    """
    return __NORMALIZE_PATTERN.sub('-', name).lower()


def _get_project_name_from_path_pattern(pattern: Pattern[str], path: str) -> str | None:
    """Extract project name from a path using a regex pattern.

    Args:
        pattern: Compiled regex pattern with a capture group for project name
        path: URL path to match against

    Returns:
        str | None: Project name if found in capture group, None otherwise
    """
    match = pattern.match(path)
    if match and match.group(1):
        return match.group(1)
    return None


async def _get_project_name_from_upload_form(request: Request) -> str | None:
    """Extract project name from form data for upload endpoint.

    Args:
        request: The request object containing form data

    Returns:
        str | None: Project name from form data if found, None otherwise
    """
    try:
        form = await request.form()
        name = form.get('name')
        return str(name) if name else None
    except RuntimeError:
        # Form not available or already consumed
        return None


async def infer_project_name_from_request(request: Request) -> str | None:
    """Infer the project name from the request path or form data.

    For POST upload requests, looks for project name in form data.
    For other endpoints, extracts from URL path.

    The function returns None for:
    - Root simple index (/prefix/simple/)
    - Upload endpoint with no form data
    - Invalid paths

    Args:
        request: The incoming request object.

    Returns:
        str | None: The inferred project name, or None if accessing root index or unable to infer.
    """
    # Root simple index always returns None
    if request.method == 'GET' and __SIMPLE_ROOT_PATTERN.match(request.url.path):
        return None

    # Upload endpoint gets project name from form data
    if request.method == 'POST' and __UPLOAD_PATTERN.match(request.url.path):
        return await _get_project_name_from_upload_form(request)

    # Try project-specific endpoints in order
    for method, pattern in [
        ('GET', __SIMPLE_PROJECT_PATTERN),
        ('GET', __ARTIFACTS_PATTERN),
        ('DELETE', __DELETE_PATTERN),
    ]:
        if (
            request.method == method
            and (
                result := _get_project_name_from_path_pattern(
                    pattern,
                    request.url.path,
                )
            )
            is not None
        ):
            return result

    msg = (
        f'Unable to infer project name from request: '
        f'method={request.method}, path={request.url.path}. '
        'Ensure the path matches one of the expected patterns.'
    )
    raise ValueError(msg)
