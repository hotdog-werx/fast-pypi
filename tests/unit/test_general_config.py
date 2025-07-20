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


def test_fallback_enabled_true(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Test that fallback_enabled flag is passed correctly when true."""
    monkeypatch.setenv('FAST_PYPI_FALLBACK_ENABLED', 'true')
    monkeypatch.setenv('FAST_PYPI_FALLBACK_URL', 'https://pypi.org/simple/')
    config = FastPypiConfig.from_env()
    assert config.fallback_enabled is True


def test_fallback_enabled_false(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Test that fallback_enabled flag is passed correctly when false."""
    monkeypatch.setenv('FAST_PYPI_FALLBACK_ENABLED', 'false')
    monkeypatch.setenv('FAST_PYPI_FALLBACK_URL', 'https://pypi.org/simple/')
    config = FastPypiConfig.from_env()
    assert config.fallback_enabled is False


def test_fallback_enabled_default_false(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Test that fallback_enabled defaults to false when not set."""
    monkeypatch.delenv('FAST_PYPI_FALLBACK_ENABLED', raising=False)
    monkeypatch.setenv('FAST_PYPI_FALLBACK_URL', 'https://pypi.org/simple/')
    config = FastPypiConfig.from_env()
    assert config.fallback_enabled is False


def test_fallback_url_custom(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Test that custom fallback_url is set correctly."""
    monkeypatch.setenv('FAST_PYPI_FALLBACK_URL', 'https://my-custom-pypi.example.com/simple/')
    config = FastPypiConfig.from_env()
    assert config.fallback_url == 'https://my-custom-pypi.example.com/simple/'


def test_fallback_url_default(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Test that fallback_url defaults to PyPI when not set."""
    monkeypatch.delenv('FAST_PYPI_FALLBACK_URL', raising=False)
    config = FastPypiConfig.from_env()
    assert config.fallback_url == 'https://pypi.org/simple/'
