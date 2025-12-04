# -*- coding: utf-8 -*-
"""Location: ./cforge/commands/resources/a2a.py
Copyright 2025
SPDX-License-Identifier: Apache-2.0
Authors: Gabe Goodhart

CLI command group: a2a
"""

# Standard
import json
from pathlib import Path
from typing import Optional

# Third-Party
import typer

# First-Party
from cforge.common import (
    get_console,
    handle_exception,
    make_authenticated_request,
    print_json,
    print_table,
    prompt_for_schema,
)
from mcpgateway.schemas import A2AAgentCreate, A2AAgentUpdate


def a2a_list(
    active_only: bool = typer.Option(False, "--active-only", help="Show only active agents"),
    json_output: bool = typer.Option(False, "--json", help="Output as JSON"),
) -> None:
    """List all A2A agents."""
    console = get_console()

    try:
        result = make_authenticated_request("GET", "/a2a", params={"include_inactive": not active_only})

        if json_output:
            print_json(result, "A2A Agents")
        else:
            agents = result if isinstance(result, list) else [result]
            if agents:
                print_table(agents, "A2A Agents", ["id", "name", "endpointUrl", "description", "enabled"], {"endpointUrl": "url"})
            else:
                console.print("[yellow]No A2A agents found[/yellow]")

    except Exception as e:
        handle_exception(e)


def a2a_get(
    agent_id: str = typer.Argument(..., help="Agent ID"),
) -> None:
    """Get details of a specific A2A agent."""
    try:
        result = make_authenticated_request("GET", f"/a2a/{agent_id}")
        print_json(result, f"A2A Agent {agent_id}")

    except Exception as e:
        handle_exception(e)


def a2a_create(
    data_file: Optional[Path] = typer.Argument(None, help="JSON file containing agent data (interactive mode if not provided)"),
    name: Optional[str] = typer.Option(None, "--name", help="Agent name"),
    url: Optional[str] = typer.Option(None, "--url", help="Agent endpoint URL"),
    description: Optional[str] = typer.Option(None, "--description", help="Agent description"),
) -> None:
    """Register a new A2A agent.

    Can be used in three ways:
    1. Provide a JSON file: cforge a2a create data.json
    2. Provide partial data via options: cforge a2a create --name myagent --url http://example.com
    3. Use interactive mode: cforge a2a create
    """
    console = get_console()

    try:
        # Collect prefilled values from options
        prefilled = {}
        if name:
            prefilled["name"] = name
        if url:
            prefilled["url"] = url
        if description:
            prefilled["description"] = description

        # Determine data source
        if data_file:
            if not data_file.exists():
                console.print(f"[red]File not found: {data_file}[/red]")
                raise typer.Exit(1)
            data = json.loads(data_file.read_text())
            data.update(prefilled)
        else:
            data = prompt_for_schema(A2AAgentCreate, prefilled=prefilled if prefilled else None)

        result = make_authenticated_request("POST", "/a2a", json_data={"agent": data})

        console.print("[green]✓ A2A agent registered successfully![/green]")
        print_json(result, "Registered A2A Agent")

    except Exception as e:
        handle_exception(e)


def a2a_update(
    agent_id: str = typer.Argument(..., help="Agent ID"),
    data_file: Optional[Path] = typer.Argument(None, help="JSON file containing updated agent data"),
) -> None:
    """Update an existing A2A agent."""
    console = get_console()

    try:
        if data_file:
            if not data_file.exists():
                console.print(f"[red]File not found: {data_file}[/red]")
                raise typer.Exit(1)
            data = json.loads(data_file.read_text())
        else:
            data = prompt_for_schema(A2AAgentUpdate)

        result = make_authenticated_request("PUT", f"/a2a/{agent_id}", json_data=data)

        console.print("[green]✓ A2A agent updated successfully![/green]")
        print_json(result, "Updated A2A Agent")

    except Exception as e:
        handle_exception(e)


def a2a_delete(
    agent_id: str = typer.Argument(..., help="Agent ID"),
    confirm: bool = typer.Option(False, "--yes", "-y", help="Skip confirmation"),
) -> None:
    """Delete an A2A agent."""
    console = get_console()

    try:
        if not confirm:
            confirmed = typer.confirm(f"Are you sure you want to delete A2A agent {agent_id}?")
            if not confirmed:
                console.print("[yellow]Cancelled[/yellow]")
                raise typer.Exit(0)

        make_authenticated_request("DELETE", f"/a2a/{agent_id}")
        console.print(f"[green]✓ A2A agent {agent_id} deleted successfully![/green]")

    except Exception as e:
        handle_exception(e)


def a2a_toggle(
    agent_id: str = typer.Argument(..., help="Agent ID"),
) -> None:
    """Toggle A2A agent active status."""
    console = get_console()

    try:
        current_status = make_authenticated_request("GET", f"/a2a/{agent_id}")
        assert isinstance(current_status, dict)
        if current_status["enabled"]:
            activate = False
        else:
            activate = True
        result = make_authenticated_request("POST", f"/a2a/{agent_id}/toggle", params={"activate": activate})
        assert isinstance(result, dict)
        assert result["enabled"] == activate, "Failed to toggle A2A Agent"
        console.print("[green]✓ A2A agent toggled successfully![/green]")
        print_json(result, "A2A Agent Status")

    except Exception as e:
        handle_exception(e)


def a2a_invoke(
    agent_name: str = typer.Argument(..., help="Agent name"),
    data_file: Path = typer.Argument(..., help="JSON file containing invocation data"),
) -> None:
    """Invoke an A2A agent with parameters."""
    console = get_console()

    try:
        if not data_file.exists():
            console.print(f"[red]File not found: {data_file}[/red]")
            raise typer.Exit(1)

        data = json.loads(data_file.read_text())
        result = make_authenticated_request("POST", f"/a2a/{agent_name}/invoke", json_data=data)

        console.print("[green]✓ A2A agent invoked successfully![/green]")
        print_json(result, "Invocation Result")

    except Exception as e:
        handle_exception(e)
