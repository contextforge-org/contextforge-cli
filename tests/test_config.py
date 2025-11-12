# -*- coding: utf-8 -*-
"""Location: ./tests/test_config.py
Copyright 2025
SPDX-License-Identifier: Apache-2.0
Authors: Gabe Goodhart

Tests for configuration management.
"""

# First-Party
from cforge.config import get_settings


class TestConfig:
    """Tests for configuration management."""

    def test_get_settings_returns_settings(self) -> None:
        """Test that get_settings returns a Settings instance."""
        settings = get_settings()
        assert settings is not None
        assert hasattr(settings, "host")
        assert hasattr(settings, "port")
        assert hasattr(settings, "mcpg_home")

    def test_get_settings_singleton(self) -> None:
        """Test that get_settings returns the same instance."""
        settings1 = get_settings()
        settings2 = get_settings()
        assert settings1 is settings2
