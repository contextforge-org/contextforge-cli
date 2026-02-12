# -*- coding: utf-8 -*-
"""Location: ./tests/test_common.py
Copyright 2025
SPDX-License-Identifier: Apache-2.0
Authors: Gabe Goodhart

Tests for common utility functions.
"""

# Standard
from pathlib import Path
from typing import Any, Dict, List, Optional
from unittest.mock import Mock, patch
import stat
import tempfile

# Third-Party
from pydantic import BaseModel, Field
from rich.panel import Panel
from rich.syntax import Syntax
from rich.table import Table
import pytest
import requests

# First-Party
from cforge.common import (
    _INT_SENTINEL_DEFAULT,
    AuthenticationError,
    CLIError,
    LineLimit,
    get_app,
    get_auth_token,
    get_console,
    get_token_file,
    load_token,
    make_authenticated_request,
    print_json,
    print_table,
    prompt_for_json_schema,
    prompt_for_schema,
    save_token,
)
from tests.conftest import mock_client_login


class TestSingletons:
    """Tests for singleton getter functions."""

    def test_get_console_returns_console(self) -> None:
        """Test that get_console returns a Console instance."""
        console = get_console()
        assert console is not None
        # Should return same instance
        assert get_console() is console

    def test_get_app_returns_typer_app(self) -> None:
        """Test that get_app returns a Typer instance."""
        app = get_app()
        assert app is not None
        # Should return same instance
        assert get_app() is app


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
        from cforge.profile_utils import AuthProfile, ProfileStore, save_profile_store
        from datetime import datetime

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
            with patch("cforge.common.get_token_file", return_value=Path(temp_token_file.name)):
                save_token(test_token)
                loaded_token = load_token()

        assert loaded_token == test_token

    def test_save_and_load_token_with_active_profile(self, mock_settings) -> None:
        """Test saving and loading a token with an active profile."""
        from cforge.profile_utils import AuthProfile, ProfileStore, save_profile_store
        from datetime import datetime

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
        from cforge.profile_utils import AuthProfile, ProfileStore, save_profile_store
        from datetime import datetime

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

        with patch("cforge.common.get_token_file", return_value=nonexistent_file):
            token = load_token()

        assert token is None

    def test_load_token_nonexistent_profile(self, mock_settings) -> None:
        """Test loading a token for a profile that doesn't have a token file."""
        from cforge.profile_utils import AuthProfile, ProfileStore, save_profile_store
        from datetime import datetime

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
        from cforge.common import get_base_url
        from cforge.profile_utils import AuthProfile, ProfileStore, save_profile_store
        from datetime import datetime

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
        from cforge.common import get_base_url

        # No profile saved, should use settings
        base_url = get_base_url()
        assert base_url == f"http://{mock_settings.host}:{mock_settings.port}"


class TestAuthentication:
    """Tests for authentication functions."""

    def test_get_auth_token_from_env(self, mock_settings) -> None:
        """Test getting auth token from environment variable."""
        # Create a new settings instance with token
        mock_settings.mcpgateway_bearer_token = "env_token"
        with patch("cforge.common.load_token", return_value=None):
            token = get_auth_token()

        assert token == "env_token"

    def test_get_auth_token_from_file(self, mock_settings) -> None:
        """Test getting auth token from file when env var not set."""
        # mock_settings already has mcpgateway_bearer_token=None
        with patch("cforge.common.load_token", return_value="file_token"):
            token = get_auth_token()

        assert token == "file_token"

    def test_get_auth_token_none(self, mock_settings) -> None:
        """Test getting auth token when none available."""
        # mock_settings already has mcpgateway_bearer_token=None
        with patch("cforge.common.load_token", return_value=None):
            token = get_auth_token()

        assert token is None


class TestAutoLogin:
    """Tests for automatic login functionality."""

    def test_attempt_auto_login_no_profile(self, mock_settings):
        """Test auto-login when no profile is active."""
        from cforge.common import attempt_auto_login

        token = attempt_auto_login()
        assert token is None

    def test_attempt_auto_login_no_credentials(self, mock_settings):
        """Test auto-login when credentials are not available."""
        from cforge.common import attempt_auto_login
        from cforge.profile_utils import AuthProfile
        from datetime import datetime

        mock_profile = AuthProfile(
            id="test-profile",
            name="Test",
            email="test@example.com",
            apiUrl="http://localhost:4444",
            isActive=True,
            createdAt=datetime.now(),
        )

        with patch("cforge.common.get_active_profile", return_value=mock_profile):
            with patch("cforge.common.load_profile_credentials", return_value=None):
                token = attempt_auto_login()
                assert token is None

    def test_attempt_auto_login_missing_email(self, mock_settings):
        """Test auto-login when email is missing from credentials."""
        from cforge.common import attempt_auto_login
        from cforge.profile_utils import AuthProfile
        from datetime import datetime

        mock_profile = AuthProfile(
            id="test-profile",
            name="Test",
            email="test@example.com",
            apiUrl="http://localhost:4444",
            isActive=True,
            createdAt=datetime.now(),
        )

        with patch("cforge.common.get_active_profile", return_value=mock_profile):
            with patch("cforge.common.load_profile_credentials", return_value={"password": "test"}):
                token = attempt_auto_login()
                assert token is None

    def test_attempt_auto_login_missing_password(self, mock_settings):
        """Test auto-login when password is missing from credentials."""
        from cforge.common import attempt_auto_login
        from cforge.profile_utils import AuthProfile
        from datetime import datetime

        mock_profile = AuthProfile(
            id="test-profile",
            name="Test",
            email="test@example.com",
            apiUrl="http://localhost:4444",
            isActive=True,
            createdAt=datetime.now(),
        )

        with patch("cforge.common.get_active_profile", return_value=mock_profile):
            with patch("cforge.common.load_profile_credentials", return_value={"email": "test@example.com"}):
                token = attempt_auto_login()
                assert token is None

    @patch("cforge.common.requests.post")
    def test_attempt_auto_login_success(self, mock_post, mock_settings):
        """Test successful auto-login."""
        from cforge.common import attempt_auto_login, load_token
        from cforge.profile_utils import AuthProfile
        from datetime import datetime

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

        with patch("cforge.common.get_active_profile", return_value=mock_profile):
            with patch("cforge.common.load_profile_credentials", return_value={"email": "test@example.com", "password": "test-pass"}):
                token = attempt_auto_login()
                assert token == "auto-login-token"

                # Verify token was saved
                saved_token = load_token()
                assert saved_token == "auto-login-token"

    @patch("cforge.common.requests.post")
    def test_attempt_auto_login_failed_login(self, mock_post, mock_settings):
        """Test auto-login when login fails."""
        from cforge.common import attempt_auto_login
        from cforge.profile_utils import AuthProfile
        from datetime import datetime

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

        with patch("cforge.common.get_active_profile", return_value=mock_profile):
            with patch("cforge.common.load_profile_credentials", return_value={"email": "test@example.com", "password": "wrong-pass"}):
                token = attempt_auto_login()
                assert token is None

    @patch("cforge.common.requests.post")
    def test_attempt_auto_login_no_token_in_response(self, mock_post, mock_settings):
        """Test auto-login when response doesn't contain token."""
        from cforge.common import attempt_auto_login
        from cforge.profile_utils import AuthProfile
        from datetime import datetime

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

        with patch("cforge.common.get_active_profile", return_value=mock_profile):
            with patch("cforge.common.load_profile_credentials", return_value={"email": "test@example.com", "password": "test-pass"}):
                token = attempt_auto_login()
                assert token is None

    @patch("cforge.common.requests.post")
    def test_attempt_auto_login_request_exception(self, mock_post, mock_settings):
        """Test auto-login when request raises exception."""
        from cforge.common import attempt_auto_login
        from cforge.profile_utils import AuthProfile
        from datetime import datetime

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

        with patch("cforge.common.get_active_profile", return_value=mock_profile):
            with patch("cforge.common.load_profile_credentials", return_value={"email": "test@example.com", "password": "test-pass"}):
                token = attempt_auto_login()
                assert token is None

    def test_get_auth_token_with_auto_login(self, mock_settings):
        """Test that get_auth_token attempts auto-login when no token is available."""
        from cforge.common import get_auth_token

        # Mock no env token and no file token, but successful auto-login
        with patch("cforge.common.load_token", return_value=None):
            with patch("cforge.common.attempt_auto_login", return_value="auto-token"):
                token = get_auth_token()
                assert token == "auto-token"


