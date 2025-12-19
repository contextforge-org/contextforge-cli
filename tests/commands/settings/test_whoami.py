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

        call_messages = [call[0][0] for call in mock_console.print.call_args_list if call and call[0]]
        assert any("Authenticated via MCPGATEWAY_BEARER_TOKEN" in call for call in call_messages)
        assert any("env_token_" in call for call in call_messages)

    def test_whoami_with_stored_token(self, mock_settings, mock_console) -> None:
        """Test whoami when authenticated via stored token file."""
        # Set up settings with no env token
        mock_settings.mcpgateway_bearer_token = None
        stored_token = "stored_token_1234567890abcdef"
        with patch("cforge.commands.settings.whoami.get_console", return_value=mock_console):
            with patch("cforge.commands.settings.whoami.get_settings", return_value=mock_settings):
                with patch("cforge.commands.settings.whoami.load_token", return_value=stored_token):
                    whoami()

        call_messages = [call[0][0] for call in mock_console.print.call_args_list if call and call[0]]
        assert any("Authenticated via stored token" in call for call in call_messages)
        assert any("stored_tok" in call for call in call_messages)

    def test_whoami_not_authenticated(self, mock_settings, mock_console) -> None:
        """Test whoami when not authenticated."""
        # Set up settings with no tokens
        mock_settings.mcpgateway_bearer_token = None

        with patch("cforge.commands.settings.whoami.get_console", return_value=mock_console):
            with patch("cforge.commands.settings.whoami.get_settings", return_value=mock_settings):
                with patch("cforge.commands.settings.whoami.load_token", return_value=None):
                    whoami()

        call_messages = [call[0][0] for call in mock_console.print.call_args_list if call and call[0]]
        assert any("Not authenticated" in call for call in call_messages)
        assert any("cforge login" in call for call in call_messages)

    def test_whoami_env_token_takes_precedence(self, mock_settings, mock_console) -> None:
        """Test that env token takes precedence over stored token."""
        # Set up both tokens - env should win
        mock_settings.mcpgateway_bearer_token = "env_token_1234567890abcdef"
        stored_token = "stored_token_1234567890abcdef"

        with patch("cforge.commands.settings.whoami.get_console", return_value=mock_console):
            with patch("cforge.commands.settings.whoami.get_settings", return_value=mock_settings):
                with patch("cforge.commands.settings.whoami.load_token", return_value=stored_token):
                    whoami()

        call_messages = [call[0][0] for call in mock_console.print.call_args_list if call and call[0]]
        assert any("MCPGATEWAY_BEARER_TOKEN" in call for call in call_messages)
        assert not any("stored token" in call for call in call_messages)


class TestWhoamiWithProfiles:
    """Tests for whoami command with profile support."""

    def test_whoami_with_active_profile_and_token(self, mock_settings, mock_console) -> None:
        """Test whoami displays active profile information along with auth status."""
        from cforge.profile_utils import AuthProfile, ProfileStore, save_profile_store
        from datetime import datetime

        # Create and save an active profile
        profile_id = "test-profile-whoami"
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

        # Set up authentication
        mock_settings.mcpgateway_bearer_token = None
        stored_token = "stored_token_1234567890abcdef"

        with patch("cforge.commands.settings.whoami.get_console", return_value=mock_console):
            with patch("cforge.commands.settings.whoami.get_settings", return_value=mock_settings):
                with patch("cforge.commands.settings.whoami.load_token", return_value=stored_token):
                    whoami()

        # Should display profile info (5 lines) + blank line + auth status (2 lines) = 8 calls
        assert mock_console.print.call_count == 8

        # Check profile information is displayed
        calls_text = " ".join([str(call[0][0]) if call[0] else "" for call in mock_console.print.call_args_list])
        assert "Active Profile:" in calls_text
        assert "Test Profile" in calls_text
        assert profile_id in calls_text
        assert "test@example.com" in calls_text
        assert "https://api.example.com" in calls_text

        # Check authentication status is still displayed
        assert "Authenticated via stored token" in calls_text
        assert "stored_tok" in calls_text

    def test_whoami_with_active_profile_with_metadata(self, mock_settings, mock_console) -> None:
        """Test whoami displays profile metadata when available."""
        from cforge.profile_utils import AuthProfile, ProfileMetadata, ProfileStore, save_profile_store
        from datetime import datetime

        # Create profile with metadata
        profile_id = "test-profile-metadata"
        metadata = ProfileMetadata(
            description="Test environment",
            environment="staging",
            color="#FF5733",
            icon="🚀",
        )
        profile = AuthProfile(
            id=profile_id,
            name="Staging Profile",
            email="staging@example.com",
            apiUrl="https://staging-api.example.com",
            isActive=True,
            createdAt=datetime.now(),
            metadata=metadata,
        )
        store = ProfileStore(
            profiles={profile_id: profile},
            activeProfileId=profile_id,
        )
        save_profile_store(store)

        mock_settings.mcpgateway_bearer_token = None

        with patch("cforge.commands.settings.whoami.get_console", return_value=mock_console):
            with patch("cforge.commands.settings.whoami.get_settings", return_value=mock_settings):
                with patch("cforge.commands.settings.whoami.load_token", return_value=None):
                    whoami()

        # Check that environment is displayed
        calls_text = " ".join([str(call[0][0]) if call[0] else "" for call in mock_console.print.call_args_list])
        assert "Environment:" in calls_text
        assert "staging" in calls_text

    def test_whoami_with_active_profile_no_auth(self, mock_settings, mock_console) -> None:
        """Test whoami with active profile but no authentication."""
        from cforge.profile_utils import AuthProfile, ProfileStore, save_profile_store
        from datetime import datetime

        # Create and save an active profile
        profile_id = "test-profile-noauth"
        profile = AuthProfile(
            id=profile_id,
            name="No Auth Profile",
            email="noauth@example.com",
            apiUrl="https://noauth-api.example.com",
            isActive=True,
            createdAt=datetime.now(),
        )
        store = ProfileStore(
            profiles={profile_id: profile},
            activeProfileId=profile_id,
        )
        save_profile_store(store)

        # No authentication
        mock_settings.mcpgateway_bearer_token = None

        with patch("cforge.commands.settings.whoami.get_console", return_value=mock_console):
            with patch("cforge.commands.settings.whoami.get_settings", return_value=mock_settings):
                with patch("cforge.commands.settings.whoami.load_token", return_value=None):
                    whoami()

        # Should display profile info + not authenticated message
        calls_text = " ".join([str(call[0][0]) if call[0] else "" for call in mock_console.print.call_args_list])
        assert "Active Profile:" in calls_text
        assert "No Auth Profile" in calls_text
        assert "Not authenticated" in calls_text
        assert "cforge login" in calls_text
