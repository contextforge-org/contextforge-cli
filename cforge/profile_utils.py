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
            return None


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
    """Get all profiles.

    Returns:
        List of all profiles, empty list if none found
    """
    if store := load_profile_store():
        return list(store.profiles.values())
    return []


def get_profile(profile_id: str) -> Optional[AuthProfile]:
    """Get a specific profile by ID.

    Args:
        profile_id: Profile ID to retrieve

    Returns:
        AuthProfile if found, None otherwise
    """
    if store := load_profile_store():
        return store.profiles.get(profile_id)


def get_active_profile() -> Optional[AuthProfile]:
    """Get the currently active profile.

    Returns:
        AuthProfile if an active profile is set, None otherwise
    """
    if (store := load_profile_store()) and store.active_profile_id:
        return store.profiles.get(store.active_profile_id)


def set_active_profile(profile_id: str) -> bool:
    """Set the active profile.

    Args:
        profile_id: Profile ID to set as active

    Returns:
        True if successful, False if profile not found
    """
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
