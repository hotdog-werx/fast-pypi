import contextlib
import os
import signal
import subprocess
import time
from collections.abc import Generator
from pathlib import Path
from typing import final

import httpx
import pytest


@final
class DemoAppError(Exception):
    """Base exception for demo app related errors."""

    message: str

    def __init__(self, message: str) -> None:
        self.message = message
        super().__init__(self.message)


@final
class URLSchemeError(ValueError):
    """Error for invalid URL schemes."""

    def __init__(self) -> None:
        super().__init__('URL must start with http:// or https://')


def wait_for_server(url: str, timeout: float = 10.0, interval: float = 0.1) -> bool:
    """Wait for server to be ready by checking health endpoint.

    Args:
        url: The URL to check
        timeout: Maximum time to wait in seconds
        interval: Time between checks in seconds

    Returns:
        bool: True if server is ready, False if timeout was reached

    Raises:
        URLSchemeError: If URL does not use http or https scheme
    """
    if not url.startswith(('http://', 'https://')):
        raise URLSchemeError

    start_time = time.time()
    while time.time() - start_time < timeout:
        try:
            with httpx.Client() as client:
                _ = client.get(
                    url,
                    headers={'User-Agent': 'Mozilla/5.0'},
                    timeout=interval,
                ).raise_for_status()
                return True
        except (httpx.RequestError, httpx.HTTPStatusError):
            time.sleep(interval)
    return False


@pytest.fixture(scope='session')
def uv_path() -> str:
    """Get the path to the uv executable.

    Returns:
        str: The path to the uv executable.

    Raises:
        DemoAppError: If uv executable is not found.
    """
    # Get the path to the UV executable
    uv_candidates = [
        '/usr/local/bin/uv',  # Default for macOS/Linux
        '/opt/homebrew/bin/uv',  # M1 Mac Homebrew
        str(Path.home() / '.local' / 'bin' / 'uv'),  # User install
    ]

    # Add PATH candidates
    uv_candidates.extend(str(Path(path) / 'uv') for path in os.environ['PATH'].split(os.pathsep))

    # Find first existing uv executable
    uv_path = next((path for path in uv_candidates if Path(path).exists()), None)

    if uv_path is None:
        msg = 'Could not find uv executable. Please install it with: curl -LsSf https://astral.sh/uv/install.sh | sh'
        raise DemoAppError(msg)

    return str(uv_path)


@pytest.fixture
def fast_pypi_demo_app(tmp_path: Path, uv_path: str) -> Generator[subprocess.Popen[bytes], None, None]:
    """Run the FastPyPI demo app in a subprocess.

    Args:
        tmp_path: Temporary directory for the demo app.
        uv_path: The path to the uv executable.

    Yields:
        The subprocess running the demo app. Will be terminated on test
            completion.
    """
    localfs_dir = tmp_path / 'fast-pypi-localfs'
    localfs_dir.mkdir(parents=True, exist_ok=True)

    # Start the demo app in a subprocess - all inputs are trusted since they
    # are hardcoded or from system paths
    cmd = [str(Path(uv_path)), 'run', 'python', '-m', 'tests.e2e.demo_app']
    cmd_str = ' '.join(cmd)

    proc = subprocess.Popen(  # noqa: S603
        cmd,
        # Start in a new session so we can kill the process group
        start_new_session=True,
        # Capture output for debugging
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        env={
            **os.environ,
            'FAST_PYPI_LOCALFS_ROOT_PATH': str(localfs_dir),
        },
    )

    # Wait for server to be ready
    if not wait_for_server('http://localhost:8000/healthz', timeout=10.0):
        stdout, stderr = proc.communicate()
        msg = (
            'Demo app failed to start or become ready.\n'
            f'Command: {cmd_str}\n'
            f'Exit code: {proc.returncode}\n'
            f'Stdout: {stdout.decode()}\n'
            f'Stderr: {stderr.decode()}'
        )
        raise DemoAppError(msg)

    yield proc

    # Graceful shutdown - send SIGTERM to process group
    with contextlib.suppress(ProcessLookupError):
        if proc.poll() is None:
            # Only try to terminate if still running
            pgid = os.getpgid(proc.pid)
            os.killpg(pgid, signal.SIGTERM)

            # Wait for process to exit with timeout
            try:
                _ = proc.wait(timeout=5.0)
            except subprocess.TimeoutExpired:
                # Force kill if it didn't exit gracefully
                with contextlib.suppress(ProcessLookupError):
                    os.killpg(pgid, signal.SIGKILL)
                    _ = proc.wait(timeout=1.0)

            # Ensure we read any remaining output
            _, _ = proc.communicate()
