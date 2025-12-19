# -*- coding: utf-8 -*-
"""Location: ./cforge/profile_utils.py
Copyright 2025
SPDX-License-Identifier: Apache-2.0
Authors: Gabe Goodhart

Profile management utilities for Context Forge CLI.
Reads profile data from the Desktop app's electron-store files.
"""

# Standard
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional
import json

# Third-Party
from pydantic import BaseModel, Field, ValidationInfo, field_validator

# Local
from cforge.config import get_settings

# Virtual default profile ID for local development
DEFAULT_PROFILE_ID = "__default__"


class ProfileMetadata(BaseModel):
    """Metadata for a profile."""

    description: Optional[str] = None
    environment: Optional[str] = None  # 'production', 'staging', 'development', 'local'
    color: Optional[str] = None
    icon: Optional[str] = None
    is_internal: Optional[bool] = Field(None, alias="isInternal")

    class Config:
        """Pydantic model config"""

        # Map naming conventions
        populate_by_name = True


class AuthProfile(BaseModel):
    """Authentication profile matching the Desktop app schema."""

    id: str
    name: str
    email: str
    api_url: str = Field(alias="apiUrl")
    is_active: bool = Field(alias="isActive")
    created_at: datetime = Field(alias="createdAt")
    last_used: Optional[datetime] = Field(None, alias="lastUsed")
    metadata: Optional[ProfileMetadata] = None

    class Config:
        """Pydantic model config"""

        # Map naming conventions
        populate_by_name = True


class ProfileStore(BaseModel):
    """Profile store structure matching the Desktop app schema."""

    profiles: Dict[str, AuthProfile] = {}
    active_profile_id: Optional[str] = Field(None, alias="activeProfileId")

    class Config:
        """Pydantic model config"""

        # Map naming conventions
        populate_by_name = True

    @field_validator("profiles")
    def validate_profiles(cls, profiles: Dict[str, AuthProfile]) -> Dict[str, AuthProfile]:
        """Validate that IDs match between keys and profile objects and only one
        profile is active
        """
        if any(key != val.id for key, val in profiles.items()):
            raise ValueError(f"key/id mismatch: {profiles}")
        if len([p.id for p in profiles.values() if p.is_active]) > 1:
            raise ValueError(f"Found multiple active profiles: {[profiles]}")
        return profiles

    @field_validator("active_profile_id")
    def validate_active_profile_id(cls, active_profile_id: Optional[str], info: ValidationInfo) -> Optional[str]:
        """Validate that the given active_profile_id corresponds to the given
        profiles
        """
        if active_profile_id is None:
            return active_profile_id

        if not (profiles := info.data.get("profiles")):
            raise ValueError(f"Cannot set active_profile_id={active_profile_id} without providing profiles")
        if not (active_profile := profiles.get(active_profile_id)):
            raise ValueError(f"active_profile_id={active_profile_id} not present in profiles={profiles}")
        if not active_profile.is_active:
            raise ValueError(f"active_profile_id={active_profile_id} is not marked as active in profiles={profiles}")

        return active_profile_id


def get_default_api_url() -> str:
    """Get the default API URL if not set via a profile

    Returns:
        URL based on configured settings
    """
    return f"http://{get_settings().host}:{get_settings().port}"


def get_profile_store_path() -> Path:
    """Get the path to the profile store file.

    Returns:
        Path to the profile store JSON file
    """
    return get_settings().contextforge_home / "context-forge-profiles.json"


def load_profile_store() -> Optional[ProfileStore]:
    """Load the profile store from disk.

    Returns:
        ProfileStore if found and valid, None otherwise
    """
    if (store_path := get_profile_store_path()) and store_path.exists():
        try:
            with open(store_path, "r", encoding="utf-8") as f:
                data = json.load(f)
                return ProfileStore.model_validate(data)
        except (json.JSONDecodeError, ValueError) as e:
            print(f"Warning: Failed to load profile store: {e}")


