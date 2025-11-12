# -*- coding: utf-8 -*-
"""Location: ./tests/commands/settings/test_whoami.py
Copyright 2025
SPDX-License-Identifier: Apache-2.0
Authors: Gabe Goodhart

Tests for the whoami command.
"""

# Standard
from unittest.mock import patch

# First-Party
from cforge.commands.settings.whoami import whoami


class TestWhoamiCommand:
    """Tests for whoami command."""

    def test_whoami_with_env_token(self, mock_settings, mock_console) -> None:
        """Test whoami when authenticated via environment variable."""
        # Set up settings with env token
        mock_settings.mcpgateway_bearer_token = "env_token_1234567890abcdef"

        with patch("cforge.commands.settings.whoami.get_console", return_value=mock_console):
            with patch("cforge.commands.settings.whoami.get_settings", return_value=mock_settings):
                with patch("cforge.commands.settings.whoami.load_token", return_value=None):
                    whoami()

        # Verify console output
        assert mock_console.print.call_count == 2

        # Check first call - authentication status
        first_call = mock_console.print.call_args_list[0][0][0]
        assert "Authenticated via MCPGATEWAY_BEARER_TOKEN" in first_call
        assert "[green]" in first_call

        # Check second call - token preview
        second_call = mock_console.print.call_args_list[1][0][0]
        assert "Token:" in second_call
        assert "env_token_" in second_call
        assert "..." in second_call

    def test_whoami_with_stored_token(self, mock_settings, mock_console) -> None:
        """Test whoami when authenticated via stored token file."""
        # Set up settings with no env token
        mock_settings.mcpgateway_bearer_token = None
        stored_token = "stored_token_1234567890abcdef"
        with patch("cforge.commands.settings.whoami.get_console", return_value=mock_console):
            with patch("cforge.commands.settings.whoami.get_settings", return_value=mock_settings):
                with patch("cforge.commands.settings.whoami.load_token", return_value=stored_token):
                    whoami()

        # Verify console output
        assert mock_console.print.call_count == 2

        # Check first call - authentication status with file path
        first_call = mock_console.print.call_args_list[0][0][0]
        assert "Authenticated via stored token" in first_call
        assert "[green]" in first_call

        # Check second call - token preview
        second_call = mock_console.print.call_args_list[1][0][0]
        assert "Token:" in second_call
        assert "stored_tok" in second_call
        assert "..." in second_call

    def test_whoami_not_authenticated(self, mock_settings, mock_console) -> None:
        """Test whoami when not authenticated."""
        # Set up settings with no tokens
        mock_settings.mcpgateway_bearer_token = None

        with patch("cforge.commands.settings.whoami.get_console", return_value=mock_console):
            with patch("cforge.commands.settings.whoami.get_settings", return_value=mock_settings):
                with patch("cforge.commands.settings.whoami.load_token", return_value=None):
                    whoami()

        # Verify console output
        mock_console.print.assert_called_once()

        # Check output message
        call_args = mock_console.print.call_args[0][0]
        assert "Not authenticated" in call_args
        assert "cforge login" in call_args
        assert "[yellow]" in call_args

    def test_whoami_env_token_takes_precedence(self, mock_settings, mock_console) -> None:
        """Test that env token takes precedence over stored token."""
        # Set up both tokens - env should win
        mock_settings.mcpgateway_bearer_token = "env_token_1234567890abcdef"
        stored_token = "stored_token_1234567890abcdef"

        with patch("cforge.commands.settings.whoami.get_console", return_value=mock_console):
            with patch("cforge.commands.settings.whoami.get_settings", return_value=mock_settings):
                with patch("cforge.commands.settings.whoami.load_token", return_value=stored_token):
                    whoami()

        # Should show env token, not stored token
        first_call = mock_console.print.call_args_list[0][0][0]
        assert "MCPGATEWAY_BEARER_TOKEN" in first_call
        assert "stored token" not in first_call
