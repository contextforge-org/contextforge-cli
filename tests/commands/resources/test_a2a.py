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
import click
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
from tests.conftest import patch_functions


class TestA2aCommands:
    """Tests for a2a commands."""

    def test_a2a_list_success(self, mock_console) -> None:
        """Test a2a list command."""
        mock_agents = [{"id": "agent-1", "name": "agent1", "url": "http://example.com", "description": "desc1", "enabled": True}]

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

    def test_a2a_list_with_active_only_true(self, mock_console) -> None:
        """Test a2a list with --active-only flag set to True."""
        mock_agents = [{"id": "agent-1", "name": "agent1", "enabled": True}]

        with patch("cforge.commands.resources.a2a.get_console", return_value=mock_console):
            with patch("cforge.commands.resources.a2a.make_authenticated_request", return_value=mock_agents) as mock_req:
                with patch("cforge.commands.resources.a2a.print_table"):
                    a2a_list(active_only=True, json_output=False)

                    # Verify that include_inactive=False was passed to API
                    call_args = mock_req.call_args
                    assert call_args[1]["params"]["include_inactive"] is False

    def test_a2a_list_with_active_only_false(self, mock_console) -> None:
        """Test a2a list with --active-only flag set to False (default)."""
        mock_agents = [{"id": "agent-1", "name": "agent1", "enabled": True}, {"id": "agent-2", "name": "agent2", "enabled": False}]

        with patch("cforge.commands.resources.a2a.get_console", return_value=mock_console):
            with patch("cforge.commands.resources.a2a.make_authenticated_request", return_value=mock_agents) as mock_req:
                with patch("cforge.commands.resources.a2a.print_table"):
                    a2a_list(active_only=False, json_output=False)

                    # Verify that include_inactive=True was passed to API
                    call_args = mock_req.call_args
                    assert call_args[1]["params"]["include_inactive"] is True

    def test_a2a_list_default_shows_all(self, mock_console) -> None:
        """Test a2a list default behavior shows all agents."""
        mock_agents = [{"id": "agent-1", "name": "agent1", "enabled": True}, {"id": "agent-2", "name": "agent2", "enabled": False}]

        with patch("cforge.commands.resources.a2a.get_console", return_value=mock_console):
            with patch("cforge.commands.resources.a2a.make_authenticated_request", return_value=mock_agents) as mock_req:
                with patch("cforge.commands.resources.a2a.print_table"):
                    # Call with explicit active_only=False (default value)
                    a2a_list(active_only=False, json_output=False)

                    # Verify that include_inactive=True was passed to API (default behavior)
                    call_args = mock_req.call_args
                    assert call_args[1]["params"]["include_inactive"] is True

    def test_a2a_get_success(self, mock_console) -> None:
        """Test a2a get command."""
        mock_agent = {"id": "agent-1", "name": "test"}

        with patch("cforge.commands.resources.a2a.get_console", return_value=mock_console):
            with patch("cforge.commands.resources.a2a.make_authenticated_request", return_value=mock_agent):
                with patch("cforge.commands.resources.a2a.print_json"):
                    a2a_get(agent_id="1")

    def test_a2a_create_from_file(self, mock_console) -> None:
        """Test a2a create from file."""
        mock_result = {"id": "agent-1", "name": "new_agent"}

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
        mock_result = {"id": "agent-1", "name": "new_agent"}

        with patch("cforge.commands.resources.a2a.get_console", return_value=mock_console):
            with patch("cforge.commands.resources.a2a.prompt_for_schema", return_value={"name": "test", "url": "http://example.com"}):
                with patch("cforge.commands.resources.a2a.make_authenticated_request", return_value=mock_result):
                    with patch("cforge.commands.resources.a2a.print_json"):
                        a2a_create(data_file=None, name=None, url=None, description=None)

    def test_a2a_create_with_options(self, mock_console) -> None:
        """Test a2a create with command-line options."""
        mock_result = {"id": "agent-1", "name": "new_agent"}

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
        mock_result = {"id": "agent-1", "name": "updated"}

        with tempfile.TemporaryDirectory() as temp_dir:
            data_file = Path(temp_dir) / "update.json"
            data_file.write_text(json.dumps({"description": "updated desc"}))

            with patch("cforge.commands.resources.a2a.get_console", return_value=mock_console):
                with patch("cforge.commands.resources.a2a.make_authenticated_request", return_value=mock_result):
                    with patch("cforge.commands.resources.a2a.print_json"):
                        a2a_update(agent_id="1", data_file=data_file)

    def test_a2a_update_file_not_found(self, mock_console) -> None:
        """Test a2a update with missing file."""
        with patch("cforge.commands.resources.a2a.get_console", return_value=mock_console):
            with pytest.raises(typer.Exit):
                a2a_update(agent_id="1", data_file=Path("/nonexistent.json"))

    def test_a2a_delete_with_confirmation(self, mock_console) -> None:
        """Test a2a delete with confirmation."""
        with patch("cforge.commands.resources.a2a.get_console", return_value=mock_console):
            with patch("cforge.commands.resources.a2a.make_authenticated_request"):
                with patch("cforge.commands.resources.a2a.typer.confirm", return_value=True):
                    a2a_delete(agent_id="1", confirm=False)

    def test_a2a_delete_cancelled(self, mock_console) -> None:
        """Test a2a delete cancelled."""
        with patch("cforge.commands.resources.a2a.get_console", return_value=mock_console):
            with patch("cforge.commands.resources.a2a.typer.confirm", return_value=False):
                with pytest.raises(typer.Exit) as exc_info:
                    a2a_delete(agent_id="1", confirm=False)

                # Note: Exit(0) gets caught by exception handler and converted to Exit(1)
                assert exc_info.value.exit_code == 1

    def test_a2a_delete_with_yes_flag(self, mock_console) -> None:
        """Test a2a delete with --yes flag."""
        with patch("cforge.commands.resources.a2a.get_console", return_value=mock_console):
            with patch("cforge.commands.resources.a2a.make_authenticated_request"):
                a2a_delete(agent_id="1", confirm=True)

        # Should not prompt
        assert not any("confirm" in str(call) for call in mock_console.print.call_args_list)

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
                    a2a_get(agent_id="1")

    def test_a2a_toggle_from_disabled_to_enabled(self, mock_console) -> None:
        """Test toggling an A2A agent from disabled to enabled."""
        with patch("cforge.commands.resources.a2a.get_console", return_value=mock_console):
            # Create side_effect list with two responses
            side_effects = [{"id": "1", "name": "test", "enabled": False}, {"id": "1", "name": "test", "enabled": True}]  # GET current status  # POST toggle result
            with patch("cforge.commands.resources.a2a.make_authenticated_request", side_effect=side_effects) as mock_req:
                with patch("cforge.commands.resources.a2a.print_json"):
                    a2a_toggle(agent_id="1")

                # Verify two calls were made
                assert mock_req.call_count == 2

                # Verify first call was GET to check current status
                get_call = mock_req.call_args_list[0]
                assert get_call[0][0] == "GET"
                assert get_call[0][1] == "/a2a/1"

                # Verify second call was POST with activate=True
                post_call = mock_req.call_args_list[1]
                assert post_call[0][0] == "POST"
                assert post_call[0][1] == "/a2a/1/toggle"
                assert post_call[1]["params"]["activate"] is True

    def test_a2a_toggle_from_enabled_to_disabled(self, mock_console) -> None:
        """Test toggling an A2A agent from enabled to disabled."""
        with patch("cforge.commands.resources.a2a.get_console", return_value=mock_console):
            # Create side_effect list with two responses
            side_effects = [{"id": "1", "name": "test", "enabled": True}, {"id": "1", "name": "test", "enabled": False}]  # GET current status  # POST toggle result
            with patch("cforge.commands.resources.a2a.make_authenticated_request", side_effect=side_effects) as mock_req:
                with patch("cforge.commands.resources.a2a.print_json"):
                    a2a_toggle(agent_id="1")

                # Verify two calls were made
                assert mock_req.call_count == 2

                # Verify first call was GET to check current status
                get_call = mock_req.call_args_list[0]
                assert get_call[0][0] == "GET"
                assert get_call[0][1] == "/a2a/1"

                # Verify second call was POST with activate=False
                post_call = mock_req.call_args_list[1]
                assert post_call[0][0] == "POST"
                assert post_call[0][1] == "/a2a/1/toggle"
                assert post_call[1]["params"]["activate"] is False

    def test_a2a_toggle_detects_current_status(self, mock_console) -> None:
        """Test that toggle command detects current status before toggling."""
        with patch("cforge.commands.resources.a2a.get_console", return_value=mock_console):
            with patch("cforge.commands.resources.a2a.make_authenticated_request") as mock_req:
                # Mock an agent that is currently enabled
                mock_req.side_effect = [{"id": "1", "name": "test", "enabled": True}, {"id": "1", "name": "test", "enabled": False}]
                with patch("cforge.commands.resources.a2a.print_json"):
                    a2a_toggle(agent_id="1")

                # Verify GET was called first to detect current status
                calls = mock_req.call_args_list
                assert len(calls) == 2
                assert calls[0][0][0] == "GET"  # First call is GET
                assert calls[1][0][0] == "POST"  # Second call is POST

    def test_a2a_toggle_error(self, mock_console) -> None:
        """Test a2a toggle error handling."""
        with patch("cforge.commands.resources.a2a.get_console", return_value=mock_console):
            with patch("cforge.commands.resources.a2a.make_authenticated_request", side_effect=Exception("API error")):
                with pytest.raises(typer.Exit):
                    a2a_toggle(agent_id="1")


