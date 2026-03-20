# -*- coding: utf-8 -*-
"""Tests for cforge.common.http."""

# Standard
from pathlib import Path
from unittest.mock import Mock, patch
import stat
import tempfile

# Third-Party
import pytest
import requests

# Local
from cforge.common.errors import AuthenticationError, CLIError
from cforge.common.http import get_auth_token, get_token_file, load_token, make_authenticated_request, save_token
from tests.conftest import mock_client_login


class TestTokenManagement:
    """Tests for token management functions."""

    def test_get_token_file(self, mock_settings) -> None:
        """Test getting the token file path."""
        token_file = get_token_file()
        assert isinstance(token_file, Path)
        assert str(token_file).endswith("token")
        assert token_file.parent == mock_settings.contextforge_home

    def test_get_token_file_with_active_profile(self, mock_settings) -> None:
        """Test getting the token file path uses active profile when available."""
        # Standard
        from datetime import datetime

        # Local
        from cforge.profile_utils import AuthProfile, ProfileStore, save_profile_store

        # Create and save an active profile
        profile_id = "active-profile-456"
        profile = AuthProfile(
            id=profile_id,
            name="Active Profile",
            email="active@example.com",
            apiUrl="https://api.example.com",
            isActive=True,
            createdAt=datetime.now(),
        )
        store = ProfileStore(
            profiles={profile_id: profile},
            activeProfileId=profile_id,
        )
        save_profile_store(store)

        # get_token_file should use the active profile
        token_file = get_token_file()
        assert str(token_file).endswith(f"token.{profile_id}")

    def test_save_and_load_token(self) -> None:
        """Test saving and loading a token."""
        test_token = "test_token_123"

        with tempfile.NamedTemporaryFile() as temp_token_file:
            with patch("cforge.common.http.get_token_file", return_value=Path(temp_token_file.name)):
                save_token(test_token)
                loaded_token = load_token()

        assert loaded_token == test_token

    def test_save_and_load_token_with_active_profile(self, mock_settings) -> None:
        """Test saving and loading a token with an active profile."""
        # Standard
        from datetime import datetime

        # Local
        from cforge.profile_utils import AuthProfile, ProfileStore, save_profile_store

        test_token = "profile_token_456"
        profile_id = "test-profile-789"

        # Create and save an active profile
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

        # Save and load token - should use profile-specific file
        save_token(test_token)
        loaded_token = load_token()

        assert loaded_token == test_token

        # Verify it was saved to profile-specific file
        token_file = mock_settings.contextforge_home / f"token.{profile_id}"
        assert token_file.exists()

    def test_save_token_different_profiles(self, mock_settings) -> None:
        """Test that different profiles have separate token files."""
        # Standard
        from datetime import datetime

        # Local
        from cforge.profile_utils import AuthProfile, ProfileStore, save_profile_store

        token1 = "token_for_profile_1"
        token2 = "token_for_profile_2"
        profile_id1 = "profile-1"
        profile_id2 = "profile-2"

        # Save token for profile 1
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
        save_token(token1)

        # Save token for profile 2
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
        save_token(token2)

        # Verify both tokens exist in separate files
        token_file1 = mock_settings.contextforge_home / f"token.{profile_id1}"
        token_file2 = mock_settings.contextforge_home / f"token.{profile_id2}"

        assert token_file1.exists()
        assert token_file2.exists()
        assert token_file1.read_text() == token1
        assert token_file2.read_text() == token2
        assert token1 != token2

    def test_load_token_nonexistent(self, tmp_path: Path) -> None:
        """Test loading a token when file doesn't exist."""
        nonexistent_file = tmp_path / "nonexistent" / "token"

        with patch("cforge.common.http.get_token_file", return_value=nonexistent_file):
            token = load_token()

        assert token is None

    def test_load_token_nonexistent_profile(self, mock_settings) -> None:
        """Test loading a token for a profile that doesn't have a token file."""
        # Standard
        from datetime import datetime

        # Local
        from cforge.profile_utils import AuthProfile, ProfileStore, save_profile_store

        profile_id = "nonexistent-profile"

        # Create an active profile but don't create a token file
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

        # Try to load token - should return None since file doesn't exist
        token = load_token()

        assert token is None


