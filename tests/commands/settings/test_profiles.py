# -*- coding: utf-8 -*-
"""Location: ./tests/commands/settings/test_profiles.py
Copyright 2025
SPDX-License-Identifier: Apache-2.0
Authors: Gabe Goodhart

Tests for profile management CLI commands.
"""

# Standard
from datetime import datetime
from pathlib import Path
from unittest.mock import Mock, patch
import json
import tempfile

# Third-Party
import pytest
import typer

# First-Party
from cforge.commands.settings.profiles import (
    profiles_create,
    profiles_get,
    profiles_list,
    profiles_switch,
)
from cforge.profile_utils import (
    AuthProfile,
    ProfileMetadata,
    ProfileStore,
    save_profile_store,
    load_profile_store,
    DEFAULT_PROFILE_ID,
)


class TestProfilesList:
    """Tests for profiles list command."""

    def test_profiles_list_success(self, mock_console, mock_settings) -> None:
        """Test listing profiles successfully."""
        # Create test profiles
        profile1 = AuthProfile(
            id="profile-1",
            name="Production",
            email="user@prod.com",
            apiUrl="https://api.prod.com",
            isActive=True,
            createdAt=datetime.now(),
            metadata=ProfileMetadata(environment="production"),
        )
        profile2 = AuthProfile(
            id="profile-2",
            name="Staging",
            email="user@staging.com",
            apiUrl="https://api.staging.com",
            isActive=False,
            createdAt=datetime.now(),
            metadata=ProfileMetadata(environment="staging"),
        )

        store = ProfileStore(
            profiles={"profile-1": profile1, "profile-2": profile2},
            activeProfileId="profile-1",
        )
        save_profile_store(store)

        with patch("cforge.commands.settings.profiles.get_console", return_value=mock_console):
            with patch("cforge.commands.settings.profiles.print_table") as mock_table:
                profiles_list()

        # Verify table was printed
        mock_table.assert_called_once()
        call_args = mock_table.call_args
        profile_data = call_args[0][0]

        # Verify profile data (should include 2 profiles + virtual default)
        assert len(profile_data) == 3
        assert any(p["id"] == "profile-1" for p in profile_data)
        assert any(p["id"] == "profile-2" for p in profile_data)
        assert any(p["id"] == DEFAULT_PROFILE_ID for p in profile_data)
        assert any(p["active"] == "✓" for p in profile_data)

        # Verify active profile message
        assert any("Currently using profile" in str(call) for call in mock_console.print.call_args_list)

    def test_profiles_list_empty(self, mock_console, mock_settings) -> None:
        """Test listing when no profiles exist (should show virtual default)."""
        with patch("cforge.commands.settings.profiles.get_console", return_value=mock_console):
            with patch("cforge.commands.settings.profiles.print_table") as mock_table:
                profiles_list()

        # Verify table was printed with virtual default
        mock_table.assert_called_once()
        call_args = mock_table.call_args
        profile_data = call_args[0][0]

        # Should have exactly 1 profile (the virtual default)
        assert len(profile_data) == 1
        assert profile_data[0]["id"] == DEFAULT_PROFILE_ID
        assert profile_data[0]["name"] == "Local Default"

    def test_profiles_list_with_active_profile(self, mock_console, mock_settings) -> None:
        """Test listing profiles when there is an active profile."""
        from datetime import datetime

        # Create test profiles with one active
        profile1 = AuthProfile(
            id="profile-1",
            name="Active Profile",
            email="active@example.com",
            apiUrl="https://api.active.com",
            isActive=True,
            createdAt=datetime.now(),
        )
        profile2 = AuthProfile(
            id="profile-2",
            name="Inactive Profile",
            email="inactive@example.com",
            apiUrl="https://api.inactive.com",
            isActive=False,
            createdAt=datetime.now(),
        )

        store = ProfileStore(
            profiles={"profile-1": profile1, "profile-2": profile2},
            activeProfileId="profile-1",
        )
        save_profile_store(store)

        with patch("cforge.commands.settings.profiles.get_console", return_value=mock_console):
            with patch("cforge.commands.settings.profiles.print_table"):
                profiles_list()

        # Verify active profile message is shown
        print_calls = [str(call) for call in mock_console.print.call_args_list]
        assert any("Currently using profile" in call for call in print_calls)
        assert any("Active Profile" in call for call in print_calls)

    def test_profiles_list_without_active_profile(self, mock_console, mock_settings) -> None:
        """Test listing profiles when there is not an active profile."""
        from datetime import datetime

        # Create test profiles with one active
        profile1 = AuthProfile(
            id="profile-1",
            name="Active Profile",
            email="active@example.com",
            apiUrl="https://api.active.com",
            isActive=False,
            createdAt=datetime.now(),
        )
        profile2 = AuthProfile(
            id="profile-2",
            name="Inactive Profile",
            email="inactive@example.com",
            apiUrl="https://api.inactive.com",
            isActive=False,
            createdAt=datetime.now(),
        )

        store = ProfileStore(
            profiles={"profile-1": profile1, "profile-2": profile2},
        )
        save_profile_store(store)

        with patch("cforge.commands.settings.profiles.get_console", return_value=mock_console):
            with patch("cforge.commands.settings.profiles.print_table"):
                profiles_list()

        # Verify active profile message shows default
        print_calls = [str(call) for call in mock_console.print.call_args_list]
        assert any("Currently using profile" in call for call in print_calls)
        assert any("Local Default" in call for call in print_calls)

    def test_profiles_list_error(self, mock_console, mock_settings) -> None:
        """Test listing profiles with an error."""
        with patch("cforge.commands.settings.profiles.get_console", return_value=mock_console):
            with patch("cforge.commands.settings.profiles.get_all_profiles", side_effect=Exception("Test error")):
                with pytest.raises(typer.Exit) as exc_info:
                    profiles_list()

        assert exc_info.value.exit_code == 1
        assert any("Error listing profiles" in str(call) for call in mock_console.print.call_args_list)


