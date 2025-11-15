# -*- coding: utf-8 -*-
"""Location: ./tests/commands/resources/test_prompts.py
Copyright 2025
SPDX-License-Identifier: Apache-2.0
Authors: Gabe Goodhart

Tests for the prompts commands.
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
from cforge.commands.resources.prompts import (
    prompts_create,
    prompts_delete,
    prompts_execute,
    prompts_get,
    prompts_list,
    prompts_toggle,
    prompts_update,
)
from tests.conftest import patch_functions


class TestPromptsCommands:
    """Tests for prompts commands."""

    def test_prompts_list_success(self, mock_console) -> None:
        """Test prompts list command."""
        mock_prompts = [{"id": 1, "name": "prompt1", "description": "desc1", "gateway_id": 1, "enabled": True}]

        with patch_functions("cforge.commands.resources.prompts", get_console=mock_console, make_authenticated_request=mock_prompts, print_table=None) as mocks:
            prompts_list(gateway_id=None, json_output=False)
            mocks.print_table.assert_called_once()

    def test_prompts_list_json_output(self, mock_console) -> None:
        """Test prompts list with JSON output."""
        with patch_functions("cforge.commands.resources.prompts", get_console=mock_console, make_authenticated_request=[], print_json=None) as mocks:
            prompts_list(gateway_id=None, json_output=True)
            mocks.print_json.assert_called_once()

    def test_prompts_list_with_filters(self, mock_console) -> None:
        """Test prompts list with filters."""
        with patch_functions("cforge.commands.resources.prompts", get_console=mock_console, make_authenticated_request=[], print_table=None) as mocks:
            prompts_list(gateway_id=5, json_output=False)

            # Verify params
            call_args = mocks.make_authenticated_request.call_args
            assert call_args[1]["params"]["gateway_id"] == 5

    def test_prompts_list_no_results(self, mock_console) -> None:
        """Test prompts list with no results."""
        with patch_functions("cforge.commands.resources.prompts", get_console=mock_console, make_authenticated_request=[]):
            prompts_list(gateway_id=None, json_output=False)

        # Verify "No prompts found" message
        assert any("No prompts found" in str(call) for call in mock_console.print.call_args_list)

    def test_prompts_list_error(self, mock_console) -> None:
        """Test prompts list error handling."""
        with patch_functions("cforge.commands.resources.prompts", get_console=mock_console, make_authenticated_request={"side_effect": Exception("API error")}):
            with pytest.raises(typer.Exit):
                prompts_list(gateway_id=None, json_output=False)

    def test_prompts_get_success(self, mock_console) -> None:
        """Test prompts get command."""
        mock_prompt = {"id": 1, "name": "test"}

        with patch_functions("cforge.commands.resources.prompts", get_console=mock_console, make_authenticated_request=mock_prompt, print_json=None):
            prompts_get(prompt_id=1)

    def test_prompts_create_from_file(self, mock_console) -> None:
        """Test prompts create from file."""
        mock_result = {"id": 1, "name": "new_prompt"}

        with tempfile.TemporaryDirectory() as temp_dir:
            data_file = Path(temp_dir) / "prompt.json"
            data_file.write_text(json.dumps({"name": "new_prompt", "description": "desc"}))

            with patch_functions("cforge.commands.resources.prompts", get_console=mock_console, make_authenticated_request=mock_result, print_json=None):
                prompts_create(data_file=data_file, name=None, description=None)

    def test_prompts_create_file_not_found(self, mock_console) -> None:
        """Test prompts create with missing file."""
        with patch_functions("cforge.commands.resources.prompts", get_console=mock_console):
            with pytest.raises(typer.Exit):
                prompts_create(data_file=Path("/nonexistent.json"), name=None, description=None)

    def test_prompts_create_interactive(self, mock_console) -> None:
        """Test prompts create interactive mode."""
        mock_result = {"id": 1, "name": "new_prompt"}

        with patch_functions("cforge.commands.resources.prompts", get_console=mock_console, prompt_for_schema={"name": "test"}, make_authenticated_request=mock_result, print_json=None):
            prompts_create(data_file=None, name=None, description=None)

    def test_prompts_create_with_options(self, mock_console) -> None:
        """Test prompts create with command-line options."""
        mock_result = {"id": 1, "name": "new_prompt"}

        with patch_functions(
            "cforge.commands.resources.prompts", get_console=mock_console, prompt_for_schema={"name": "test", "description": "desc"}, make_authenticated_request=mock_result, print_json=None
        ) as mocks:
            prompts_create(data_file=None, name="test", description="desc")

            # Verify prefilled values
            call_args = mocks.prompt_for_schema.call_args
            assert call_args[1]["prefilled"]["name"] == "test"
            assert call_args[1]["prefilled"]["description"] == "desc"

    def test_prompts_update_success(self, mock_console) -> None:
        """Test prompts update command."""
        mock_result = {"id": 1, "name": "updated"}

        with tempfile.TemporaryDirectory() as temp_dir:
            data_file = Path(temp_dir) / "update.json"
            data_file.write_text(json.dumps({"description": "updated desc"}))

            with patch_functions("cforge.commands.resources.prompts", get_console=mock_console, make_authenticated_request=mock_result, print_json=None):
                prompts_update(prompt_id=1, data_file=data_file)

    def test_prompts_update_file_not_found(self, mock_console) -> None:
        """Test prompts update with missing file."""
        with patch_functions("cforge.commands.resources.prompts", get_console=mock_console):
            with pytest.raises(typer.Exit):
                prompts_update(prompt_id=1, data_file=Path("/nonexistent.json"))

    def test_prompts_delete_with_confirmation(self, mock_console) -> None:
        """Test prompts delete with confirmation."""
        with patch_functions("cforge.commands.resources.prompts", get_console=mock_console, make_authenticated_request=None):
            with patch("cforge.commands.resources.prompts.typer.confirm", return_value=True):
                prompts_delete(prompt_id=1, confirm=False)

    def test_prompts_delete_cancelled(self, mock_console) -> None:
        """Test prompts delete cancelled."""
        with patch_functions("cforge.commands.resources.prompts", get_console=mock_console):
            with patch("cforge.commands.resources.prompts.typer.confirm", return_value=False):
                with pytest.raises(typer.Exit) as exc_info:
                    prompts_delete(prompt_id=1, confirm=False)

                # Note: Exit(0) gets caught by exception handler and converted to Exit(1)
                assert exc_info.value.exit_code == 1

    def test_prompts_delete_with_yes_flag(self, mock_console) -> None:
        """Test prompts delete with --yes flag."""
        with patch_functions("cforge.commands.resources.prompts", get_console=mock_console, make_authenticated_request=None):
            prompts_delete(prompt_id=1, confirm=True)

        # Should not prompt
        assert not any("confirm" in str(call) for call in mock_console.print.call_args_list)

    def test_prompts_toggle_success(self, mock_console) -> None:
        """Test prompts toggle command."""
        mock_result = {"id": 1, "enabled": False}

        with patch_functions("cforge.commands.resources.prompts", get_console=mock_console, make_authenticated_request=mock_result, print_json=None):
            prompts_toggle(prompt_id=1)

    def test_prompts_execute_success(self, mock_console) -> None:
        """Test prompts execute command."""
        mock_result = {"result": "success"}

        with patch_functions("cforge.commands.resources.prompts", get_console=mock_console, make_authenticated_request=mock_result, print_json=None):
            prompts_execute(prompt_id=1, data_file=None)

    def test_prompts_execute_with_data_file(self, mock_console) -> None:
        """Test prompts execute with data file."""
        mock_result = {"result": "success"}

        with tempfile.TemporaryDirectory() as temp_dir:
            data_file = Path(temp_dir) / "args.json"
            data_file.write_text(json.dumps({"arg1": "value1"}))

            with patch_functions("cforge.commands.resources.prompts", get_console=mock_console, make_authenticated_request=mock_result, print_json=None) as mocks:
                prompts_execute(prompt_id=1, data_file=data_file)

                # Verify data was passed
                call_args = mocks.make_authenticated_request.call_args
                assert call_args[1]["json_data"]["arg1"] == "value1"

    def test_prompts_execute_data_file_not_found(self, mock_console) -> None:
        """Test prompts execute with missing data file."""
        with patch_functions("cforge.commands.resources.prompts", get_console=mock_console):
            with pytest.raises(typer.Exit):
                prompts_execute(prompt_id=1, data_file=Path("/nonexistent.json"))

    def test_prompts_get_error(self, mock_console) -> None:
        """Test prompts get error handling."""
        with patch_functions("cforge.commands.resources.prompts", get_console=mock_console, make_authenticated_request={"side_effect": Exception("API error")}):
            with pytest.raises(typer.Exit):
                prompts_get(prompt_id=1)

    def test_prompts_toggle_error(self, mock_console) -> None:
        """Test prompts toggle error handling."""
        with patch_functions("cforge.commands.resources.prompts", get_console=mock_console, make_authenticated_request={"side_effect": Exception("API error")}):
            with pytest.raises(typer.Exit):
                prompts_toggle(prompt_id=1)


class TestPromptsCommandsIntegration:
    """Test prompts commands with a real gateway test client."""

    def test_prompts_list_get(self, mock_console, registered_mcp_server) -> None:
        """Test listing and getting prompts from a registered MCP server"""
        with patch_functions("cforge.commands.resources.prompts", get_console=mock_console, print_json=None) as mocks:
            prompts_list(json_output=True)
            mocks.print_json.assert_called_once()
            body = mocks.print_json.call_args[0][0]
            assert isinstance(body, list) and len(body) == 2
            for prompt in body:
                mocks.print_json.reset_mock()
                prompts_get(prompt["id"])
                mocks.print_json.assert_called_once()
                body = mocks.print_json.call_args[0][0]
                assert isinstance(body, dict)