class TestBaseUrl:
    """Tests for get_base_url function."""

    def test_get_base_url_with_active_profile(self, mock_settings) -> None:
        """Test get_base_url returns profile's API URL when active profile exists."""
        # Standard
        from datetime import datetime

        # Local
        from cforge.common.http import get_base_url
        from cforge.profile_utils import AuthProfile, ProfileStore, save_profile_store

        # Create and save a profile
        profile = AuthProfile(
            id="profile-1",
            name="Test Profile",
            email="test@example.com",
            apiUrl="https://custom-api.example.com",
            isActive=True,
            createdAt=datetime.now(),
        )
        store = ProfileStore(
            profiles={"profile-1": profile},
            activeProfileId="profile-1",
        )
        save_profile_store(store)

        # Get base URL should return the profile's API URL
        base_url = get_base_url()
        assert base_url == "https://custom-api.example.com"

    def test_get_base_url_without_active_profile(self, mock_settings) -> None:
        """Test get_base_url returns default URL when no active profile."""
        # Local
        from cforge.common.http import get_base_url

        # No profile saved, should use settings
        base_url = get_base_url()
        assert base_url == f"http://{mock_settings.host}:{mock_settings.port}"


class TestAuthentication:
    """Tests for authentication functions."""

    def test_get_auth_token_from_env(self, mock_settings) -> None:
        """Test getting auth token from environment variable."""
        # Create a new settings instance with token
        mock_settings.mcpgateway_bearer_token = "env_token"
        with patch("cforge.common.http.load_token", return_value=None):
            token = get_auth_token()

        assert token == "env_token"

    def test_get_auth_token_from_file(self, mock_settings) -> None:
        """Test getting auth token from file when env var not set."""
        # mock_settings already has mcpgateway_bearer_token=None
        with patch("cforge.common.http.load_token", return_value="file_token"):
            token = get_auth_token()

        assert token == "file_token"

    def test_get_auth_token_none(self, mock_settings) -> None:
        """Test getting auth token when none available."""
        # mock_settings already has mcpgateway_bearer_token=None
        with patch("cforge.common.http.load_token", return_value=None):
            token = get_auth_token()

        assert token is None