def save_profile_store(store: ProfileStore) -> None:
    """Save the profile store to disk.

    Args:
        store: ProfileStore to save
    """
    store_path = get_profile_store_path()
    store_path.parent.mkdir(exist_ok=True)

    with open(store_path, "w", encoding="utf-8") as f:
        # Convert to dict with original field names (camelCase)
        data = store.model_dump(by_alias=True)
        json.dump(data, f, indent=2, default=str)


def get_all_profiles() -> List[AuthProfile]:
    """Get all profiles, including the virtual default profile.

    Returns:
        List of all profiles, including virtual default if no Desktop default exists
    """
    profiles = []
    if store := load_profile_store():
        profiles = list(store.profiles.values())

    # Check if Desktop app has created a default profile
    expected_default_url = get_default_api_url()
    has_desktop_default = any(p.api_url == expected_default_url and p.metadata and p.metadata.is_internal for p in profiles)

    # Only include virtual default if Desktop hasn't created one
    if not has_desktop_default:
        default_profile = AuthProfile(
            id=DEFAULT_PROFILE_ID,
            name="Local Default",
            email="admin@localhost",
            api_url=expected_default_url,
            is_active=not bool(store and store.active_profile_id),
            created_at=datetime.now(),
            metadata=ProfileMetadata(
                description="Default local development profile",
                environment="local",
            ),
        )
        profiles.append(default_profile)

    return profiles


def get_profile(profile_id: str) -> Optional[AuthProfile]:
    """Get a specific profile by ID, including the virtual default profile.

    Args:
        profile_id: Profile ID to retrieve

    Returns:
        AuthProfile if found, None otherwise
    """
    # Check for virtual default profile
    if profile_id == DEFAULT_PROFILE_ID:
        store = load_profile_store()
        return AuthProfile(
            id=DEFAULT_PROFILE_ID,
            name="Local Default",
            email="admin@localhost",
            api_url=get_default_api_url(),
            is_active=not bool(store and store.active_profile_id),
            created_at=datetime.now(),
            metadata=ProfileMetadata(
                description="Default local development profile",
                environment="local",
            ),
        )

    if store := load_profile_store():
        return store.profiles.get(profile_id)


def get_active_profile() -> AuthProfile:
    """Get the currently active profile, including the virtual default profile.

    Returns:
        AuthProfile if an active profile is set, or default (virtual or desktop)
    """
    if (store := load_profile_store()) and store.active_profile_id:
        profile = store.profiles.get(store.active_profile_id)
        # This should be unreachable due to validation on loading
        assert profile, "BAD STATE: Profile store active profile id not found in profiles"
        return profile

    # Check if Desktop app has created a default profile
    expected_default_url = get_default_api_url()

    if store:
        for profile in store.profiles.values():
            if profile.api_url == expected_default_url and profile.metadata and profile.metadata.is_internal:
                # If Desktop default exists, use that
                return profile

    # Return virtual default profile if no Desktop default exists
    return AuthProfile(
        id=DEFAULT_PROFILE_ID,
        name="Local Default",
        email="admin@localhost",
        api_url=expected_default_url,
        is_active=True,
        created_at=datetime.now(),
        metadata=ProfileMetadata(
            description="Default local development profile",
            environment="local",
        ),
    )


def set_active_profile(profile_id: str) -> bool:
    """Set the active profile, including support for the virtual default profile.

    Args:
        profile_id: Profile ID to set as active

    Returns:
        True if successful, False if profile not found
    """
    # Handle virtual default profile
    if profile_id == DEFAULT_PROFILE_ID:
        if store := load_profile_store():
            # Deactivate all profiles to switch to default
            for pid in store.profiles:
                store.profiles[pid].is_active = False
            store.active_profile_id = None
            save_profile_store(store)
        # Always return True for default profile (it always exists)
        return True

    store = load_profile_store()
    if not store:
        return False

    if profile_id not in store.profiles:
        return False

    # Update all profiles to inactive
    for pid in store.profiles:
        store.profiles[pid].is_active = False

    # Set the selected profile as active
    store.profiles[profile_id].is_active = True
    store.profiles[profile_id].last_used = datetime.now()
    store.active_profile_id = profile_id

    save_profile_store(store)
    return True
