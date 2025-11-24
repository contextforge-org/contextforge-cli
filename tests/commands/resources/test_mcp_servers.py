# -*- coding: utf-8 -*-
"""Location: ./tests/commands/resources/test_mcp_servers.py
Copyright 2025
SPDX-License-Identifier: Apache-2.0
Authors: Gabe Goodhart

Tests for the mcp-servers commands.
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
from cforge.commands.resources.mcp_servers import (
    mcp_servers_create,
    mcp_servers_delete,
    mcp_servers_get,
    mcp_servers_list,
    mcp_servers_toggle,
    mcp_servers_update,
)
from tests.conftest import patch_functions


class TestMcpServersCommands:
    """Tests for mcp-servers commands."""

    def test_mcp_servers_list_success(self, mock_console) -> None:
        """Test mcp-servers list command."""
        mock_servers = [{"id": "test-server-1234", "name": "server1", "url": "http://example.com", "description": "desc1", "enabled": True}]

        with patch_functions("cforge.commands.resources.mcp_servers", make_authenticated_request=mock_servers, print_table=None) as mocks:
            mcp_servers_list(json_output=False)
            mocks.print_table.assert_called_once()

    def test_mcp_servers_list_json_output(self, mock_console) -> None:
        """Test mcp-servers list with JSON output."""
        with patch_functions("cforge.commands.resources.mcp_servers", make_authenticated_request=[], print_json=None) as mocks:
            mcp_servers_list(json_output=True)
            mocks.print_json.assert_called_once()

    def test_mcp_servers_list_no_results(self, mock_console) -> None:
        """Test mcp-servers list with no results."""
        with patch_functions("cforge.commands.resources.mcp_servers", make_authenticated_request=[]):
            mcp_servers_list(json_output=False)

        # Verify "No MCP servers found" message
        assert any("No MCP servers found" in str(call) for call in mock_console.print.call_args_list)

    def test_mcp_servers_list_error(self, mock_console) -> None:
        """Test mcp-servers list error handling."""
        with patch_functions("cforge.commands.resources.mcp_servers", make_authenticated_request={"side_effect": Exception("API error")}):
            with pytest.raises(typer.Exit):
                mcp_servers_list(json_output=False)

    def test_mcp_servers_list_with_active_only_true(self, mock_console) -> None:
        """Test mcp-servers list with --active-only flag set to True."""
        mock_servers = [{"id": "test-server-1234", "name": "server1", "enabled": True}]

        with patch_functions("cforge.commands.resources.mcp_servers", make_authenticated_request=mock_servers, print_table=None) as mocks:
            mcp_servers_list(active_only=True, json_output=False)

            # Verify that include_inactive=False was passed to API
            call_args = mocks.make_authenticated_request.call_args
            assert call_args[1]["params"]["include_inactive"] is False

    def test_mcp_servers_list_with_active_only_false(self, mock_console) -> None:
        """Test mcp-servers list with --active-only flag set to False (default)."""
        mock_servers = [{"id": "test-server-1234", "name": "server1", "enabled": True}, {"id": "test-server-5678", "name": "server2", "enabled": False}]

        with patch_functions("cforge.commands.resources.mcp_servers", make_authenticated_request=mock_servers, print_table=None) as mocks:
            mcp_servers_list(active_only=False, json_output=False)

            # Verify that include_inactive=True was passed to API
            call_args = mocks.make_authenticated_request.call_args
            assert call_args[1]["params"]["include_inactive"] is True

    def test_mcp_servers_list_default_shows_all(self, mock_console) -> None:
        """Test mcp-servers list default behavior shows all servers."""
        mock_servers = [{"id": "test-server-1234", "name": "server1", "enabled": True}, {"id": "test-server-5678", "name": "server2", "enabled": False}]

        with patch_functions("cforge.commands.resources.mcp_servers", make_authenticated_request=mock_servers, print_table=None, get_console=mock_console) as mocks:
            # Call with explicit active_only=False (default value)
            mcp_servers_list(active_only=False, json_output=False)

            # Verify that include_inactive=True was passed to API (default behavior)
            call_args = mocks.make_authenticated_request.call_args
            assert call_args[1]["params"]["include_inactive"] is True

    def test_mcp_servers_get_success(self, mock_console) -> None:
        """Test mcp-servers get command."""
        mock_server = {"id": "test-server-1234", "name": "test"}

        with patch_functions("cforge.commands.resources.mcp_servers", make_authenticated_request=mock_server, print_json=None):
            mcp_servers_get(mcp_server_id="test-server-123")

    def test_mcp_servers_create_from_file(self, mock_console) -> None:
        """Test mcp-servers create from file."""
        mock_result = {"id": "test-server-1234", "name": "new_server"}

        with tempfile.TemporaryDirectory() as temp_dir:
            data_file = Path(temp_dir) / "server.json"
            data_file.write_text(json.dumps({"name": "new_server", "url": "http://example.com", "description": "desc"}))

            with patch_functions("cforge.commands.resources.mcp_servers", make_authenticated_request=mock_result, print_json=None):
                mcp_servers_create(data_file=data_file, name=None, url=None, description=None)

    def test_mcp_servers_create_file_not_found(self, mock_console) -> None:
        """Test mcp-servers create with missing file."""
        with patch_functions("cforge.commands.resources.mcp_servers", get_console=mock_console):
            with pytest.raises(typer.Exit):
                mcp_servers_create(data_file=Path("/nonexistent.json"), name=None, url=None, description=None)

    def test_mcp_servers_create_interactive(self, mock_console) -> None:
        """Test mcp-servers create interactive mode."""
        mock_result = {"id": "test-server-1234", "name": "new_server"}

        with patch_functions(
            "cforge.commands.resources.mcp_servers",
            get_console=mock_console,
            prompt_for_schema={"name": "test", "url": "http://example.com"},
            make_authenticated_request=mock_result,
            print_json=None,
        ):
            mcp_servers_create(data_file=None, name=None, url=None, description=None)

    def test_mcp_servers_create_with_options(self, mock_console) -> None:
        """Test mcp-servers create with command-line options."""
        mock_result = {"id": "test-server-1234", "name": "new_server"}

        with patch_functions(
            "cforge.commands.resources.mcp_servers",
            get_console=mock_console,
            prompt_for_schema={"name": "test", "url": "http://example.com", "description": "desc"},
            make_authenticated_request=mock_result,
            print_json=None,
        ) as mocks:
            mcp_servers_create(data_file=None, name="test", url="http://example.com", description="desc")

            # Verify prefilled values
            call_args = mocks.prompt_for_schema.call_args
            assert call_args[1]["prefilled"]["name"] == "test"
            assert call_args[1]["prefilled"]["url"] == "http://example.com"
            assert call_args[1]["prefilled"]["description"] == "desc"

    def test_mcp_servers_update_success(self, mock_console) -> None:
        """Test mcp-servers update command."""
        mock_result = {"id": "test-server-1234", "name": "updated"}

        with tempfile.TemporaryDirectory() as temp_dir:
            data_file = Path(temp_dir) / "update.json"
            data_file.write_text(json.dumps({"description": "updated desc"}))

            with patch_functions("cforge.commands.resources.mcp_servers", make_authenticated_request=mock_result, print_json=None):
                mcp_servers_update(mcp_server_id="test-server-123", data_file=data_file)

    def test_mcp_servers_update_file_not_found(self, mock_console) -> None:
        """Test mcp-servers update with missing file."""
        with patch_functions("cforge.commands.resources.mcp_servers", get_console=mock_console):
            with pytest.raises(typer.Exit):
                mcp_servers_update(mcp_server_id="test-server-123", data_file=Path("/nonexistent.json"))

    def test_mcp_servers_update_prompt_for_schema(self, mock_console) -> None:
        """Test mcp-servers update with interactive schema prompt."""
        with patch_functions("cforge.commands.resources.mcp_servers", make_authenticated_request=None, print_json=None, get_console=mock_console) as mocks:
            update_body = {"name": "updated"}
            with patch("cforge.commands.resources.mcp_servers.prompt_for_schema", return_value=update_body):
                mcp_servers_update(mcp_server_id="test-server-123", data_file=None)
                mocks.make_authenticated_request.assert_called_once_with("PUT", "/gateways/test-server-123", json_data=update_body)

    def test_mcp_servers_delete_with_confirmation(self, mock_console) -> None:
        """Test mcp-servers delete with confirmation."""
        with patch_functions("cforge.commands.resources.mcp_servers", make_authenticated_request=None):
            with patch("cforge.commands.resources.mcp_servers.typer.confirm", return_value=True):
                mcp_servers_delete(mcp_server_id="test-server-123", confirm=False)

    def test_mcp_servers_delete_cancelled(self, mock_console) -> None:
        """Test mcp-servers delete cancelled."""
        with patch_functions("cforge.commands.resources.mcp_servers", get_console=mock_console):
            with patch("cforge.commands.resources.mcp_servers.typer.confirm", return_value=False):
                with pytest.raises(typer.Exit) as exc_info:
                    mcp_servers_delete(mcp_server_id="test-server-123", confirm=False)

                # Note: Exit(0) gets caught by exception handler and converted to Exit(1)
                assert exc_info.value.exit_code == 1

    def test_mcp_servers_delete_with_yes_flag(self, mock_console) -> None:
        """Test mcp-servers delete with --yes flag."""
        with patch_functions("cforge.commands.resources.mcp_servers", make_authenticated_request=None):
            mcp_servers_delete(mcp_server_id="test-server-123", confirm=True)

        # Should not prompt
        assert not any("confirm" in str(call) for call in mock_console.print.call_args_list)

    def test_mcp_servers_get_error(self, mock_console) -> None:
        """Test mcp-servers get error handling."""
        with patch_functions("cforge.commands.resources.mcp_servers", make_authenticated_request={"side_effect": Exception("API error")}):
            with pytest.raises(typer.Exit):
                mcp_servers_get(mcp_server_id="test-server-123")

    def test_mcp_servers_toggle_from_disabled_to_enabled(self, mock_console) -> None:
        """Test toggling an MCP server from disabled to enabled."""
        with patch_functions(
            "cforge.commands.resources.mcp_servers",
            get_console=mock_console,
            make_authenticated_request={
                "side_effect": [
                    {"id": "test-server-123", "name": "test", "enabled": False},  # GET current status
                    {"gateway": {"id": "test-server-123", "name": "test", "enabled": True}},  # POST toggle result
                ]
            },
            print_json=None,
        ) as mocks:

            mcp_servers_toggle(mcp_server_id="test-server-123")

            # Verify two calls were made
            assert mocks.make_authenticated_request.call_count == 2

            # Verify first call was GET to check current status
            get_call = mocks.make_authenticated_request.call_args_list[0]
            assert get_call[0][0] == "GET"
            assert get_call[0][1] == "/gateways/test-server-123"

            # Verify second call was POST with activate=True
            post_call = mocks.make_authenticated_request.call_args_list[1]
            assert post_call[0][0] == "POST"
            assert post_call[0][1] == "/gateways/test-server-123/toggle"
            assert post_call[1]["params"]["activate"] is True

    def test_mcp_servers_toggle_from_enabled_to_disabled(self, mock_console) -> None:
        """Test toggling an MCP server from enabled to disabled."""
        with patch_functions(
            "cforge.commands.resources.mcp_servers",
            get_console=mock_console,
            make_authenticated_request={
                "side_effect": [
                    {"id": "test-server-123", "name": "test", "enabled": True},  # GET current status
                    {"gateway": {"id": "test-server-123", "name": "test", "enabled": False}},  # POST toggle result
                ]
            },
            print_json=None,
        ) as mocks:

            mcp_servers_toggle(mcp_server_id="test-server-123")

            # Verify two calls were made
            assert mocks.make_authenticated_request.call_count == 2

            # Verify first call was GET to check current status
            get_call = mocks.make_authenticated_request.call_args_list[0]
            assert get_call[0][0] == "GET"
            assert get_call[0][1] == "/gateways/test-server-123"

            # Verify second call was POST with activate=False
            post_call = mocks.make_authenticated_request.call_args_list[1]
            assert post_call[0][0] == "POST"
            assert post_call[0][1] == "/gateways/test-server-123/toggle"
            assert post_call[1]["params"]["activate"] is False

    def test_mcp_servers_toggle_detects_current_status(self, mock_console) -> None:
        """Test that toggle command detects current status before toggling."""
        with patch_functions(
            "cforge.commands.resources.mcp_servers",
            get_console=mock_console,
            make_authenticated_request={"side_effect": [{"id": "test-server-123", "name": "test", "enabled": True}, {"gateway": {"id": "test-server-123", "name": "test", "enabled": False}}]},
            print_json=None,
        ) as mocks:

            mcp_servers_toggle(mcp_server_id="test-server-123")

            # Verify GET was called first to detect current status
            calls = mocks.make_authenticated_request.call_args_list
            assert len(calls) == 2
            assert calls[0][0][0] == "GET"  # First call is GET
            assert calls[1][0][0] == "POST"  # Second call is POST

    def test_mcp_servers_toggle_error(self, mock_console) -> None:
        """Test mcp-servers toggle error handling."""
        with patch_functions("cforge.commands.resources.mcp_servers", make_authenticated_request={"side_effect": Exception("API error")}):
            with pytest.raises(typer.Exit):
                mcp_servers_toggle(mcp_server_id="test-server-123")


class TestMcpServersCommandsIntegration:
    """Test mcp-servers commands with a real gateway test client."""

    def test_mcp_servers_lifecycle(self, mock_console, authorized_mock_client, mock_mcp_server) -> None:
        """Test the full CRUD lifecycle of an mcp-server.

        NOTE: This test mutates the state of the session gateway!
        """
        with patch_functions("cforge.commands.resources.mcp_servers", print_json=None) as mocks:

            # Create a new MCP Server in the gateway
            with patch("cforge.commands.resources.mcp_servers.prompt_for_schema", return_value=mock_mcp_server):
                mcp_servers_create(None)
            assert len(mocks.print_json.call_args_list) == 1
            mcp_server_body = mocks.print_json.call_args[0][0]
            mcp_server_id = mcp_server_body["id"]
            assert mcp_server_body["enabled"]
            mocks.print_json.reset_mock()

            # Retrieve it and verify
            mcp_servers_get(mcp_server_id)
            assert len(mocks.print_json.call_args_list) == 1
            mcp_server_body = mocks.print_json.call_args[0][0]
            assert mcp_server_body["id"] == mcp_server_id
            mocks.print_json.reset_mock()

            # Update it
            mcp_server_body["description"] = "A new description"
            with tempfile.NamedTemporaryFile("w") as data_file:
                data_file.write(json.dumps(mcp_server_body))
                data_file.flush()
                mcp_servers_update(mcp_server_id, Path(data_file.name))
            assert len(mocks.print_json.call_args_list) == 1
            mcp_server_body = mocks.print_json.call_args[0][0]
            assert mcp_server_body["description"] == "A new description"
            mocks.print_json.reset_mock()

            # Deactivate it
            mcp_servers_toggle(mcp_server_id)
            assert len(mocks.print_json.call_args_list) == 1
            mcp_server_body = mocks.print_json.call_args[0][0]["gateway"]
            assert not mcp_server_body["enabled"]
            mocks.print_json.reset_mock()

            # Re-activate it
            mcp_servers_toggle(mcp_server_id)
            assert len(mocks.print_json.call_args_list) == 1
            mcp_server_body = mocks.print_json.call_args[0][0]["gateway"]
            assert mcp_server_body["enabled"]
            mocks.print_json.reset_mock()

            # Delete it
            mcp_servers_delete(mcp_server_id)

            # Verify it's gone
            with pytest.raises(click.exceptions.Exit):
                mcp_servers_get(mcp_server_id)

    def test_mcp_servers_list_active_only_integration(self, mock_console, authorized_mock_client, mock_mcp_server) -> None:
        """Test --active-only flag filters correctly with real server."""
        with patch_functions("cforge.commands.resources.mcp_servers", print_json=None) as mocks:
            # Create a new MCP Server
            with patch("cforge.commands.resources.mcp_servers.prompt_for_schema", return_value=mock_mcp_server):
                mcp_servers_create(None)
            mcp_server_id = mocks.print_json.call_args[0][0]["id"]
            mocks.print_json.reset_mock()

            # List with active_only=True should include it (starts enabled)
            mcp_servers_list(active_only=True, json_output=True)
            active_servers = mocks.print_json.call_args[0][0]
            assert any(s["id"] == mcp_server_id for s in active_servers), "Enabled server should appear in active-only list"
            mocks.print_json.reset_mock()

            # Disable it
            mcp_servers_toggle(mcp_server_id)
            mocks.print_json.reset_mock()

            # List with active_only=True should NOT include it
            mcp_servers_list(active_only=True, json_output=True)
            active_servers = mocks.print_json.call_args[0][0]
            assert not any(s["id"] == mcp_server_id for s in active_servers), "Disabled server should NOT appear in active-only list"
            mocks.print_json.reset_mock()

            # List with active_only=False should include it
            mcp_servers_list(active_only=False, json_output=True)
            all_servers = mocks.print_json.call_args[0][0]
            assert any(s["id"] == mcp_server_id for s in all_servers), "Disabled server should appear in full list"
            mocks.print_json.reset_mock()

            # Re-enable it
            mcp_servers_toggle(mcp_server_id)
            mocks.print_json.reset_mock()

            # List with active_only=True should include it again
            mcp_servers_list(active_only=True, json_output=True)
            active_servers = mocks.print_json.call_args[0][0]
            assert any(s["id"] == mcp_server_id for s in active_servers), "Re-enabled server should appear in active-only list"

            # Cleanup
            mcp_servers_delete(mcp_server_id)

    def test_mcp_servers_toggle_status_detection_integration(self, mock_console, authorized_mock_client, mock_mcp_server) -> None:
        """Test toggle command detects current status correctly with real server."""
        with patch_functions("cforge.commands.resources.mcp_servers", print_json=None, get_console=mock_console) as mocks:
            # Create a new MCP Server (starts enabled)
            with patch("cforge.commands.resources.mcp_servers.prompt_for_schema", return_value=mock_mcp_server):
                mcp_servers_create(None)
            mcp_server_id = mocks.print_json.call_args[0][0]["id"]
            mocks.print_json.reset_mock()

            # Get initial status (should be enabled)
            mcp_servers_get(mcp_server_id)
            initial_status = mocks.print_json.call_args[0][0]["enabled"]
            assert initial_status is True, "New server should start enabled"
            mocks.print_json.reset_mock()

            # Toggle (should detect enabled and switch to disabled)
            mcp_servers_toggle(mcp_server_id)
            mocks.print_json.reset_mock()

            # Verify status changed by getting it again
            mcp_servers_get(mcp_server_id)
            current_status = mocks.print_json.call_args[0][0]["enabled"]
            assert current_status is False, "Server should now be disabled"
            mocks.print_json.reset_mock()

            # Toggle again (should detect disabled and switch to enabled)
            mcp_servers_toggle(mcp_server_id)
            mocks.print_json.reset_mock()

            # Verify status changed back
            mcp_servers_get(mcp_server_id)
            final_status = mocks.print_json.call_args[0][0]["enabled"]
            assert final_status is True, "Server should be enabled again"

            # Cleanup
            mcp_servers_delete(mcp_server_id)
