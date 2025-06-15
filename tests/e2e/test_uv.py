import json
import subprocess as sp
from contextlib import ExitStack
from pathlib import Path

import pytest

from tests.e2e.utils import create_publishable_package


@pytest.mark.usefixtures('fast_pypi_demo_app')
def test_uv_publish(tmp_path: Path, uv_path: str):
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
                    package_type='uv',
                    package_name=package_name,
                    package_version=package_version,
                )
            )

            _ = sp.check_output(  # noqa: S603
                [
                    uv_path,
                    '--project',
                    str(package_path),
                    'build',
                ],
            )
            _ = sp.check_output(  # noqa: S603
                [
                    uv_path,
                    '--project',
                    str(package_path),
                    'publish',
                    '--publish-url',
                    'http://localhost:8000/fast-pypi/upload/',
                    '--username',
                    'hot',
                    '--password',
                    'dog',
                    str(package_path / 'dist' / '*'),
                ],
            )

    pip_versions_example_package_output = sp.check_output(  # noqa: S603
        [
            f'{uv_path}',
            'run',
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

    project_dir = tmp_path / 'test-project'

    _ = sp.check_output(  # noqa: S603
        [
            uv_path,
            'init',
            str(project_dir),
            '--name',
            'test-project',
        ]
    )
    _ = sp.check_output(  # noqa: S603
        [
            uv_path,
            'add',
            'example-package==0.2.0',
            '--index',
            'http://hot:dog@localhost:8000/fast-pypi/simple/',
            '--no-cache',
            '--project',
            str(project_dir),
        ]
    )

    # Verify the package was installed correctly
    installed_output = sp.check_output(  # noqa: S603
        [
            f'{uv_path}',
            '--project',
            str(project_dir),
            'pip',
            'list',
            '--format=json',
        ],
        text=True,
        start_new_session=True,
    )

    installed_packages = json.loads(installed_output)
    example_package = next(
        (pkg for pkg in installed_packages if pkg['name'] == 'example-package'),
        None,
    )

    assert example_package is not None, [pkg['name'] for pkg in installed_packages]
    assert example_package['version'] == '0.2.0', example_package
