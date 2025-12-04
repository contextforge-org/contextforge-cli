# -*- coding: utf-8 -*-
"""Location: ./tests/commands/settings/test_logout.py
Copyright 2025
SPDX-License-Identifier: Apache-2.0
Authors: Gabe Goodhart

Tests for the logout command.
"""

# Standard
import tempfile
from pathlib import Path
from unittest.mock import patch

# Third-Party
import pytest

# First-Party
from cforge.commands.settings.login import login
from cforge.commands.settings.logout import logout
from cforge.common import AuthenticationError, make_authenticated_request


class TestLogoutCommand:
    """Tests for logout command."""

    def test_logout_removes_existing_token(self, mock_console) -> None:
        """Test logout removes token file when it exists."""
        with tempfile.TemporaryDirectory() as temp_dir:
            token_file = Path(temp_dir) / "token"
            token_file.write_text("test_token")

            with patch("cforge.commands.settings.logout.get_console", return_value=mock_console):
                with patch("cforge.commands.settings.logout.get_token_file", return_value=token_file):
                    logout()

            # Token file should be deleted
            assert not token_file.exists()

            # Verify console output
            assert mock_console.print.call_count == 2
            first_call = mock_console.print.call_args_list[0][0][0]
            assert "Token removed" in first_call
            assert str(token_file) in first_call

    def test_logout_handles_no_token_file(self, mock_console) -> None:
        """Test logout handles case where token file doesn't exist."""
        with tempfile.TemporaryDirectory() as temp_dir:
            token_file = Path(temp_dir) / "nonexistent" / "token"

            with patch("cforge.commands.settings.logout.get_console", return_value=mock_console):
                with patch("cforge.commands.settings.logout.get_token_file", return_value=token_file):
                    logout()

            # Verify console output
            mock_console.print.assert_called_once()
            call_args = mock_console.print.call_args[0][0]
            assert "No stored token found" in call_args
            assert "[yellow]" in call_args


class TestLogoutCommandIntegration:
    """Test the logout command with a real gateway server."""

    def test_logout_lifecycle(self, mock_console, mock_client, mock_settings) -> None:
        """Test the full lifecycle of trying logged, logging in, then logging out"""

        with patch("cforge.commands.settings.login.requests", mock_client):

            # Try making an authenticated call (without the saved token)
            with pytest.raises(AuthenticationError):
                make_authenticated_request("GET", "/tools")

            # Log in and try again
            login(
                email=mock_settings.platform_admin_email,
                password=mock_settings.platform_admin_password.get_secret_value(),
                save=True,
            )
            make_authenticated_request("GET", "/tools")

            # Log out
            logout()

            # Try again (should fail)
            with pytest.raises(AuthenticationError):
                make_authenticated_request("GET", "/tools")