class TestAutoLogin:
    """Tests for automatic login functionality."""

    def test_attempt_auto_login_no_profile(self, mock_settings):
        """Test auto-login when no profile is active."""
        # Local
        from cforge.common.http import attempt_auto_login

        token = attempt_auto_login()
        assert token is None

    def test_attempt_auto_login_no_credentials(self, mock_settings):
        """Test auto-login when credentials are not available."""
        # Standard
        from datetime import datetime

        # Local
        from cforge.common.http import attempt_auto_login
        from cforge.profile_utils import AuthProfile

        mock_profile = AuthProfile(
            id="test-profile",
            name="Test",
            email="test@example.com",
            apiUrl="http://localhost:4444",
            isActive=True,
            createdAt=datetime.now(),
        )

        with patch("cforge.common.http.get_active_profile", return_value=mock_profile):
            with patch("cforge.common.http.load_profile_credentials", return_value=None):
                token = attempt_auto_login()
                assert token is None

    def test_attempt_auto_login_missing_email(self, mock_settings):
        """Test auto-login when email is missing from credentials."""
        # Standard
        from datetime import datetime

        # Local
        from cforge.common.http import attempt_auto_login
        from cforge.profile_utils import AuthProfile

        mock_profile = AuthProfile(
            id="test-profile",
            name="Test",
            email="test@example.com",
            apiUrl="http://localhost:4444",
            isActive=True,
            createdAt=datetime.now(),
        )

        with patch("cforge.common.http.get_active_profile", return_value=mock_profile):
            with patch("cforge.common.http.load_profile_credentials", return_value={"password": "test"}):
                token = attempt_auto_login()
                assert token is None

    def test_attempt_auto_login_missing_password(self, mock_settings):
        """Test auto-login when password is missing from credentials."""
        # Standard
        from datetime import datetime

        # Local
        from cforge.common.http import attempt_auto_login
        from cforge.profile_utils import AuthProfile

        mock_profile = AuthProfile(
            id="test-profile",
            name="Test",
            email="test@example.com",
            apiUrl="http://localhost:4444",
            isActive=True,
            createdAt=datetime.now(),
        )

        with patch("cforge.common.http.get_active_profile", return_value=mock_profile):
            with patch("cforge.common.http.load_profile_credentials", return_value={"email": "test@example.com"}):
                token = attempt_auto_login()
                assert token is None

    @patch("cforge.common.http.requests.post")
    def test_attempt_auto_login_success(self, mock_post, mock_settings):
        """Test successful auto-login."""
        # Standard
        from datetime import datetime

        # Local
        from cforge.common.http import attempt_auto_login, load_token
        from cforge.profile_utils import AuthProfile

        mock_profile = AuthProfile(
            id="test-profile",
            name="Test",
            email="test@example.com",
            apiUrl="http://localhost:4444",
            isActive=True,
            createdAt=datetime.now(),
        )

        # Mock successful login response
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"access_token": "auto-login-token"}
        mock_post.return_value = mock_response

        with patch("cforge.common.http.get_active_profile", return_value=mock_profile):
            with patch("cforge.common.http.load_profile_credentials", return_value={"email": "test@example.com", "password": "test-pass"}):
                token = attempt_auto_login()
                assert token == "auto-login-token"

                # Verify token was saved
                saved_token = load_token()
                assert saved_token == "auto-login-token"

    @patch("cforge.common.http.requests.post")
    def test_attempt_auto_login_failed_login(self, mock_post, mock_settings):
        """Test auto-login when login fails."""
        # Standard
        from datetime import datetime

        # Local
        from cforge.common.http import attempt_auto_login
        from cforge.profile_utils import AuthProfile

        mock_profile = AuthProfile(
            id="test-profile",
            name="Test",
            email="test@example.com",
            apiUrl="http://localhost:4444",
            isActive=True,
            createdAt=datetime.now(),
        )

        # Mock failed login response
        mock_response = Mock()
        mock_response.status_code = 401
        mock_post.return_value = mock_response

        with patch("cforge.common.http.get_active_profile", return_value=mock_profile):
            with patch("cforge.common.http.load_profile_credentials", return_value={"email": "test@example.com", "password": "wrong-pass"}):
                token = attempt_auto_login()
                assert token is None

    @patch("cforge.common.http.requests.post")
    def test_attempt_auto_login_no_token_in_response(self, mock_post, mock_settings):
        """Test auto-login when response doesn't contain token."""
        # Standard
        from datetime import datetime

        # Local
        from cforge.common.http import attempt_auto_login
        from cforge.profile_utils import AuthProfile

        mock_profile = AuthProfile(
            id="test-profile",
            name="Test",
            email="test@example.com",
            apiUrl="http://localhost:4444",
            isActive=True,
            createdAt=datetime.now(),
        )

        # Mock response without token
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {}
        mock_post.return_value = mock_response

        with patch("cforge.common.http.get_active_profile", return_value=mock_profile):
            with patch("cforge.common.http.load_profile_credentials", return_value={"email": "test@example.com", "password": "test-pass"}):
                token = attempt_auto_login()
                assert token is None

    @patch("cforge.common.http.requests.post")
    def test_attempt_auto_login_request_exception(self, mock_post, mock_settings):
        """Test auto-login when request raises exception."""
        # Standard
        from datetime import datetime

        # Local
        from cforge.common.http import attempt_auto_login
        from cforge.profile_utils import AuthProfile

        mock_profile = AuthProfile(
            id="test-profile",
            name="Test",
            email="test@example.com",
            apiUrl="http://localhost:4444",
            isActive=True,
            createdAt=datetime.now(),
        )

        # Mock request exception
        mock_post.side_effect = Exception("Connection error")

        with patch("cforge.common.http.get_active_profile", return_value=mock_profile):
            with patch("cforge.common.http.load_profile_credentials", return_value={"email": "test@example.com", "password": "test-pass"}):
                token = attempt_auto_login()
                assert token is None

    def test_get_auth_token_with_auto_login(self, mock_settings):
        """Test that get_auth_token attempts auto-login when no token is available."""
        # Local
        from cforge.common.http import get_auth_token

        # Mock no env token and no file token, but successful auto-login
        with patch("cforge.common.http.load_token", return_value=None):
            with patch("cforge.common.http.attempt_auto_login", return_value="auto-token"):
                token = get_auth_token()
                assert token == "auto-token"


