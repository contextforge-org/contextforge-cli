# -*- coding: utf-8 -*-
"""Location: ./tests/conftest.py
Copyright 2025
SPDX-License-Identifier: Apache-2.0
Authors: Gabe Goodhart

Pytest configuration and shared fixtures for Context Forge CLI tests.
"""

# Standard
import sys
import tempfile
from contextlib import contextmanager
from pathlib import Path
from types import SimpleNamespace
from typing import Generator, List
from unittest.mock import Mock, patch

# Third-Party
import pytest
from fastapi.testclient import TestClient
from typer.testing import CliRunner

# First-Party
from cforge.config import CLISettings, get_settings


# ==============================================================================
# Helper Functions
# ==============================================================================


@contextmanager
def patch_functions(module_path: str, **patches):
    """Context manager to patch multiple functions in a module.

    This eliminates the need for deeply nested `with patch()` blocks in tests.

    Args:
        module_path: The module path (e.g., "cforge.commands.resources.prompts")
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

    try:
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


@contextmanager
def mock_client_login(mock_client: TestClient) -> Generator[None, None, None]:
    """Provide a context manager for logging into a FastAPI TestClient."""
    cfg = get_settings()
    current_token = cfg.mcpgateway_bearer_token
    resp = mock_client.post("/auth/login", json={"email": cfg.platform_admin_email, "password": cfg.basic_auth_password})
    cfg.mcpgateway_bearer_token = resp.json()["access_token"]
    setattr(mock_client, "settings", cfg)
    try:
        yield
    finally:
        cfg.mcpgateway_bearer_token = current_token
        get_settings.cache_clear()


@pytest.fixture
def authorized_mock_client(mock_client) -> Generator[None, None, None]:
    """Provide a fixture for a FastAPI TestClient with an authorized user."""
    with mock_client_login(mock_client) as client:
        yield client


@contextmanager
def patch_everywhere(name: str, **kwargs) -> Generator[List[None], None, None]:
    """Patch a function in every place it is imported."""
    # Find all modules that have the function
    mod_names = [m for m, mod in sys.modules.items() if m.startswith("cforge") and hasattr(mod, name)]
    patches = [patch(f"{m}.{name}", **kwargs) for m in mod_names]
    yields = [p.__enter__() for p in patches]
    try:
        yield yields
    finally:
        for p in patches:
            p.__exit__(None, None, None)


@pytest.fixture
def mock_settings() -> Generator[CLISettings, None, None]:
    """Provide a context manager for mocking settings."""
    with tempfile.TemporaryDirectory(prefix="cforge_") as tmpdir:
        settings = CLISettings(mcpg_home=Path(tmpdir))
        with patch_everywhere("get_settings", return_value=settings):
            yield settings
