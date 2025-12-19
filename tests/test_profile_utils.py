# -*- coding: utf-8 -*-
"""Location: ./tests/test_profile_utils.py
Copyright 2025
SPDX-License-Identifier: Apache-2.0
Authors: Gabe Goodhart

Tests for profile management utilities.
"""

# Standard
import json
from datetime import datetime
from pathlib import Path

# First-Party
from cforge.profile_utils import (
    AuthProfile,
    DEFAULT_PROFILE_ID,
    ProfileMetadata,
    ProfileStore,
    get_all_profiles,
    get_active_profile,
    get_profile,
    get_profile_store_path,
    load_profile_store,
    save_profile_store,
    set_active_profile,
)


class TestProfileModels:
    """Tests for Pydantic profile models."""

    def test_profile_metadata_creation(self) -> None:
        """Test creating ProfileMetadata with various fields."""
        metadata = ProfileMetadata(
            description="Test profile",
            environment="production",
            color="#FF0000",
            icon="🚀",
            isInternal=True,
        )

        assert metadata.description == "Test profile"
        assert metadata.environment == "production"
        assert metadata.color == "#FF0000"
        assert metadata.icon == "🚀"
        assert metadata.is_internal is True

    def test_profile_metadata_optional_fields(self) -> None:
        """Test ProfileMetadata with optional fields omitted."""
        metadata = ProfileMetadata()

        assert metadata.description is None
        assert metadata.environment is None
        assert metadata.color is None
        assert metadata.icon is None
        assert metadata.is_internal is None

    def test_auth_profile_creation(self) -> None:
        """Test creating AuthProfile with required fields."""
        now = datetime.now()
        profile = AuthProfile(
            id="profile-123",
            name="Test Profile",
            email="test@example.com",
            apiUrl="https://api.example.com",
            isActive=True,
            createdAt=now,
            lastUsed=now,
        )

        assert profile.id == "profile-123"
        assert profile.name == "Test Profile"
        assert profile.email == "test@example.com"
        assert profile.api_url == "https://api.example.com"
        assert profile.is_active is True
        assert profile.created_at == now
        assert profile.last_used == now

    def test_auth_profile_with_metadata(self) -> None:
        """Test AuthProfile with metadata."""
        metadata = ProfileMetadata(environment="staging")
        profile = AuthProfile(
            id="profile-123",
            name="Test Profile",
            email="test@example.com",
            apiUrl="https://api.example.com",
            isActive=False,
            createdAt=datetime.now(),
            metadata=metadata,
        )

        assert profile.metadata is not None
        assert profile.metadata.environment == "staging"

    def test_profile_store_creation(self) -> None:
        """Test creating ProfileStore."""
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

        ProfileStore(
            profiles={"profile-1": profile1, "profile-2": profile2},
            activeProfileId="profile-1",
        )

    def test_profile_store_key_id_mismatch(self) -> None:
        """Test ProfileStore validation fails when key doesn't match profile ID."""
        profile = AuthProfile(
            id="profile-1",
            name="Profile 1",
            email="user1@example.com",
            apiUrl="https://api1.example.com",
            isActive=True,
            createdAt=datetime.now(),
        )

        try:
            ProfileStore(
                profiles={"wrong-key": profile},  # Key doesn't match profile.id
                activeProfileId="profile-1",
            )
            assert False, "Expected ValueError for key/id mismatch"
        except ValueError as e:
            assert "key/id mismatch" in str(e)

    def test_profile_store_multiple_active_profiles(self) -> None:
        """Test ProfileStore validation fails when multiple profiles are active."""
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
            isActive=True,  # Both profiles are active
            createdAt=datetime.now(),
        )

        try:
            ProfileStore(
                profiles={"profile-1": profile1, "profile-2": profile2},
                activeProfileId="profile-1",
            )
            assert False, "Expected ValueError for multiple active profiles"
        except ValueError as e:
            assert "Found multiple active profiles" in str(e)

    def test_profile_store_active_id_without_profiles(self) -> None:
        """Test ProfileStore validation fails when active_profile_id is set without profiles."""
        try:
            ProfileStore(
                profiles={},
                activeProfileId="profile-1",
            )
            assert False, "Expected ValueError for active_profile_id without profiles"
        except ValueError as e:
            assert "Cannot set active_profile_id" in str(e)
            assert "without providing profiles" in str(e)

    def test_profile_store_active_id_not_in_profiles(self) -> None:
        """Test ProfileStore validation fails when active_profile_id is not in profiles."""
        profile = AuthProfile(
            id="profile-1",
            name="Profile 1",
            email="user1@example.com",
            apiUrl="https://api1.example.com",
            isActive=True,
            createdAt=datetime.now(),
        )

        try:
            ProfileStore(
                profiles={"profile-1": profile},
                activeProfileId="profile-2",  # ID not in profiles
            )
            assert False, "Expected ValueError for active_profile_id not in profiles"
        except ValueError as e:
            assert "not present in profiles" in str(e)

    def test_profile_store_active_id_not_marked_active(self) -> None:
        """Test ProfileStore validation fails when active_profile_id profile is not marked active."""
        profile = AuthProfile(
            id="profile-1",
            name="Profile 1",
            email="user1@example.com",
            apiUrl="https://api1.example.com",
            isActive=False,  # Not marked as active
            createdAt=datetime.now(),
        )

        try:
            ProfileStore(
                profiles={"profile-1": profile},
                activeProfileId="profile-1",
            )
            assert False, "Expected ValueError for active_profile_id not marked as active"
        except ValueError as e:
            assert "is not marked as active" in str(e)

    def test_profile_store_active_id_mismatch(self) -> None:
        """Test ProfileStore validation fails when active_profile_id doesn't match the active profile."""
        profile1 = AuthProfile(
            id="profile-1",
            name="Profile 1",
            email="user1@example.com",
            apiUrl="https://api1.example.com",
            isActive=False,
            createdAt=datetime.now(),
        )
        profile2 = AuthProfile(
            id="profile-2",
            name="Profile 2",
            email="user2@example.com",
            apiUrl="https://api2.example.com",
            isActive=True,  # profile-2 is active
            createdAt=datetime.now(),
        )

        try:
            ProfileStore(
                profiles={"profile-1": profile1, "profile-2": profile2},
                activeProfileId="profile-1",  # But active_profile_id points to profile-1
            )
            assert False, "Expected ValueError for active profile ID mismatch"
        except ValueError as e:
            assert "is not marked as active" in str(e)

    def test_profile_store_empty(self) -> None:
        """Test creating empty ProfileStore."""
        store = ProfileStore()

        assert len(store.profiles) == 0
        assert store.active_profile_id is None


