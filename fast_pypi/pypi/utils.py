import re

from fastapi import Request

__PATTERN = re.compile(r'[-_.]+', re.ASCII)


def pypi_normalize(name: str) -> str:
    """Normalize a PyPI package name.

    This function replaces any sequence of hyphens, underscores, or dots
    with a single hyphen and converts the name to lowercase.

    Args:
        name: The name of the package to normalize.

    Returns:
        The normalized package name.
    """
    return __PATTERN.sub('-', name).lower()


def _get_project_name_from_path(endpoint: str, path_parts: list[str]) -> str | None:
    """Extract project name from path parts for a specific endpoint.

    Args:
        endpoint: The endpoint to look for ('simple', 'artifacts', 'delete')
        path_parts: List of URL path components

    Returns:
        str | None: Project name if found after the endpoint, None otherwise
    """
    try:
        idx = path_parts.index(endpoint)
        # For simple endpoint, root path returns None
        if endpoint == 'simple' and idx == len(path_parts) - 1:
            return None
        # For all endpoints, get the part after the endpoint if it exists
        if idx < len(path_parts) - 1:
            return path_parts[idx + 1]
    except (ValueError, IndexError):
        pass
    return None


async def _get_project_name_from_upload_form(request: Request) -> str | None:
    """Extract project name from form data for upload endpoint.

    Args:
        request: The request object containing form data

    Returns:
        str | None: Project name from form data if found, None otherwise
    """
    form = await request.form()
    name = form.get('name')
    return str(name) if name else None


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
    path_parts = request.url.path.strip('/').split('/')

    # For upload endpoint, get project name from form data
    if 'upload' in path_parts:
        return await _get_project_name_from_upload_form(request)

    # Try known endpoints in order
    for endpoint in ['simple', 'artifacts', 'delete']:
        result = _get_project_name_from_path(endpoint, path_parts)
        if result is not None:
            return result

    return None
