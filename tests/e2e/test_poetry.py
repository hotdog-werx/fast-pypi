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
                    f'{uv_path}x',
                    'poetry',
                    'build',
                ],
                cwd=package_path,
            )

            # Publish to our local PyPI server
            _ = sp.check_output(  # noqa: S603
                [
                    f'{uv_path}x',
                    'poetry',
                    'config',
                    'repositories.fastpypi',
                    'http://hot:dog@localhost:8000/fast-pypi/upload/',
                ],
                cwd=package_path,
            )
            _ = sp.check_output(  # noqa: S603
                [
                    f'{uv_path}x',
                    'poetry',
                    'publish',
                    '--repository',
                    'fastpypi',
                ],
                cwd=package_path,
                env={
                    **os.environ,
                    'POETRY_HTTP_BASIC_FASTPYPI_USERNAME': 'hot',
                    'POETRY_HTTP_BASIC_FASTPYPI_PASSWORD': 'dog',
                },
            )

    # Verify published versions using pip
    pip_versions_example_package_output = sp.check_output(  # noqa: S603
        [
            f'{uv_path}x',
            'pip',
            'index',
            'versions',
            'example-package',
            '--index-url',
            'http://hot:dog@localhost:8000/fast-pypi/simple/',
            '--json',
            '--pre',
        ]
    ).decode('utf-8')

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
            f'{uv_path}x',
            'poetry',
            'init',
            '--name=test-project',
            '--description=""',
            '--author=""',
            '--no-interaction',
        ],
        cwd=project_dir,
    )

    # Add our published package as a dependency
    _ = sp.check_output(  # noqa: S603
        [
            f'{uv_path}x',
            'poetry',
            'source',
            'add',
            'fastpypi',
            'http://localhost:8000/fast-pypi/simple/',
        ],
        cwd=project_dir,
    )
    _ = sp.check_output(  # noqa: S603
        [
            f'{uv_path}x',
            'poetry',
            'add',
            'example-package==0.2.0',
            '--source',
            'fastpypi',
            '-vvv',  # Add verbose output
        ],
        cwd=project_dir,
        env={
            **os.environ,
            'POETRY_HTTP_BASIC_FASTPYPI_USERNAME': 'hot',
            'POETRY_HTTP_BASIC_FASTPYPI_PASSWORD': 'dog',
        },
        stderr=sp.PIPE,  # Capture stderr
    )

    # Verify the package was installed correctly
    installed_output = sp.check_output(  # noqa: S603
        [
            f'{uv_path}x',
            'poetry',
            'show',
            '--tree',
        ],
        cwd=project_dir,
    ).decode('utf-8')
    assert 'example-package 0.2.0' in installed_output