class TestProfileStorePath:
    """Tests for profile store path functions."""

    def test_get_profile_store_path(self, mock_settings) -> None:
        """Test getting the profile store path."""
        path = get_profile_store_path()

        assert isinstance(path, Path)
        assert path.name == "context-forge-profiles.json"
        assert mock_settings.contextforge_home == path.parent


class TestLoadProfileStore:
    """Tests for loading profile store."""

    def test_load_profile_store_success(self, mock_settings) -> None:
        """Test successfully loading a profile store."""
        # Create a test profile store file
        store_path = get_profile_store_path()
        store_path.parent.mkdir(exist_ok=True)

        test_data = {
            "profiles": {
                "profile-1": {
                    "id": "profile-1",
                    "name": "Test Profile",
                    "email": "test@example.com",
                    "apiUrl": "https://api.example.com",
                    "isActive": True,
                    "createdAt": "2025-01-01T00:00:00",
                }
            },
            "activeProfileId": "profile-1",
        }

        with open(store_path, "w", encoding="utf-8") as f:
            json.dump(test_data, f)

        store = load_profile_store()

        assert store is not None
        assert len(store.profiles) == 1
        assert store.active_profile_id == "profile-1"
        assert "profile-1" in store.profiles

    def test_load_profile_store_not_found(self, mock_settings) -> None:
        """Test loading when profile store doesn't exist."""
        store = load_profile_store()

        assert store is None

    def test_load_profile_store_invalid_json(self, mock_settings) -> None:
        """Test loading with invalid JSON."""
        store_path = get_profile_store_path()
        store_path.parent.mkdir(exist_ok=True)

        with open(store_path, "w", encoding="utf-8") as f:
            f.write("invalid json {")

        store = load_profile_store()

        assert store is None

    def test_load_profile_store_invalid_schema(self, mock_settings) -> None:
        """Test loading with invalid schema."""
        store_path = get_profile_store_path()
        store_path.parent.mkdir(exist_ok=True)

        # Missing required fields
        test_data = {"profiles": {}}

        with open(store_path, "w", encoding="utf-8") as f:
            json.dump(test_data, f)

        store = load_profile_store()

        # Should still load with defaults
        assert store is not None
        assert len(store.profiles) == 0


