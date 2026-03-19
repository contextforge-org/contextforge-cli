# -*- coding: utf-8 -*-
"""Location: ./tests/commands/server/test_serve.py
Copyright 2025
SPDX-License-Identifier: Apache-2.0
Authors: Gabe Goodhart

Tests for the serve command.
"""

# Standard
from unittest.mock import patch
import threading
import time

# Third-Party
import requests

# Local
from cforge.commands.server.serve import serve
from tests.conftest import get_open_port, invoke_typer_command


class TestServeCommand:
    """Tests for serve command."""

    def test_serve_with_defaults(self) -> None:
        """Test serve command with default parameters."""
        with patch("cforge.commands.server.serve.uvicorn.run") as mock_run:
            invoke_typer_command(serve)
            mock_run.assert_called_once()
            args, kwargs = mock_run.call_args
            assert "mcpgateway.main:app" in args

    def test_serve_with_custom_host_port(self) -> None:
        """Test serve command with custom host and port."""
        with patch("cforge.commands.server.serve.uvicorn.run") as mock_run:
            invoke_typer_command(serve, host="0.0.0.0", port=8080)
            mock_run.assert_called_once()
            _, kwargs = mock_run.call_args
            assert kwargs.get("host") == "0.0.0.0"
            assert kwargs.get("port") == 8080

    def test_serve_with_reload(self) -> None:
        """Test serve command with reload enabled."""
        with patch("cforge.commands.server.serve.uvicorn.run") as mock_run:
            invoke_typer_command(serve, reload=True)
            mock_run.assert_called_once()
            _, kwargs = mock_run.call_args
            assert kwargs.get("reload") is True

    def test_serve_with_no_auth_sets_auth_required_false(self) -> None:
        """Test serve command with --no-auth sets auth_required to False."""
        with patch("cforge.commands.server.serve.uvicorn.run") as mock_run, patch("cforge.commands.server.serve.set_serve_settings") as mock_set_settings:
            invoke_typer_command(serve, no_auth=True, headless=False)
            mock_run.assert_called_once()
            # When headless=False (default), UI and admin API are enabled (not headless = True)
            # When no_auth=True, auth_required should be False (not no_auth = False)
            mock_set_settings.assert_called_once_with(
                mcpgateway_ui_enabled=True,
                mcpgateway_admin_api_enabled=True,
                auth_required=False,
            )

    def test_serve_without_no_auth_sets_auth_required_true(self) -> None:
        """Test serve command without --no-auth sets auth_required to True."""
        with patch("cforge.commands.server.serve.uvicorn.run") as mock_run, patch("cforge.commands.server.serve.set_serve_settings") as mock_set_settings:
            invoke_typer_command(serve, no_auth=False, headless=False)
            mock_run.assert_called_once()
            # When headless=False (default), UI and admin API are enabled (not headless = True)
            # When no_auth=False (default), auth_required should be True (not no_auth = True)
            mock_set_settings.assert_called_once_with(
                mcpgateway_ui_enabled=True,
                mcpgateway_admin_api_enabled=True,
                auth_required=True,
            )


class TestServeCommandIntegration:
    """Integration tests for the serve command"""

    def test_serve_starts_and_responds(self, mock_settings):
        """Run the ``serve`` command and verify a simple request succeeds.

        The server is started in a daemon thread; the test polls the ``/health``
        endpoint until it receives a ``200`` response or times out.
        """
        port = get_open_port()

        # Start the server in a background thread. ``daemon=True`` ensures the
        # thread does not block process exit.
        server_thread = threading.Thread(
            target=serve,
            kwargs={"host": "127.0.0.1", "port": port, "reload": False, "workers": 1, "log_level": "error", "no_auth": False},
            daemon=True,
        )
        server_thread.start()

        # Poll the server until it is ready.
        deadline = time.time() + 5.0
        while True:
            try:
                resp = requests.get(f"http://127.0.0.1:{port}/health", timeout=0.5)
                if resp.status_code == 200:
                    return
            except Exception:
                pass
            if time.time() > deadline:
                raise AssertionError("Server failed to start within timeout")
            time.sleep(0.01)
