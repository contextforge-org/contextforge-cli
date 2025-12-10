# -*- coding: utf-8 -*-
"""Location: ./tests/test_config.py
Copyright 2025
SPDX-License-Identifier: Apache-2.0
Authors: Gabe Goodhart

Tests for configuration management.
"""
# Standard
from pathlib import Path
from unittest import mock
import os
import tempfile

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
        assert hasattr(settings, "contextforge_home")

    def test_get_settings_singleton(self) -> None:
        """Test that get_settings returns the same instance."""
        settings1 = get_settings()
        settings2 = get_settings()
        assert settings1 is settings2

    def test_get_settings_make_home(self) -> None:
        """Test that get_settings will create the home dir if needed"""
        try:
            get_settings.cache_clear()
            with tempfile.TemporaryDirectory() as work_dir:
                home_dir = Path(work_dir) / "some_new_home"
                assert not home_dir.exists()
                with mock.patch.dict(os.environ, {"CONTEXTFORGE_HOME": str(home_dir)}):
                    settings = get_settings()
                    assert settings.contextforge_home == home_dir
                    assert home_dir.exists()
        finally:
            get_settings.cache_clear()
