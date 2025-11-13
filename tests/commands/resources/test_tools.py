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


class TestToolsCommands:
    """Tests for tools commands."""

    def test_tools_list_success(self, mock_console) -> None:
        """Test tools list command."""
        mock_tools = [{"id": 1, "name": "tool1", "description": "desc1", "gateway_id": 1, "is_active": True}]

        with patch("cforge.commands.resources.tools.get_console", return_value=mock_console):
            with patch("cforge.commands.resources.tools.make_authenticated_request", return_value=mock_tools):
                with patch("cforge.commands.resources.tools.print_table") as mock_print:
                    tools_list(gateway_id=None, active_only=False, json_output=False)
                    mock_print.assert_called_once()

    def test_tools_list_json_output(self, mock_console) -> None:
        """Test tools list with JSON output."""
        with patch("cforge.commands.resources.tools.get_console", return_value=mock_console):
            with patch("cforge.commands.resources.tools.make_authenticated_request", return_value=[]):
                with patch("cforge.commands.resources.tools.print_json") as mock_print:
                    tools_list(gateway_id=None, active_only=False, json_output=True)
                    mock_print.assert_called_once()

    def test_tools_list_with_filters(self, mock_console) -> None:
        """Test tools list with filters."""
        with patch("cforge.commands.resources.tools.get_console", return_value=mock_console):
            with patch("cforge.commands.resources.tools.make_authenticated_request", return_value=[]) as mock_req:
                with patch("cforge.commands.resources.tools.print_table"):
                    tools_list(gateway_id=5, active_only=True, json_output=False)

                # Verify params
                call_args = mock_req.call_args
                assert call_args[1]["params"]["gateway_id"] == 5
                assert call_args[1]["params"]["active"] == "true"

    def test_tools_list_no_results(self, mock_console) -> None:
        """Test tools list with no results."""
        with patch("cforge.commands.resources.tools.get_console", return_value=mock_console):
            with patch("cforge.commands.resources.tools.make_authenticated_request", return_value=[]):
                tools_list(gateway_id=None, active_only=False, json_output=False)

        # Verify "No tools found" message
        assert any("No tools found" in str(call) for call in mock_console.print.call_args_list)

    def test_tools_list_error(self, mock_console) -> None:
        """Test tools list error handling."""
        with patch("cforge.commands.resources.tools.get_console", return_value=mock_console):
            with patch("cforge.commands.resources.tools.make_authenticated_request", side_effect=Exception("API error")):
                with pytest.raises(typer.Exit):
                    tools_list(gateway_id=None, active_only=False, json_output=False)

    def test_tools_get_success(self, mock_console) -> None:
        """Test tools get command."""
        mock_tool = {"id": 1, "name": "test"}

        with patch("cforge.commands.resources.tools.get_console", return_value=mock_console):
            with patch("cforge.commands.resources.tools.make_authenticated_request", return_value=mock_tool):
                with patch("cforge.commands.resources.tools.print_json"):
                    tools_get(tool_id=1, json_output=False)

    def test_tools_create_from_file(self, mock_console) -> None:
        """Test tools create from file."""
        mock_result = {"id": 1, "name": "new_tool"}

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
        mock_result = {"id": 1, "name": "new_tool"}

        with patch("cforge.commands.resources.tools.get_console", return_value=mock_console):
            with patch("cforge.commands.resources.tools.prompt_for_schema", return_value={"name": "test"}):
                with patch("cforge.commands.resources.tools.make_authenticated_request", return_value=mock_result):
                    with patch("cforge.commands.resources.tools.print_json"):
                        tools_create(data_file=None, name=None, description=None)

    def test_tools_create_with_options(self, mock_console) -> None:
        """Test tools create with command-line options."""
        mock_result = {"id": 1, "name": "new_tool"}

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
        mock_result = {"id": 1, "name": "updated"}

        with tempfile.TemporaryDirectory() as temp_dir:
            data_file = Path(temp_dir) / "update.json"
            data_file.write_text(json.dumps({"description": "updated desc"}))

            with patch("cforge.commands.resources.tools.get_console", return_value=mock_console):
                with patch("cforge.commands.resources.tools.make_authenticated_request", return_value=mock_result):
                    with patch("cforge.commands.resources.tools.print_json"):
                        tools_update(tool_id=1, data_file=data_file)

    def test_tools_update_file_not_found(self, mock_console) -> None:
        """Test tools update with missing file."""
        with patch("cforge.commands.resources.tools.get_console", return_value=mock_console):
            with pytest.raises(typer.Exit):
                tools_update(tool_id=1, data_file=Path("/nonexistent.json"))

    def test_tools_delete_with_confirmation(self, mock_console) -> None:
        """Test tools delete with confirmation."""
        with patch("cforge.commands.resources.tools.get_console", return_value=mock_console):
            with patch("cforge.commands.resources.tools.make_authenticated_request"):
                with patch("cforge.commands.resources.tools.typer.confirm", return_value=True):
                    tools_delete(tool_id=1, confirm=False)

    def test_tools_delete_cancelled(self, mock_console) -> None:
        """Test tools delete cancelled."""
        with patch("cforge.commands.resources.tools.get_console", return_value=mock_console):
            with patch("cforge.commands.resources.tools.typer.confirm", return_value=False):
                with pytest.raises(typer.Exit) as exc_info:
                    tools_delete(tool_id=1, confirm=False)

                # Note: Exit(0) gets caught by exception handler and converted to Exit(1)
                assert exc_info.value.exit_code == 1

    def test_tools_delete_with_yes_flag(self, mock_console) -> None:
        """Test tools delete with --yes flag."""
        with patch("cforge.commands.resources.tools.get_console", return_value=mock_console):
            with patch("cforge.commands.resources.tools.make_authenticated_request"):
                tools_delete(tool_id=1, confirm=True)

        # Should not prompt
        assert not any("confirm" in str(call) for call in mock_console.print.call_args_list)

    def test_tools_toggle_success(self, mock_console) -> None:
        """Test tools toggle command."""
        mock_result = {"id": 1, "is_active": False}

        with patch("cforge.commands.resources.tools.get_console", return_value=mock_console):
            with patch("cforge.commands.resources.tools.make_authenticated_request", return_value=mock_result):
                with patch("cforge.commands.resources.tools.print_json"):
                    tools_toggle(tool_id=1)

    def test_tools_get_error(self, mock_console) -> None:
        """Test tools get error handling."""
        with patch("cforge.commands.resources.tools.get_console", return_value=mock_console):
            with patch("cforge.commands.resources.tools.make_authenticated_request", side_effect=Exception("API error")):
                with pytest.raises(typer.Exit):
                    tools_get(tool_id=1)

    def test_tools_toggle_error(self, mock_console) -> None:
        """Test tools toggle error handling."""
        with patch("cforge.commands.resources.tools.get_console", return_value=mock_console):
            with patch("cforge.commands.resources.tools.make_authenticated_request", side_effect=Exception("API error")):
                with pytest.raises(typer.Exit):
                    tools_toggle(tool_id=1)