class TestSaveProfileStore:
    """Tests for saving profile store."""

    def test_save_profile_store_success(self, mock_settings) -> None:
        """Test successfully saving a profile store."""
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

        # Verify file was created
        store_path = get_profile_store_path()
        assert store_path.exists()

        # Verify content
        with open(store_path, "r", encoding="utf-8") as f:
            data = json.load(f)

        assert "profiles" in data
        assert "profile-1" in data["profiles"]
        assert data["activeProfileId"] == "profile-1"
        assert data["profiles"]["profile-1"]["apiUrl"] == "https://api.example.com"

    def test_save_profile_store_creates_directory(self, mock_settings) -> None:
        """Test that save creates parent directory if needed."""
        store = ProfileStore()
        store_path = get_profile_store_path()

        # Ensure directory doesn't exist
        if store_path.parent.exists():
            import shutil

            shutil.rmtree(store_path.parent)

        save_profile_store(store)

        assert store_path.parent.exists()
        assert store_path.exists()


class TestGetAllProfiles:
    """Tests for getting all profiles."""

    def test_get_all_profiles_success(self, mock_settings) -> None:
        """Test getting all profiles (includes virtual default)."""
        # Create test profiles
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

        profiles = get_all_profiles()

        # Should include 2 profiles + virtual default
        assert len(profiles) == 3
        assert any(p.id == "profile-1" for p in profiles)
        assert any(p.id == "profile-2" for p in profiles)
        assert any(p.id == DEFAULT_PROFILE_ID for p in profiles)

    def test_get_all_profiles_empty(self, mock_settings) -> None:
        """Test getting profiles when none exist (returns virtual default)."""
        profiles = get_all_profiles()

        # Should return only the virtual default profile
        assert len(profiles) == 1
        assert profiles[0].id == DEFAULT_PROFILE_ID
        assert profiles[0].name == "Local Default"


class TestGetProfile:
    """Tests for getting a specific profile."""

    def test_get_profile_success(self, mock_settings) -> None:
        """Test getting a specific profile by ID."""
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

        result = get_profile("profile-1")

        assert result is not None
        assert result.id == "profile-1"
        assert result.name == "Test Profile"

    def test_get_profile_not_found(self, mock_settings) -> None:
        """Test getting a profile that doesn't exist."""
        result = get_profile("nonexistent")

        assert result is None

    def test_get_profile_no_store(self, mock_settings) -> None:
        """Test getting a profile when store doesn't exist."""
        result = get_profile("profile-1")

        assert result is None


class TestGetActiveProfile:
    """Tests for getting the active profile."""

    def test_get_active_profile_success(self, mock_settings) -> None:
        """Test getting the active profile."""
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

        result = get_active_profile()

        assert result is not None
        assert result.id == "profile-1"
        assert result.is_active is True

    def test_get_active_profile_none_set(self, mock_settings) -> None:
        """Test getting active profile when none is set (returns virtual default)."""
        profile = AuthProfile(
            id="profile-1",
            name="Profile 1",
            email="user1@example.com",
            apiUrl="https://api1.example.com",
            isActive=False,
            createdAt=datetime.now(),
        )

        store = ProfileStore(
            profiles={"profile-1": profile},
            activeProfileId=None,
        )
        save_profile_store(store)

        result = get_active_profile()

        # Should return virtual default profile
        assert result is not None
        assert result.id == DEFAULT_PROFILE_ID
        assert result.name == "Local Default"
        assert result.is_active is True

    def test_get_active_profile_no_store(self, mock_settings) -> None:
        """Test getting active profile when store doesn't exist (returns virtual default)."""
        result = get_active_profile()

        # Should return virtual default profile
        assert result is not None
        assert result.id == DEFAULT_PROFILE_ID
        assert result.name == "Local Default"
        assert result.is_active is True


