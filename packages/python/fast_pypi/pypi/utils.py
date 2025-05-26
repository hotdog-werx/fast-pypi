import re

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