class TestMakeAuthenticatedRequest:
    """Tests for make_authenticated_request function using a server mock."""

    def test_request_no_auth_raises_error_when_server_requires_it(self, mock_settings) -> None:
        """Test that request without auth raises AuthenticationError when server requires it."""
        # Ensure no token is available
        with patch("cforge.common.http.load_token", return_value=None):
            # Mock a 401 response from server (authentication required)
            mock_response = Mock()
            mock_response.status_code = 401
            mock_response.text = "Unauthorized"

            with patch("cforge.common.http.requests.request", return_value=mock_response):
                with pytest.raises(AuthenticationError) as exc_info:
                    make_authenticated_request("GET", "/test")

                assert "Authentication required but not configured" in str(exc_info.value)

    def test_request_without_auth_succeeds_on_unauthenticated_server(self, mock_settings) -> None:
        """Test that request without auth succeeds when server doesn't require it."""
        # Ensure no token is available
        with patch("cforge.common.http.load_token", return_value=None):
            # Mock a successful response from server (no auth required)
            mock_response = Mock()
            mock_response.status_code = 200
            mock_response.json.return_value = {"result": "success"}

            with patch("cforge.common.http.requests.request", return_value=mock_response) as mock_req:
                result = make_authenticated_request("GET", "/test")

                # Verify the request was made without Authorization header
                call_args = mock_req.call_args
                assert "Authorization" not in call_args[1]["headers"]
                assert result == {"result": "success"}

    def test_request_with_bearer_token(self, mock_client, mock_settings) -> None:
        """Test successful request with Bearer token."""
        mock_client.reset_mock()
        with mock_client_login(mock_client):
            mock_req = mock_client.request
            result = make_authenticated_request("GET", "/tools")

            # Verify request was made correctly
            mock_req.assert_called_once()
            call_args = mock_req.call_args
            assert call_args[1]["method"] == "GET"
            assert call_args[1]["url"] == f"http://{mock_client.settings.host}:{mock_client.settings.port}/tools"
            assert call_args[1]["headers"]["Authorization"] == f"Bearer {mock_client.settings.mcpgateway_bearer_token}"
            assert call_args[1]["headers"]["Content-Type"] == "application/json"
            assert isinstance(result, list)

    def test_request_with_basic_auth(self, mock_settings) -> None:
        """Test request with Basic auth token."""
        # Set up settings with Basic auth token
        mock_settings.mcpgateway_bearer_token = "Basic dGVzdDp0ZXN0"

        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"result": "success"}

        with patch("cforge.common.http.requests.request", return_value=mock_response) as mock_req:
            make_authenticated_request("POST", "/api/test", json_data={"data": "value"})

            # Verify Basic auth is passed as-is
            call_args = mock_req.call_args
            assert call_args[1]["headers"]["Authorization"] == "Basic dGVzdDp0ZXN0"

    def test_request_api_error(self, mock_settings) -> None:
        """Test that API errors are properly raised."""
        mock_settings.mcpgateway_bearer_token = "test_token"

        mock_response = Mock()
        mock_response.status_code = 404
        mock_response.text = "Not found"

        with patch("cforge.common.http.requests.request", return_value=mock_response):
            with pytest.raises(CLIError) as exc_info:
                make_authenticated_request("GET", "/api/missing")

            assert "API request failed (404)" in str(exc_info.value)
            assert "Not found" in str(exc_info.value)

    def test_request_connection_error(self, mock_settings) -> None:
        """Test that connection errors are properly raised."""
        mock_settings.mcpgateway_bearer_token = "test_token"

        with patch("cforge.common.http.requests.request", side_effect=requests.ConnectionError("Connection refused")):
            with pytest.raises(CLIError) as exc_info:
                make_authenticated_request("GET", "/api/test")

            assert "Failed to connect to gateway" in str(exc_info.value)
            assert "Connection refused" in str(exc_info.value)


