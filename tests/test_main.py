# -*- coding: utf-8 -*-
"""Location: ./tests/test_main.py
Copyright 2025
SPDX-License-Identifier: Apache-2.0
Authors: Gabe Goodhart

Tests for the main CLI application.
"""

# Third-Party
from typer.testing import CliRunner

# First-Party
from cforge.main import app


class TestMain:
    """Tests for main CLI application."""

    def test_app_help(self, cli_runner: CliRunner) -> None:
        """Test that the CLI help command works."""
        result = cli_runner.invoke(app, ["--help"])
        assert result.exit_code == 0
        assert "MCP Gateway" in result.stdout

    def test_app_version(self, cli_runner: CliRunner) -> None:
        """Test that the version command works."""
        result = cli_runner.invoke(app, ["version"])
        assert result.exit_code == 0
        assert "version" in result.stdout.lower()
