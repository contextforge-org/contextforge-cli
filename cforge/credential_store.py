# -*- coding: utf-8 -*-
"""Location: ./cforge/credential_store.py
Copyright 2025
SPDX-License-Identifier: Apache-2.0
Authors: Gabe Goodhart

Credential storage utilities compatible with desktop app's electron-store encryption.
"""

# Standard
import json
from pathlib import Path
from typing import Optional

# Third-Party
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC

# First-Party
from cforge.config import get_settings


def get_credential_store_path() -> Path:
    """Get the path to the encrypted credential store file.

    Returns:
        Path to the credential store JSON file
    """
    return get_settings().contextforge_home / "context-forge-credentials.json"


def get_encryption_key_path() -> Path:
    """Get the path to the encryption key file.

    Returns:
        Path to the encryption key JSON file
    """
    return get_settings().contextforge_home / "context-forge-keys.json"


def load_encryption_key() -> Optional[str]:
    """Load the encryption key from the key store.

    Returns:
        Encryption key string if found, None otherwise
    """
    key_path = get_encryption_key_path()
    if not key_path.exists():
        return None

    try:
        with open(key_path, "r", encoding="utf-8") as f:
            data = json.load(f)
            return data.get("encryptionKey")
    except (json.JSONDecodeError, OSError) as e:
        print(f"Warning: Failed to load encryption key: {e}")
        return None


def decrypt_credential_data(encrypted_data: bytes, encryption_key: str) -> Optional[str]:
    """Decrypt credential data using the same format as electron-store/conf.

    The format is: [16 bytes IV][':'][encrypted data]
    Uses AES-256-CBC with PBKDF2 key derivation (10,000 iterations, SHA-512)

    Args:
        encrypted_data: The encrypted data bytes
        encryption_key: The encryption key string

    Returns:
        Decrypted string if successful, None otherwise
    """
    try:
        # Extract IV from first 16 bytes
        if len(encrypted_data) < 17:
            return None

        iv = encrypted_data[:16]

        # Verify separator (should be ':' at byte 16)
        if encrypted_data[16:17] != b":":
            # Try legacy format without separator
            encrypted_payload = encrypted_data[16:]
        else:
            # Skip IV and ':' separator (17 bytes total)
            encrypted_payload = encrypted_data[17:]

        # Derive key using PBKDF2 with same parameters as conf package
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA512(),
            length=32,  # 32 bytes = 256 bits for AES-256
            salt=iv,  # IV is used as salt
            iterations=10_000,
            backend=default_backend(),
        )
        key = kdf.derive(encryption_key.encode("utf-8"))

        # Decrypt using AES-256-CBC
        cipher = Cipher(algorithms.AES(key), modes.CBC(iv), backend=default_backend())
        decryptor = cipher.decryptor()
        decrypted_data = decryptor.update(encrypted_payload) + decryptor.finalize()

        # Remove PKCS7 padding
        padding_length = decrypted_data[-1]
        decrypted_data = decrypted_data[:-padding_length]

        return decrypted_data.decode("utf-8")
    except Exception as e:
        print(f"Warning: Failed to decrypt credential data: {e}")
        return None


def load_profile_credentials(profile_id: str) -> Optional[dict]:
    """Load credentials for a specific profile from the encrypted store.

    Args:
        profile_id: The profile ID to load credentials for

    Returns:
        Dictionary with 'email' and 'password' if found, None otherwise
    """
    # Load encryption key
    encryption_key = load_encryption_key()
    if not encryption_key:
        return None

    # Load encrypted credential store
    cred_path = get_credential_store_path()
    if not cred_path.exists():
        return None

    try:
        # Read the encrypted file as bytes
        with open(cred_path, "rb") as f:
            encrypted_data = f.read()

        # Decrypt the data
        decrypted_json = decrypt_credential_data(encrypted_data, encryption_key)
        if not decrypted_json:
            return None

        # Parse JSON
        credentials = json.loads(decrypted_json)

        # Get credentials for the specific profile
        profile_creds = credentials.get(profile_id)
        if not profile_creds:
            return None

        return {
            "email": profile_creds.get("email"),
            "password": profile_creds.get("password"),
        }
    except (json.JSONDecodeError, OSError) as e:
        print(f"Warning: Failed to load profile credentials: {e}")
        return None
