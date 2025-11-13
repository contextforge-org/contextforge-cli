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


class TestMcpServersCommands:
    """Tests for mcp-servers commands."""

    def test_mcp_servers_list_success(self, mock_console) -> None:
        """Test mcp-servers list command."""
        mock_servers = [{"id": 1, "name": "server1", "url": "http://example.com", "description": "desc1", "is_active": True}]

        with patch("cforge.commands.resources.mcp_servers.get_console", return_value=mock_console):
            with patch("cforge.commands.resources.mcp_servers.make_authenticated_request", return_value=mock_servers):
                with patch("cforge.commands.resources.mcp_servers.print_table") as mock_print:
                    mcp_servers_list(json_output=False)
                    mock_print.assert_called_once()

    def test_mcp_servers_list_json_output(self, mock_console) -> None:
        """Test mcp-servers list with JSON output."""
        with patch("cforge.commands.resources.mcp_servers.get_console", return_value=mock_console):
            with patch("cforge.commands.resources.mcp_servers.make_authenticated_request", return_value=[]):
                with patch("cforge.commands.resources.mcp_servers.print_json") as mock_print:
                    mcp_servers_list(json_output=True)
                    mock_print.assert_called_once()

    def test_mcp_servers_list_no_results(self, mock_console) -> None:
        """Test mcp-servers list with no results."""
        with patch("cforge.commands.resources.mcp_servers.get_console", return_value=mock_console):
            with patch("cforge.commands.resources.mcp_servers.make_authenticated_request", return_value=[]):
                mcp_servers_list(json_output=False)

        # Verify "No MCP servers found" message
        assert any("No MCP servers found" in str(call) for call in mock_console.print.call_args_list)

    def test_mcp_servers_list_error(self, mock_console) -> None:
        """Test mcp-servers list error handling."""
        with patch("cforge.commands.resources.mcp_servers.get_console", return_value=mock_console):
            with patch("cforge.commands.resources.mcp_servers.make_authenticated_request", side_effect=Exception("API error")):
                with pytest.raises(typer.Exit):
                    mcp_servers_list(json_output=False)

    def test_mcp_servers_get_success(self, mock_console) -> None:
        """Test mcp-servers get command."""
        mock_server = {"id": 1, "name": "test"}

        with patch("cforge.commands.resources.mcp_servers.get_console", return_value=mock_console):
            with patch("cforge.commands.resources.mcp_servers.make_authenticated_request", return_value=mock_server):
                with patch("cforge.commands.resources.mcp_servers.print_json"):
                    mcp_servers_get(gateway_id=1)

    def test_mcp_servers_create_from_file(self, mock_console) -> None:
        """Test mcp-servers create from file."""
        mock_result = {"id": 1, "name": "new_server"}

        with tempfile.TemporaryDirectory() as temp_dir:
            data_file = Path(temp_dir) / "server.json"
            data_file.write_text(json.dumps({"name": "new_server", "url": "http://example.com", "description": "desc"}))

            with patch("cforge.commands.resources.mcp_servers.get_console", return_value=mock_console):
                with patch("cforge.commands.resources.mcp_servers.make_authenticated_request", return_value=mock_result):
                    with patch("cforge.commands.resources.mcp_servers.print_json"):
                        mcp_servers_create(data_file=data_file, name=None, url=None, description=None)

    def test_mcp_servers_create_file_not_found(self, mock_console) -> None:
        """Test mcp-servers create with missing file."""
        with patch("cforge.commands.resources.mcp_servers.get_console", return_value=mock_console):
            with pytest.raises(typer.Exit):
                mcp_servers_create(data_file=Path("/nonexistent.json"), name=None, url=None, description=None)

    def test_mcp_servers_create_interactive(self, mock_console) -> None:
        """Test mcp-servers create interactive mode."""
        mock_result = {"id": 1, "name": "new_server"}

        with patch("cforge.commands.resources.mcp_servers.get_console", return_value=mock_console):
            with patch("cforge.commands.resources.mcp_servers.prompt_for_schema", return_value={"name": "test", "url": "http://example.com"}):
                with patch("cforge.commands.resources.mcp_servers.make_authenticated_request", return_value=mock_result):
                    with patch("cforge.commands.resources.mcp_servers.print_json"):
                        mcp_servers_create(data_file=None, name=None, url=None, description=None)

    def test_mcp_servers_create_with_options(self, mock_console) -> None:
        """Test mcp-servers create with command-line options."""
        mock_result = {"id": 1, "name": "new_server"}

        with patch("cforge.commands.resources.mcp_servers.get_console", return_value=mock_console):
            with patch("cforge.commands.resources.mcp_servers.prompt_for_schema", return_value={"name": "test", "url": "http://example.com", "description": "desc"}) as mock_prompt:
                with patch("cforge.commands.resources.mcp_servers.make_authenticated_request", return_value=mock_result):
                    with patch("cforge.commands.resources.mcp_servers.print_json"):
                        mcp_servers_create(data_file=None, name="test", url="http://example.com", description="desc")

                # Verify prefilled values
                call_args = mock_prompt.call_args
                assert call_args[1]["prefilled"]["name"] == "test"
                assert call_args[1]["prefilled"]["url"] == "http://example.com"
                assert call_args[1]["prefilled"]["description"] == "desc"

    def test_mcp_servers_update_success(self, mock_console) -> None:
        """Test mcp-servers update command."""
        mock_result = {"id": 1, "name": "updated"}

        with tempfile.TemporaryDirectory() as temp_dir:
            data_file = Path(temp_dir) / "update.json"
            data_file.write_text(json.dumps({"description": "updated desc"}))

            with patch("cforge.commands.resources.mcp_servers.get_console", return_value=mock_console):
                with patch("cforge.commands.resources.mcp_servers.make_authenticated_request", return_value=mock_result):
                    with patch("cforge.commands.resources.mcp_servers.print_json"):
                        mcp_servers_update(gateway_id=1, data_file=data_file)

    def test_mcp_servers_update_file_not_found(self, mock_console) -> None:
        """Test mcp-servers update with missing file."""
        with patch("cforge.commands.resources.mcp_servers.get_console", return_value=mock_console):
            with pytest.raises(typer.Exit):
                mcp_servers_update(gateway_id=1, data_file=Path("/nonexistent.json"))

    def test_mcp_servers_delete_with_confirmation(self, mock_console) -> None:
        """Test mcp-servers delete with confirmation."""
        with patch("cforge.commands.resources.mcp_servers.get_console", return_value=mock_console):
            with patch("cforge.commands.resources.mcp_servers.make_authenticated_request"):
                with patch("cforge.commands.resources.mcp_servers.typer.confirm", return_value=True):
                    mcp_servers_delete(gateway_id=1, confirm=False)

    def test_mcp_servers_delete_cancelled(self, mock_console) -> None:
        """Test mcp-servers delete cancelled."""
        with patch("cforge.commands.resources.mcp_servers.get_console", return_value=mock_console):
            with patch("cforge.commands.resources.mcp_servers.typer.confirm", return_value=False):
                with pytest.raises(typer.Exit) as exc_info:
                    mcp_servers_delete(gateway_id=1, confirm=False)

                # Note: Exit(0) gets caught by exception handler and converted to Exit(1)
                assert exc_info.value.exit_code == 1

    def test_mcp_servers_delete_with_yes_flag(self, mock_console) -> None:
        """Test mcp-servers delete with --yes flag."""
        with patch("cforge.commands.resources.mcp_servers.get_console", return_value=mock_console):
            with patch("cforge.commands.resources.mcp_servers.make_authenticated_request"):
                mcp_servers_delete(gateway_id=1, confirm=True)

        # Should not prompt
        assert not any("confirm" in str(call) for call in mock_console.print.call_args_list)

    def test_mcp_servers_toggle_success(self, mock_console) -> None:
        """Test mcp-servers toggle command."""
        mock_result = {"id": 1, "is_active": False}

        with patch("cforge.commands.resources.mcp_servers.get_console", return_value=mock_console):
            with patch("cforge.commands.resources.mcp_servers.make_authenticated_request", return_value=mock_result):
                with patch("cforge.commands.resources.mcp_servers.print_json"):
                    mcp_servers_toggle(gateway_id=1)

    def test_mcp_servers_get_error(self, mock_console) -> None:
        """Test mcp-servers get error handling."""
        with patch("cforge.commands.resources.mcp_servers.get_console", return_value=mock_console):
            with patch("cforge.commands.resources.mcp_servers.make_authenticated_request", side_effect=Exception("API error")):
                with pytest.raises(typer.Exit):
                    mcp_servers_get(gateway_id=1)

    def test_mcp_servers_toggle_error(self, mock_console) -> None:
        """Test mcp-servers toggle error handling."""
        with patch("cforge.commands.resources.mcp_servers.get_console", return_value=mock_console):
            with patch("cforge.commands.resources.mcp_servers.make_authenticated_request", side_effect=Exception("API error")):
                with pytest.raises(typer.Exit):
                    mcp_servers_toggle(gateway_id=1)
