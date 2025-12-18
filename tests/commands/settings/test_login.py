# -*- coding: utf-8 -*-
"""Location: ./tests/commands/settings/test_login.py
Copyright 2025
SPDX-License-Identifier: Apache-2.0
Authors: Gabe Goodhart

Tests for the login command.
"""

# Standard
import tempfile
from pathlib import Path
from unittest.mock import Mock, patch

# Third-Party
import pytest
import requests
import typer

# First-Party
from cforge.commands.settings.login import login
from cforge.common import AuthenticationError, make_authenticated_request


class TestLoginCommand:
    """Tests for login command."""

    def test_login_success_with_save(self, mock_base_url, mock_console) -> None:
        """Test successful login with token save."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"access_token": "test_token_123"}

        with tempfile.TemporaryDirectory() as temp_dir:
            token_file = Path(temp_dir) / "token"

            with patch("cforge.commands.settings.login.get_console", return_value=mock_console):
                with patch("cforge.commands.settings.login.get_base_url", return_value=mock_base_url):
                    with patch("cforge.commands.settings.login.requests.post", return_value=mock_response):
                        with patch("cforge.commands.settings.login.save_token") as mock_save:
                            with patch("cforge.commands.settings.login.get_token_file", return_value=token_file):
                                login(email="test@example.com", password="password", save=True)

            # Verify token was saved
            mock_save.assert_called_once_with("test_token_123")

            # Verify console output
            assert any("Login successful" in str(call) for call in mock_console.print.call_args_list)
            assert any("Token saved" in str(call) for call in mock_console.print.call_args_list)

    def test_login_success_without_save(self, mock_base_url, mock_console) -> None:
        """Test successful login without saving token."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"access_token": "test_token_123"}

        with patch("cforge.commands.settings.login.get_console", return_value=mock_console):
            with patch("cforge.commands.settings.login.get_base_url", return_value=mock_base_url):
                with patch("cforge.commands.settings.login.requests.post", return_value=mock_response):
                    with patch("cforge.commands.settings.login.save_token") as mock_save:
                        login(email="test@example.com", password="password", save=False)

        # Verify token was NOT saved
        mock_save.assert_not_called()

        # Verify console shows export instruction
        assert any("MCPGATEWAY_BEARER_TOKEN" in str(call) for call in mock_console.print.call_args_list)

    def test_login_http_error(self, mock_base_url, mock_console) -> None:
        """Test login with HTTP error response."""
        mock_response = Mock()
        mock_response.status_code = 401
        mock_response.text = "Invalid credentials"

        with patch("cforge.commands.settings.login.get_console", return_value=mock_console):
            with patch("cforge.commands.settings.login.get_base_url", return_value=mock_base_url):
                with patch("cforge.commands.settings.login.requests.post", return_value=mock_response):
                    with pytest.raises(typer.Exit) as exc_info:
                        login(email="test@example.com", password="wrong", save=True)

        # Should exit with code 1
        assert exc_info.value.exit_code == 1

        # Verify error message
        assert any("Login failed" in str(call) for call in mock_console.print.call_args_list)

    def test_login_no_token_in_response(self, mock_base_url, mock_console) -> None:
        """Test login when server doesn't return a token."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {}  # No access_token

        with patch("cforge.commands.settings.login.get_console", return_value=mock_console):
            with patch("cforge.commands.settings.login.get_base_url", return_value=mock_base_url):
                with patch("cforge.commands.settings.login.requests.post", return_value=mock_response):
                    with pytest.raises(typer.Exit) as exc_info:
                        login(email="test@example.com", password="password", save=True)

        # Should exit with code 1
        assert exc_info.value.exit_code == 1

        # Verify error message
        assert any("No token received" in str(call) for call in mock_console.print.call_args_list)

    def test_login_connection_error(self, mock_base_url, mock_console) -> None:
        """Test login with connection error."""
        with patch("cforge.commands.settings.login.get_console", return_value=mock_console):
            with patch("cforge.commands.settings.login.get_base_url", return_value=mock_base_url):
                with patch("cforge.commands.settings.login.requests.post", side_effect=requests.ConnectionError("Connection refused")):
                    with pytest.raises(typer.Exit) as exc_info:
                        login(email="test@example.com", password="password", save=True)

        # Should exit with code 1
        assert exc_info.value.exit_code == 1

        # Verify error message
        assert any("Failed to connect" in str(call) for call in mock_console.print.call_args_list)


class TestLoginCommandIntegration:
    """Test the login command with a real gateway server."""

    def test_login_lifecycle(self, mock_console, mock_client, mock_settings) -> None:
        """Test the full lifecycle of trying logged out then logging in."""

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


class TestLoginWithProfiles:
    """Tests for login command with profile support."""

    def test_login_saves_to_profile_specific_token_file(self, mock_base_url, mock_console, mock_settings) -> None:
        """Test that login saves token to profile-specific file when profile is active."""
        from cforge.profile_utils import AuthProfile, ProfileStore, save_profile_store
        from datetime import datetime

        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"access_token": "profile_token_123"}

        # Create and save an active profile
        profile_id = "test-profile-login"
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

        with patch("cforge.commands.settings.login.get_console", return_value=mock_console):
            with patch("cforge.commands.settings.login.get_base_url", return_value=mock_base_url):
                with patch("cforge.commands.settings.login.requests.post", return_value=mock_response):
                    login(email="test@example.com", password="password", save=True)

        # Verify token was saved to profile-specific file
        assert token_file.exists()
        assert token_file.read_text() == "profile_token_123"

    def test_login_with_multiple_profiles(self, mock_base_url, mock_console, mock_settings) -> None:
        """Test that different profiles can have different tokens."""
        from cforge.profile_utils import AuthProfile, ProfileStore, save_profile_store
        from datetime import datetime

        profile_id1 = "profile-1"
        profile_id2 = "profile-2"

        token_file1 = mock_settings.contextforge_home / f"token.{profile_id1}"
        token_file2 = mock_settings.contextforge_home / f"token.{profile_id2}"

        # Login to profile 1
        mock_response1 = Mock()
        mock_response1.status_code = 200
        mock_response1.json.return_value = {"access_token": "token_profile_1"}

        profile1 = AuthProfile(
            id=profile_id1,
            name="Profile 1",
            email="user1@example.com",
            apiUrl="https://api1.example.com",
            isActive=True,
            createdAt=datetime.now(),
        )
        store1 = ProfileStore(
            profiles={profile_id1: profile1},
            activeProfileId=profile_id1,
        )
        save_profile_store(store1)

        with patch("cforge.commands.settings.login.get_console", return_value=mock_console):
            with patch("cforge.commands.settings.login.get_base_url", return_value=mock_base_url):
                with patch("cforge.commands.settings.login.requests.post", return_value=mock_response1):
                    login(email="user1@example.com", password="password1", save=True)

        # Login to profile 2
        mock_response2 = Mock()
        mock_response2.status_code = 200
        mock_response2.json.return_value = {"access_token": "token_profile_2"}

        profile2 = AuthProfile(
            id=profile_id2,
            name="Profile 2",
            email="user2@example.com",
            apiUrl="https://api2.example.com",
            isActive=True,
            createdAt=datetime.now(),
        )
        store2 = ProfileStore(
            profiles={profile_id2: profile2},
            activeProfileId=profile_id2,
        )
        save_profile_store(store2)

        with patch("cforge.commands.settings.login.get_console", return_value=mock_console):
            with patch("cforge.commands.settings.login.get_base_url", return_value=mock_base_url):
                with patch("cforge.commands.settings.login.requests.post", return_value=mock_response2):
                    login(email="user2@example.com", password="password2", save=True)

        # Verify both tokens exist and are different
        assert token_file1.exists()
        assert token_file2.exists()
        assert token_file1.read_text() == "token_profile_1"
        assert token_file2.read_text() == "token_profile_2"
        assert token_file1.read_text() != token_file2.read_text()
