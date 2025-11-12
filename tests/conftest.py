# -*- coding: utf-8 -*-
"""Location: ./tests/conftest.py
Copyright 2025
SPDX-License-Identifier: Apache-2.0
Authors: Gabe Goodhart

Pytest configuration and shared fixtures for Context Forge CLI tests.
"""

# Standard
import socket
import tempfile
import time
from multiprocessing import Process
from pathlib import Path
from typing import Generator
from unittest.mock import Mock, patch

# Third-Party
import pytest
import requests
from fastapi.testclient import TestClient
from typer.testing import CliRunner

# First-Party
from cforge.config import CLISettings


# ==============================================================================
# Helper Functions
# ==============================================================================


def get_open_port() -> int:
    """Find an available ephemeral port.

    This function binds to port 0, which tells the OS to assign an
    available ephemeral port. We then immediately close the socket
    and return that port number.

    Note: There's a small race condition where another process could
    grab this port before we use it, but this is generally acceptable
    for testing.

    Returns:
        An available port number
    """
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("", 0))
        s.listen(1)
        port = s.getsockname()[1]
    return port


# ==============================================================================
# CLI Testing Fixtures
# ==============================================================================


@pytest.fixture
def cli_runner() -> CliRunner:
    """Provide a Typer CLI test runner.

    Returns:
        CliRunner instance for testing CLI commands
    """
    return CliRunner()


@pytest.fixture
def mock_console() -> Generator[Mock, None, None]:
    """Mock the Rich console for testing output.

    Yields:
        Mock console object
    """
    with patch("cforge.common.get_console") as mock:
        yield mock.return_value


@pytest.fixture
def mock_settings() -> Generator[CLISettings, None, None]:
    """Provide test settings with temporary directories and ephemeral port.

    Creates a real CLISettings instance (not a Mock) with test-appropriate
    values. Uses tempfile for cross-platform temporary directory handling
    and allocates an ephemeral port for the test server.

    Yields:
        CLISettings instance configured for testing
    """
    # Create temporary directory for test data
    with tempfile.TemporaryDirectory(prefix="cforge_test_") as temp_dir:
        temp_path = Path(temp_dir)

        # Get an ephemeral port for testing
        test_port = get_open_port()

        # Create real settings instance with test values
        with patch.dict(
            "os.environ",
            {
                "MCG_HOST": "127.0.0.1",
                "MCG_PORT": str(test_port),
                "MCPG_HOME": str(temp_path),
            },
            clear=False,
        ):
            # Clear the lru_cache to get fresh settings
            from cforge.config import get_settings

            get_settings.cache_clear()

            settings = CLISettings(
                host="127.0.0.1",
                port=test_port,
                mcpg_home=temp_path,
                mcpgateway_bearer_token=None,
                database_url="sqlite:///:memory:",
            )

            with patch("cforge.common.get_settings", return_value=settings):
                try:
                    yield settings
                finally:
                    # Clear cache again after test
                    get_settings.cache_clear()


# ==============================================================================
# Server Testing Fixtures (FastAPI TestClient - Recommended)
# ==============================================================================


@pytest.fixture
def test_client() -> TestClient:
    """Provide a FastAPI TestClient for testing server endpoints.

    This is the recommended way to test FastAPI applications. It doesn't
    require actual network binding and is much faster than spinning up
    a real server.

    Returns:
        TestClient instance connected to the FastAPI app

    Example:
        def test_endpoint(test_client):
            response = test_client.get("/health")
            assert response.status_code == 200
    """
    from mcpgateway.main import app

    return TestClient(app)


@pytest.fixture
def authenticated_test_client(test_client: TestClient) -> TestClient:
    """Provide an authenticated TestClient with a valid token.

    Returns:
        TestClient with authentication headers set

    Example:
        def test_protected_endpoint(authenticated_test_client):
            response = authenticated_test_client.get("/protected")
            assert response.status_code == 200
    """
    # Create a test token (you may need to adjust this based on your auth implementation)
    test_token = "test_token_123"
    test_client.headers["Authorization"] = f"Bearer {test_token}"
    return test_client


# ==============================================================================
# Real Server Testing Fixtures (Integration Tests)
# ==============================================================================


def _run_server(host: str, port: int) -> None:
    """Run the uvicorn server in a separate process.

    Args:
        host: Host to bind to
        port: Port to bind to
    """
    import uvicorn

    uvicorn.run(
        "mcpgateway.main:app",
        host=host,
        port=port,
        log_level="error",  # Suppress logs during testing
        access_log=False,
    )


