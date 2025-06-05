from dataclasses import dataclass
from pathlib import Path

import pytest

from fast_pypi.backends.localfs.env import LocalFSConfig


@dataclass
class LocalFSConfigFromEnvTestCase:
    env: dict[str, str]
    expected: LocalFSConfig


@pytest.mark.parametrize(
    'test_case',
    [
        LocalFSConfigFromEnvTestCase(
            env={
                'FAST_PYPI_LOCALFS_ROOT_PATH': '/var/lib/fast-pypi/storage',
            },
            expected=LocalFSConfig(
                root_path=Path('/var/lib/fast-pypi/storage'),
            ),
        ),
    ],
)
def test_localfs_config_from_env(test_case: LocalFSConfigFromEnvTestCase, monkeypatch: pytest.MonkeyPatch):
    """Test LocalFSConfig.from_env with environment configuration.

    Args:
        test_case: The test case containing environment variables and expected config
        monkeypatch: pytest fixture for modifying environment variables
    """
    # Set up environment variables
    for key, value in test_case.env.items():
        monkeypatch.setenv(key, value)

    # Clear any variables not in test case
    for key in [
        'FAST_PYPI_LOCALFS_ROOT_PATH',
    ]:
        if key not in test_case.env:
            monkeypatch.delenv(key, raising=False)

    # Create config from environment
    config = LocalFSConfig.from_env()

    # Assert all fields match
    assert config.root_path == test_case.expected.root_path