class TestErrors:
    """Tests for custom error classes."""

    def test_cli_error(self) -> None:
        """Test CLIError exception."""
        error = CLIError("Test error")
        assert str(error) == "Test error"

    def test_authentication_error(self) -> None:
        """Test AuthenticationError exception."""
        error = AuthenticationError("Auth failed")
        assert str(error) == "Auth failed"
        assert isinstance(error, CLIError)


class TestLineLimit:
    """Tests for LineLimit class that truncates rendered content."""

    def test_line_limit_basic_truncation(self) -> None:
        """Test that LineLimit truncates content to max_lines."""
        from rich.text import Text
        from rich.console import Console

        console = Console()
        # Create text with 5 lines
        text = Text("Line 1\nLine 2\nLine 3\nLine 4\nLine 5")
        limited = LineLimit(text, max_lines=3)

        # Render to string and verify truncation
        with console.capture() as capture:
            console.print(limited)

        output = capture.get()
        # Should contain first 3 lines
        assert "Line 1" in output
        assert "Line 2" in output
        assert "Line 3" in output
        # Should NOT contain lines 4 and 5
        assert "Line 4" not in output
        assert "Line 5" not in output
        # Should have ellipsis
        assert "..." in output

    def test_line_limit_no_truncation_needed(self) -> None:
        """Test that LineLimit doesn't truncate when content is within limit."""
        from rich.text import Text
        from rich.console import Console

        console = Console()
        # Create text with 2 lines, limit to 5
        text = Text("Line 1\nLine 2")
        limited = LineLimit(text, max_lines=5)

        with console.capture() as capture:
            console.print(limited)

        output = capture.get()
        # Should contain both lines
        assert "Line 1" in output
        assert "Line 2" in output
        # Should NOT have ellipsis since no truncation
        assert "..." not in output

    def test_line_limit_exact_match(self) -> None:
        """Test LineLimit when content exactly matches max_lines."""
        from rich.text import Text
        from rich.console import Console

        console = Console()
        # Create text with exactly 3 lines
        text = Text("Line 1\nLine 2\nLine 3")
        limited = LineLimit(text, max_lines=3)

        with console.capture() as capture:
            console.print(limited)

        output = capture.get()
        # Should contain all 3 lines
        assert "Line 1" in output
        assert "Line 2" in output
        assert "Line 3" in output
        # Should NOT have ellipsis since content fits exactly
        assert "..." not in output

    def test_line_limit_zero_lines(self) -> None:
        """Test LineLimit with max_lines=0 shows only ellipsis."""
        from rich.text import Text
        from rich.console import Console

        console = Console()
        text = Text("Line 1\nLine 2")
        limited = LineLimit(text, max_lines=0)

        with console.capture() as capture:
            console.print(limited)

        output = capture.get()
        # Should only show ellipsis, no content
        assert "..." in output
        assert "Line 1" not in output
        assert "Line 2" not in output

    def test_line_limit_one_line(self) -> None:
        """Test LineLimit with max_lines=1."""
        from rich.text import Text
        from rich.console import Console

        console = Console()
        text = Text("Line 1\nLine 2\nLine 3")
        limited = LineLimit(text, max_lines=1)

        with console.capture() as capture:
            console.print(limited)

        output = capture.get()
        # Should show only first line and ellipsis
        assert "Line 1" in output
        assert "..." in output
        assert "Line 2" not in output
        assert "Line 3" not in output

    def test_line_limit_with_long_single_line(self) -> None:
        """Test LineLimit with a single long line that wraps."""
        from rich.text import Text
        from rich.console import Console

        console = Console(width=80)  # Set fixed width for predictable wrapping
        # Create a very long line that will wrap
        long_text = "A" * 200
        text = Text(long_text)
        limited = LineLimit(text, max_lines=2)

        with console.capture() as capture:
            console.print(limited)

        output = capture.get()
        # Should contain some A's but be truncated
        assert "A" in output
        # Should have ellipsis since it wraps to more than 2 lines
        assert "..." in output

    def test_line_limit_measurement_passthrough(self) -> None:
        """Test that LineLimit passes through measurement to wrapped renderable."""
        from rich.text import Text
        from rich.console import Console

        console = Console()
        text = Text("Test content")
        limited = LineLimit(text, max_lines=3)

        # Get measurement using console's options
        measurement = console.measure(limited)

        # Should return a valid Measurement
        assert measurement is not None
        assert hasattr(measurement, "minimum")
        assert hasattr(measurement, "maximum")

    def test_line_limit_with_empty_content(self) -> None:
        """Test LineLimit with empty content."""
        from rich.text import Text
        from rich.console import Console

        console = Console()
        text = Text("")
        limited = LineLimit(text, max_lines=3)

        with console.capture() as capture:
            console.print(limited)

        output = capture.get()
        # Empty content should produce minimal output
        # Should not have ellipsis since there's nothing to truncate
        assert "..." not in output

    def test_line_limit_preserves_styling(self) -> None:
        """Test that LineLimit preserves rich styling in truncated content."""
        from rich.text import Text
        from rich.console import Console

        console = Console()
        # Create styled text
        text = Text()
        text.append("Line 1\n", style="bold red")
        text.append("Line 2\n", style="italic blue")
        text.append("Line 3\n", style="underline green")
        text.append("Line 4", style="bold yellow")

        limited = LineLimit(text, max_lines=2)

        with console.capture() as capture:
            console.print(limited)

        output = capture.get()
        # Should contain first 2 lines
        assert "Line 1" in output
        assert "Line 2" in output
        # Should NOT contain lines 3 and 4
        assert "Line 3" not in output
        assert "Line 4" not in output
        # Should have ellipsis
        assert "..." in output


