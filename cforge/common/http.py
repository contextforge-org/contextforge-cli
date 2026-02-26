# -*- coding: utf-8 -*-
"""
SPDX-License-Identifier: Apache-2.0

HTTP and authentication primitives for gateway access.

This module owns token persistence, profile-aware auth lookup, optional
auto-login, and authenticated request dispatch. Command modules call these
helpers instead of handling auth headers and base URL resolution themselves.
"""

from pathlib import Path
from typing import Any, Dict, Optional

import requests

from cforge.common.errors import AuthenticationError, CLIError
from cforge.config import get_settings
from cforge.credential_store import load_profile_credentials
from cforge.profile_utils import DEFAULT_PROFILE_ID, get_active_profile


def get_base_url() -> str:
    """Get the full base URL for the current profile's server."""
    return get_active_profile().api_url


def get_token_file() -> Path:
    """Get the path to the token file in contextforge_home."""
    profile = get_active_profile()
    suffix = "" if profile.id == DEFAULT_PROFILE_ID else f".{profile.id}"
    return get_settings().contextforge_home / f"token{suffix}"


def save_token(token: str) -> None:
    """Save authentication token to contextforge_home/token file."""
    token_file = get_token_file()
    token_file.parent.mkdir(parents=True, exist_ok=True)
    token_file.write_text(token, encoding="utf-8")
    token_file.chmod(0o600)


def load_token() -> Optional[str]:
    """Load authentication token from contextforge_home/token file."""
    token_file = get_token_file()
    if token_file.exists():
        return token_file.read_text(encoding="utf-8").strip()
    return None


def attempt_auto_login() -> Optional[str]:
    """Attempt to automatically login using stored credentials."""
    profile = get_active_profile()
    credentials = load_profile_credentials(profile.id)
    if not credentials or not credentials.get("email") or not credentials.get("password"):
        return None

    try:
        gateway_url = get_base_url()
        response = requests.post(
            f"{gateway_url}/auth/email/login",
            json={"email": credentials["email"], "password": credentials["password"]},
            headers={"Content-Type": "application/json"},
        )

        if response.status_code == 200:
            data = response.json()
            token = data.get("access_token")
            if token:
                save_token(token)
                return token
    except Exception:
        pass

    return None


def get_auth_token() -> Optional[str]:
    """Get authentication token from environment, token file, or auto-login."""
    token: Optional[str] = get_settings().mcpgateway_bearer_token
    if token:
        return token

    token = load_token()
    if token:
        return token

    token = attempt_auto_login()
    if token:
        return token

    return None


def make_authenticated_request(
    method: str,
    url: str,
    json_data: Optional[Dict[str, Any]] = None,
    params: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """Make an authenticated HTTP request to the gateway API."""
    token = get_auth_token()

    headers = {"Content-Type": "application/json"}
    if token:
        if token.startswith("Basic "):
            headers["Authorization"] = token
        else:
            headers["Authorization"] = f"Bearer {token}"

    gateway_url = get_base_url()
    full_url = f"{gateway_url}{url}"

    try:
        response = requests.request(method=method, url=full_url, json=json_data, params=params, headers=headers)

        if response.status_code in (401, 403):
            raise AuthenticationError("Authentication required but not configured. Set MCPGATEWAY_BEARER_TOKEN environment variable or run 'cforge login'.")

        if response.status_code >= 400:
            raise CLIError(f"API request failed ({response.status_code}): {response.text}")

        return response.json()

    except requests.RequestException as exception:
        raise CLIError(f"Failed to connect to gateway at {gateway_url}: {str(exception)}")
