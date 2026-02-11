# -*- coding: utf-8 -*-
"""Location: ./tests/commands/resources/test_plugins.py
Copyright 2025
SPDX-License-Identifier: Apache-2.0
Authors: Matthew Grigsby

Tests for the plugins commands.
"""

# Third-Party
import pytest
import typer

# First-Party
from cforge.commands.resources.plugins import PluginMode, plugins_get, plugins_list, plugins_stats
from cforge.common import AuthenticationError, CLIError
from tests.conftest import invoke_typer_command, patch_functions


class TestPluginCommands:
    """Tests for plugins commands."""

    def test_plugin_mode_enum_is_case_insensitive(self) -> None:
        """Typer Enum choices should accept case-insensitive values."""
        assert PluginMode("EnFoRcE") == PluginMode.ENFORCE

    def test_plugin_mode_enum_missing_non_string(self) -> None:
        """Non-string values should not be coerced into Enum members."""
        assert PluginMode._missing_(123) is None

    def test_plugin_mode_enum_missing_unknown_value(self) -> None:
        """Unknown strings should not be coerced into Enum members."""
        assert PluginMode._missing_("nope") is None

    def test_plugins_list_success(self, mock_console) -> None:
        """Test plugins list command with table output."""
        mock_response = {
            "plugins": [
                {"name": "pii_filter", "version": "1.0.0", "author": "ContextForge", "mode": "enforce", "status": "enabled", "priority": 10, "hooks": ["tool_pre_invoke"], "tags": ["security"]}
            ],
            "total": 1,
            "enabled_count": 1,
            "disabled_count": 0,
        }

        with patch_functions(
            "cforge.commands.resources.plugins",
            get_console=mock_console,
            make_authenticated_request={"return_value": mock_response},
            print_table=None,
        ) as mocks:
            invoke_typer_command(plugins_list)
            mocks.print_table.assert_called_once()

    def test_plugins_list_json_output(self, mock_console) -> None:
        """Test plugins list with JSON output."""
        mock_response = {"plugins": [], "total": 0, "enabled_count": 0, "disabled_count": 0}
        with patch_functions(
            "cforge.commands.resources.plugins",
            get_console=mock_console,
            make_authenticated_request={"return_value": mock_response},
            print_json=None,
        ) as mocks:
            invoke_typer_command(plugins_list, json_output=True)
            mocks.print_json.assert_called_once()

    def test_plugins_list_no_results(self, mock_console) -> None:
        """Test plugins list with no results."""
        mock_response = {"plugins": [], "total": 0, "enabled_count": 0, "disabled_count": 0}
        with patch_functions("cforge.commands.resources.plugins", get_console=mock_console, make_authenticated_request={"return_value": mock_response}):
            invoke_typer_command(plugins_list)

        assert any("No plugins found" in str(call) for call in mock_console.print.call_args_list)

    def test_plugins_list_with_filters(self, mock_console) -> None:
        """Test plugins list with all filters."""
        with patch_functions(
            "cforge.commands.resources.plugins",
            get_console=mock_console,
            make_authenticated_request={"return_value": {"plugins": [], "total": 0, "enabled_count": 0, "disabled_count": 0}},
            print_table=None,
        ) as mocks:
            invoke_typer_command(plugins_list, search="pii", mode=PluginMode.ENFORCE, hook="tool_pre_invoke", tag="security")

            call_args = mocks.make_authenticated_request.call_args
            assert call_args[0][0] == "GET"
            assert call_args[0][1] == "/admin/plugins"
            assert call_args[1]["params"] == {"search": "pii", "mode": "enforce", "hook": "tool_pre_invoke", "tag": "security"}

    def test_plugins_list_error(self, mock_console) -> None:
        """Test plugins list error handling."""
        with patch_functions("cforge.commands.resources.plugins", get_console=mock_console, make_authenticated_request={"side_effect": Exception("API error")}):
            with pytest.raises(typer.Exit):
                invoke_typer_command(plugins_list)

    def test_plugins_get_success(self, mock_console) -> None:
        """Test plugins get command."""
        mock_plugin = {"name": "pii_filter", "version": "1.0.0"}
        with patch_functions(
            "cforge.commands.resources.plugins",
            get_console=mock_console,
            make_authenticated_request={"return_value": mock_plugin},
            print_json=None,
        ) as mocks:
            invoke_typer_command(plugins_get, name="pii_filter")
            mocks.print_json.assert_called_once()

    def test_plugins_get_error(self, mock_console) -> None:
        """Test plugins get error handling."""
        with patch_functions("cforge.commands.resources.plugins", get_console=mock_console, make_authenticated_request={"side_effect": Exception("API error")}):
            with pytest.raises(typer.Exit):
                invoke_typer_command(plugins_get, name="pii_filter")

    def test_plugins_stats_success(self, mock_console) -> None:
        """Test plugins stats command."""
        mock_stats = {"total_plugins": 4, "enabled_plugins": 3, "disabled_plugins": 1, "plugins_by_hook": {"tool_pre_invoke": 3}, "plugins_by_mode": {"enforce": 3, "disabled": 1}}
        with patch_functions(
            "cforge.commands.resources.plugins",
            get_console=mock_console,
            make_authenticated_request={"return_value": mock_stats},
            print_json=None,
        ) as mocks:
            invoke_typer_command(plugins_stats)
            mocks.print_json.assert_called_once()

    def test_plugins_stats_error(self, mock_console) -> None:
        """Test plugins stats error handling."""
        with patch_functions("cforge.commands.resources.plugins", get_console=mock_console, make_authenticated_request={"side_effect": Exception("API error")}):
            with pytest.raises(typer.Exit):
                invoke_typer_command(plugins_stats)

    def test_plugins_list_forbidden_shows_permission_hint(self, mock_console) -> None:
        """Test plugins list shows a targeted hint on forbidden/admin failures."""
        with patch_functions(
            "cforge.commands.resources.plugins",
            get_console=mock_console,
            make_authenticated_request={"side_effect": AuthenticationError("Authentication required but not configured")},
        ):
            with pytest.raises(typer.Exit):
                invoke_typer_command(plugins_list)

        assert any("Requires admin.plugins permission" in str(call) for call in mock_console.print.call_args_list)

    def test_plugins_list_not_found_shows_admin_api_hint(self, mock_console) -> None:
        """Test plugins list shows an admin-api hint on 404."""
        with patch_functions(
            "cforge.commands.resources.plugins",
            get_console=mock_console,
            make_authenticated_request={"side_effect": CLIError("API request failed (404): Not Found")},
        ):
            with pytest.raises(typer.Exit):
                invoke_typer_command(plugins_list)

        assert any("Admin plugin API unavailable" in str(call) for call in mock_console.print.call_args_list)
