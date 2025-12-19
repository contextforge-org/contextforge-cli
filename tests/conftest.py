# -*- coding: utf-8 -*-
"""Location: ./tests/conftest.py
Copyright 2025
SPDX-License-Identifier: Apache-2.0
Authors: Gabe Goodhart

Pytest configuration and shared fixtures for Context Forge CLI tests.
"""

# Standard
import logging
import os
import socket
import sys
import tempfile
import time
import threading
import urllib3
from contextlib import contextmanager
from pathlib import Path
from types import SimpleNamespace
from typing import Any, Callable, Generator, List, Union
from unittest.mock import Mock, patch

# Third-Party
import pytest
import uvicorn
from fastapi.testclient import TestClient
from mcp.server.fastmcp import FastMCP
from pydantic import SecretStr
from typer.testing import CliRunner


# Before importing anything from the core, force the database to use a temp dir
# NOTE: In memory results in missing table errors
working_dir = tempfile.TemporaryDirectory()
os.environ["DATABASE_URL"] = f"sqlite:////{working_dir.__enter__()}/mcp.db"


# First-Party
from cforge.config import CLISettings, get_settings  # noqa: E402


# Suppress urllib3 retry warnings during tests
logging.getLogger("urllib3.connectionpool").setLevel(logging.ERROR)

# ==============================================================================
# Helper Functions
# ==============================================================================


@contextmanager
def patch_everywhere(name: str, **kwargs) -> Generator[List[Any], None, None]:
    """Patch a function in every place it is imported."""
    # Find all modules that have the function
    mod_names = [m for m, mod in sys.modules.items() if ((m.startswith("cforge") or (m.startswith("test") and "conftest" in m)) and hasattr(mod, name))]
    patches = [patch(f"{m}.{name}", **kwargs) for m in mod_names]
    yields = [p.__enter__() for p in patches]
    try:
        yield yields
    finally:
        for p in patches:
            p.__exit__(None, None, None)


@contextmanager
def patch_functions(module_paths: Union[str, List[str]], **patches):
    """Context manager to patch multiple functions in a module.

    This eliminates the need for deeply nested `with patch()` blocks in tests.

    Args:
        module_paths: The module path (e.g., "cforge.commands.resources.prompts")
        **patches: Keyword arguments where:
            - key is the function name to patch
            - value is either:
                - A dict with patch kwargs (e.g., {"return_value": x, "side_effect": Exception()})
                - Any other value to use as return_value
                - An empty dict {} to create a mock without specific configuration

    Yields:
        SimpleNamespace with attributes for each patched function's mock

    Example:
        with patch_functions("cforge.commands.resources.prompts",
                           get_console=mock_console,
                           make_authenticated_request={"return_value": mock_data},
                           print_table={}) as mocks:
            prompts_list(gateway_id=None, json_output=False)
            mocks.print_table.assert_called_once()

    Example with side_effect:
        with patch_functions("cforge.commands.resources.prompts",
                           get_console=mock_console,
                           make_authenticated_request={"side_effect": Exception("API error")}) as mocks:
            with pytest.raises(typer.Exit):
                prompts_list(gateway_id=None, json_output=False)
    """
    patch_contexts = []
    mocks = SimpleNamespace()
    module_paths = module_paths if isinstance(module_paths, list) else [module_paths]

    try:
        for module_path in module_paths:
            for func_name, config in patches.items():
                full_path = f"{module_path}.{func_name}"

                # If config is a dict, use it as patch kwargs
                # Otherwise, use it as return_value
                if config is None or isinstance(config, dict):
                    patch_kwargs = config or {}
                else:
                    patch_kwargs = {"return_value": config}

                patch_obj = patch(full_path, **patch_kwargs)
                mock = patch_obj.__enter__()
                patch_contexts.append(patch_obj)
                setattr(mocks, func_name, mock)

        yield mocks
    finally:
        for patch_ctx in reversed(patch_contexts):
            patch_ctx.__exit__(None, None, None)


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


@contextmanager
def mock_client_login(mock_client: TestClient) -> Generator[None, None, None]:
    """Provide a context manager for logging into a FastAPI TestClient."""
    cfg = get_settings()
    current_token = cfg.mcpgateway_bearer_token
    pw = cfg.basic_auth_password
    if isinstance(pw, SecretStr):
        pw = pw.get_secret_value()
    resp = mock_client.post("/auth/login", json={"email": cfg.platform_admin_email, "password": pw})
    cfg.mcpgateway_bearer_token = resp.json()["access_token"]
    setattr(mock_client, "settings", cfg)
    try:
        yield
    finally:
        cfg.mcpgateway_bearer_token = current_token
        get_settings.cache_clear()


