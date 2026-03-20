# -*- coding: utf-8 -*-
"""Tests for cforge.common.console."""

# Local
from cforge.common.console import get_app, get_console


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
