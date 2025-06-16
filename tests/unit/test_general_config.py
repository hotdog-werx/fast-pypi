import pytest

from fast_pypi.config import FastPypiConfig


def test_get_backend_allow_overwrite_true(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Test that allow_overwrite flag is passed correctly when true."""
    monkeypatch.setenv('FAST_PYPI_ALLOW_OVERWRITE', 'true')
    config = FastPypiConfig.from_env()
    assert config.allow_overwrite is True


def test_get_backend_allow_overwrite_false(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Test that allow_overwrite flag is passed correctly when false."""
    monkeypatch.setenv('FAST_PYPI_ALLOW_OVERWRITE', 'false')
    config = FastPypiConfig.from_env()
    assert config.allow_overwrite is False
