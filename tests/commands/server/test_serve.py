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

# First-Party
from cforge.commands.server.serve import serve
from tests.conftest import get_open_port


class TestServeCommand:
    """Tests for serve command."""

    def test_serve_with_defaults(self) -> None:
        """Test serve command with default parameters."""
        with patch("cforge.commands.server.serve.uvicorn.run") as mock_run:
            serve()
            mock_run.assert_called_once()
            args, kwargs = mock_run.call_args
            assert "mcpgateway.main:app" in args

    def test_serve_with_custom_host_port(self) -> None:
        """Test serve command with custom host and port."""
        with patch("cforge.commands.server.serve.uvicorn.run") as mock_run:
            serve(host="0.0.0.0", port=8080)
            mock_run.assert_called_once()
            _, kwargs = mock_run.call_args
            assert kwargs.get("host") == "0.0.0.0"
            assert kwargs.get("port") == 8080

    def test_serve_with_reload(self) -> None:
        """Test serve command with reload enabled."""
        with patch("cforge.commands.server.serve.uvicorn.run") as mock_run:
            serve(reload=True)
            mock_run.assert_called_once()
            _, kwargs = mock_run.call_args
            assert kwargs.get("reload") is True


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
            kwargs={"host": "127.0.0.1", "port": port, "reload": False, "workers": 1, "log_level": "error"},
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
