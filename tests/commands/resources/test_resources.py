# -*- coding: utf-8 -*-
"""Location: ./tests/commands/resources/test_resources.py
Copyright 2025
SPDX-License-Identifier: Apache-2.0
Authors: Gabe Goodhart

Tests for the resources commands.
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
from cforge.commands.resources.resources import (
    resources_create,
    resources_delete,
    resources_get,
    resources_list,
    resources_templates,
    resources_toggle,
    resources_update,
)
from tests.conftest import patch_functions


class TestResourcesCommands:
    """Tests for resources commands."""

    def test_resources_list_success(self, mock_console) -> None:
        """Test resources list command."""
        mock_resources = [{"id": 1, "name": "resource1", "uri": "file:///path", "description": "desc1", "mcp_server_id": "server1234", "enabled": True}]

        with patch("cforge.commands.resources.resources.get_console", return_value=mock_console):
            with patch("cforge.commands.resources.resources.make_authenticated_request", return_value=mock_resources):
                with patch("cforge.commands.resources.resources.print_table") as mock_print:
                    resources_list(mcp_server_id=None, json_output=False)
                    mock_print.assert_called_once()

    def test_resources_list_json_output(self, mock_console) -> None:
        """Test resources list with JSON output."""
        with patch("cforge.commands.resources.resources.get_console", return_value=mock_console):
            with patch("cforge.commands.resources.resources.make_authenticated_request", return_value=[]):
                with patch("cforge.commands.resources.resources.print_json") as mock_print:
                    resources_list(mcp_server_id=None, json_output=True)
                    mock_print.assert_called_once()

    def test_resources_list_with_filters(self, mock_console) -> None:
        """Test resources list with filters."""
        with patch("cforge.commands.resources.resources.get_console", return_value=mock_console):
            with patch("cforge.commands.resources.resources.make_authenticated_request", return_value=[]) as mock_req:
                with patch("cforge.commands.resources.resources.print_table"):
                    resources_list(mcp_server_id=5, json_output=False)

                # Verify params
                call_args = mock_req.call_args
                assert call_args[1]["params"]["gateway_id"] == 5

    def test_resources_list_no_results(self, mock_console) -> None:
        """Test resources list with no results."""
        with patch("cforge.commands.resources.resources.get_console", return_value=mock_console):
            with patch("cforge.commands.resources.resources.make_authenticated_request", return_value=[]):
                resources_list(mcp_server_id=None, json_output=False)

        # Verify "No resources found" message
        assert any("No resources found" in str(call) for call in mock_console.print.call_args_list)

    def test_resources_list_error(self, mock_console) -> None:
        """Test resources list error handling."""
        with patch("cforge.commands.resources.resources.get_console", return_value=mock_console):
            with patch("cforge.commands.resources.resources.make_authenticated_request", side_effect=Exception("API error")):
                with pytest.raises(typer.Exit):
                    resources_list(mcp_server_id=None, json_output=False)

    def test_resources_list_with_active_only_true(self, mock_console) -> None:
        """Test resources list with --active-only flag set to True."""
        mock_resources = [{"id": 1, "name": "resource1", "isActive": True}]

        with patch("cforge.commands.resources.resources.get_console", return_value=mock_console):
            with patch("cforge.commands.resources.resources.make_authenticated_request", return_value=mock_resources) as mock_req:
                with patch("cforge.commands.resources.resources.print_table"):
                    resources_list(mcp_server_id=None, active_only=True, json_output=False)

                    # Verify that include_inactive=False was passed to API
                    call_args = mock_req.call_args
                    assert call_args[1]["params"]["include_inactive"] is False

    def test_resources_list_with_active_only_false(self, mock_console) -> None:
        """Test resources list with --active-only flag set to False (default)."""
        mock_resources = [{"id": 1, "name": "resource1", "isActive": True}, {"id": 2, "name": "resource2", "isActive": False}]

        with patch("cforge.commands.resources.resources.get_console", return_value=mock_console):
            with patch("cforge.commands.resources.resources.make_authenticated_request", return_value=mock_resources) as mock_req:
                with patch("cforge.commands.resources.resources.print_table"):
                    resources_list(mcp_server_id=None, active_only=False, json_output=False)

                    # Verify that include_inactive=True was passed to API
                    call_args = mock_req.call_args
                    assert call_args[1]["params"]["include_inactive"] is True

    def test_resources_list_default_shows_all(self, mock_console) -> None:
        """Test resources list default behavior shows all resources."""
        mock_resources = [{"id": 1, "name": "resource1", "isActive": True}, {"id": 2, "name": "resource2", "isActive": False}]

        with patch("cforge.commands.resources.resources.get_console", return_value=mock_console):
            with patch("cforge.commands.resources.resources.make_authenticated_request", return_value=mock_resources) as mock_req:
                with patch("cforge.commands.resources.resources.print_table"):
                    # Call with explicit active_only=False (default value)
                    resources_list(mcp_server_id=None, active_only=False, json_output=False)

                    # Verify that include_inactive=True was passed to API (default behavior)
                    call_args = mock_req.call_args
                    assert call_args[1]["params"]["include_inactive"] is True

    def test_resources_list_with_filters_and_active_only(self, mock_console) -> None:
        """Test resources list with both mcp_server_id and active_only filters."""
        with patch("cforge.commands.resources.resources.get_console", return_value=mock_console):
            with patch("cforge.commands.resources.resources.make_authenticated_request", return_value=[]) as mock_req:
                with patch("cforge.commands.resources.resources.print_table"):
                    resources_list(mcp_server_id=5, active_only=True, json_output=False)

                # Verify params include both filters
                call_args = mock_req.call_args
                assert call_args[1]["params"]["gateway_id"] == 5
                assert call_args[1]["params"]["include_inactive"] is False

    def test_resources_get_success(self, mock_console) -> None:
        """Test resources get command."""
        mock_resource = {"id": 1, "name": "test"}

        with patch("cforge.commands.resources.resources.get_console", return_value=mock_console):
            with patch("cforge.commands.resources.resources.make_authenticated_request", return_value=mock_resource):
                with patch("cforge.commands.resources.resources.print_json"):
                    resources_get(resource_id=1)

    def test_resources_create_from_file(self, mock_console) -> None:
        """Test resources create from file."""
        mock_result = {"id": 1, "name": "new_resource"}

        with tempfile.TemporaryDirectory() as temp_dir:
            data_file = Path(temp_dir) / "resource.json"
            data_file.write_text(json.dumps({"name": "new_resource", "uri": "file:///path", "description": "desc"}))

            with patch("cforge.commands.resources.resources.get_console", return_value=mock_console):
                with patch("cforge.commands.resources.resources.make_authenticated_request", return_value=mock_result):
                    with patch("cforge.commands.resources.resources.print_json"):
                        resources_create(data_file=data_file, name=None, uri=None, description=None)

    def test_resources_create_file_not_found(self, mock_console) -> None:
        """Test resources create with missing file."""
        with patch("cforge.commands.resources.resources.get_console", return_value=mock_console):
            with pytest.raises(typer.Exit):
                resources_create(data_file=Path("/nonexistent.json"), name=None, uri=None, description=None)

    def test_resources_create_interactive(self, mock_console) -> None:
        """Test resources create interactive mode."""
        mock_result = {"id": 1, "name": "new_resource"}

        with patch("cforge.commands.resources.resources.get_console", return_value=mock_console):
            with patch("cforge.commands.resources.resources.prompt_for_schema", return_value={"name": "test", "uri": "file:///path"}):
                with patch("cforge.commands.resources.resources.make_authenticated_request", return_value=mock_result):
                    with patch("cforge.commands.resources.resources.print_json"):
                        resources_create(data_file=None, name=None, uri=None, description=None)

    def test_resources_create_with_options(self, mock_console) -> None:
        """Test resources create with command-line options."""
        mock_result = {"id": 1, "name": "new_resource"}

        with patch("cforge.commands.resources.resources.get_console", return_value=mock_console):
            with patch("cforge.commands.resources.resources.prompt_for_schema", return_value={"name": "test", "uri": "file:///path", "description": "desc"}) as mock_prompt:
                with patch("cforge.commands.resources.resources.make_authenticated_request", return_value=mock_result):
                    with patch("cforge.commands.resources.resources.print_json"):
                        resources_create(data_file=None, name="test", uri="file:///path", description="desc")

                # Verify prefilled values
                call_args = mock_prompt.call_args
                assert call_args[1]["prefilled"]["name"] == "test"
                assert call_args[1]["prefilled"]["uri"] == "file:///path"
                assert call_args[1]["prefilled"]["description"] == "desc"

    def test_resources_update_success(self, mock_console) -> None:
        """Test resources update command."""
        mock_result = {"id": 1, "name": "updated"}

        with tempfile.TemporaryDirectory() as temp_dir:
            data_file = Path(temp_dir) / "update.json"
            data_file.write_text(json.dumps({"description": "updated desc"}))

            with patch("cforge.commands.resources.resources.get_console", return_value=mock_console):
                with patch("cforge.commands.resources.resources.make_authenticated_request", return_value=mock_result):
                    with patch("cforge.commands.resources.resources.print_json"):
                        resources_update(resource_id=1, data_file=data_file)

    def test_resources_update_file_not_found(self, mock_console) -> None:
        """Test resources update with missing file."""
        with patch("cforge.commands.resources.resources.get_console", return_value=mock_console):
            with pytest.raises(typer.Exit):
                resources_update(resource_id=1, data_file=Path("/nonexistent.json"))

    def test_resources_update_resource_for_schema(self, mock_console) -> None:
        """Test resources update with interactive schema resource."""
        with patch_functions("cforge.commands.resources.resources", make_authenticated_request=None, print_json=None, get_console=mock_console) as mocks:
            update_body = {"name": "updated"}
            with patch("cforge.commands.resources.resources.prompt_for_schema", return_value=update_body):
                resources_update(resource_id=1, data_file=None)
                mocks.make_authenticated_request.assert_called_once_with("PUT", "/resources/1", json_data=update_body)

    def test_resources_delete_with_confirmation(self, mock_console) -> None:
        """Test resources delete with confirmation."""
        with patch("cforge.commands.resources.resources.get_console", return_value=mock_console):
            with patch("cforge.commands.resources.resources.make_authenticated_request"):
                with patch("cforge.commands.resources.resources.typer.confirm", return_value=True):
                    resources_delete(resource_id=1, confirm=False)

    def test_resources_delete_cancelled(self, mock_console) -> None:
        """Test resources delete cancelled."""
        with patch("cforge.commands.resources.resources.get_console", return_value=mock_console):
            with patch("cforge.commands.resources.resources.typer.confirm", return_value=False):
                with pytest.raises(typer.Exit) as exc_info:
                    resources_delete(resource_id=1, confirm=False)

                # Note: Exit(0) gets caught by exception handler and converted to Exit(1)
                assert exc_info.value.exit_code == 1

    def test_resources_delete_with_yes_flag(self, mock_console) -> None:
        """Test resources delete with --yes flag."""
        with patch("cforge.commands.resources.resources.get_console", return_value=mock_console):
            with patch("cforge.commands.resources.resources.make_authenticated_request"):
                resources_delete(resource_id=1, confirm=True)

        # Should not prompt
        assert not any("confirm" in str(call) for call in mock_console.print.call_args_list)

    def test_resources_toggle_from_inactive_to_active(self, mock_console) -> None:
        """Test toggling a resource from inactive to active."""
        with patch("cforge.commands.resources.resources.get_console", return_value=mock_console):
            with patch("cforge.commands.resources.resources.make_authenticated_request") as mock_req:
                # First call (GET list) returns list with inactive resource, second call (POST) returns active resource
                mock_req.side_effect = [[{"id": 1, "name": "test", "isActive": False}], {"id": 1, "name": "test", "isActive": True}]  # GET list with include_inactive=True  # POST toggle result
                with patch("cforge.commands.resources.resources.print_json"):
                    resources_toggle(resource_id=1)

                # Verify two calls were made
                assert mock_req.call_count == 2

                # Verify first call was GET to list with include_inactive=True
                get_call = mock_req.call_args_list[0]
                assert get_call[0][0] == "GET"
                assert get_call[0][1] == "/resources"
                assert get_call[1]["params"]["include_inactive"] is True

                # Verify second call was POST with activate=True
                post_call = mock_req.call_args_list[1]
                assert post_call[0][0] == "POST"
                assert post_call[0][1] == "/resources/1/toggle"
                assert post_call[1]["params"]["activate"] is True

    def test_resources_toggle_from_active_to_inactive(self, mock_console) -> None:
        """Test toggling a resource from active to inactive."""
        with patch("cforge.commands.resources.resources.get_console", return_value=mock_console):
            with patch("cforge.commands.resources.resources.make_authenticated_request") as mock_req:
                # First call (GET list) returns list with active resource, second call (POST) returns inactive resource
                mock_req.side_effect = [[{"id": 1, "name": "test", "isActive": True}], {"id": 1, "name": "test", "isActive": False}]  # GET list with include_inactive=True  # POST toggle result
                with patch("cforge.commands.resources.resources.print_json"):
                    resources_toggle(resource_id=1)

                # Verify two calls were made
                assert mock_req.call_count == 2

                # Verify first call was GET to list with include_inactive=True
                get_call = mock_req.call_args_list[0]
                assert get_call[0][0] == "GET"
                assert get_call[0][1] == "/resources"
                assert get_call[1]["params"]["include_inactive"] is True

                # Verify second call was POST with activate=False
                post_call = mock_req.call_args_list[1]
                assert post_call[0][0] == "POST"
                assert post_call[0][1] == "/resources/1/toggle"
                assert post_call[1]["params"]["activate"] is False

    def test_resources_toggle_detects_current_status(self, mock_console) -> None:
        """Test that toggle command queries list to detect current status before toggling."""
        with patch("cforge.commands.resources.resources.get_console", return_value=mock_console):
            with patch("cforge.commands.resources.resources.make_authenticated_request") as mock_req:
                # Mock a resource that is currently active
                mock_req.side_effect = [[{"id": 1, "name": "test", "isActive": True}], {"id": 1, "name": "test", "isActive": False}]
                with patch("cforge.commands.resources.resources.print_json"):
                    resources_toggle(resource_id=1)

                # Verify GET list was called first to detect current status
                calls = mock_req.call_args_list
                assert len(calls) == 2
                assert calls[0][0][0] == "GET"  # First call is GET
                assert calls[0][0][1] == "/resources"  # GET list endpoint
                assert calls[1][0][0] == "POST"  # Second call is POST

    def test_resources_toggle_resource_not_found(self, mock_console) -> None:
        """Test toggle command error when resource is not found in list."""
        with patch("cforge.commands.resources.resources.get_console", return_value=mock_console):
            with patch("cforge.commands.resources.resources.make_authenticated_request") as mock_req:
                # Return empty list (resource not found)
                mock_req.return_value = [{"id": 2, "name": "other", "isActive": True}]

                with pytest.raises(typer.Exit) as exc_info:
                    resources_toggle(resource_id=1)

                # Verify error was raised
                assert exc_info.value.exit_code == 1

                # Verify only GET was called (POST never happened)
                assert mock_req.call_count == 1

    def test_resources_templates_success(self, mock_console) -> None:
        """Test resources templates command."""
        mock_templates = [{"name": "template1", "description": "desc1"}]

        with patch("cforge.commands.resources.resources.get_console", return_value=mock_console):
            with patch("cforge.commands.resources.resources.make_authenticated_request", return_value=mock_templates):
                with patch("cforge.commands.resources.resources.print_json"):
                    resources_templates()

    def test_resources_get_error(self, mock_console) -> None:
        """Test resources get error handling."""
        with patch("cforge.commands.resources.resources.get_console", return_value=mock_console):
            with patch("cforge.commands.resources.resources.make_authenticated_request", side_effect=Exception("API error")):
                with pytest.raises(typer.Exit):
                    resources_get(resource_id=1)

    def test_resources_toggle_error(self, mock_console) -> None:
        """Test resources toggle error handling."""
        with patch("cforge.commands.resources.resources.get_console", return_value=mock_console):
            with patch("cforge.commands.resources.resources.make_authenticated_request", side_effect=Exception("API error")):
                with pytest.raises(typer.Exit):
                    resources_toggle(resource_id=1)

    def test_resources_templates_error(self, mock_console) -> None:
        """Test resources templates error handling."""
        with patch("cforge.commands.resources.resources.get_console", return_value=mock_console):
            with patch("cforge.commands.resources.resources.make_authenticated_request", side_effect=Exception("API error")):
                with pytest.raises(typer.Exit):
                    resources_templates()


class TestResourcesCommandsIntegration:
    """Test resources commands with a real gateway test client."""

    def test_resources_list_get(self, mock_console, registered_mcp_server) -> None:
        """Test listing and getting resources from a registered MCP server"""
        with patch_functions("cforge.commands.resources.resources", get_console=mock_console, print_json=None) as mocks:
            resources_list(json_output=True)
            mocks.print_json.assert_called_once()
            body = mocks.print_json.call_args[0][0]
            assert isinstance(body, list) and len(body) == 1
            for prompt in body:
                mocks.print_json.reset_mock()
                resources_get(prompt["id"])
                mocks.print_json.assert_called_once()
                body = mocks.print_json.call_args[0][0]
                assert isinstance(body, dict)

    def test_resources_lifecycle(self, mock_console, authorized_mock_client) -> None:
        """Test the lifecycle of resources created via the API not a server"""
        resource_body = {"name": "foo", "content": "hi there", "uri": "resource://test-greet"}
        with patch_functions(
            "cforge.commands.resources.resources",
            get_console=mock_console,
            print_json=None,
            prompt_for_schema={"return_value": resource_body},
        ) as mocks:
            # Create the resource
            resources_create(data_file=None)
            mocks.print_json.assert_called_once()
            body = mocks.print_json.call_args[0][0]
            resource_id = body["id"]
            mocks.print_json.reset_mock()

            # Get the resource by id
            resources_get(resource_id)
            mocks.print_json.assert_called_once()
            body = mocks.print_json.call_args[0][0]
            assert body["uri"] == resource_body["uri"]
            assert body["text"] == resource_body["content"]
            mocks.print_json.reset_mock()

        update_resource_body = {"name": "foobar", "content": "oh hello there"}
        with patch_functions(
            "cforge.commands.resources.resources",
            get_console=mock_console,
            print_json=None,
            prompt_for_schema={"return_value": update_resource_body},
        ) as mocks:
            # Update the resource
            resources_update(resource_id, data_file=None)
            mocks.print_json.assert_called_once()
            body = mocks.print_json.call_args[0][0]
            assert body["uri"] == resource_body["uri"]
            assert body["name"] == update_resource_body["name"]
            mocks.print_json.reset_mock()
            resources_get(resource_id)
            mocks.print_json.assert_called_once()
            body = mocks.print_json.call_args[0][0]
            assert body["text"] == update_resource_body["content"]

            # Delete the resource
            resources_delete(resource_id)
            mocks.print_json.reset_mock()

            # Make sure it's gone
            with pytest.raises(click.exceptions.Exit):
                resources_get(resource_id)
