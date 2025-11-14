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

            # Delete it
            mcp_servers_delete(mcp_server_id)

            # Verify it's gone
            with pytest.raises(click.exceptions.Exit):
                mcp_servers_get(mcp_server_id)
