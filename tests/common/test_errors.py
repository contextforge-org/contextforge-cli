# -*- coding: utf-8 -*-
"""Tests for cforge.common.errors."""

# First-Party
from cforge.common.errors import AuthenticationError, CLIError


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
