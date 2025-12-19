# -*- coding: utf-8 -*-
"""Location: ./tests/test_credential_store.py
Copyright 2025
SPDX-License-Identifier: Apache-2.0
Authors: Gabe Goodhart

Tests for credential store functionality.
"""

# Standard
import json

# Third-Party
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC

# First-Party
from cforge.credential_store import (
    decrypt_credential_data,
    get_credential_store_path,
    get_encryption_key_path,
    load_encryption_key,
    load_profile_credentials,
)


class TestCredentialStorePaths:
    """Tests for credential store path functions."""

    def test_get_credential_store_path(self, mock_settings):
        """Test getting the credential store path."""
        path = get_credential_store_path()
        assert path == mock_settings.contextforge_home / "context-forge-credentials.json"

    def test_get_encryption_key_path(self, mock_settings):
        """Test getting the encryption key path."""
        path = get_encryption_key_path()
        assert path == mock_settings.contextforge_home / "context-forge-keys.json"


class TestEncryptionKeyLoading:
    """Tests for encryption key loading."""

    def test_load_encryption_key_success(self, mock_settings):
        """Test loading encryption key successfully."""
        key_path = get_encryption_key_path()
        key_path.parent.mkdir(parents=True, exist_ok=True)
        key_data = {"encryptionKey": "test-encryption-key-12345"}  # gitleaks:allow
        key_path.write_text(json.dumps(key_data), encoding="utf-8")

        key = load_encryption_key()
        assert key == "test-encryption-key-12345"  # gitleaks:allow

    def test_load_encryption_key_missing_file(self, mock_settings):
        """Test loading encryption key when file doesn't exist."""
        key = load_encryption_key()
        assert key is None

    def test_load_encryption_key_invalid_json(self, mock_settings):
        """Test loading encryption key with invalid JSON."""
        key_path = get_encryption_key_path()
        key_path.parent.mkdir(parents=True, exist_ok=True)
        key_path.write_text("invalid json", encoding="utf-8")

        key = load_encryption_key()
        assert key is None


class TestCredentialDecryption:
    """Tests for credential decryption."""

    def _encrypt_data(self, data: str, encryption_key: str) -> bytes:
        """Helper to encrypt data using the same format as electron-store/conf."""
        import os

        # Generate random IV
        iv = os.urandom(16)

        # Derive key using PBKDF2
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA512(),
            length=32,
            salt=iv,
            iterations=10_000,
            backend=default_backend(),
        )
        key = kdf.derive(encryption_key.encode("utf-8"))

        # Encrypt using AES-256-CBC
        cipher = Cipher(algorithms.AES(key), modes.CBC(iv), backend=default_backend())
        encryptor = cipher.encryptor()

        # Add PKCS7 padding
        data_bytes = data.encode("utf-8")
        padding_length = 16 - (len(data_bytes) % 16)
        padded_data = data_bytes + bytes([padding_length] * padding_length)

        encrypted = encryptor.update(padded_data) + encryptor.finalize()

        # Format: [IV][':'][encrypted data]
        return iv + b":" + encrypted

    def test_decrypt_credential_data_success(self):
        """Test successful credential decryption."""
        test_data = '{"test": "data"}'
        encryption_key = "test-key-12345"

        encrypted = self._encrypt_data(test_data, encryption_key)
        decrypted = decrypt_credential_data(encrypted, encryption_key)

        assert decrypted == test_data

    def test_decrypt_credential_data_wrong_key(self):
        """Test decryption with wrong key fails gracefully."""
        test_data = '{"test": "data"}'
        encryption_key = "test-key-12345"
        wrong_key = "wrong-key-67890"  # gitleaks:allow

        encrypted = self._encrypt_data(test_data, encryption_key)
        decrypted = decrypt_credential_data(encrypted, wrong_key)

        # Decryption should fail and return None or not match original
        assert decrypted is None or decrypted != test_data

    def test_decrypt_credential_data_invalid_format(self):
        """Test decryption with invalid data format."""
        decrypted = decrypt_credential_data(b"invalid data", "test-key")
        assert decrypted is None