@contextmanager
def mock_mcp_server_sse(name: str, tools: List[Callable], prompts: List[str], resources: List[str]) -> Generator[dict, None, None]:
    """Manage the context for an ephemeral MCP server with SSE."""
    mcp = FastMCP("Test")

    for tool in tools:
        mcp.tool()(tool)
    for prompt in prompts:
        mcp.prompt(name=prompt[:5])(lambda: prompt)
    for i, resource in enumerate(resources):

        def my_resource() -> str:
            return resource

        mcp.resource(f"resource://{resource[:5]}", name=f"resource_{i}")(my_resource)

    port = get_open_port()
    config = uvicorn.Config(mcp.sse_app(), host="localhost", port=port, log_level="debug")
    server = uvicorn.Server(config)
    thread = threading.Thread(target=server.run)
    try:
        thread.start()
        max_wait = 1
        start_time = time.time()
        while time.time() - start_time < max_wait:
            # Query a fake endpoint and if you get _any_ response (even a 404), it's up
            try:
                urllib3.request("GET", f"http://localhost:{port}/poke", timeout=0.05)
            except Exception:
                time.sleep(0.1)
            else:
                break
        else:
            raise RuntimeError("Failed to start MCP server")
        yield {
            "url": f"http://localhost:{config.port}/sse",
            "name": name,
            "description": "A server for testing",
        }
    finally:
        server.should_exit = True
        thread.join(timeout=5)


@contextmanager
def register_mcp_server(server_settings: dict, authorized_mock_client: TestClient) -> Generator[dict, None, None]:
    """Contextmanager to register and unregister an MCP server"""
    headers = {"Authorization": f"Bearer {authorized_mock_client.settings.mcpgateway_bearer_token}"}
    result = authorized_mock_client.post("/gateways", json=server_settings, headers=headers)
    body = result.json()
    mcp_server_id = body["id"]
    try:
        yield body
    finally:
        authorized_mock_client.delete(f"/gateways/{mcp_server_id}", headers=headers)


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
    console_mock = Mock()
    with patch_everywhere("get_console", return_value=console_mock):
        yield console_mock


@pytest.fixture(scope="session")
def mock_client() -> Generator[TestClient, None, None]:
    """Provide a FastAPI TestClient for testing server endpoints.

    This is the recommended way to test FastAPI applications. It doesn't
    require actual network binding and is much faster than spinning up
    a real server.

    Returns:
        TestClient instance connected to the FastAPI app

    Example:
        def test_endpoint(mock_client):
            response = mock_client.get("/health")
            assert response.status_code == 200
    """
    from mcpgateway.main import app

    client = TestClient(app)
    mock_client = Mock(wraps=client)

    with patch("cforge.common.requests.request", mock_client.request):
        yield mock_client


@pytest.fixture
def authorized_mock_client(mock_client) -> Generator[None, None, None]:
    """Provide a fixture for a FastAPI TestClient with an authorized user."""
    with mock_client_login(mock_client):
        yield mock_client


@pytest.fixture
def mock_settings() -> Generator[CLISettings, None, None]:
    """Provide a context manager for mocking settings."""
    with tempfile.TemporaryDirectory(prefix="cforge_") as tmpdir:
        settings = CLISettings(contextforge_home=Path(tmpdir))
        with patch_everywhere("get_settings", return_value=settings):
            yield settings


@pytest.fixture(scope="session")
def mock_mcp_server() -> Generator[dict, None, None]:
    """Fixture for a running mock MCP server with several tools."""

    def hi(name: str) -> str:
        return f"Hello, {name}!"

    def add(a: int, b: int) -> int:
        return a + b

    with mock_mcp_server_sse(
        name="test-server",
        tools=[hi, add],
        prompts=["Hello world!", "You are a math machine"],
        resources=["addition: 1 + 1 = 2"],
    ) as server_cfg:
        yield server_cfg


@pytest.fixture
def registered_mcp_server(mock_mcp_server, authorized_mock_client) -> Generator[dict, None, None]:
    """Test-level fixture to register the mock server and unregister at the end"""
    with register_mcp_server(mock_mcp_server, authorized_mock_client) as mcp_server:
        yield mcp_server


@pytest.fixture
def mock_base_url(mock_settings):
    yield f"http://{mock_settings.host}:{mock_settings.port}"
