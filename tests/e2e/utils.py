import tempfile
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path
from typing import Literal

from jinja2 import Template

PACKAGE_FILES = [
    'src/__init__.py',
    'src/version.py',
    'pyproject.toml',
    'README.md',
]

PackageType = Literal['uv', 'poetry']


@contextmanager
def create_publishable_package(
    package_type: PackageType,
    package_name: str,
    package_version: str,
) -> Iterator[Path]:
    template_dir = Path(__file__).parent / 'publishable_templates' / f'example_package_{package_type}'
    with tempfile.TemporaryDirectory() as temp_dir:
        package_path = Path(temp_dir) / package_name
        package_path.mkdir(parents=True, exist_ok=True)

        for package_file in PACKAGE_FILES:
            file_path = package_path / package_file
            file_path.parent.mkdir(parents=True, exist_ok=True)

            _ = file_path.write_text(
                Template((template_dir / package_file).read_text()).render(
                    package_name=package_name,
                    package_version=package_version,
                )
            )

        yield package_path
