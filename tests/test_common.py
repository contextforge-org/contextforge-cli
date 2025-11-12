# -*- coding: utf-8 -*-
"""Location: ./tests/test_common.py
Copyright 2025
SPDX-License-Identifier: Apache-2.0
Authors: Gabe Goodhart

Tests for common utility functions.
"""

# Standard
from pathlib import Path
from unittest.mock import patch
import tempfile

# First-Party
from cforge.common import (
    AuthenticationError,
    CLIError,
    get_app,
    get_auth_token,
    get_console,
    get_token_file,
    load_token,
    save_token,
)


class TestSingletons:
    """Tests for singleton getter functions."""

    def test_get_console_returns_console(self) -> None:
        """Test that get_console returns a Console instance."""
        console = get_console()
        assert console is not None
        # Should return same instance
        assert get_console() is console

    def test_get_app_returns_typer_app(self) -> None:
        """Test that get_app returns a Typer instance."""
        app = get_app()
        assert app is not None
        # Should return same instance
        assert get_app() is app


class TestTokenManagement:
    """Tests for token management functions."""

    def test_get_token_file(self, mock_settings) -> None:
        """Test getting the token file path."""
        token_file = get_token_file()
        assert isinstance(token_file, Path)
        assert str(token_file).endswith("token")
        # Verify it's in the test mcpg_home directory
        assert token_file.parent == mock_settings.mcpg_home

    def test_save_and_load_token(self) -> None:
        """Test saving and loading a token."""
        test_token = "test_token_123"

        with tempfile.NamedTemporaryFile() as temp_token_file:
            with patch("cforge.common.get_token_file", return_value=Path(temp_token_file.name)):
                save_token(test_token)
                loaded_token = load_token()

        assert loaded_token == test_token

    def test_load_token_nonexistent(self, tmp_path: Path) -> None:
        """Test loading a token when file doesn't exist."""
        nonexistent_file = tmp_path / "nonexistent" / "token"

        with patch("cforge.common.get_token_file", return_value=nonexistent_file):
            token = load_token()

        assert token is None


class TestAuthentication:
    """Tests for authentication functions."""

    def test_get_auth_token_from_env(self, mock_settings) -> None:
        """Test getting auth token from environment variable."""
        # Create a new settings instance with token
        from cforge.config import CLISettings

        settings_with_token = CLISettings(
            host=mock_settings.host,
            port=mock_settings.port,
            mcpg_home=mock_settings.mcpg_home,
            mcpgateway_bearer_token="env_token",
        )

        with patch("cforge.common.get_settings", return_value=settings_with_token):
            with patch("cforge.common.load_token", return_value=None):
                token = get_auth_token()

        assert token == "env_token"

    def test_get_auth_token_from_file(self, mock_settings) -> None:
        """Test getting auth token from file when env var not set."""
        # mock_settings already has mcpgateway_bearer_token=None
        with patch("cforge.common.load_token", return_value="file_token"):
            token = get_auth_token()

        assert token == "file_token"

    def test_get_auth_token_none(self, mock_settings) -> None:
        """Test getting auth token when none available."""
        # mock_settings already has mcpgateway_bearer_token=None
        with patch("cforge.common.load_token", return_value=None):
            token = get_auth_token()

        assert token is None


class TestErrors:
    """Tests for custom error classes."""

    def test_cli_error(self) -> None:
        """Test CLIError exception."""
        error = CLIError("Test error")
        assert str(error) == "Test error"

    def test_authentication_error(self) -> None:
        """Test AuthenticationError exception."""
        error = AuthenticationError("Auth failed")
        assert str(error) == "Auth failed"
        assert isinstance(error, CLIError)
