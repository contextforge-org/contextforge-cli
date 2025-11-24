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
import click
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
            prompts_list(mcp_server_id=None, json_output=False)
            mocks.print_table.assert_called_once()

    def test_prompts_list_json_output(self, mock_console) -> None:
        """Test prompts list with JSON output."""
        with patch_functions("cforge.commands.resources.prompts", get_console=mock_console, make_authenticated_request=[], print_json=None) as mocks:
            prompts_list(mcp_server_id=None, json_output=True)
            mocks.print_json.assert_called_once()

    def test_prompts_list_with_filters(self, mock_console) -> None:
        """Test prompts list with filters."""
        with patch_functions("cforge.commands.resources.prompts", get_console=mock_console, make_authenticated_request=[], print_table=None) as mocks:
            prompts_list(mcp_server_id="5", json_output=False)

            # Verify params
            call_args = mocks.make_authenticated_request.call_args
            assert call_args[1]["params"]["gateway_id"] == "5"

    def test_prompts_list_no_results(self, mock_console) -> None:
        """Test prompts list with no results."""
        with patch_functions("cforge.commands.resources.prompts", get_console=mock_console, make_authenticated_request=[]):
            prompts_list(mcp_server_id=None, json_output=False)

        # Verify "No prompts found" message
        assert any("No prompts found" in str(call) for call in mock_console.print.call_args_list)

    def test_prompts_list_error(self, mock_console) -> None:
        """Test prompts list error handling."""
        with patch_functions("cforge.commands.resources.prompts", get_console=mock_console, make_authenticated_request={"side_effect": Exception("API error")}):
            with pytest.raises(typer.Exit):
                prompts_list(mcp_server_id=None, json_output=False)

    def test_prompts_list_with_active_only_true(self, mock_console) -> None:
        """Test prompts list with --active-only flag set to True."""
        mock_prompts = [{"id": 1, "name": "prompt1", "isActive": True}]

        with patch_functions("cforge.commands.resources.prompts", get_console=mock_console, make_authenticated_request=mock_prompts, print_table=None) as mocks:
            prompts_list(mcp_server_id=None, active_only=True, json_output=False)

            # Verify that include_inactive=False was passed to API
            call_args = mocks.make_authenticated_request.call_args
            assert call_args[1]["params"]["include_inactive"] is False

    def test_prompts_list_with_active_only_false(self, mock_console) -> None:
        """Test prompts list with --active-only flag set to False (default)."""
        mock_prompts = [{"id": 1, "name": "prompt1", "isActive": True}, {"id": 2, "name": "prompt2", "isActive": False}]

        with patch_functions("cforge.commands.resources.prompts", get_console=mock_console, make_authenticated_request=mock_prompts, print_table=None) as mocks:
            prompts_list(mcp_server_id=None, active_only=False, json_output=False)

            # Verify that include_inactive=True was passed to API
            call_args = mocks.make_authenticated_request.call_args
            assert call_args[1]["params"]["include_inactive"] is True

    def test_prompts_list_default_shows_all(self, mock_console) -> None:
        """Test prompts list default behavior shows all prompts."""
        mock_prompts = [{"id": 1, "name": "prompt1", "isActive": True}, {"id": 2, "name": "prompt2", "isActive": False}]

        with patch_functions("cforge.commands.resources.prompts", get_console=mock_console, make_authenticated_request=mock_prompts, print_table=None) as mocks:
            # Call with explicit active_only=False (default value)
            prompts_list(mcp_server_id=None, active_only=False, json_output=False)

            # Verify that include_inactive=True was passed to API (default behavior)
            call_args = mocks.make_authenticated_request.call_args
            assert call_args[1]["params"]["include_inactive"] is True

    def test_prompts_list_with_filters_and_active_only(self, mock_console) -> None:
        """Test prompts list with both mcp_server_id and active_only filters."""
        with patch_functions("cforge.commands.resources.prompts", get_console=mock_console, make_authenticated_request=[], print_table=None) as mocks:
            prompts_list(mcp_server_id="5", active_only=True, json_output=False)

            # Verify params include both filters
            call_args = mocks.make_authenticated_request.call_args
            assert call_args[1]["params"]["gateway_id"] == "5"
            assert call_args[1]["params"]["include_inactive"] is False

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

    def test_prompts_update_prompt_for_schema(self, mock_console) -> None:
        """Test prompts update with interactive schema prompt."""
        with patch_functions("cforge.commands.resources.prompts", make_authenticated_request=None, print_json=None, get_console=mock_console) as mocks:
            update_body = {"name": "updated"}
            with patch("cforge.commands.resources.prompts.prompt_for_schema", return_value=update_body):
                prompts_update(prompt_id=1, data_file=None)
                mocks.make_authenticated_request.assert_called_once_with("PUT", "/prompts/1", json_data=update_body)

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

    def test_prompts_toggle_from_inactive_to_active(self, mock_console) -> None:
        """Test toggling a prompt from inactive to active."""
        with patch_functions(
            "cforge.commands.resources.prompts",
            get_console=mock_console,
            print_json=None,
            make_authenticated_request={
                "side_effect": [[{"id": 1, "name": "test", "isActive": False}], {"id": 1, "name": "test", "isActive": True}]  # GET list with include_inactive=True  # POST toggle result
            },
        ) as mocks:

            prompts_toggle(prompt_id=1)

            # Verify two calls were made
            assert mocks.make_authenticated_request.call_count == 2

            # Verify first call was GET to list with include_inactive=True
            get_call = mocks.make_authenticated_request.call_args_list[0]
            assert get_call[0][0] == "GET"
            assert get_call[0][1] == "/prompts"
            assert get_call[1]["params"]["include_inactive"] is True

            # Verify second call was POST with activate=True
            post_call = mocks.make_authenticated_request.call_args_list[1]
            assert post_call[0][0] == "POST"
            assert post_call[0][1] == "/prompts/1/toggle"
            assert post_call[1]["params"]["activate"] is True

    def test_prompts_toggle_from_active_to_inactive(self, mock_console) -> None:
        """Test toggling a prompt from active to inactive."""
        with patch_functions(
            "cforge.commands.resources.prompts",
            get_console=mock_console,
            print_json=None,
            make_authenticated_request={
                "side_effect": [[{"id": 1, "name": "test", "isActive": True}], {"id": 1, "name": "test", "isActive": False}]  # GET list with include_inactive=True  # POST toggle result
            },
        ) as mocks:

            prompts_toggle(prompt_id=1)

            # Verify two calls were made
            assert mocks.make_authenticated_request.call_count == 2

            # Verify first call was GET to list with include_inactive=True
            get_call = mocks.make_authenticated_request.call_args_list[0]
            assert get_call[0][0] == "GET"
            assert get_call[0][1] == "/prompts"
            assert get_call[1]["params"]["include_inactive"] is True

            # Verify second call was POST with activate=False
            post_call = mocks.make_authenticated_request.call_args_list[1]
            assert post_call[0][0] == "POST"
            assert post_call[0][1] == "/prompts/1/toggle"
            assert post_call[1]["params"]["activate"] is False

    def test_prompts_toggle_detects_current_status(self, mock_console) -> None:
        """Test that toggle command queries list to detect current status before toggling."""
        with patch_functions(
            "cforge.commands.resources.prompts",
            get_console=mock_console,
            print_json=None,
            make_authenticated_request={"side_effect": [[{"id": 1, "name": "test", "isActive": True}], {"id": 1, "name": "test", "isActive": False}]},
        ) as mocks:

            prompts_toggle(prompt_id=1)

            # Verify GET list was called first to detect current status
            calls = mocks.make_authenticated_request.call_args_list
            assert len(calls) == 2
            assert calls[0][0][0] == "GET"  # First call is GET
            assert calls[0][0][1] == "/prompts"  # GET list endpoint
            assert calls[1][0][0] == "POST"  # Second call is POST

    def test_prompts_toggle_prompt_not_found(self, mock_console) -> None:
        """Test toggle command error when prompt is not found in list."""
        with patch_functions("cforge.commands.resources.prompts", get_console=mock_console, make_authenticated_request=[{"id": 2, "name": "other", "isActive": True}]) as mocks:

            with pytest.raises(typer.Exit) as exc_info:
                prompts_toggle(prompt_id=1)

            # Verify error was raised
            assert exc_info.value.exit_code == 1

            # Verify only GET was called (POST never happened)
            assert mocks.make_authenticated_request.call_count == 1

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

    def test_prompts_lifecycle(self, mock_console, authorized_mock_client) -> None:
        """Test the lifecycle of prompts created via the API not a server"""
        with patch_functions(
            "cforge.commands.resources.prompts",
            get_console=mock_console,
            print_json=None,
            prompt_for_schema={"return_value": {"name": "foo", "template": "Hi there", "description": "greeting"}},
        ) as mocks:
            # Create the prompt
            prompts_create(data_file=None)
            mocks.print_json.assert_called_once()
            body = mocks.print_json.call_args[0][0]
            prompt_id = body["id"]
            mocks.print_json.reset_mock()

            # Get the prompt by id
            prompts_get(prompt_id)
            mocks.print_json.assert_called_once()
            body = mocks.print_json.call_args[0][0]
            assert body["description"] == "greeting"
            mocks.print_json.reset_mock()

            # Delete the prompt
            prompts_delete(prompt_id)
            mocks.print_json.reset_mock()

            # Make sure it's gone
            with pytest.raises(click.exceptions.Exit):
                prompts_get(prompt_id)
