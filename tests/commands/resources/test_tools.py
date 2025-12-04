# -*- coding: utf-8 -*-
"""Location: ./tests/commands/resources/test_tools.py
Copyright 2025
SPDX-License-Identifier: Apache-2.0
Authors: Gabe Goodhart

Tests for the tools commands.
"""

# Standard
import json
import tempfile
from pathlib import Path
from unittest.mock import patch

# Third-Party
import click
import pytest
import typer

# First-Party
from cforge.commands.resources.tools import (
    tools_create,
    tools_delete,
    tools_get,
    tools_list,
    tools_toggle,
    tools_update,
)
from tests.conftest import patch_functions


class TestToolsCommands:
    """Tests for tools commands."""

    def test_tools_list_success(self, mock_console) -> None:
        """Test tools list command."""
        mock_tools = [{"id": "tool-1", "name": "tool1", "description": "desc1", "mcp_server_id": "mcp-1", "enabled": True}]

        with patch("cforge.commands.resources.tools.get_console", return_value=mock_console):
            with patch("cforge.commands.resources.tools.make_authenticated_request", return_value=mock_tools):
                with patch("cforge.commands.resources.tools.print_table") as mock_print:
                    tools_list(mcp_server_id=None, active_only=False, json_output=False)
                    mock_print.assert_called_once()

    def test_tools_list_json_output(self, mock_console) -> None:
        """Test tools list with JSON output."""
        with patch("cforge.commands.resources.tools.get_console", return_value=mock_console):
            with patch("cforge.commands.resources.tools.make_authenticated_request", return_value=[]):
                with patch("cforge.commands.resources.tools.print_json") as mock_print:
                    tools_list(mcp_server_id=None, active_only=False, json_output=True)
                    mock_print.assert_called_once()

    def test_tools_list_with_filters(self, mock_console) -> None:
        """Test tools list with filters."""
        with patch("cforge.commands.resources.tools.get_console", return_value=mock_console):
            with patch("cforge.commands.resources.tools.make_authenticated_request", return_value=[]) as mock_req:
                with patch("cforge.commands.resources.tools.print_table"):
                    tools_list(mcp_server_id="5", active_only=True, json_output=False)

                # Verify params
                call_args = mock_req.call_args
                assert call_args[1]["params"]["gateway_id"] == "5"
                assert call_args[1]["params"]["include_inactive"] is False

    def test_tools_list_no_results(self, mock_console) -> None:
        """Test tools list with no results."""
        with patch("cforge.commands.resources.tools.get_console", return_value=mock_console):
            with patch("cforge.commands.resources.tools.make_authenticated_request", return_value=[]):
                tools_list(mcp_server_id=None, active_only=False, json_output=False)

        # Verify "No tools found" message
        assert any("No tools found" in str(call) for call in mock_console.print.call_args_list)

    def test_tools_list_error(self, mock_console) -> None:
        """Test tools list error handling."""
        with patch("cforge.commands.resources.tools.get_console", return_value=mock_console):
            with patch("cforge.commands.resources.tools.make_authenticated_request", side_effect=Exception("API error")):
                with pytest.raises(typer.Exit):
                    tools_list(mcp_server_id=None, active_only=False, json_output=False)

    def test_tools_get_success(self, mock_console) -> None:
        """Test tools get command."""
        mock_tool = {"id": "tool-1", "name": "test"}

        with patch("cforge.commands.resources.tools.get_console", return_value=mock_console):
            with patch("cforge.commands.resources.tools.make_authenticated_request", return_value=mock_tool):
                with patch("cforge.commands.resources.tools.print_json"):
                    tools_get(tool_id="tool-1", json_output=False)

    def test_tools_create_from_file(self, mock_console) -> None:
        """Test tools create from file."""
        mock_result = {"id": "tool-1", "name": "new_tool"}

        with tempfile.TemporaryDirectory() as temp_dir:
            data_file = Path(temp_dir) / "tool.json"
            data_file.write_text(json.dumps({"name": "new_tool", "description": "desc"}))

            with patch("cforge.commands.resources.tools.get_console", return_value=mock_console):
                with patch("cforge.commands.resources.tools.make_authenticated_request", return_value=mock_result):
                    with patch("cforge.commands.resources.tools.print_json"):
                        tools_create(data_file=data_file, name=None, description=None)

    def test_tools_create_file_not_found(self, mock_console) -> None:
        """Test tools create with missing file."""
        with patch("cforge.commands.resources.tools.get_console", return_value=mock_console):
            with pytest.raises(typer.Exit):
                tools_create(data_file=Path("/nonexistent.json"), name=None, description=None)

    def test_tools_create_interactive(self, mock_console) -> None:
        """Test tools create interactive mode."""
        mock_result = {"id": "tool-1", "name": "new_tool"}

        with patch("cforge.commands.resources.tools.get_console", return_value=mock_console):
            with patch("cforge.commands.resources.tools.prompt_for_schema", return_value={"name": "test"}):
                with patch("cforge.commands.resources.tools.make_authenticated_request", return_value=mock_result):
                    with patch("cforge.commands.resources.tools.print_json"):
                        tools_create(data_file=None, name=None, description=None)

    def test_tools_create_with_options(self, mock_console) -> None:
        """Test tools create with command-line options."""
        mock_result = {"id": "tool-1", "name": "new_tool"}

        with patch("cforge.commands.resources.tools.get_console", return_value=mock_console):
            with patch("cforge.commands.resources.tools.prompt_for_schema", return_value={"name": "test", "description": "desc"}) as mock_prompt:
                with patch("cforge.commands.resources.tools.make_authenticated_request", return_value=mock_result):
                    with patch("cforge.commands.resources.tools.print_json"):
                        tools_create(data_file=None, name="test", description="desc")

                # Verify prefilled values
                call_args = mock_prompt.call_args
                assert call_args[1]["prefilled"]["name"] == "test"
                assert call_args[1]["prefilled"]["description"] == "desc"

    def test_tools_update_success(self, mock_console) -> None:
        """Test tools update command."""
        mock_result = {"id": "tool-1", "name": "updated"}

        with tempfile.TemporaryDirectory() as temp_dir:
            data_file = Path(temp_dir) / "update.json"
            data_file.write_text(json.dumps({"description": "updated desc"}))

            with patch("cforge.commands.resources.tools.get_console", return_value=mock_console):
                with patch("cforge.commands.resources.tools.make_authenticated_request", return_value=mock_result):
                    with patch("cforge.commands.resources.tools.print_json"):
                        tools_update(tool_id="tool-1", data_file=data_file)

    def test_tools_update_file_not_found(self, mock_console) -> None:
        """Test tools update with missing file."""
        with patch("cforge.commands.resources.tools.get_console", return_value=mock_console):
            with pytest.raises(typer.Exit):
                tools_update(tool_id="tool-1", data_file=Path("/nonexistent.json"))

    def test_tools_delete_with_confirmation(self, mock_console) -> None:
        """Test tools delete with confirmation."""
        with patch("cforge.commands.resources.tools.get_console", return_value=mock_console):
            with patch("cforge.commands.resources.tools.make_authenticated_request"):
                with patch("cforge.commands.resources.tools.typer.confirm", return_value=True):
                    tools_delete(tool_id="tool-1", confirm=False)

    def test_tools_delete_cancelled(self, mock_console) -> None:
        """Test tools delete cancelled."""
        with patch("cforge.commands.resources.tools.get_console", return_value=mock_console):
            with patch("cforge.commands.resources.tools.typer.confirm", return_value=False):
                with pytest.raises(typer.Exit) as exc_info:
                    tools_delete(tool_id="tool-1", confirm=False)

                # Note: Exit(0) gets caught by exception handler and converted to Exit(1)
                assert exc_info.value.exit_code == 1

    def test_tools_delete_with_yes_flag(self, mock_console) -> None:
        """Test tools delete with --yes flag."""
        with patch("cforge.commands.resources.tools.get_console", return_value=mock_console):
            with patch("cforge.commands.resources.tools.make_authenticated_request"):
                tools_delete(tool_id="tool-1", confirm=True)

        # Should not prompt
        assert not any("confirm" in str(call) for call in mock_console.print.call_args_list)

    def test_tools_toggle_from_disabled_to_enabled(self, mock_console) -> None:
        """Test toggling a tool from disabled to enabled."""
        with patch("cforge.commands.resources.tools.get_console", return_value=mock_console):
            with patch("cforge.commands.resources.tools.make_authenticated_request") as mock_req:
                # First call (GET) returns disabled tool, second call (POST) returns enabled tool
                mock_req.side_effect = [{"id": "1", "name": "test", "enabled": False}, {"id": "1", "name": "test", "enabled": True}]  # GET current status  # POST toggle result
                with patch("cforge.commands.resources.tools.print_json"):
                    tools_toggle(tool_id="1")

                # Verify two calls were made
                assert mock_req.call_count == 2

                # Verify first call was GET to check current status
                get_call = mock_req.call_args_list[0]
                assert get_call[0][0] == "GET"
                assert get_call[0][1] == "/tools/1"

                # Verify second call was POST with activate=True
                post_call = mock_req.call_args_list[1]
                assert post_call[0][0] == "POST"
                assert post_call[0][1] == "/tools/1/toggle"
                assert post_call[1]["params"]["activate"] is True

    def test_tools_toggle_from_enabled_to_disabled(self, mock_console) -> None:
        """Test toggling a tool from enabled to disabled."""
        with patch("cforge.commands.resources.tools.get_console", return_value=mock_console):
            with patch("cforge.commands.resources.tools.make_authenticated_request") as mock_req:
                # First call (GET) returns enabled tool, second call (POST) returns disabled tool
                mock_req.side_effect = [{"id": "1", "name": "test", "enabled": True}, {"id": "1", "name": "test", "enabled": False}]  # GET current status  # POST toggle result
                with patch("cforge.commands.resources.tools.print_json"):
                    tools_toggle(tool_id="1")

                # Verify two calls were made
                assert mock_req.call_count == 2

                # Verify first call was GET to check current status
                get_call = mock_req.call_args_list[0]
                assert get_call[0][0] == "GET"
                assert get_call[0][1] == "/tools/1"

                # Verify second call was POST with activate=False
                post_call = mock_req.call_args_list[1]
                assert post_call[0][0] == "POST"
                assert post_call[0][1] == "/tools/1/toggle"
                assert post_call[1]["params"]["activate"] is False

    def test_tools_toggle_detects_current_status(self, mock_console) -> None:
        """Test that toggle command detects current status before toggling."""
        with patch("cforge.commands.resources.tools.get_console", return_value=mock_console):
            with patch("cforge.commands.resources.tools.make_authenticated_request") as mock_req:
                # Mock a tool that is currently enabled
                mock_req.side_effect = [{"id": "1", "name": "test", "enabled": True}, {"id": "1", "name": "test", "enabled": False}]
                with patch("cforge.commands.resources.tools.print_json"):
                    tools_toggle(tool_id="1")

                # Verify GET was called first to detect current status
                calls = mock_req.call_args_list
                assert len(calls) == 2
                assert calls[0][0][0] == "GET"  # First call is GET
                assert calls[1][0][0] == "POST"  # Second call is POST

    def test_tools_get_error(self, mock_console) -> None:
        """Test tools get error handling."""
        with patch("cforge.commands.resources.tools.get_console", return_value=mock_console):
            with patch("cforge.commands.resources.tools.make_authenticated_request", side_effect=Exception("API error")):
                with pytest.raises(typer.Exit):
                    tools_get(tool_id="tool-1")

    def test_tools_toggle_error(self, mock_console) -> None:
        """Test tools toggle error handling."""
        with patch("cforge.commands.resources.tools.get_console", return_value=mock_console):
            with patch("cforge.commands.resources.tools.make_authenticated_request", side_effect=Exception("API error")):
                with pytest.raises(typer.Exit):
                    tools_toggle(tool_id="tool-1")