class TestTokenFilePermissions:
    """Tests for token file permission handling."""

    def test_save_token_creates_parent_dirs(self) -> None:
        """Test that save_token creates parent directories."""
        with tempfile.TemporaryDirectory() as temp_dir:
            token_path = Path(temp_dir) / "nested" / "dirs" / "token"

            with patch("cforge.common.http.get_token_file", return_value=token_path):
                save_token("test_token")

                assert token_path.exists()
                assert token_path.read_text() == "test_token"

    def test_save_token_sets_permissions(self) -> None:
        """Test that save_token sets restrictive permissions."""
        with tempfile.NamedTemporaryFile(delete=False) as temp_file:
            token_path = Path(temp_file.name)

            try:
                with patch("cforge.common.http.get_token_file", return_value=token_path):
                    save_token("test_token")

                    # Check permissions are 0o600 (read/write for owner only)
                    file_stat = token_path.stat()
                    file_mode = stat.S_IMODE(file_stat.st_mode)
                    assert file_mode == 0o600
            finally:
                token_path.unlink(missing_ok=True)


class TestMakeAuthenticatedRequestIntegration:
    """Integration tests for make_authenticated_request with real server.

    These tests use the session_settings fixture which provides a real
    running mcpgateway server and properly configured settings. This validates
    that the client code actually works with the server, not just that it
    makes the right calls.
    """

    def test_request_with_bearer_token_to_health_endpoint(self, mock_client) -> None:
        """Test successful authenticated request to /health endpoint."""

        # Make a request to the health endpoint (no auth required)
        make_authenticated_request("GET", "/health")

        # Make a request to an authorized endpoint before login
        with pytest.raises(CLIError):
            make_authenticated_request("GET", "/tools")

        # Log in and try again
        with mock_client_login(mock_client):

            # Make a real HTTP request to the session server's health endpoint
            result = make_authenticated_request("GET", "/tools")

        # The tools endpoint should return a successful response
        assert result is not None
        assert isinstance(result, list)

    def test_request_to_nonexistent_endpoint_raises_error(self, authorized_mock_client) -> None:
        """Test that requesting a nonexistent endpoint raises CLIError."""
        # Try to request an endpoint that doesn't exist
        with pytest.raises(CLIError) as exc_info:
            make_authenticated_request("GET", "/api/this/endpoint/does/not/exist")

        # Should get a 404 error
        assert "404" in str(exc_info.value) or "not found" in str(exc_info.value).lower()

    def test_request_with_params_and_json_data(self, authorized_mock_client) -> None:
        """Test request with query parameters.

        This test verifies that parameters are correctly passed through
        to the server in a real HTTP request.
        """
        # Test that we can make requests with params
        # The health endpoint may not use params, but we can verify the request succeeds
        result = make_authenticated_request("GET", "/health", params={"test": "value"})

        # Should still get a valid response even with unused params
        assert result is not None
        assert isinstance(result, dict)