class TestProfilesGet:
    """Tests for profiles get command."""

    def test_profiles_get_by_id(self, mock_console, mock_settings) -> None:
        """Test getting a specific profile by ID."""
        profile = AuthProfile(
            id="profile-1",
            name="Test Profile",
            email="test@example.com",
            apiUrl="https://api.example.com",
            isActive=True,
            createdAt=datetime.now(),
            lastUsed=datetime.now(),
            metadata=ProfileMetadata(
                description="Test description",
                environment="production",
                icon="🚀",
            ),
        )

        store = ProfileStore(
            profiles={"profile-1": profile},
            activeProfileId="profile-1",
        )
        save_profile_store(store)

        with patch("cforge.commands.settings.profiles.get_console", return_value=mock_console):
            profiles_get(profile_id="profile-1", json_output=False)

        # Verify profile details were printed
        print_calls = [str(call) for call in mock_console.print.call_args_list]
        assert any("Test Profile" in call for call in print_calls)
        assert any("test@example.com" in call for call in print_calls)
        assert any("https://api.example.com" in call for call in print_calls)

    def test_profiles_get_active(self, mock_console, mock_settings) -> None:
        """Test getting the active profile when no ID provided."""
        profile = AuthProfile(
            id="profile-1",
            name="Active Profile",
            email="active@example.com",
            apiUrl="https://api.example.com",
            isActive=True,
            createdAt=datetime.now(),
        )

        store = ProfileStore(
            profiles={"profile-1": profile},
            activeProfileId="profile-1",
        )
        save_profile_store(store)

        with patch("cforge.commands.settings.profiles.get_console", return_value=mock_console):
            profiles_get(profile_id=None, json_output=False)

        # Verify active profile was shown
        print_calls = [str(call) for call in mock_console.print.call_args_list]
        assert any("Active Profile" in call for call in print_calls)

    def test_profiles_get_default(self, mock_console, mock_settings) -> None:
        """Test getting the virtual default profile."""
        with patch("cforge.commands.settings.profiles.get_console", return_value=mock_console):
            profiles_get(profile_id=DEFAULT_PROFILE_ID, json_output=False)

        # Verify default profile was shown
        print_calls = [str(call) for call in mock_console.print.call_args_list]
        assert any("Local Default" in call for call in print_calls)
        assert any("admin@localhost" in call for call in print_calls)

    def test_profiles_get_not_found(self, mock_console, mock_settings) -> None:
        """Test getting a profile that doesn't exist."""
        with patch("cforge.commands.settings.profiles.get_console", return_value=mock_console):
            with pytest.raises(typer.Exit):
                profiles_get(profile_id="nonexistent", json_output=False)

    def test_profiles_get_active_when_none_exists(self, mock_console, mock_settings) -> None:
        """Test getting active profile when profile_id is None and no profile is active (edge case)."""
        # Create a profile store with a profile but no active profile
        profile = AuthProfile(
            id="profile-1",
            name="Inactive Profile",
            email="inactive@example.com",
            apiUrl="https://api.example.com",
            isActive=False,
            createdAt=datetime.now(),
        )

        store = ProfileStore(
            profiles={"profile-1": profile},
            activeProfileId=None,
        )
        save_profile_store(store)

        with patch("cforge.commands.settings.profiles.get_console", return_value=mock_console):
            # Should not raise an error, should return virtual default
            profiles_get(profile_id=None, json_output=False)

        # Should show the virtual default profile
        print_calls = [str(call) for call in mock_console.print.call_args_list]
        assert any("Local Default" in call for call in print_calls)

    def test_profiles_get_no_active(self, mock_console, mock_settings) -> None:
        """Test getting active profile when none is set (should return default)."""
        with patch("cforge.commands.settings.profiles.get_console", return_value=mock_console):
            profiles_get(profile_id=None, json_output=False)

        # Should show the virtual default profile
        print_calls = [str(call) for call in mock_console.print.call_args_list]
        assert any("Default local development profile" in call for call in print_calls)

    def test_profiles_get_no_active_no_profiles(self, mock_console, mock_settings) -> None:
        """Test getting active profile when no profiles exist and none active (returns default)."""
        # Don't create any profile store - should return virtual default
        with patch("cforge.commands.settings.profiles.get_console", return_value=mock_console):
            profiles_get(profile_id=None, json_output=False)

        # Should show the virtual default profile
        print_calls = [str(call) for call in mock_console.print.call_args_list]
        assert any("Local Default" in call for call in print_calls)

        assert any("Local Default" in call for call in print_calls)

    def test_profiles_get_json_output(self, mock_console, mock_settings) -> None:
        """Test getting profile with JSON output."""
        profile = AuthProfile(
            id="profile-1",
            name="Test Profile",
            email="test@example.com",
            apiUrl="https://api.example.com",
            isActive=True,
            createdAt=datetime.now(),
        )

        store = ProfileStore(
            profiles={"profile-1": profile},
            activeProfileId="profile-1",
        )
        save_profile_store(store)

        with patch("cforge.commands.settings.profiles.get_console", return_value=mock_console):
            with patch("cforge.commands.settings.profiles.print_json") as mock_json:
                profiles_get(profile_id="profile-1", json_output=True)

        # Verify JSON output was called
        mock_json.assert_called_once()

    def test_profiles_get_with_metadata_fields(self, mock_console, mock_settings) -> None:
        """Test getting profile with all metadata fields displayed."""
        profile = AuthProfile(
            id="profile-1",
            name="Test Profile",
            email="test@example.com",
            apiUrl="https://api.example.com",
            isActive=True,
            createdAt=datetime.now(),
            lastUsed=datetime.now(),
            metadata=ProfileMetadata(
                description="Test description",
                environment="production",
                icon="🚀",
            ),
        )

        store = ProfileStore(
            profiles={"profile-1": profile},
            activeProfileId="profile-1",
        )
        save_profile_store(store)

        with patch("cforge.commands.settings.profiles.get_console", return_value=mock_console):
            profiles_get(profile_id="profile-1", json_output=False)

        # Verify all metadata fields are printed
        print_calls = [str(call) for call in mock_console.print.call_args_list]
        assert any("Description" in call and "Test description" in call for call in print_calls)
        assert any("Environment" in call and "production" in call for call in print_calls)
        assert any("Icon" in call and "🚀" in call for call in print_calls)
        assert any("Last Used" in call for call in print_calls)

    def test_profiles_get_error(self, mock_console, mock_settings) -> None:
        """Test getting profile with an error."""
        with patch("cforge.commands.settings.profiles.get_console", return_value=mock_console):
            with patch("cforge.commands.settings.profiles.get_profile", side_effect=Exception("Test error")):
                with pytest.raises(typer.Exit) as exc_info:
                    profiles_get(profile_id="profile-1", json_output=False)

        assert exc_info.value.exit_code == 1
        assert any("Error retrieving profile" in str(call) for call in mock_console.print.call_args_list)

    def test_profiles_get_partial_metadata(self, mock_console, mock_settings) -> None:
        """Test getting a profile with partial metadata still works."""
        profile = AuthProfile(
            id="profile-1",
            name="Active Profile",
            email="active@example.com",
            apiUrl="https://api.example.com",
            isActive=True,
            createdAt=datetime.now(),
            metadata=ProfileMetadata(isInternal=True),
        )

        store = ProfileStore(
            profiles={"profile-1": profile},
            activeProfileId="profile-1",
        )
        save_profile_store(store)

        with patch("cforge.commands.settings.profiles.get_console", return_value=mock_console):
            profiles_get(profile_id=None, json_output=False)

        # Verify active profile was shown
        print_calls = [str(call) for call in mock_console.print.call_args_list]
        assert any("Active Profile" in call for call in print_calls)
        assert not any("Description:" in call for call in mock_console.print.call_args_list)
        assert not any("Environment:" in call for call in mock_console.print.call_args_list)
        assert not any("Icon:" in call for call in mock_console.print.call_args_list)


