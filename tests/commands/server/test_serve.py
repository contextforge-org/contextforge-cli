# -*- coding: utf-8 -*-
"""Location: ./tests/commands/server/test_serve.py
Copyright 2025
SPDX-License-Identifier: Apache-2.0
Authors: Gabe Goodhart

Tests for the serve command.
"""

# Standard
from unittest.mock import patch

# First-Party
from cforge.commands.server.serve import serve


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