class TestMakeAuthenticatedRequest:
    """Tests for make_authenticated_request function using a server mock."""

    def test_request_no_auth_raises_error_when_server_requires_it(self, mock_settings) -> None:
        """Test that request without auth raises AuthenticationError when server requires it."""
        # Ensure no token is available
        with patch("cforge.common.load_token", return_value=None):
            # Mock a 401 response from server (authentication required)
            mock_response = Mock()
            mock_response.status_code = 401
            mock_response.text = "Unauthorized"

            with patch("cforge.common.requests.request", return_value=mock_response):
                with pytest.raises(AuthenticationError) as exc_info:
                    make_authenticated_request("GET", "/test")

                assert "Authentication required but not configured" in str(exc_info.value)

    def test_request_without_auth_succeeds_on_unauthenticated_server(self, mock_settings) -> None:
        """Test that request without auth succeeds when server doesn't require it."""
        # Ensure no token is available
        with patch("cforge.common.load_token", return_value=None):
            # Mock a successful response from server (no auth required)
            mock_response = Mock()
            mock_response.status_code = 200
            mock_response.json.return_value = {"result": "success"}

            with patch("cforge.common.requests.request", return_value=mock_response) as mock_req:
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

        with patch("cforge.common.requests.request", return_value=mock_response) as mock_req:
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

        with patch("cforge.common.requests.request", return_value=mock_response):
            with pytest.raises(CLIError) as exc_info:
                make_authenticated_request("GET", "/api/missing")

            assert "API request failed (404)" in str(exc_info.value)
            assert "Not found" in str(exc_info.value)

    def test_request_connection_error(self, mock_settings) -> None:
        """Test that connection errors are properly raised."""
        mock_settings.mcpgateway_bearer_token = "test_token"

        with patch("cforge.common.requests.request", side_effect=requests.ConnectionError("Connection refused")):
            with pytest.raises(CLIError) as exc_info:
                make_authenticated_request("GET", "/api/test")

            assert "Failed to connect to gateway" in str(exc_info.value)
            assert "Connection refused" in str(exc_info.value)


class TestPrettyPrinting:
    """Tests for pretty printing functions."""

    def test_print_json_with_title(self, mock_console) -> None:
        """Test print_json with a title."""
        test_data = {"key": "value", "number": 42}

        print_json(test_data, "Test Title")

        # Verify console.print was called
        mock_console.print.assert_called_once()
        call_args = mock_console.print.call_args[0]

        # Should be wrapped in a Panel
        assert isinstance(call_args[0], Panel)

    def test_print_json_without_title(self, mock_console) -> None:
        """Test print_json without a title."""
        test_data = {"key": "value"}

        print_json(test_data)

        # Verify console.print was called
        mock_console.print.assert_called_once()
        call_args = mock_console.print.call_args[0]

        # Should be Syntax object, not Panel
        assert isinstance(call_args[0], Syntax)

    def test_print_table(self, mock_console) -> None:
        """Test print_table with data."""
        test_data = [
            {"id": 1, "name": "Item 1", "value": "A"},
            {"id": 2, "name": "Item 2", "value": "B"},
        ]
        columns = ["id", "name", "value"]

        print_table(test_data, "Test Table", columns)

        # Verify console.print was called
        mock_console.print.assert_called_once()
        call_args = mock_console.print.call_args[0]

        # Should be a Table
        assert isinstance(call_args[0], Table)

    def test_print_table_missing_columns(self, mock_console) -> None:
        """Test print_table handles missing columns gracefully."""
        test_data = [
            {"id": 1, "name": "Item 1"},  # Missing 'value' column
        ]
        columns = ["id", "name", "value"]

        # Should not raise an error
        print_table(test_data, "Test Table", columns)
        mock_console.print.assert_called_once()

    def test_print_table_wraps_all_cells_with_line_limit(self) -> None:
        """Test that print_table wraps all cell values with LineLimit for truncation."""
        from unittest.mock import patch

        # Create test data with various types
        test_data = [
            {"id": 1, "name": "Item 1", "description": "Short text"},
            {"id": 2, "name": "Item 2", "description": "Line 1\nLine 2\nLine 3\nLine 4\nLine 5"},
        ]
        columns = ["id", "name", "description"]

        # Mock Table.add_row to capture what's passed to it
        with patch.object(Table, "add_row") as mock_add_row:
            print_table(test_data, "Test Table", columns)

            # Verify add_row was called for each data row
            assert mock_add_row.call_count == 2

            # Check that all arguments to add_row are LineLimit instances
            for call in mock_add_row.call_args_list:
                args = call[0]  # Get positional arguments
                for arg in args:
                    assert isinstance(arg, LineLimit), f"Expected LineLimit but got {type(arg)}"
                    # Verify max_lines is set to 4
                    assert arg.max_lines == 4

    def test_print_table_with_custom_max_lines(self, mock_settings) -> None:
        """Test that print_table respects custom table_max_lines configuration."""
        from unittest.mock import patch

        # Configure mock_settings with custom max_lines value
        mock_settings.table_max_lines = 2

        test_data = [
            {"id": 1, "name": "Item 1", "description": "Short text"},
            {"id": 2, "name": "Item 2", "description": "Line 1\nLine 2\nLine 3\nLine 4\nLine 5"},
        ]
        columns = ["id", "name", "description"]

        # Mock Table.add_row to capture what's passed to it
        with patch.object(Table, "add_row") as mock_add_row:
            print_table(test_data, "Test Table", columns)

            # Verify add_row was called for each data row
            assert mock_add_row.call_count == 2

            # Check that all arguments to add_row are LineLimit instances with custom max_lines
            for call in mock_add_row.call_args_list:
                args = call[0]  # Get positional arguments
                for arg in args:
                    assert isinstance(arg, LineLimit), f"Expected LineLimit but got {type(arg)}"
                    # Verify max_lines is set to custom value of 2
                    assert arg.max_lines == 2

    def test_print_table_with_disabled_line_limit(self, mock_settings) -> None:
        """Test that print_table skips LineLimit wrapping when table_max_lines is 0 or negative."""
        from unittest.mock import patch

        # Configure mock_settings with disabled max_lines value (0)
        mock_settings.table_max_lines = 0

        test_data = [
            {"id": 1, "name": "Item 1", "description": "Short text"},
            {"id": 2, "name": "Item 2", "description": "Line 1\nLine 2\nLine 3\nLine 4\nLine 5"},
        ]
        columns = ["id", "name", "description"]

        # Mock Table.add_row to capture what's passed to it
        with patch.object(Table, "add_row") as mock_add_row:
            print_table(test_data, "Test Table", columns)

            # Verify add_row was called for each data row
            assert mock_add_row.call_count == 2

            # Check that arguments to add_row are plain strings, NOT LineLimit instances
            for call in mock_add_row.call_args_list:
                args = call[0]  # Get positional arguments
                for arg in args:
                    assert isinstance(arg, str), f"Expected str but got {type(arg)}"
                    assert not isinstance(arg, LineLimit), "Should not wrap with LineLimit when disabled"