class TestProfilesSwitch:
    """Tests for profiles switch command."""

    def test_profiles_switch_success(self, mock_console, mock_settings) -> None:
        """Test successfully switching profiles."""
        profile1 = AuthProfile(
            id="profile-1",
            name="Profile 1",
            email="user1@example.com",
            apiUrl="https://api1.example.com",
            isActive=True,
            createdAt=datetime.now(),
        )
        profile2 = AuthProfile(
            id="profile-2",
            name="Profile 2",
            email="user2@example.com",
            apiUrl="https://api2.example.com",
            isActive=False,
            createdAt=datetime.now(),
        )

        store = ProfileStore(
            profiles={"profile-1": profile1, "profile-2": profile2},
            activeProfileId="profile-1",
        )
        save_profile_store(store)

        with patch("cforge.commands.settings.profiles.get_console", return_value=mock_console):
            with patch("cforge.commands.settings.profiles.get_settings") as mock_get_settings:
                mock_get_settings.cache_clear = Mock()
                profiles_switch(profile_id="profile-2")

        # Verify success message
        print_calls = [str(call) for call in mock_console.print.call_args_list]
        assert any("Switched to profile" in call for call in print_calls)
        assert any("Profile 2" in call for call in print_calls)

        # Verify cache was cleared
        mock_get_settings.cache_clear.assert_called_once()

    def test_profiles_switch_to_default(self, mock_console, mock_settings) -> None:
        """Test switching to the virtual default profile."""
        profile1 = AuthProfile(
            id="profile-1",
            name="Profile 1",
            email="user1@example.com",
            apiUrl="https://api1.example.com",
            isActive=True,
            createdAt=datetime.now(),
        )

        store = ProfileStore(
            profiles={"profile-1": profile1},
            activeProfileId="profile-1",
        )
        save_profile_store(store)

        with patch("cforge.commands.settings.profiles.get_console", return_value=mock_console):
            with patch("cforge.commands.settings.profiles.get_settings") as mock_get_settings:
                mock_get_settings.cache_clear = Mock()
                profiles_switch(profile_id=DEFAULT_PROFILE_ID)

        # Verify success message
        print_calls = [str(call) for call in mock_console.print.call_args_list]
        assert any("Switched to profile" in call for call in print_calls)
        assert any("Local Default" in call for call in print_calls)

        # Verify all profiles are now inactive
        updated_store = load_profile_store()
        assert updated_store is not None
        assert updated_store.active_profile_id is None
        assert all(not p.is_active for p in updated_store.profiles.values())

    def test_profiles_switch_not_found(self, mock_console, mock_settings) -> None:
        """Test switching to a profile that doesn't exist."""
        with patch("cforge.commands.settings.profiles.get_console", return_value=mock_console):
            with pytest.raises(typer.Exit) as exc_info:
                profiles_switch(profile_id="nonexistent")

        assert exc_info.value.exit_code == 1
        assert any("Profile not found" in str(call) for call in mock_console.print.call_args_list)

    def test_profiles_switch_error(self, mock_console, mock_settings) -> None:
        """Test switching profiles with an error."""
        profile = AuthProfile(
            id="profile-1",
            name="Profile 1",
            email="user1@example.com",
            apiUrl="https://api1.example.com",
            isActive=True,
            createdAt=datetime.now(),
        )

        store = ProfileStore(
            profiles={"profile-1": profile},
            activeProfileId="profile-1",
        )
        save_profile_store(store)

        with patch("cforge.commands.settings.profiles.get_console", return_value=mock_console):
            with patch("cforge.commands.settings.profiles.set_active_profile", side_effect=Exception("Test error")):
                with pytest.raises(typer.Exit) as exc_info:
                    profiles_switch(profile_id="profile-1")

        assert exc_info.value.exit_code == 1
        assert any("Error switching profile" in str(call) for call in mock_console.print.call_args_list)

    def test_profiles_switch_failed_to_switch(self, mock_console, mock_settings) -> None:
        """Test switching profiles when set_active_profile returns False."""
        profile = AuthProfile(
            id="profile-1",
            name="Profile 1",
            email="user1@example.com",
            apiUrl="https://api1.example.com",
            isActive=True,
            createdAt=datetime.now(),
        )

        store = ProfileStore(
            profiles={"profile-1": profile},
            activeProfileId="profile-1",
        )
        save_profile_store(store)

        with patch("cforge.commands.settings.profiles.get_console", return_value=mock_console):
            with patch("cforge.commands.settings.profiles.set_active_profile", return_value=False):
                with pytest.raises(typer.Exit) as exc_info:
                    profiles_switch(profile_id="profile-1")

        assert exc_info.value.exit_code == 1
        assert any("Failed to switch to profile" in str(call) for call in mock_console.print.call_args_list)


