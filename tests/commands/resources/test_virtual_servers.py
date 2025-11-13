# -*- coding: utf-8 -*-
"""Location: ./tests/commands/resources/test_virtual_servers.py
Copyright 2025
SPDX-License-Identifier: Apache-2.0
Authors: Gabe Goodhart

Tests for the virtual-servers commands.
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
from cforge.commands.resources.virtual_servers import (
    virtual_servers_create,
    virtual_servers_delete,
    virtual_servers_get,
    virtual_servers_list,
    virtual_servers_prompts,
    virtual_servers_resources,
    virtual_servers_toggle,
    virtual_servers_tools,
    virtual_servers_update,
)


class TestVirtualServersCommands:
    """Tests for virtual-servers commands."""

    def test_virtual_servers_list_success(self, mock_console) -> None:
        """Test virtual-servers list command."""
        mock_servers = [{"id": 1, "name": "server1", "description": "desc1", "is_active": True}]

        with patch("cforge.commands.resources.virtual_servers.get_console", return_value=mock_console):
            with patch("cforge.commands.resources.virtual_servers.make_authenticated_request", return_value=mock_servers):
                with patch("cforge.commands.resources.virtual_servers.print_table") as mock_print:
                    virtual_servers_list(json_output=False)
                    mock_print.assert_called_once()

    def test_virtual_servers_list_json_output(self, mock_console) -> None:
        """Test virtual-servers list with JSON output."""
        with patch("cforge.commands.resources.virtual_servers.get_console", return_value=mock_console):
            with patch("cforge.commands.resources.virtual_servers.make_authenticated_request", return_value=[]):
                with patch("cforge.commands.resources.virtual_servers.print_json") as mock_print:
                    virtual_servers_list(json_output=True)
                    mock_print.assert_called_once()

    def test_virtual_servers_list_no_results(self, mock_console) -> None:
        """Test virtual-servers list with no results."""
        with patch("cforge.commands.resources.virtual_servers.get_console", return_value=mock_console):
            with patch("cforge.commands.resources.virtual_servers.make_authenticated_request", return_value=[]):
                virtual_servers_list(json_output=False)

        # Verify "No virtual servers found" message
        assert any("No virtual servers found" in str(call) for call in mock_console.print.call_args_list)

    def test_virtual_servers_list_error(self, mock_console) -> None:
        """Test virtual-servers list error handling."""
        with patch("cforge.commands.resources.virtual_servers.get_console", return_value=mock_console):
            with patch("cforge.commands.resources.virtual_servers.make_authenticated_request", side_effect=Exception("API error")):
                with pytest.raises(typer.Exit):
                    virtual_servers_list(json_output=False)

    def test_virtual_servers_get_success(self, mock_console) -> None:
        """Test virtual-servers get command."""
        mock_server = {"id": 1, "name": "test"}

        with patch("cforge.commands.resources.virtual_servers.get_console", return_value=mock_console):
            with patch("cforge.commands.resources.virtual_servers.make_authenticated_request", return_value=mock_server):
                with patch("cforge.commands.resources.virtual_servers.print_json"):
                    virtual_servers_get(server_id=1)

    def test_virtual_servers_create_from_file(self, mock_console) -> None:
        """Test virtual-servers create from file."""
        mock_result = {"id": 1, "name": "new_server"}

        with tempfile.TemporaryDirectory() as temp_dir:
            data_file = Path(temp_dir) / "server.json"
            data_file.write_text(json.dumps({"name": "new_server", "description": "desc"}))

            with patch("cforge.commands.resources.virtual_servers.get_console", return_value=mock_console):
                with patch("cforge.commands.resources.virtual_servers.make_authenticated_request", return_value=mock_result):
                    with patch("cforge.commands.resources.virtual_servers.print_json"):
                        virtual_servers_create(data_file=data_file, name=None, description=None)

    def test_virtual_servers_create_file_not_found(self, mock_console) -> None:
        """Test virtual-servers create with missing file."""
        with patch("cforge.commands.resources.virtual_servers.get_console", return_value=mock_console):
            with pytest.raises(typer.Exit):
                virtual_servers_create(data_file=Path("/nonexistent.json"), name=None, description=None)

    def test_virtual_servers_create_interactive(self, mock_console) -> None:
        """Test virtual-servers create interactive mode."""
        mock_result = {"id": 1, "name": "new_server"}

        with patch("cforge.commands.resources.virtual_servers.get_console", return_value=mock_console):
            with patch("cforge.commands.resources.virtual_servers.prompt_for_schema", return_value={"name": "test"}):
                with patch("cforge.commands.resources.virtual_servers.make_authenticated_request", return_value=mock_result):
                    with patch("cforge.commands.resources.virtual_servers.print_json"):
                        virtual_servers_create(data_file=None, name=None, description=None)

    def test_virtual_servers_create_with_options(self, mock_console) -> None:
        """Test virtual-servers create with command-line options."""
        mock_result = {"id": 1, "name": "new_server"}

        with patch("cforge.commands.resources.virtual_servers.get_console", return_value=mock_console):
            with patch("cforge.commands.resources.virtual_servers.prompt_for_schema", return_value={"name": "test", "description": "desc"}) as mock_prompt:
                with patch("cforge.commands.resources.virtual_servers.make_authenticated_request", return_value=mock_result):
                    with patch("cforge.commands.resources.virtual_servers.print_json"):
                        virtual_servers_create(data_file=None, name="test", description="desc")

                # Verify prefilled values
                call_args = mock_prompt.call_args
                assert call_args[1]["prefilled"]["name"] == "test"
                assert call_args[1]["prefilled"]["description"] == "desc"

    def test_virtual_servers_update_success(self, mock_console) -> None:
        """Test virtual-servers update command."""
        mock_result = {"id": 1, "name": "updated"}

        with tempfile.TemporaryDirectory() as temp_dir:
            data_file = Path(temp_dir) / "update.json"
            data_file.write_text(json.dumps({"description": "updated desc"}))

            with patch("cforge.commands.resources.virtual_servers.get_console", return_value=mock_console):
                with patch("cforge.commands.resources.virtual_servers.make_authenticated_request", return_value=mock_result):
                    with patch("cforge.commands.resources.virtual_servers.print_json"):
                        virtual_servers_update(server_id=1, data_file=data_file)

    def test_virtual_servers_update_file_not_found(self, mock_console) -> None:
        """Test virtual-servers update with missing file."""
        with patch("cforge.commands.resources.virtual_servers.get_console", return_value=mock_console):
            with pytest.raises(typer.Exit):
                virtual_servers_update(server_id=1, data_file=Path("/nonexistent.json"))

    def test_virtual_servers_delete_with_confirmation(self, mock_console) -> None:
        """Test virtual-servers delete with confirmation."""
        with patch("cforge.commands.resources.virtual_servers.get_console", return_value=mock_console):
            with patch("cforge.commands.resources.virtual_servers.make_authenticated_request"):
                with patch("cforge.commands.resources.virtual_servers.typer.confirm", return_value=True):
                    virtual_servers_delete(server_id=1, confirm=False)

    def test_virtual_servers_delete_cancelled(self, mock_console) -> None:
        """Test virtual-servers delete cancelled."""
        with patch("cforge.commands.resources.virtual_servers.get_console", return_value=mock_console):
            with patch("cforge.commands.resources.virtual_servers.typer.confirm", return_value=False):
                with pytest.raises(typer.Exit) as exc_info:
                    virtual_servers_delete(server_id=1, confirm=False)

                # Note: Exit(0) gets caught by exception handler and converted to Exit(1)
                assert exc_info.value.exit_code == 1

    def test_virtual_servers_delete_with_yes_flag(self, mock_console) -> None:
        """Test virtual-servers delete with --yes flag."""
        with patch("cforge.commands.resources.virtual_servers.get_console", return_value=mock_console):
            with patch("cforge.commands.resources.virtual_servers.make_authenticated_request"):
                virtual_servers_delete(server_id=1, confirm=True)

        # Should not prompt
        assert not any("confirm" in str(call) for call in mock_console.print.call_args_list)

    def test_virtual_servers_toggle_success(self, mock_console) -> None:
        """Test virtual-servers toggle command."""
        mock_result = {"id": 1, "is_active": False}

        with patch("cforge.commands.resources.virtual_servers.get_console", return_value=mock_console):
            with patch("cforge.commands.resources.virtual_servers.make_authenticated_request", return_value=mock_result):
                with patch("cforge.commands.resources.virtual_servers.print_json"):
                    virtual_servers_toggle(server_id=1)

    def test_virtual_servers_tools_success(self, mock_console) -> None:
        """Test virtual-servers tools command."""
        mock_tools = [{"id": 1, "name": "tool1", "description": "desc1"}]

        with patch("cforge.commands.resources.virtual_servers.get_console", return_value=mock_console):
            with patch("cforge.commands.resources.virtual_servers.make_authenticated_request", return_value=mock_tools):
                with patch("cforge.commands.resources.virtual_servers.print_table"):
                    virtual_servers_tools(server_id=1, json_output=False)

    def test_virtual_servers_tools_json_output(self, mock_console) -> None:
        """Test virtual-servers tools with JSON output."""
        mock_tools = [{"id": 1, "name": "tool1"}]

        with patch("cforge.commands.resources.virtual_servers.get_console", return_value=mock_console):
            with patch("cforge.commands.resources.virtual_servers.make_authenticated_request", return_value=mock_tools):
                with patch("cforge.commands.resources.virtual_servers.print_json"):
                    virtual_servers_tools(server_id=1, json_output=True)

    def test_virtual_servers_tools_no_results(self, mock_console) -> None:
        """Test virtual-servers tools with no results."""
        with patch("cforge.commands.resources.virtual_servers.get_console", return_value=mock_console):
            with patch("cforge.commands.resources.virtual_servers.make_authenticated_request", return_value=[]):
                virtual_servers_tools(server_id=1, json_output=False)

        # Verify "No tools found" message
        assert any("No tools found" in str(call) for call in mock_console.print.call_args_list)

    def test_virtual_servers_resources_success(self, mock_console) -> None:
        """Test virtual-servers resources command."""
        mock_resources = [{"id": 1, "name": "resource1", "uri": "file:///path", "description": "desc1"}]

        with patch("cforge.commands.resources.virtual_servers.get_console", return_value=mock_console):
            with patch("cforge.commands.resources.virtual_servers.make_authenticated_request", return_value=mock_resources):
                with patch("cforge.commands.resources.virtual_servers.print_table"):
                    virtual_servers_resources(server_id=1, json_output=False)

    def test_virtual_servers_resources_json_output(self, mock_console) -> None:
        """Test virtual-servers resources with JSON output."""
        mock_resources = [{"id": 1, "name": "resource1"}]

        with patch("cforge.commands.resources.virtual_servers.get_console", return_value=mock_console):
            with patch("cforge.commands.resources.virtual_servers.make_authenticated_request", return_value=mock_resources):
                with patch("cforge.commands.resources.virtual_servers.print_json"):
                    virtual_servers_resources(server_id=1, json_output=True)

    def test_virtual_servers_resources_no_results(self, mock_console) -> None:
        """Test virtual-servers resources with no results."""
        with patch("cforge.commands.resources.virtual_servers.get_console", return_value=mock_console):
            with patch("cforge.commands.resources.virtual_servers.make_authenticated_request", return_value=[]):
                virtual_servers_resources(server_id=1, json_output=False)

        # Verify "No resources found" message
        assert any("No resources found" in str(call) for call in mock_console.print.call_args_list)

    def test_virtual_servers_prompts_success(self, mock_console) -> None:
        """Test virtual-servers prompts command."""
        mock_prompts = [{"id": 1, "name": "prompt1", "description": "desc1"}]

        with patch("cforge.commands.resources.virtual_servers.get_console", return_value=mock_console):
            with patch("cforge.commands.resources.virtual_servers.make_authenticated_request", return_value=mock_prompts):
                with patch("cforge.commands.resources.virtual_servers.print_table"):
                    virtual_servers_prompts(server_id=1, json_output=False)

    def test_virtual_servers_prompts_json_output(self, mock_console) -> None:
        """Test virtual-servers prompts with JSON output."""
        mock_prompts = [{"id": 1, "name": "prompt1"}]

        with patch("cforge.commands.resources.virtual_servers.get_console", return_value=mock_console):
            with patch("cforge.commands.resources.virtual_servers.make_authenticated_request", return_value=mock_prompts):
                with patch("cforge.commands.resources.virtual_servers.print_json"):
                    virtual_servers_prompts(server_id=1, json_output=True)

    def test_virtual_servers_prompts_no_results(self, mock_console) -> None:
        """Test virtual-servers prompts with no results."""
        with patch("cforge.commands.resources.virtual_servers.get_console", return_value=mock_console):
            with patch("cforge.commands.resources.virtual_servers.make_authenticated_request", return_value=[]):
                virtual_servers_prompts(server_id=1, json_output=False)

        # Verify "No prompts found" message
        assert any("No prompts found" in str(call) for call in mock_console.print.call_args_list)

    def test_virtual_servers_get_error(self, mock_console) -> None:
        """Test virtual-servers get error handling."""
        with patch("cforge.commands.resources.virtual_servers.get_console", return_value=mock_console):
            with patch("cforge.commands.resources.virtual_servers.make_authenticated_request", side_effect=Exception("API error")):
                with pytest.raises(typer.Exit):
                    virtual_servers_get(server_id=1)

    def test_virtual_servers_toggle_error(self, mock_console) -> None:
        """Test virtual-servers toggle error handling."""
        with patch("cforge.commands.resources.virtual_servers.get_console", return_value=mock_console):
            with patch("cforge.commands.resources.virtual_servers.make_authenticated_request", side_effect=Exception("API error")):
                with pytest.raises(typer.Exit):
                    virtual_servers_toggle(server_id=1)

    def test_virtual_servers_tools_error(self, mock_console) -> None:
        """Test virtual-servers tools error handling."""
        with patch("cforge.commands.resources.virtual_servers.get_console", return_value=mock_console):
            with patch("cforge.commands.resources.virtual_servers.make_authenticated_request", side_effect=Exception("API error")):
                with pytest.raises(typer.Exit):
                    virtual_servers_tools(server_id=1, json_output=False)

    def test_virtual_servers_resources_error(self, mock_console) -> None:
        """Test virtual-servers resources error handling."""
        with patch("cforge.commands.resources.virtual_servers.get_console", return_value=mock_console):
            with patch("cforge.commands.resources.virtual_servers.make_authenticated_request", side_effect=Exception("API error")):
                with pytest.raises(typer.Exit):
                    virtual_servers_resources(server_id=1, json_output=False)

    def test_virtual_servers_prompts_error(self, mock_console) -> None:
        """Test virtual-servers prompts error handling."""
        with patch("cforge.commands.resources.virtual_servers.get_console", return_value=mock_console):
            with patch("cforge.commands.resources.virtual_servers.make_authenticated_request", side_effect=Exception("API error")):
                with pytest.raises(typer.Exit):
                    virtual_servers_prompts(server_id=1, json_output=False)