class TestLoadProfileCredentials:
    """Tests for loading profile credentials."""

    def test_load_profile_credentials_success(self, mock_settings):
        """Test loading profile credentials successfully."""
        profile_id = "test-profile-123"
        encryption_key = "test-encryption-key"
        credentials_data = {profile_id: {"email": "test@example.com", "password": "test-password"}}

        # Setup encryption key
        key_path = get_encryption_key_path()
        key_path.parent.mkdir(parents=True, exist_ok=True)
        key_path.write_text(json.dumps({"encryptionKey": encryption_key}), encoding="utf-8")

        # Setup encrypted credentials
        cred_path = get_credential_store_path()
        encrypted_data = self._encrypt_data(json.dumps(credentials_data), encryption_key)
        cred_path.write_bytes(encrypted_data)

        # Load credentials
        creds = load_profile_credentials(profile_id)
        assert creds is not None
        assert creds["email"] == "test@example.com"
        assert creds["password"] == "test-password"

    def test_load_profile_credentials_no_key(self, mock_settings):
        """Test loading credentials when encryption key is missing."""
        creds = load_profile_credentials("test-profile")
        assert creds is None

    def test_load_profile_credentials_no_store(self, mock_settings):
        """Test loading credentials when credential store is missing."""
        # Setup encryption key only
        key_path = get_encryption_key_path()
        key_path.parent.mkdir(parents=True, exist_ok=True)
        key_path.write_text(json.dumps({"encryptionKey": "test-key"}), encoding="utf-8")

        creds = load_profile_credentials("test-profile")
        assert creds is None

    def test_load_profile_credentials_profile_not_found(self, mock_settings):
        """Test loading credentials for non-existent profile."""
        encryption_key = "test-encryption-key"
        credentials_data = {"other-profile": {"email": "other@example.com", "password": "other-password"}}

        # Setup encryption key
        key_path = get_encryption_key_path()
        key_path.parent.mkdir(parents=True, exist_ok=True)
        key_path.write_text(json.dumps({"encryptionKey": encryption_key}), encoding="utf-8")

        # Setup encrypted credentials
        cred_path = get_credential_store_path()
        encrypted_data = self._encrypt_data(json.dumps(credentials_data), encryption_key)
        cred_path.write_bytes(encrypted_data)

        # Try to load non-existent profile
        creds = load_profile_credentials("test-profile")
        assert creds is None

    def test_load_profile_credentials_invalid_json(self, mock_settings):
        """Test loading credentials when decrypted data is invalid JSON."""
        encryption_key = "test-encryption-key"

        # Setup encryption key
        key_path = get_encryption_key_path()
        key_path.parent.mkdir(parents=True, exist_ok=True)
        key_path.write_text(json.dumps({"encryptionKey": encryption_key}), encoding="utf-8")

        # Setup encrypted credentials with invalid JSON
        cred_path = get_credential_store_path()
        encrypted_data = self._encrypt_data("invalid json {", encryption_key)
        cred_path.write_bytes(encrypted_data)

        # Try to load - should handle JSON error gracefully
        creds = load_profile_credentials("test-profile")
        assert creds is None

    def test_load_profile_credentials_decryption_fails(self, mock_settings):
        """Test loading credentials when decryption fails."""
        encryption_key = "test-encryption-key"

        # Setup encryption key
        key_path = get_encryption_key_path()
        key_path.parent.mkdir(parents=True, exist_ok=True)
        key_path.write_text(json.dumps({"encryptionKey": encryption_key}), encoding="utf-8")

        # Setup credential store with corrupted data
        cred_path = get_credential_store_path()
        cred_path.write_bytes(b"corrupted data that will fail decryption")

        # Try to load - should handle decryption failure gracefully
        creds = load_profile_credentials("test-profile")
        assert creds is None

    def _encrypt_data(self, data: str, encryption_key: str) -> bytes:
        """Helper to encrypt data using the same format as electron-store/conf."""
        import os

        # Generate random IV
        iv = os.urandom(16)

        # Derive key using PBKDF2
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA512(),
            length=32,
            salt=iv,
            iterations=10_000,
            backend=default_backend(),
        )
        key = kdf.derive(encryption_key.encode("utf-8"))

        # Encrypt using AES-256-CBC
        cipher = Cipher(algorithms.AES(key), modes.CBC(iv), backend=default_backend())
        encryptor = cipher.encryptor()

        # Add PKCS7 padding
        data_bytes = data.encode("utf-8")
        padding_length = 16 - (len(data_bytes) % 16)
        padded_data = data_bytes + bytes([padding_length] * padding_length)

        encrypted = encryptor.update(padded_data) + encryptor.finalize()

        # Format: [IV][':'][encrypted data]
        return iv + b":" + encrypted