@pytest.fixture(scope="session")
def session_server() -> Generator[dict[str, str | int], None, None]:
    """Start a single MCP Gateway server for the entire test session.

    This fixture starts an actual uvicorn server once at the beginning of the
    test session and keeps it running for all tests. This is much faster than
    starting a new server for each test.

    IMPORTANT: Since this server is shared across all tests, you must handle
    state mutations carefully:
    1. Use unique identifiers in test data (e.g., timestamps, UUIDs)
    2. Clean up created resources after tests (use try/finally)
    3. Don't rely on specific server state from other tests
    4. Consider using fixtures that clean up after themselves

    Yields:
        Dictionary with server connection info:
            - host: Server host (str)
            - port: Server port (int)
            - base_url: Full base URL (str)

    Example:
        def test_with_session_server(session_server):
            # Server is already running, just use it
            response = requests.get(f"{session_server['base_url']}/health")
            assert response.status_code == 200

        def test_create_and_cleanup(session_server):
            import time
            # Create resource with unique name
            response = requests.post(
                f"{session_server['base_url']}/api/resource",
                json={"name": f"test_{time.time()}"}
            )
            resource_id = response.json()["id"]

            try:
                # Test with resource
                assert response.status_code == 200
            finally:
                # Clean up
                requests.delete(
                    f"{session_server['base_url']}/api/resource/{resource_id}"
                )
    """
    host = "127.0.0.1"
    port = get_open_port()
    base_url = f"http://{host}:{port}"

    # Start server in separate process
    server_process = Process(target=_run_server, args=(host, port), daemon=True)
    server_process.start()

    # Wait for server to be ready (with timeout)
    max_retries = 50  # 5 seconds total
    retry_delay = 0.1
    for _ in range(max_retries):
        try:
            response = requests.get(f"{base_url}/health", timeout=1)
            if response.status_code == 200:
                break
        except (requests.ConnectionError, requests.Timeout):
            time.sleep(retry_delay)
    else:
        # Server didn't start in time
        server_process.terminate()
        server_process.join(timeout=5)
        if server_process.is_alive():
            server_process.kill()
        pytest.fail(f"Session server failed to start on {host}:{port} within timeout")

    # Yield server info to all tests
    try:
        yield {
            "host": host,
            "port": port,
            "base_url": base_url,
        }
    finally:
        # Clean up: terminate server process at end of session
        server_process.terminate()
        server_process.join(timeout=5)
        if server_process.is_alive():
            # Force kill if it didn't terminate gracefully
            server_process.kill()
            server_process.join()


@pytest.fixture
def test_server() -> Generator[dict[str, str | int], None, None]:
    """Start a real MCP Gateway server for integration testing.

    This fixture starts an actual uvicorn server in a separate process,
    waits for it to be ready, yields connection info, and then terminates
    the server when the test completes.

    Use this only when you need to test actual HTTP communication or
    client-server interaction that requires an isolated server instance.
    For shared server tests, use `session_server` instead (much faster).
    For most API endpoint tests, use the `test_client` fixture (fastest).

    Yields:
        Dictionary with server connection info:
            - host: Server host (str)
            - port: Server port (int)
            - base_url: Full base URL (str)

    Example:
        def test_real_server(test_server):
            response = requests.get(f"{test_server['base_url']}/health")
            assert response.status_code == 200
    """
    host = "127.0.0.1"
    port = get_open_port()
    base_url = f"http://{host}:{port}"

    # Start server in separate process
    server_process = Process(target=_run_server, args=(host, port), daemon=True)
    server_process.start()

    # Wait for server to be ready (with timeout)
    max_retries = 50  # 5 seconds total
    retry_delay = 0.1
    for _ in range(max_retries):
        try:
            response = requests.get(f"{base_url}/health", timeout=1)
            if response.status_code == 200:
                break
        except (requests.ConnectionError, requests.Timeout):
            time.sleep(retry_delay)
    else:
        # Server didn't start in time
        server_process.terminate()
        server_process.join(timeout=5)
        if server_process.is_alive():
            server_process.kill()
        pytest.fail(f"Server failed to start on {host}:{port} within timeout")

    # Yield server info to test
    try:
        yield {
            "host": host,
            "port": port,
            "base_url": base_url,
        }
    finally:
        # Clean up: terminate server process
        server_process.terminate()
        server_process.join(timeout=5)
        if server_process.is_alive():
            # Force kill if it didn't terminate gracefully
            server_process.kill()
            server_process.join()


@pytest.fixture
def get_open_port_fixture() -> callable:
    """Provide the get_open_port function as a fixture.

    Useful when tests need to get multiple ports dynamically.

    Returns:
        The get_open_port function

    Example:
        def test_multiple_ports(get_open_port_fixture):
            port1 = get_open_port_fixture()
            port2 = get_open_port_fixture()
            assert port1 != port2
    """
    return get_open_port


# ==============================================================================
# Integration Testing Fixtures (CLI + Session Server)
# ==============================================================================


@pytest.fixture
def session_settings(session_server: dict[str, str | int]) -> Generator[CLISettings, None, None]:
    """Provide CLISettings configured to connect to the session server.

    This fixture combines the session_server with proper settings configuration,
    allowing tests to use make_authenticated_request() against a real server.

    Args:
        session_server: The session server fixture providing host/port/base_url

    Yields:
        CLISettings configured for the session server

    Example:
        def test_with_session_settings(session_settings):
            from cforge.common import make_authenticated_request

            # This will make a real HTTP request to the session server
            result = make_authenticated_request("GET", "/health")
            assert result["status"] == "healthy"
    """
    with tempfile.TemporaryDirectory(prefix="cforge_test_") as temp_dir:
        temp_path = Path(temp_dir)

        # Create settings pointing to the session server
        settings = CLISettings(
            host=str(session_server["host"]),
            port=int(session_server["port"]),
            mcpg_home=temp_path,
            mcpgateway_bearer_token="test_session_token",
            database_url="sqlite:///:memory:",
        )

        # Patch get_settings to return our test settings
        with patch("cforge.common.get_settings", return_value=settings):
            # Clear the lru_cache to ensure fresh settings
            from cforge.config import get_settings as config_get_settings

            config_get_settings.cache_clear()

            try:
                yield settings
            finally:
                # Clear cache again after test
                config_get_settings.cache_clear()