class TestA2ACommandsIntegration:
    """Test a2a commands with a real gateway test client."""

    def test_a2a_lifecycle(self, mock_console, authorized_mock_client) -> None:
        """Test the full CRUD lifecycle of an a2a server.

        NOTE: This test mutates the state of the session gateway!
        """
        with patch_functions("cforge.commands.resources.a2a", print_json=None) as mocks:

            # Create a new MCP Server in the gateway
            a2a_body = {
                "name": "test-a2a-server",
                "endpoint_url": "http://foo.bar.com",
                "description": "A test A2A server",
            }
            with patch("cforge.commands.resources.a2a.prompt_for_schema", return_value=a2a_body):
                a2a_create(None)
            assert len(mocks.print_json.call_args_list) == 1
            body = mocks.print_json.call_args[0][0]
            a2a_id = body["id"]
            assert body["enabled"]
            mocks.print_json.reset_mock()

            # Retrieve it and verify
            a2a_get(a2a_id)
            assert len(mocks.print_json.call_args_list) == 1
            body = mocks.print_json.call_args[0][0]
            assert body["id"] == a2a_id
            mocks.print_json.reset_mock()

            # Update it
            update_body = {"description": "A new description"}
            with patch("cforge.commands.resources.a2a.prompt_for_schema", return_value=update_body):
                a2a_update(a2a_id, data_file=None)
            assert len(mocks.print_json.call_args_list) == 1
            body = mocks.print_json.call_args[0][0]
            assert body["description"] == update_body["description"]
            mocks.print_json.reset_mock()

            # Deactivate it
            a2a_toggle(a2a_id)
            assert len(mocks.print_json.call_args_list) == 1
            body = mocks.print_json.call_args[0][0]
            assert not body["enabled"]
            mocks.print_json.reset_mock()

            # Re-activate it
            a2a_toggle(a2a_id)
            assert len(mocks.print_json.call_args_list) == 1
            body = mocks.print_json.call_args[0][0]
            assert body["enabled"]
            mocks.print_json.reset_mock()

            # Delete it
            a2a_delete(a2a_id)

            # Verify it's gone
            with pytest.raises(click.exceptions.Exit):
                a2a_get(a2a_id)

    def test_a2a_list_active_only_integration(self, mock_console, authorized_mock_client) -> None:
        """Test --active-only flag filters correctly with real server."""
        with patch_functions("cforge.commands.resources.a2a", print_json=None, get_console=mock_console) as mocks:
            # Create an A2A agent
            a2a_body = {
                "name": "test-a2a-active",
                "endpoint_url": "http://test.example.com",
                "description": "Test A2A for active-only",
            }
            with patch("cforge.commands.resources.a2a.prompt_for_schema", return_value=a2a_body):
                a2a_create(None)
            a2a_id = mocks.print_json.call_args[0][0]["id"]
            mocks.print_json.reset_mock()

            # List with active_only=True should include it (starts enabled)
            a2a_list(active_only=True, json_output=True)
            active_agents = mocks.print_json.call_args[0][0]
            assert any(a["id"] == a2a_id for a in active_agents)
            mocks.print_json.reset_mock()

            # Disable the A2A agent
            a2a_toggle(agent_id=a2a_id)
            mocks.print_json.reset_mock()

            # List with active_only=True should NOT include it now
            a2a_list(active_only=True, json_output=True)
            active_agents = mocks.print_json.call_args[0][0]
            assert not any(a["id"] == a2a_id for a in active_agents)
            mocks.print_json.reset_mock()

            # List with active_only=False should still include it
            a2a_list(active_only=False, json_output=True)
            all_agents = mocks.print_json.call_args[0][0]
            assert any(a["id"] == a2a_id for a in all_agents)
            mocks.print_json.reset_mock()

            # Re-enable the A2A agent
            a2a_toggle(agent_id=a2a_id)
            mocks.print_json.reset_mock()

            # List with active_only=True should include it again
            a2a_list(active_only=True, json_output=True)
            active_agents = mocks.print_json.call_args[0][0]
            assert any(a["id"] == a2a_id for a in active_agents)

            # Clean up
            a2a_delete(a2a_id, confirm=True)

    def test_a2a_toggle_status_detection_integration(self, mock_console, authorized_mock_client) -> None:
        """Test toggle command detects current status correctly with real server."""
        with patch_functions("cforge.commands.resources.a2a", print_json=None, get_console=mock_console) as mocks:
            # Create an A2A agent
            a2a_body = {
                "name": "test-a2a-toggle",
                "endpoint_url": "http://test-toggle.example.com",
                "description": "Test A2A for toggle detection",
            }
            with patch("cforge.commands.resources.a2a.prompt_for_schema", return_value=a2a_body):
                a2a_create(None)
            a2a_id = mocks.print_json.call_args[0][0]["id"]
            initial_status = mocks.print_json.call_args[0][0]["enabled"]
            assert initial_status is True, "New A2A agent should start enabled"
            mocks.print_json.reset_mock()

            # Toggle (should detect enabled and switch to disabled)
            a2a_toggle(agent_id=a2a_id)
            mocks.print_json.reset_mock()

            # Verify status changed by getting it
            a2a_get(a2a_id)
            current_status = mocks.print_json.call_args[0][0]["enabled"]
            assert current_status is False, "A2A agent should now be disabled"
            mocks.print_json.reset_mock()

            # Toggle again (should detect disabled and switch to enabled)
            a2a_toggle(agent_id=a2a_id)
            mocks.print_json.reset_mock()

            # Verify status changed back
            a2a_get(a2a_id)
            final_status = mocks.print_json.call_args[0][0]["enabled"]
            assert final_status is True, "A2A agent should be enabled again"

            # Clean up
            a2a_delete(a2a_id, confirm=True)
