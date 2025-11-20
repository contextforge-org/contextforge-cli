# -*- coding: utf-8 -*-
"""Location: ./tests/commands/settings/test_version.py
Copyright 2025
SPDX-License-Identifier: Apache-2.0
Authors: Gabe Goodhart

Tests for the version command.
"""

# First-Party
from cforge.commands.settings.version import version
from mcpgateway import __version__


class TestVersionCommand:
    """Tests for version command."""

    def test_version_live_server(self, mock_console, authorized_mock_client) -> None:
        """Test with a live server."""
        version()
        assert mock_console.print.call_count == 2
        lines = [call[0][0] for call in mock_console.print.call_args_list]
        assert any("Client" in line and __version__ in line for line in lines)
        assert any("Server" in line and __version__ in line for line in lines)

    def test_version_no_server(self, mock_console) -> None:
        """Test with no live server."""
        version()
        assert mock_console.print.call_count == 3
        lines = [call[0][0] for call in mock_console.print.call_args_list]
        assert any("Client" in line and __version__ in line for line in lines)
        assert any("Server" in line and "UNREACHABLE" in line for line in lines)
