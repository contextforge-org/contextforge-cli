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


class TestLogoutWithProfiles:
    """Tests for logout command with profile support."""

    def test_logout_removes_profile_specific_token(self, mock_console, mock_settings) -> None:
        """Test that logout removes profile-specific token file."""
        from cforge.profile_utils import AuthProfile, ProfileStore, save_profile_store
        from datetime import datetime

        # Create and save an active profile
        profile_id = "test-profile-logout"
        profile = AuthProfile(
            id=profile_id,
            name="Test Profile",
            email="test@example.com",
            apiUrl="https://api.example.com",
            isActive=True,
            createdAt=datetime.now(),
        )
        store = ProfileStore(
            profiles={profile_id: profile},
            activeProfileId=profile_id,
        )
        save_profile_store(store)

        token_file = mock_settings.contextforge_home / f"token.{profile_id}"
        token_file.write_text("profile_token")

        with patch("cforge.commands.settings.logout.get_console", return_value=mock_console):
            logout()

        # Token file should be deleted
        assert not token_file.exists()

        # Verify console output mentions the profile-specific file
        assert mock_console.print.call_count == 2
        first_call = mock_console.print.call_args_list[0][0][0]
        assert "Token removed" in first_call
        assert profile_id in str(token_file)

    def test_logout_only_removes_active_profile_token(self, mock_console, mock_settings) -> None:
        """Test that logout only removes the active profile's token, not others."""
        from cforge.profile_utils import AuthProfile, ProfileStore, save_profile_store
        from datetime import datetime

        profile_id1 = "profile-1"
        profile_id2 = "profile-2"

        # Create profile 2 as active
        profile2 = AuthProfile(
            id=profile_id2,
            name="Profile 2",
            email="user2@example.com",
            apiUrl="https://api2.example.com",
            isActive=True,
            createdAt=datetime.now(),
        )
        store = ProfileStore(
            profiles={profile_id2: profile2},
            activeProfileId=profile_id2,
        )
        save_profile_store(store)

        token_file1 = mock_settings.contextforge_home / f"token.{profile_id1}"
        token_file2 = mock_settings.contextforge_home / f"token.{profile_id2}"

        # Create both token files
        token_file1.write_text("token_profile_1")
        token_file2.write_text("token_profile_2")

        with patch("cforge.commands.settings.logout.get_console", return_value=mock_console):
            logout()

        # Only profile 2's token should be deleted (the active one)
        assert token_file1.exists()  # Profile 1's token still exists
        assert not token_file2.exists()  # Profile 2's token was deleted
        assert token_file1.read_text() == "token_profile_1"
