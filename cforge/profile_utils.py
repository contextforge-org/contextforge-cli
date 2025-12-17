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
from typing import Dict, List, Optional, Tuple
from urllib.parse import urlparse
import json

# Third-Party
from pydantic import BaseModel, Field


class ProfileMetadata(BaseModel):
    """Metadata for a profile."""

    description: Optional[str] = None
    environment: Optional[str] = None  # 'production', 'staging', 'development', 'local'
    color: Optional[str] = None
    icon: Optional[str] = None
    is_internal: Optional[bool] = Field(None, alias="isInternal")

    class Config:
        """Pydantic model config"""

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

        populate_by_name = True


class ProfileStore(BaseModel):
    """Profile store structure matching the Desktop app schema."""

    profiles: Dict[str, AuthProfile] = {}
    active_profile_id: Optional[str] = Field(None, alias="activeProfileId")

    class Config:
        """Pydantic model config"""

        populate_by_name = True


def get_contextforge_home() -> Path:
    """Get the Context Forge home directory.

    Returns:
        Path to the Context Forge home directory
    """
    from cforge.config import get_settings

    return get_settings().contextforge_home


def get_profile_store_path() -> Path:
    """Get the path to the profile store file.

    Returns:
        Path to the profile store JSON file
    """
    return get_contextforge_home() / "context-forge-profiles.json"


def load_profile_store() -> Optional[ProfileStore]:
    """Load the profile store from disk.

    Returns:
        ProfileStore if found and valid, None otherwise
    """
    store_path = get_profile_store_path()
    if not store_path.exists():
        return None

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
    store_path.parent.mkdir(parents=True, exist_ok=True)

    with open(store_path, "w", encoding="utf-8") as f:
        # Convert to dict with original field names (camelCase)
        data = store.model_dump(by_alias=True)
        json.dump(data, f, indent=2, default=str)


def get_all_profiles() -> List[AuthProfile]:
    """Get all profiles.

    Returns:
        List of all profiles, empty list if none found
    """
    store = load_profile_store()
    if not store:
        return []

    return list(store.profiles.values())


def get_profile(profile_id: str) -> Optional[AuthProfile]:
    """Get a specific profile by ID.

    Args:
        profile_id: Profile ID to retrieve

    Returns:
        AuthProfile if found, None otherwise
    """
    store = load_profile_store()
    if not store:
        return None

    return store.profiles.get(profile_id)


def get_active_profile() -> Optional[AuthProfile]:
    """Get the currently active profile.

    Returns:
        AuthProfile if an active profile is set, None otherwise
    """
    store = load_profile_store()
    if not store or not store.active_profile_id:
        return None

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


def parse_api_url(api_url: str) -> Tuple[str, int]:
    """Parse an API URL into host and port.

    Args:
        api_url: API URL to parse (e.g., 'http://localhost:4444')

    Returns:
        Tuple of (host, port)
    """
    parsed = urlparse(api_url)
    host = parsed.hostname or "localhost"
    port = parsed.port or (443 if parsed.scheme == "https" else 80)
    return host, port


def get_active_host_port() -> Tuple[str, int]:
    """Get the host and port from the active profile.

    Returns:
        Tuple of (host, port), defaults to ('localhost', 4444) if no active profile
    """
    profile = get_active_profile()
    if not profile:
        return "localhost", 4444

    return parse_api_url(profile.api_url)