class TestPromptForSchema:
    """Tests for prompt_for_schema function."""

    def test_prompt_with_prefilled_values(self, mock_console) -> None:
        """Test that prefilled values are used and not prompted."""

        class TestSchema(BaseModel):
            name: str
            description: str

        prefilled = {"name": "test_name", "description": "test_desc"}

        result = prompt_for_schema(TestSchema, prefilled=prefilled)

        # Should return prefilled values without prompting
        assert result == prefilled
        # Console should show the prefilled values
        assert mock_console.print.call_count >= 3  # Header + 2 fields

    def test_prompt_skips_internal_fields(self, mock_console) -> None:
        """Test that internal fields are skipped."""

        class TestSchema(BaseModel):
            name: str
            model_config: dict = {}  # Should be skipped
            auth_value: str = ""  # Should be skipped

        prefilled = {"name": "test"}

        result = prompt_for_schema(TestSchema, prefilled=prefilled)

        # Should only have the name field
        assert "name" in result
        assert "model_config" not in result
        assert "auth_value" not in result

    def test_prompt_with_string_field(self, mock_console) -> None:
        """Test prompting for string fields."""

        class TestSchema(BaseModel):
            name: str = Field(description="The name")

        with patch("typer.prompt", return_value="user_input"):
            result = prompt_for_schema(TestSchema)

            assert result["name"] == "user_input"

    def test_prompt_with_optional_field(self, mock_console) -> None:
        """Test prompting for optional fields."""

        class TestSchema(BaseModel):
            required_field: str
            optional_field: Optional[str] = None

        with patch("typer.prompt", side_effect=["required_value", ""]):
            result = prompt_for_schema(TestSchema)

            assert result["required_field"] == "required_value"
            # Optional field with empty input should not be in result
            assert "optional_field" not in result or result["optional_field"] == ""

    def test_prompt_with_bool_field(self, mock_console) -> None:
        """Test prompting for boolean fields."""

        class TestSchema(BaseModel):
            enabled: bool

        with patch("typer.confirm", return_value=True):
            with patch("typer.prompt", return_value=True):
                result = prompt_for_schema(TestSchema)

                assert result["enabled"] is True

    def test_prompt_with_optional_bool_field_declined(self, mock_console) -> None:
        """Test prompting for optional boolean field that is declined."""

        class TestSchema(BaseModel):
            enabled: Optional[bool] = None

        # First confirm returns False (don't include field)
        with patch("typer.confirm", return_value=False):
            result = prompt_for_schema(TestSchema)

            # Field should not be in result when declined
            assert "enabled" not in result

    def test_prompt_with_int_field(self, mock_console) -> None:
        """Test prompting for integer fields."""

        class TestSchema(BaseModel):
            count: int

        with patch("typer.prompt", return_value=42):
            result = prompt_for_schema(TestSchema)

            assert result["count"] == 42

    def test_prompt_with_int_field_empty_input(self, mock_console) -> None:
        """Test prompting for optional integer field with empty input."""

        class TestSchema(BaseModel):
            count: Optional[int] = None

        # Return sentinel to simulate skipping optional field
        with patch("typer.prompt", return_value=_INT_SENTINEL_DEFAULT):
            result = prompt_for_schema(TestSchema)

            # Field should not be in result when empty
            assert "count" not in result

    def test_prompt_with_list_field(self, mock_console) -> None:
        """Test prompting for list fields."""

        class TestSchema(BaseModel):
            tags: List[str]

        with patch("typer.prompt", return_value="tag1, tag2, tag3"):
            result = prompt_for_schema(TestSchema)

            assert result["tags"] == ["tag1", "tag2", "tag3"]

    def test_prompt_with_list_field_empty(self, mock_console) -> None:
        """Test prompting for list fields with empty input."""

        class TestSchema(BaseModel):
            tags: Optional[List[str]] = None

        with patch("typer.prompt", return_value=""):
            result = prompt_for_schema(TestSchema)

            # Empty input for list should not add the field
            assert "tags" not in result or result.get("tags") is None

    def test_prompt_dict_str_str(self, mock_console) -> None:
        """Test prompting for a string to string dict"""

        class TestSchema(BaseModel):
            key: Dict[str, str]

        with patch("typer.confirm", side_effect=["y", "y", ""]), patch("typer.prompt", side_effect=["k1", "v1", "k2", "v2"]):
            result = prompt_for_schema(TestSchema)

            # Empty input for list should not add the field
            assert result == {
                "key": {"k1": "v1", "k2": "v2"},
            }

    def test_prompt_with_nested_dicts(self, mock_console) -> None:
        """Test prompting for a nested dict with dict values"""

        class SubSchema(BaseModel):
            num: int

        class TestSchema(BaseModel):
            key: Dict[str, Any]
            sub: SubSchema
            sub_dict: Dict[str, SubSchema]

        with patch("typer.confirm", side_effect=["y", "y", "", "y", ""]), patch("typer.prompt", side_effect=["k1", '{"foo": 1}', "k2", "[1, 2, 3]", 42, "a-num", 123]):
            result = prompt_for_schema(TestSchema)

            # Empty input for list should not add the field
            assert result == {
                "key": {"k1": {"foo": 1}, "k2": [1, 2, 3]},
                "sub": {"num": 42},
                "sub_dict": {"a-num": {"num": 123}},
            }

    def test_prompt_list_of_sub_models(self, mock_console) -> None:
        """Test prompting for a list of sub pydantic models"""

        class SubSchema(BaseModel):
            num: int

        class TestSchema(BaseModel):
            nums: List[SubSchema]

        with patch("typer.confirm", side_effect=["y", "y", ""]), patch("typer.prompt", side_effect=[1, 2]):
            result = prompt_for_schema(TestSchema)

            # Empty input for list should not add the field
            assert result == {"nums": [{"num": 1}, {"num": 2}]}

    def test_prompt_with_default(self, mock_console) -> None:
        """Test prompting with defaults and make sure prompt string added."""

        class TestSchema(BaseModel):
            name: str = "foobar"
            some_val: int = 42

        with patch("typer.prompt", side_effect=["", ""]) as prompt_mock:
            prompt_for_schema(TestSchema)
            assert prompt_mock.call_count == 2
            assert prompt_mock.call_args_list[0][1]["default"] == "foobar"
            assert prompt_mock.call_args_list[1][1]["default"] == 42
            assert any("foobar" in call[0][0] for call in mock_console.print.call_args_list)
            assert any("42" in call[0][0] for call in mock_console.print.call_args_list)

    def test_prompt_missing_required_string(self, mock_console) -> None:
        """Test that an exception is raised if a required string is unset."""

        class TestSchema(BaseModel):
            foo: str

        with patch("typer.prompt", return_value=""):
            with pytest.raises(CLIError):
                prompt_for_schema(TestSchema)


