import json
import os
import subprocess as sp
from contextlib import ExitStack
from pathlib import Path

import pytest

from tests.e2e.utils import create_publishable_package


@pytest.mark.usefixtures('fast_pypi_demo_app')
def test_poetry_publish(tmp_path: Path, uv_path: str):
    """Test publishing and installing packages using Poetry."""
    package_versions = [
        ('example-package', '0.1.0'),
        ('example-package', '0.2.0'),
        ('example-package', '0.2.0a1'),
        ('other-package', '0.1.0'),
    ]

    with ExitStack() as stack:
        for package_name, package_version in package_versions:
            package_path = stack.enter_context(
                create_publishable_package(
                    package_type='poetry',
                    package_name=package_name,
                    package_version=package_version,
                )
            )

            # Build the package with poetry
            _ = sp.check_output(  # noqa: S603
                [
                    uv_path,
                    'run',
                    'poetry',
                    'build',
                    '--project',
                    str(package_path),
                ],
                text=True,
                start_new_session=True,
            )

            # Publish to our local PyPI server
            _ = sp.check_output(  # noqa: S603
                [
                    uv_path,
                    'run',
                    'poetry',
                    '--project',
                    str(package_path),
                    'config',
                    'repositories.fastpypi',
                    'http://hot:dog@localhost:8000/fast-pypi/upload/',
                ],
                text=True,
                start_new_session=True,
            )
            _ = sp.check_output(  # noqa: S603
                [
                    uv_path,
                    'run',
                    'poetry',
                    '--project',
                    str(package_path),
                    'publish',
                    '--repository',
                    'fastpypi',
                ],
                env={
                    **os.environ,
                    'POETRY_HTTP_BASIC_FASTPYPI_USERNAME': 'hot',
                    'POETRY_HTTP_BASIC_FASTPYPI_PASSWORD': 'dog',
                },
                text=True,
                start_new_session=True,
            )

    # Verify published versions using pip
    pip_versions_example_package_output = sp.check_output(  # noqa: S603
        [
            uv_path,
            'run',
            'pip',
            'index',
            'versions',
            'example-package',
            '--index-url',
            'http://hot:dog@localhost:8000/fast-pypi/simple/',
            '--json',
            '--pre',
        ],
        text=True,
        start_new_session=True,
    )

    pip_versions_example_package = json.loads(pip_versions_example_package_output)

    assert pip_versions_example_package['name'] == 'example-package'
    assert sorted(
        pip_versions_example_package['versions'],
    ) == ['0.1.0', '0.2.0', '0.2.0a1']

    # Test installing the package
    project_dir = tmp_path / 'test-project'
    project_dir.mkdir(parents=True, exist_ok=True)

    # Initialize a new Poetry project
    _ = sp.check_output(  # noqa: S603
        [
            uv_path,
            'run',
            'poetry',
            '--project',
            str(project_dir),
            'init',
            '--name=test-project',
            '--description=""',
            '--author=""',
            '--no-interaction',
        ],
        text=True,
        start_new_session=True,
    )

    # Add our published package as a dependency
    _ = sp.check_output(  # noqa: S603
        [
            uv_path,
            'run',
            'poetry',
            '--project',
            str(project_dir),
            'source',
            'add',
            'fastpypi',
            'http://localhost:8000/fast-pypi/simple/',
        ],
        text=True,
        start_new_session=True,
    )
    _ = sp.check_output(  # noqa: S603
        [
            uv_path,
            'run',
            'poetry',
            '--project',
            str(project_dir),
            'add',
            'example-package==0.2.0',
            '--source',
            'fastpypi',
            '-vvv',  # Add verbose output
        ],
        env={
            **os.environ,
            'POETRY_HTTP_BASIC_FASTPYPI_USERNAME': 'hot',
            'POETRY_HTTP_BASIC_FASTPYPI_PASSWORD': 'dog',
        },
        stderr=sp.PIPE,  # Capture stderr
        text=True,
        start_new_session=True,
    )

    # Verify the package was installed correctly
    installed_output = sp.check_output(  # noqa: S603
        [
            uv_path,
            'run',
            'poetry',
            '--project',
            str(project_dir),
            'show',
            '--tree',
        ],
        env={
            **os.environ,
            'POETRY_HTTP_BASIC_FASTPYPI_USERNAME': 'hot',
            'POETRY_HTTP_BASIC_FASTPYPI_PASSWORD': 'dog',
        },
        text=True,
        start_new_session=True,
    )
    assert 'example-package 0.2.0' in installed_output
