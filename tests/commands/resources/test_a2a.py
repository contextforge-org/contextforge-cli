# -*- coding: utf-8 -*-
"""Location: ./tests/commands/resources/test_a2a.py
Copyright 2025
SPDX-License-Identifier: Apache-2.0
Authors: Gabe Goodhart

Tests for the a2a commands.
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
from cforge.commands.resources.a2a import (
    a2a_create,
    a2a_delete,
    a2a_get,
    a2a_invoke,
    a2a_list,
    a2a_toggle,
    a2a_update,
)


class TestA2aCommands:
    """Tests for a2a commands."""

    def test_a2a_list_success(self, mock_console) -> None:
        """Test a2a list command."""
        mock_agents = [{"id": 1, "name": "agent1", "url": "http://example.com", "description": "desc1", "is_active": True}]

        with patch("cforge.commands.resources.a2a.get_console", return_value=mock_console):
            with patch("cforge.commands.resources.a2a.make_authenticated_request", return_value=mock_agents):
                with patch("cforge.commands.resources.a2a.print_table") as mock_print:
                    a2a_list(json_output=False)
                    mock_print.assert_called_once()

    def test_a2a_list_json_output(self, mock_console) -> None:
        """Test a2a list with JSON output."""
        with patch("cforge.commands.resources.a2a.get_console", return_value=mock_console):
            with patch("cforge.commands.resources.a2a.make_authenticated_request", return_value=[]):
                with patch("cforge.commands.resources.a2a.print_json") as mock_print:
                    a2a_list(json_output=True)
                    mock_print.assert_called_once()

    def test_a2a_list_no_results(self, mock_console) -> None:
        """Test a2a list with no results."""
        with patch("cforge.commands.resources.a2a.get_console", return_value=mock_console):
            with patch("cforge.commands.resources.a2a.make_authenticated_request", return_value=[]):
                a2a_list(json_output=False)

        # Verify "No A2A agents found" message
        assert any("No A2A agents found" in str(call) for call in mock_console.print.call_args_list)

    def test_a2a_list_error(self, mock_console) -> None:
        """Test a2a list error handling."""
        with patch("cforge.commands.resources.a2a.get_console", return_value=mock_console):
            with patch("cforge.commands.resources.a2a.make_authenticated_request", side_effect=Exception("API error")):
                with pytest.raises(typer.Exit):
                    a2a_list(json_output=False)

    def test_a2a_get_success(self, mock_console) -> None:
        """Test a2a get command."""
        mock_agent = {"id": 1, "name": "test"}

        with patch("cforge.commands.resources.a2a.get_console", return_value=mock_console):
            with patch("cforge.commands.resources.a2a.make_authenticated_request", return_value=mock_agent):
                with patch("cforge.commands.resources.a2a.print_json"):
                    a2a_get(agent_id=1)

    def test_a2a_create_from_file(self, mock_console) -> None:
        """Test a2a create from file."""
        mock_result = {"id": 1, "name": "new_agent"}

        with tempfile.TemporaryDirectory() as temp_dir:
            data_file = Path(temp_dir) / "agent.json"
            data_file.write_text(json.dumps({"name": "new_agent", "url": "http://example.com", "description": "desc"}))

            with patch("cforge.commands.resources.a2a.get_console", return_value=mock_console):
                with patch("cforge.commands.resources.a2a.make_authenticated_request", return_value=mock_result):
                    with patch("cforge.commands.resources.a2a.print_json"):
                        a2a_create(data_file=data_file, name=None, url=None, description=None)

    def test_a2a_create_file_not_found(self, mock_console) -> None:
        """Test a2a create with missing file."""
        with patch("cforge.commands.resources.a2a.get_console", return_value=mock_console):
            with pytest.raises(typer.Exit):
                a2a_create(data_file=Path("/nonexistent.json"), name=None, url=None, description=None)

    def test_a2a_create_interactive(self, mock_console) -> None:
        """Test a2a create interactive mode."""
        mock_result = {"id": 1, "name": "new_agent"}

        with patch("cforge.commands.resources.a2a.get_console", return_value=mock_console):
            with patch("cforge.commands.resources.a2a.prompt_for_schema", return_value={"name": "test", "url": "http://example.com"}):
                with patch("cforge.commands.resources.a2a.make_authenticated_request", return_value=mock_result):
                    with patch("cforge.commands.resources.a2a.print_json"):
                        a2a_create(data_file=None, name=None, url=None, description=None)

    def test_a2a_create_with_options(self, mock_console) -> None:
        """Test a2a create with command-line options."""
        mock_result = {"id": 1, "name": "new_agent"}

        with patch("cforge.commands.resources.a2a.get_console", return_value=mock_console):
            with patch("cforge.commands.resources.a2a.prompt_for_schema", return_value={"name": "test", "url": "http://example.com", "description": "desc"}) as mock_prompt:
                with patch("cforge.commands.resources.a2a.make_authenticated_request", return_value=mock_result):
                    with patch("cforge.commands.resources.a2a.print_json"):
                        a2a_create(data_file=None, name="test", url="http://example.com", description="desc")

                # Verify prefilled values
                call_args = mock_prompt.call_args
                assert call_args[1]["prefilled"]["name"] == "test"
                assert call_args[1]["prefilled"]["url"] == "http://example.com"
                assert call_args[1]["prefilled"]["description"] == "desc"

    def test_a2a_update_success(self, mock_console) -> None:
        """Test a2a update command."""
        mock_result = {"id": 1, "name": "updated"}

        with tempfile.TemporaryDirectory() as temp_dir:
            data_file = Path(temp_dir) / "update.json"
            data_file.write_text(json.dumps({"description": "updated desc"}))

            with patch("cforge.commands.resources.a2a.get_console", return_value=mock_console):
                with patch("cforge.commands.resources.a2a.make_authenticated_request", return_value=mock_result):
                    with patch("cforge.commands.resources.a2a.print_json"):
                        a2a_update(agent_id=1, data_file=data_file)

    def test_a2a_update_file_not_found(self, mock_console) -> None:
        """Test a2a update with missing file."""
        with patch("cforge.commands.resources.a2a.get_console", return_value=mock_console):
            with pytest.raises(typer.Exit):
                a2a_update(agent_id=1, data_file=Path("/nonexistent.json"))

    def test_a2a_delete_with_confirmation(self, mock_console) -> None:
        """Test a2a delete with confirmation."""
        with patch("cforge.commands.resources.a2a.get_console", return_value=mock_console):
            with patch("cforge.commands.resources.a2a.make_authenticated_request"):
                with patch("cforge.commands.resources.a2a.typer.confirm", return_value=True):
                    a2a_delete(agent_id=1, confirm=False)

    def test_a2a_delete_cancelled(self, mock_console) -> None:
        """Test a2a delete cancelled."""
        with patch("cforge.commands.resources.a2a.get_console", return_value=mock_console):
            with patch("cforge.commands.resources.a2a.typer.confirm", return_value=False):
                with pytest.raises(typer.Exit) as exc_info:
                    a2a_delete(agent_id=1, confirm=False)

                # Note: Exit(0) gets caught by exception handler and converted to Exit(1)
                assert exc_info.value.exit_code == 1

    def test_a2a_delete_with_yes_flag(self, mock_console) -> None:
        """Test a2a delete with --yes flag."""
        with patch("cforge.commands.resources.a2a.get_console", return_value=mock_console):
            with patch("cforge.commands.resources.a2a.make_authenticated_request"):
                a2a_delete(agent_id=1, confirm=True)

        # Should not prompt
        assert not any("confirm" in str(call) for call in mock_console.print.call_args_list)

    def test_a2a_toggle_success(self, mock_console) -> None:
        """Test a2a toggle command."""
        mock_result = {"id": 1, "is_active": False}

        with patch("cforge.commands.resources.a2a.get_console", return_value=mock_console):
            with patch("cforge.commands.resources.a2a.make_authenticated_request", return_value=mock_result):
                with patch("cforge.commands.resources.a2a.print_json"):
                    a2a_toggle(agent_id=1)

    def test_a2a_invoke_success(self, mock_console) -> None:
        """Test a2a invoke command."""
        mock_result = {"result": "success"}

        with tempfile.TemporaryDirectory() as temp_dir:
            data_file = Path(temp_dir) / "invoke.json"
            data_file.write_text(json.dumps({"param": "value"}))

            with patch("cforge.commands.resources.a2a.get_console", return_value=mock_console):
                with patch("cforge.commands.resources.a2a.make_authenticated_request", return_value=mock_result):
                    with patch("cforge.commands.resources.a2a.print_json"):
                        a2a_invoke(agent_name="test_agent", data_file=data_file)

    def test_a2a_invoke_file_not_found(self, mock_console) -> None:
        """Test a2a invoke with missing file."""
        with patch("cforge.commands.resources.a2a.get_console", return_value=mock_console):
            with pytest.raises(typer.Exit):
                a2a_invoke(agent_name="test_agent", data_file=Path("/nonexistent.json"))

    def test_a2a_get_error(self, mock_console) -> None:
        """Test a2a get error handling."""
        with patch("cforge.commands.resources.a2a.get_console", return_value=mock_console):
            with patch("cforge.commands.resources.a2a.make_authenticated_request", side_effect=Exception("API error")):
                with pytest.raises(typer.Exit):
                    a2a_get(agent_id=1)

    def test_a2a_toggle_error(self, mock_console) -> None:
        """Test a2a toggle error handling."""
        with patch("cforge.commands.resources.a2a.get_console", return_value=mock_console):
            with patch("cforge.commands.resources.a2a.make_authenticated_request", side_effect=Exception("API error")):
                with pytest.raises(typer.Exit):
                    a2a_toggle(agent_id=1)