class TestPromptForJsonSchema:
    """Tests for prompt_for_json_schema function."""

    def test_prompt_for_json_schema_required_only_with_prefilled(self, mock_console) -> None:
        """Test prompting only missing required fields when prefilled data exists."""
        schema = {
            "type": "object",
            "properties": {
                "query": {"type": "string"},
                "limit": {"type": "integer"},
            },
            "required": ["query"],
        }
        prefilled = {"limit": 10}

        with patch("typer.prompt", return_value="search term") as mock_prompt:
            result = prompt_for_json_schema(schema, prefilled=prefilled, prompt_optional=False)

        assert result["query"] == "search term"
        assert result["limit"] == 10
        assert mock_prompt.call_count == 1

    def test_prompt_for_json_schema_skips_optional_fields_when_required_only(self, mock_console) -> None:
        """Test optional fields are skipped entirely in required-only mode."""
        schema = {
            "type": "object",
            "properties": {
                "query": {"type": "string"},
            },
        }

        with patch("typer.prompt") as mock_prompt:
            result = prompt_for_json_schema(schema, prompt_optional=False)

        assert result == {}
        mock_prompt.assert_not_called()

    def test_prompt_for_json_schema_prompts_optional_fields(self, mock_console) -> None:
        """Test optional fields are prompted in full interactive mode."""
        schema = {
            "type": "object",
            "properties": {
                "query": {"type": "string"},
            },
        }

        with patch("typer.prompt", return_value="search term"):
            result = prompt_for_json_schema(schema, prompt_optional=True)

        assert result["query"] == "search term"

    def test_prompt_for_json_schema_prefilled_nested_object_prompts_missing_required(self, mock_console) -> None:
        """Test nested required fields are prompted when parent object is prefilled."""
        schema = {
            "type": "object",
            "properties": {
                "config": {
                    "type": "object",
                    "properties": {
                        "name": {"type": "string"},
                        "timeout": {"type": "integer"},
                    },
                    "required": ["name"],
                }
            },
            "required": ["config"],
        }
        prefilled = {"config": {"timeout": 30}}

        with patch("typer.prompt", return_value="tool-name") as mock_prompt:
            result = prompt_for_json_schema(schema, prefilled=prefilled, prompt_optional=False)

        assert result == {"config": {"timeout": 30, "name": "tool-name"}}
        assert mock_prompt.call_count == 1

    def test_prompt_for_json_schema_requires_object_schema(self, mock_console) -> None:
        """Test non-object root schema raises a CLIError."""
        schema = {"type": "string"}

        with pytest.raises(CLIError):
            prompt_for_json_schema(schema)

    def test_prompt_for_json_schema_resolves_ref_object(self, mock_console) -> None:
        """Test object fields referenced via $ref are prompted as objects."""
        schema = {
            "type": "object",
            "$defs": {
                "NestedArgs": {
                    "type": "object",
                    "properties": {
                        "name": {"type": "string"},
                    },
                    "required": ["name"],
                }
            },
            "properties": {
                "config": {"$ref": "#/$defs/NestedArgs"},
            },
            "required": ["config"],
        }

        with patch("typer.prompt", return_value="nested-name") as mock_prompt:
            result = prompt_for_json_schema(schema, prompt_optional=False)

        assert result == {"config": {"name": "nested-name"}}
        assert mock_prompt.call_count == 1

    def test_prompt_for_json_schema_resolves_ref_array(self, mock_console) -> None:
        """Test array fields referenced via $ref are prompted as arrays."""
        schema = {
            "type": "object",
            "$defs": {
                "TagList": {
                    "type": "array",
                    "items": {"type": "string"},
                }
            },
            "properties": {
                "tags": {"$ref": "#/$defs/TagList"},
            },
            "required": ["tags"],
        }

        with patch("typer.confirm", side_effect=[True, True, False]), patch("typer.prompt", side_effect=["one", "two"]):
            result = prompt_for_json_schema(schema, prompt_optional=False)

        assert result == {"tags": ["one", "two"]}

    def test_prompt_for_json_schema_missing_ref_raises(self, mock_console) -> None:
        """Test missing local $ref path raises a CLIError."""
        schema = {
            "type": "object",
            "$defs": {},
            "properties": {
                "config": {"$ref": "#/$defs/DoesNotExist"},
            },
            "required": ["config"],
        }

        with pytest.raises(CLIError, match="Schema reference not found"):
            prompt_for_json_schema(schema, prompt_optional=False)

    def test_prompt_for_json_schema_external_ref_raises(self, mock_console) -> None:
        """Test non-local $ref values are rejected."""
        schema = {
            "type": "object",
            "properties": {
                "config": {"$ref": "https://example.com/schema.json#/$defs/Config"},
            },
            "required": ["config"],
        }

        with pytest.raises(CLIError, match="Only local schema references are supported"):
            prompt_for_json_schema(schema, prompt_optional=False)

    def test_prompt_for_json_schema_cyclic_ref_raises(self, mock_console) -> None:
        """Test cyclic $ref graphs raise a CLIError."""
        schema = {
            "type": "object",
            "$defs": {
                "Node": {"$ref": "#/$defs/Node"},
            },
            "properties": {
                "node": {"$ref": "#/$defs/Node"},
            },
            "required": ["node"],
        }

        with pytest.raises(CLIError, match="Cyclic schema reference detected"):
            prompt_for_json_schema(schema, prompt_optional=False)

    def test_prompt_for_json_schema_non_object_input_schema_raises(self, mock_console) -> None:
        """Test non-dictionary schemas are rejected."""
        with pytest.raises(CLIError, match="Input schema must be a JSON object"):
            prompt_for_json_schema(["not", "an", "object"])  # type: ignore[arg-type]

    def test_prompt_for_json_schema_non_object_prefilled_raises(self, mock_console) -> None:
        """Test non-dictionary prefilled payloads are rejected."""
        schema = {
            "type": "object",
            "properties": {"query": {"type": "string"}},
        }

        with pytest.raises(CLIError, match="Prefilled input must be a JSON object"):
            prompt_for_json_schema(schema, prefilled=["bad"])  # type: ignore[arg-type]

    def test_prompt_for_json_schema_ref_resolving_to_scalar_raises(self, mock_console) -> None:
        """Test $ref pointers resolving to scalar nodes are rejected."""
        schema = {
            "type": "object",
            "$defs": {
                "Config": {
                    "type": "object",
                    "properties": {"kind": {"type": "string"}},
                }
            },
            "properties": {
                "config": {"$ref": "#/$defs/Config/type"},
            },
            "required": ["config"],
        }

        with pytest.raises(CLIError, match="does not resolve to an object schema"):
            prompt_for_json_schema(schema, prompt_optional=False)

    def test_prompt_for_json_schema_ref_invalid_array_index_raises(self, mock_console) -> None:
        """Test invalid array indexes in local $ref pointers are rejected."""
        schema = {
            "type": "object",
            "$defs": {
                "Variants": [{"type": "string"}],
            },
            "properties": {
                "value": {"$ref": "#/$defs/Variants/not-an-index"},
            },
            "required": ["value"],
        }

        with pytest.raises(CLIError, match="Invalid array index in schema reference"):
            prompt_for_json_schema(schema, prompt_optional=False)

    def test_prompt_for_json_schema_handles_nullable_integer_type_lists(self, mock_console) -> None:
        """Test `type` lists like [null, integer] prompt using the concrete type."""
        schema = {
            "type": "object",
            "properties": {
                "limit": {"type": ["null", "integer"]},
            },
            "required": ["limit"],
        }

        with patch("typer.prompt", return_value=7):
            result = prompt_for_json_schema(schema, prompt_optional=False)

        assert result == {"limit": 7}

    def test_prompt_for_json_schema_ref_index_out_of_bounds_raises(self, mock_console) -> None:
        """Test out-of-bounds array indexes in local $ref pointers are rejected."""
        schema = {
            "type": "object",
            "$defs": {
                "Variants": [{"type": "string"}],
            },
            "properties": {
                "value": {"$ref": "#/$defs/Variants/1"},
            },
            "required": ["value"],
        }

        with pytest.raises(CLIError, match="Schema reference index out of bounds"):
            prompt_for_json_schema(schema, prompt_optional=False)

    def test_prompt_for_json_schema_ref_valid_array_index_resolves(self, mock_console) -> None:
        """Test valid array indexes in local $ref pointers resolve correctly."""
        schema = {
            "type": "object",
            "$defs": {
                "Variants": [
                    {
                        "type": "object",
                        "properties": {"name": {"type": "string"}},
                        "required": ["name"],
                    }
                ],
            },
            "properties": {
                "value": {"$ref": "#/$defs/Variants/0"},
            },
            "required": ["value"],
        }

        with patch("typer.prompt", return_value="selected"):
            result = prompt_for_json_schema(schema, prompt_optional=False)

        assert result == {"value": {"name": "selected"}}

    def test_prompt_for_json_schema_ref_path_invalid_raises(self, mock_console) -> None:
        """Test local $ref traversal fails on invalid scalar path traversal."""
        schema = {
            "type": "object",
            "$defs": {
                "Scalar": 1,
            },
            "properties": {
                "value": {"$ref": "#/$defs/Scalar/child"},
            },
            "required": ["value"],
        }

        with pytest.raises(CLIError, match="Schema reference path is invalid"):
            prompt_for_json_schema(schema, prompt_optional=False)

    def test_prompt_for_json_schema_nested_with_non_empty_indent(self, mock_console) -> None:
        """Test nested prompting works with a non-empty root indent."""
        schema = {
            "type": "object",
            "properties": {
                "config": {
                    "type": "object",
                    "properties": {
                        "name": {"type": "string"},
                    },
                    "required": ["name"],
                }
            },
            "required": ["config"],
        }

        with patch("typer.prompt", return_value="nested-name"):
            result = prompt_for_json_schema(schema, indent="|", prompt_optional=False)

        assert result == {"config": {"name": "nested-name"}}

    def test_prompt_for_json_schema_fallback_title_and_prompt_text_metadata(self, mock_console) -> None:
        """Test fallback display title and prompt metadata formatting branches."""
        schema = {
            "type": "object",
            "title": 123,
            "properties": {
                "query": {
                    "type": "string",
                    "description": "Search query",
                    "default": "seed",
                }
            },
            "required": ["query"],
        }

        with patch("typer.prompt", return_value="manual"):
            result = prompt_for_json_schema(schema, prompt_optional=False)

        assert result == {"query": "manual"}

    def test_prompt_for_json_schema_optional_object_decline(self, mock_console) -> None:
        """Test optional object fields can be skipped."""
        schema = {
            "type": "object",
            "properties": {
                "config": {
                    "properties": {
                        "name": {"type": "string"},
                    },
                }
            },
        }

        with patch("typer.confirm", return_value=False):
            result = prompt_for_json_schema(schema, prompt_optional=True)

        assert result == {}

    def test_prompt_for_json_schema_optional_object_included(self, mock_console) -> None:
        """Test optional object fields can be included and prompted."""
        schema = {
            "type": "object",
            "properties": {
                "config": {
                    "type": "object",
                    "properties": {
                        "name": {"type": "string"},
                    },
                    "required": ["name"],
                }
            },
        }

        with patch("typer.confirm", return_value=True), patch("typer.prompt", return_value="chosen"):
            result = prompt_for_json_schema(schema, prompt_optional=True)

        assert result == {"config": {"name": "chosen"}}

    def test_prompt_for_json_schema_object_inferred_from_required_keyword(self, mock_console) -> None:
        """Test object type inference from `required` when `type` is missing."""
        schema = {
            "type": "object",
            "properties": {
                "meta": {
                    "required": ["id"],
                }
            },
            "required": ["meta"],
        }

        result = prompt_for_json_schema(schema, prompt_optional=False)
        assert result == {"meta": {}}

    def test_prompt_for_json_schema_optional_array_inferred_and_declined(self, mock_console) -> None:
        """Test optional arrays inferred from `items` can be skipped."""
        schema = {
            "type": "object",
            "properties": {
                "tags": {
                    "items": {"type": "string"},
                }
            },
        }

        with patch("typer.confirm", return_value=False):
            result = prompt_for_json_schema(schema, prompt_optional=True)

        assert result == {}

    def test_prompt_for_json_schema_type_list_non_string_falls_back_to_items(self, mock_console) -> None:
        """Test non-string type list values fall back to schema-shape inference."""
        schema = {
            "type": "object",
            "properties": {
                "tags": {
                    "type": [1],
                    "items": {"type": "string"},
                }
            },
        }

        with patch("typer.confirm", return_value=False):
            result = prompt_for_json_schema(schema, prompt_optional=True)

        assert result == {}

    def test_prompt_for_json_schema_optional_array_include_no_entries(self, mock_console) -> None:
        """Test optional arrays can be included with no entries."""
        schema = {
            "type": "object",
            "properties": {
                "tags": {
                    "type": "array",
                    "items": {"type": "string"},
                }
            },
        }

        with patch("typer.confirm", side_effect=[True, False]):
            result = prompt_for_json_schema(schema, prompt_optional=True)

        assert result == {"tags": []}

    def test_prompt_for_json_schema_optional_array_collects_multiple_entries(self, mock_console) -> None:
        """Test array entry prompting loops correctly for multiple values."""
        schema = {
            "type": "object",
            "properties": {
                "tags": {
                    "type": "array",
                    "items": {"type": "integer"},
                }
            },
        }

        with patch("typer.confirm", side_effect=[True, True, True, False]), patch("typer.prompt", side_effect=[1, 2]):
            result = prompt_for_json_schema(schema, prompt_optional=True)

        assert result == {"tags": [1, 2]}

    def test_prompt_for_json_schema_prefilled_array_of_objects_and_scalars(self, mock_console) -> None:
        """Test prefilled object-array entries recurse for objects and passthrough other values."""
        schema = {
            "type": "object",
            "properties": {
                "rows": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {"name": {"type": "string"}},
                        "required": ["name"],
                    },
                }
            },
            "required": ["rows"],
        }
        prefilled = {"rows": [{"name": "row-one"}, "raw-entry"]}

        result = prompt_for_json_schema(schema, prefilled=prefilled, prompt_optional=False)
        assert result == prefilled

    def test_prompt_for_json_schema_prefilled_array_of_arrays(self, mock_console) -> None:
        """Test prefilled nested arrays recurse through nested item schemas."""
        schema = {
            "type": "object",
            "properties": {
                "matrix": {
                    "type": "array",
                    "items": {
                        "type": "array",
                        "items": {"type": "integer"},
                    },
                }
            },
            "required": ["matrix"],
        }
        prefilled = {"matrix": [[1, 2], 3]}

        result = prompt_for_json_schema(schema, prefilled=prefilled, prompt_optional=False)
        assert result == prefilled

    def test_prompt_for_json_schema_enum_uses_raw_string_match(self, mock_console) -> None:
        """Test enum prompts accept raw values when JSON parsing changes type."""
        schema = {
            "type": "object",
            "properties": {
                "mode": {
                    "enum": ["1"],
                    "default": "1",
                }
            },
            "required": ["mode"],
        }

        with patch("typer.prompt", return_value="1"):
            result = prompt_for_json_schema(schema, prompt_optional=False)

        assert result == {"mode": "1"}

    def test_prompt_for_json_schema_enum_uses_json_parsed_match(self, mock_console) -> None:
        """Test enum prompts accept values that match after JSON parsing."""
        schema = {
            "type": "object",
            "properties": {
                "priority": {
                    "enum": [1, 2],
                }
            },
            "required": ["priority"],
        }

        with patch("typer.prompt", return_value="1"):
            result = prompt_for_json_schema(schema, prompt_optional=False)

        assert result == {"priority": 1}

    def test_prompt_for_json_schema_optional_enum_blank_is_skipped(self, mock_console) -> None:
        """Test optional enum fields are skipped when left blank."""
        schema = {
            "type": "object",
            "properties": {
                "mode": {"enum": ["enforce", "disabled"]},
            },
        }

        with patch("typer.prompt", return_value=""):
            result = prompt_for_json_schema(schema, prompt_optional=True)

        assert result == {}

    def test_prompt_for_json_schema_required_enum_blank_raises(self, mock_console) -> None:
        """Test required enum fields reject blank values."""
        schema = {
            "type": "object",
            "properties": {
                "mode": {"enum": ["enforce", "disabled"]},
            },
            "required": ["mode"],
        }

        with patch("typer.prompt", return_value=""):
            with pytest.raises(CLIError, match="Field 'mode' is required"):
                prompt_for_json_schema(schema, prompt_optional=False)

    def test_prompt_for_json_schema_invalid_enum_value_raises(self, mock_console) -> None:
        """Test invalid enum values raise a clear error."""
        schema = {
            "type": "object",
            "properties": {
                "mode": {"enum": ["enforce", "disabled"]},
            },
            "required": ["mode"],
        }

        with patch("typer.prompt", return_value="invalid"):
            with pytest.raises(CLIError, match="must be one of"):
                prompt_for_json_schema(schema, prompt_optional=False)

    def test_prompt_for_json_schema_optional_boolean_include_and_prompt(self, mock_console) -> None:
        """Test optional booleans prompt when included."""
        schema = {
            "type": "object",
            "properties": {
                "enabled": {
                    "type": "boolean",
                    "default": True,
                }
            },
        }

        with patch("typer.confirm", return_value=True), patch("typer.prompt", return_value=False):
            result = prompt_for_json_schema(schema, prompt_optional=True)

        assert result == {"enabled": False}

    def test_prompt_for_json_schema_optional_boolean_decline(self, mock_console) -> None:
        """Test optional booleans can be skipped by declining inclusion."""
        schema = {
            "type": "object",
            "properties": {
                "enabled": {
                    "type": "boolean",
                }
            },
        }

        with patch("typer.confirm", return_value=False):
            result = prompt_for_json_schema(schema, prompt_optional=True)

        assert result == {}

    def test_prompt_for_json_schema_required_boolean_prompts_directly(self, mock_console) -> None:
        """Test required booleans prompt without inclusion confirmation."""
        schema = {
            "type": "object",
            "properties": {
                "enabled": {
                    "type": "boolean",
                }
            },
            "required": ["enabled"],
        }

        with patch("typer.prompt", return_value=True):
            result = prompt_for_json_schema(schema, prompt_optional=False)

        assert result == {"enabled": True}

    def test_prompt_for_json_schema_integer_with_default(self, mock_console) -> None:
        """Test integer prompts with integer defaults."""
        schema = {
            "type": "object",
            "properties": {
                "count": {
                    "type": "integer",
                    "default": 3,
                }
            },
            "required": ["count"],
        }

        with patch("typer.prompt", return_value=7):
            result = prompt_for_json_schema(schema, prompt_optional=False)

        assert result == {"count": 7}

    def test_prompt_for_json_schema_required_integer_sentinel_raises(self, mock_console) -> None:
        """Test required integers reject sentinel-equivalent empty values."""
        schema = {
            "type": "object",
            "properties": {
                "count": {"type": "integer"},
            },
            "required": ["count"],
        }

        with patch("typer.prompt", return_value=_INT_SENTINEL_DEFAULT):
            with pytest.raises(CLIError, match="Field 'count' is required"):
                prompt_for_json_schema(schema, prompt_optional=False)

    def test_prompt_for_json_schema_optional_integer_sentinel_is_skipped(self, mock_console) -> None:
        """Test optional integers are skipped when sentinel-equivalent value is returned."""
        schema = {
            "type": "object",
            "properties": {
                "count": {"type": "integer"},
            },
        }

        with patch("typer.prompt", return_value=_INT_SENTINEL_DEFAULT):
            result = prompt_for_json_schema(schema, prompt_optional=True)

        assert result == {}

    def test_prompt_for_json_schema_number_with_default(self, mock_console) -> None:
        """Test number prompts parse float values and respect defaults."""
        schema = {
            "type": "object",
            "properties": {
                "score": {
                    "type": "number",
                    "default": 1.5,
                }
            },
            "required": ["score"],
        }

        with patch("typer.prompt", return_value="2.25"):
            result = prompt_for_json_schema(schema, prompt_optional=False)

        assert result == {"score": 2.25}

    def test_prompt_for_json_schema_required_number_blank_raises(self, mock_console) -> None:
        """Test required numbers reject blank input."""
        schema = {
            "type": "object",
            "properties": {
                "score": {"type": "number"},
            },
            "required": ["score"],
        }

        with patch("typer.prompt", return_value=""):
            with pytest.raises(CLIError, match="Field 'score' is required"):
                prompt_for_json_schema(schema, prompt_optional=False)

    def test_prompt_for_json_schema_optional_number_blank_is_skipped(self, mock_console) -> None:
        """Test optional numbers are skipped when blank input is provided."""
        schema = {
            "type": "object",
            "properties": {
                "score": {"type": "number"},
            },
        }

        with patch("typer.prompt", return_value=""):
            result = prompt_for_json_schema(schema, prompt_optional=True)

        assert result == {}

    def test_prompt_for_json_schema_invalid_number_raises(self, mock_console) -> None:
        """Test invalid numeric input raises a number-specific error."""
        schema = {
            "type": "object",
            "properties": {
                "score": {"type": "number"},
            },
            "required": ["score"],
        }

        with patch("typer.prompt", return_value="not-a-number"):
            with pytest.raises(CLIError, match="Field 'score' must be a number"):
                prompt_for_json_schema(schema, prompt_optional=False)

    def test_prompt_for_json_schema_nullable_type_list_with_only_null(self, mock_console) -> None:
        """Test union-like type lists containing only null resolve to None."""
        schema = {
            "type": "object",
            "properties": {
                "empty_value": {"type": ["null"]},
            },
            "required": ["empty_value"],
        }

        result = prompt_for_json_schema(schema, prompt_optional=False)
        assert result == {"empty_value": None}

    def test_prompt_for_json_schema_string_default_non_string_value(self, mock_console) -> None:
        """Test string-like fallback prompts render non-string defaults."""
        schema = {
            "type": "object",
            "properties": {
                "payload": {
                    "default": {"kind": "map"},
                }
            },
            "required": ["payload"],
        }

        with patch("typer.prompt", return_value='{"ok":true}'):
            result = prompt_for_json_schema(schema, prompt_optional=False)

        assert result == {"payload": '{"ok":true}'}

    def test_prompt_for_json_schema_required_fallback_string_blank_raises(self, mock_console) -> None:
        """Test required fallback string fields reject blank input."""
        schema = {
            "type": "object",
            "properties": {
                "name": {},
            },
            "required": ["name"],
        }

        with patch("typer.prompt", return_value=""):
            with pytest.raises(CLIError, match="Field 'name' is required"):
                prompt_for_json_schema(schema, prompt_optional=False)

    def test_prompt_for_json_schema_optional_fallback_string_blank_is_skipped(self, mock_console) -> None:
        """Test optional fallback string fields are skipped when blank."""
        schema = {
            "type": "object",
            "properties": {
                "name": {},
            },
        }

        with patch("typer.prompt", return_value=""):
            result = prompt_for_json_schema(schema, prompt_optional=True)

        assert result == {}

    def test_prompt_for_json_schema_additional_properties_schema(self, mock_console) -> None:
        """Test `additionalProperties` schema prompts for typed extra fields."""
        schema = {
            "type": "object",
            "additionalProperties": {"type": "integer"},
        }

        with patch("typer.confirm", side_effect=[True, False]), patch("typer.prompt", side_effect=["max_items", 10]):
            result = prompt_for_json_schema(schema, prompt_optional=True)

        assert result == {"max_items": 10}

    def test_prompt_for_json_schema_additional_properties_true_json_and_raw(self, mock_console) -> None:
        """Test `additionalProperties: true` parses JSON and falls back to raw strings."""
        schema = {
            "type": "object",
            "additionalProperties": True,
        }

        with patch("typer.confirm", side_effect=[True, True, False]), patch("typer.prompt", side_effect=["alpha", '{"nested": 1}', "beta", "raw-text"]):
            result = prompt_for_json_schema(schema, prompt_optional=True)

        assert result == {"alpha": {"nested": 1}, "beta": "raw-text"}


class TestTokenFilePermissions:
    """Tests for token file permission handling."""

    def test_save_token_creates_parent_dirs(self) -> None:
        """Test that save_token creates parent directories."""
        with tempfile.TemporaryDirectory() as temp_dir:
            token_path = Path(temp_dir) / "nested" / "dirs" / "token"

            with patch("cforge.common.get_token_file", return_value=token_path):
                save_token("test_token")

                assert token_path.exists()
                assert token_path.read_text() == "test_token"

    def test_save_token_sets_permissions(self) -> None:
        """Test that save_token sets restrictive permissions."""
        with tempfile.NamedTemporaryFile(delete=False) as temp_file:
            token_path = Path(temp_file.name)

            try:
                with patch("cforge.common.get_token_file", return_value=token_path):
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