class TestProfilesCreate:
    """Tests for profiles create command."""

    def test_profiles_create_success(self, mock_console, mock_settings) -> None:
        """Test successfully creating a new profile."""
        with patch("cforge.commands.settings.profiles.get_console", return_value=mock_console):
            with patch("cforge.commands.settings.profiles.prompt_for_schema") as mock_prompt:
                with patch("cforge.commands.settings.profiles.typer.confirm", return_value=False):
                    # Mock the prompt to return profile data
                    mock_prompt.return_value = {
                        "id": "test-profile-id",
                        "name": "Test Profile",
                        "email": "test@example.com",
                        "api_url": "https://api.test.com",
                        "is_active": False,
                        "created_at": datetime.now(),
                    }

                    profiles_create(None)

        # Verify success message
        print_calls = [str(call) for call in mock_console.print.call_args_list]
        assert any("Profile created successfully" in call for call in print_calls)
        assert any("Test Profile" in call for call in print_calls)

    def test_profiles_create_and_enable(self, mock_console, mock_settings) -> None:
        """Test creating a profile and enabling it."""
        with patch("cforge.commands.settings.profiles.get_console", return_value=mock_console):
            with patch("cforge.commands.settings.profiles.prompt_for_schema") as mock_prompt:
                with patch("cforge.commands.settings.profiles.typer.confirm", return_value=True):
                    with patch("cforge.commands.settings.profiles.set_active_profile", return_value=True) as set_active_profile_mock:
                        with patch("cforge.commands.settings.profiles.get_settings") as mock_get_settings:
                            mock_get_settings.cache_clear = Mock()

                            # Mock the prompt to return profile data
                            mock_prompt.return_value = {
                                "id": "test-profile-id",
                                "name": "Test Profile",
                                "email": "test@example.com",
                                "api_url": "https://api.test.com",
                                "is_active": False,
                                "created_at": datetime.now(),
                            }

                            profiles_create(None)

        # Verify success and enable messages
        print_calls = [str(call) for call in mock_console.print.call_args_list]
        assert any("Profile created successfully" in call for call in print_calls)
        assert any("Profile enabled" in call for call in print_calls)
        set_active_profile_mock.assert_called_with("test-profile-id")

    def test_profiles_create_error(self, mock_console, mock_settings) -> None:
        """Test creating profile with an error."""
        with patch("cforge.commands.settings.profiles.get_console", return_value=mock_console):
            with patch("cforge.commands.settings.profiles.prompt_for_schema", side_effect=Exception("Test error")):
                with pytest.raises(typer.Exit) as exc_info:
                    profiles_create(None)

        assert exc_info.value.exit_code == 1
        assert any("Error creating profile" in str(call) for call in mock_console.print.call_args_list)

    def test_profiles_create_enable_fails(self, mock_console, mock_settings) -> None:
        """Test creating profile but enabling fails."""
        with patch("cforge.commands.settings.profiles.get_console", return_value=mock_console):
            with patch("cforge.commands.settings.profiles.prompt_for_schema") as mock_prompt:
                with patch("cforge.commands.settings.profiles.typer.confirm", return_value=True):
                    with patch("cforge.commands.settings.profiles.set_active_profile", return_value=False):
                        # Mock the prompt to return profile data
                        mock_prompt.return_value = {
                            "id": "test-profile-id",
                            "name": "Test Profile",
                            "email": "test@example.com",
                            "api_url": "https://api.test.com",
                            "is_active": False,
                            "created_at": datetime.now(),
                        }

                        profiles_create(None)

        # Verify failure message
        print_calls = [str(call) for call in mock_console.print.call_args_list]
        assert any("Failed to enable profile" in call for call in print_calls)

    def test_profiles_create_with_existing_store(self, mock_console, mock_settings) -> None:
        """Test creating a profile when a profile store already exists."""
        from cforge.profile_utils import load_profile_store

        # Create an existing profile store
        existing_profile = AuthProfile(
            id="existing-profile",
            name="Existing Profile",
            email="existing@example.com",
            apiUrl="https://api.existing.com",
            isActive=True,
            createdAt=datetime.now(),
        )
        store = ProfileStore(
            profiles={"existing-profile": existing_profile},
            activeProfileId="existing-profile",
        )
        save_profile_store(store)

        with patch("cforge.commands.settings.profiles.get_console", return_value=mock_console):
            with patch("cforge.commands.settings.profiles.prompt_for_schema") as mock_prompt:
                with patch("cforge.commands.settings.profiles.typer.confirm", return_value=False):
                    # Mock the prompt to return profile data
                    mock_prompt.return_value = {
                        "id": "new-profile-id",
                        "name": "New Profile",
                        "email": "new@example.com",
                        "api_url": "https://api.new.com",
                        "is_active": False,
                        "created_at": datetime.now(),
                    }

                    profiles_create(None)

        # Verify both profiles exist in the store
        updated_store = load_profile_store()
        assert updated_store is not None
        assert len(updated_store.profiles) == 2
        assert "existing-profile" in updated_store.profiles
        assert "new-profile-id" in updated_store.profiles

    def test_profiles_create_data_file(self, mock_console, mock_settings) -> None:
        """Test successfully creating a new profile using a data file."""
        with patch("cforge.commands.settings.profiles.get_console", return_value=mock_console):
            with patch("cforge.commands.settings.profiles.typer.confirm", return_value=False):
                data_file_content = {
                    "name": "Test Profile",
                    "email": "test@example.com",
                    "api_url": "https://api.test.com",
                    "is_active": False,
                }
                with tempfile.NamedTemporaryFile("w") as data_file:
                    data_file.write(json.dumps(data_file_content))
                    data_file.flush()
                    profiles_create(Path(data_file.name))

        # Verify both profiles exist in the store
        updated_store = load_profile_store()
        assert updated_store is not None
        assert len(updated_store.profiles) == 1
        profile_id = list(updated_store.profiles.keys())[0]
        profile = list(updated_store.profiles.values())[0]
        assert profile.id == profile_id
        assert profile.name == data_file_content["name"]
        assert profile.email == data_file_content["email"]
        assert profile.api_url == data_file_content["api_url"]
        assert profile.is_active == data_file_content["is_active"]

    def test_profiles_create_bad_data_file(self, mock_console, mock_settings) -> None:
        """Test error handling when data file is not found"""
        with patch("cforge.commands.settings.profiles.get_console", return_value=mock_console):
            with patch("cforge.commands.settings.profiles.typer.confirm", return_value=False):
                with pytest.raises(typer.Exit) as exc_info:
                    profiles_create(mock_settings.contextforge_home / "does" / "not" / "exist")
                assert exc_info.value.exit_code == 1