class TestToolsCommandsIntegration:
    """Test tools commands with a real gateway test client."""

    def test_tools_list_get(self, mock_console, registered_mcp_server) -> None:
        """Test listing and getting tools from a registered MCP server"""
        with patch_functions("cforge.commands.resources.tools", get_console=mock_console, print_json=None) as mocks:
            tools_list(json_output=True, mcp_server_id=None, active_only=False)
            mocks.print_json.assert_called_once()
            body = mocks.print_json.call_args[0][0]
            assert isinstance(body, list) and len(body) == 2
            for prompt in body:
                mocks.print_json.reset_mock()
                tools_get(prompt["id"])
                mocks.print_json.assert_called_once()
                body = mocks.print_json.call_args[0][0]
                assert isinstance(body, dict)

    def test_tools_lifecycle(self, mock_console, authorized_mock_client) -> None:
        """Test the lifecycle of tools created via the API not a server"""
        tool_body = {"name": "foo", "content": "hi there", "url": "http://test-greet"}
        with patch_functions(
            "cforge.commands.resources.tools",
            get_console=mock_console,
            print_json=None,
            prompt_for_schema={"return_value": tool_body},
        ) as mocks:
            # Create the resource
            tools_create(data_file=None)
            mocks.print_json.assert_called_once()
            body = mocks.print_json.call_args[0][0]
            tool_id = body["id"]
            mocks.print_json.reset_mock()

            # Get the tool by id
            tools_get(tool_id)
            mocks.print_json.assert_called_once()
            body = mocks.print_json.call_args[0][0]
            assert body["url"] == tool_body["url"]
            mocks.print_json.reset_mock()

        update_tool_body = {"name": "foobar"}
        with patch_functions(
            "cforge.commands.resources.tools",
            get_console=mock_console,
            print_json=None,
            prompt_for_schema={"return_value": update_tool_body},
        ) as mocks:
            # Update the resource
            tools_update(tool_id, data_file=None)
            mocks.print_json.assert_called_once()
            body = mocks.print_json.call_args[0][0]
            assert body["url"] == tool_body["url"]
            assert body["name"] == update_tool_body["name"]
            mocks.print_json.reset_mock()
            tools_get(tool_id)
            mocks.print_json.assert_called_once()
            body = mocks.print_json.call_args[0][0]

            # Delete the resource
            tools_delete(tool_id)
            mocks.print_json.reset_mock()

            # Make sure it's gone
            with pytest.raises(click.exceptions.Exit):
                tools_get(tool_id)

    def test_tools_list_active_only_integration(self, mock_console, registered_mcp_server) -> None:
        """Test --active-only flag filters correctly with real server."""
        with patch_functions("cforge.commands.resources.tools", print_json=None, get_console=mock_console) as mocks:
            # Get the tools from the registered server
            tools_list(mcp_server_id=None, active_only=False, json_output=True)
            all_tools = mocks.print_json.call_args[0][0]
            assert len(all_tools) >= 1, "Should have at least one tool from registered server"
            tool_id = all_tools[0]["id"]
            mocks.print_json.reset_mock()

            # Verify it starts enabled (tools from MCP servers start enabled)
            tools_list(mcp_server_id=None, active_only=True, json_output=True)
            active_tools = mocks.print_json.call_args[0][0]
            assert any(t["id"] == tool_id for t in active_tools), "Tool should start in active-only list"
            mocks.print_json.reset_mock()

            # Disable it
            tools_toggle(tool_id)
            mocks.print_json.reset_mock()

            # List with active_only=True should NOT include it
            tools_list(mcp_server_id=None, active_only=True, json_output=True)
            active_tools = mocks.print_json.call_args[0][0]
            assert not any(t["id"] == tool_id for t in active_tools), "Disabled tool should NOT appear in active-only list"
            mocks.print_json.reset_mock()

            # List with active_only=False should include it
            tools_list(mcp_server_id=None, active_only=False, json_output=True)
            all_tools = mocks.print_json.call_args[0][0]
            assert any(t["id"] == tool_id for t in all_tools), "Disabled tool should appear in full list"
            mocks.print_json.reset_mock()

            # Re-enable it
            tools_toggle(tool_id)
            mocks.print_json.reset_mock()

            # List with active_only=True should include it again
            tools_list(mcp_server_id=None, active_only=True, json_output=True)
            active_tools = mocks.print_json.call_args[0][0]
            assert any(t["id"] == tool_id for t in active_tools), "Re-enabled tool should appear in active-only list"

    def test_tools_toggle_status_detection_integration(self, mock_console, registered_mcp_server) -> None:
        """Test toggle command detects current status correctly with real server."""
        with patch_functions("cforge.commands.resources.tools", print_json=None, get_console=mock_console) as mocks:
            # Get a tool from the registered server
            tools_list(mcp_server_id=None, active_only=False, json_output=True)
            all_tools = mocks.print_json.call_args[0][0]
            tool_id = all_tools[0]["id"]
            mocks.print_json.reset_mock()

            # Get initial status (should be enabled)
            tools_get(tool_id)
            initial_status = mocks.print_json.call_args[0][0]["enabled"]
            assert initial_status is True, "Tool from MCP server should start enabled"
            mocks.print_json.reset_mock()

            # Toggle (should detect enabled and switch to disabled)
            tools_toggle(tool_id)
            mocks.print_json.reset_mock()

            # Verify status changed by getting it again
            tools_get(tool_id)
            current_status = mocks.print_json.call_args[0][0]["enabled"]
            assert current_status is False, "Tool should now be disabled"
            mocks.print_json.reset_mock()

            # Toggle again (should detect disabled and switch to enabled)
            tools_toggle(tool_id)
            mocks.print_json.reset_mock()

            # Verify status changed back
            tools_get(tool_id)
            final_status = mocks.print_json.call_args[0][0]["enabled"]
            assert final_status is True, "Tool should be enabled again"