class TestSetActiveProfile:
    """Tests for setting the active profile."""

    def test_set_active_profile_success(self, mock_settings) -> None:
        """Test successfully setting the active profile."""
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

        # Switch to profile-2
        result = set_active_profile("profile-2")

        assert result is True

        # Verify the change
        updated_store = load_profile_store()
        assert updated_store is not None
        assert updated_store.active_profile_id == "profile-2"
        assert updated_store.profiles["profile-2"].is_active is True
        assert updated_store.profiles["profile-1"].is_active is False
        assert updated_store.profiles["profile-2"].last_used is not None

    def test_set_active_profile_not_found(self, mock_settings) -> None:
        """Test setting active profile when profile doesn't exist."""
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

        result = set_active_profile("nonexistent")

        assert result is False

    def test_set_active_profile_no_store(self, mock_settings) -> None:
        """Test setting active profile when store doesn't exist."""
        result = set_active_profile("profile-1")

        assert result is False

    def test_set_active_profile_updates_last_used(self, mock_settings) -> None:
        """Test that setting active profile updates last_used timestamp."""
        profile = AuthProfile(
            id="profile-1",
            name="Profile 1",
            email="user1@example.com",
            apiUrl="https://api1.example.com",
            isActive=False,
            createdAt=datetime.now(),
            lastUsed=None,
        )

        store = ProfileStore(
            profiles={"profile-1": profile},
            activeProfileId=None,
        )
        save_profile_store(store)

        # Set as active
        result = set_active_profile("profile-1")

        assert result is True

        # Verify last_used was updated
        updated_store = load_profile_store()
        assert updated_store is not None
        assert updated_store.profiles["profile-1"].last_used is not None


class TestDesktopDefaultProfile:
    """Tests for Desktop app default profile detection."""

    def test_get_all_profiles_with_desktop_default(self, mock_settings) -> None:
        """Test that virtual default is not included when Desktop default exists."""
        # Create a Desktop-created default profile
        desktop_default = AuthProfile(
            id="random-desktop-id",
            name="Desktop Default",
            email="admin@localhost",
            apiUrl=f"http://{mock_settings.host}:{mock_settings.port}",
            isActive=True,
            createdAt=datetime.now(),
            metadata=ProfileMetadata(
                description="Desktop default profile",
                environment="local",
                is_internal=True,
            ),
        )

        store = ProfileStore(
            profiles={"random-desktop-id": desktop_default},
            activeProfileId="random-desktop-id",
        )
        save_profile_store(store)

        profiles = get_all_profiles()

        # Should only have the Desktop default, not the virtual default
        assert len(profiles) == 1
        assert profiles[0].id == "random-desktop-id"
        assert profiles[0].metadata.is_internal is True
        assert not any(p.id == DEFAULT_PROFILE_ID for p in profiles)

    def test_get_all_profiles_without_desktop_default(self, mock_settings) -> None:
        """Test that virtual default is included when no Desktop default exists."""
        # Create a non-default profile
        profile = AuthProfile(
            id="profile-1",
            name="Custom Profile",
            email="user@example.com",
            apiUrl="https://api.example.com",
            isActive=True,
            createdAt=datetime.now(),
        )

        store = ProfileStore(
            profiles={"profile-1": profile},
            activeProfileId="profile-1",
        )
        save_profile_store(store)

        profiles = get_all_profiles()

        # Should have both the custom profile and virtual default
        assert len(profiles) == 2
        assert any(p.id == "profile-1" for p in profiles)
        assert any(p.id == DEFAULT_PROFILE_ID for p in profiles)

    def test_get_active_profile_with_desktop_default_inactive(self, mock_settings) -> None:
        """Test that the desktop default is returned when Desktop default exists but is not active."""
        # Create a Desktop-created default profile that is NOT active
        desktop_default = AuthProfile(
            id="random-desktop-id",
            name="Desktop Default",
            email="admin@localhost",
            apiUrl=f"http://{mock_settings.host}:{mock_settings.port}",
            isActive=False,
            createdAt=datetime.now(),
            metadata=ProfileMetadata(
                description="Desktop default profile",
                environment="local",
                is_internal=True,
            ),
        )

        store = ProfileStore(
            profiles={"random-desktop-id": desktop_default},
            activeProfileId=None,
        )
        save_profile_store(store)

        result = get_active_profile()

        # Should return None because Desktop default exists (even if not active)
        assert result == desktop_default

    def test_get_active_profile_without_desktop_default(self, mock_settings) -> None:
        """Test that virtual default is returned when no Desktop default exists."""
        # Create a non-default profile that is NOT active
        profile = AuthProfile(
            id="profile-1",
            name="Custom Profile",
            email="user@example.com",
            apiUrl="https://api.example.com",
            isActive=False,
            createdAt=datetime.now(),
        )

        store = ProfileStore(
            profiles={"profile-1": profile},
            activeProfileId=None,
        )
        save_profile_store(store)

        result = get_active_profile()

        # Should return virtual default
        assert result is not None
        assert result.id == DEFAULT_PROFILE_ID
        assert result.name == "Local Default"

    def test_set_active_profile_default_no_store(self, mock_settings) -> None:
        """Test setting active profile to the default with no store passes"""
        result = set_active_profile(DEFAULT_PROFILE_ID)

        assert result is True
