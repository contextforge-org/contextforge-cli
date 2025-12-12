# -*- coding: utf-8 -*-
"""Location: ./cforge/commands/resources/virtual_servers.py
Copyright 2025
SPDX-License-Identifier: Apache-2.0
Authors: Gabe Goodhart

CLI command group: virtual-servers
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
from mcpgateway.schemas import ServerCreate, ServerUpdate


def _fixup_payload(data: dict) -> dict:
    """There's an inconsistency between IDs in the body for this call and how
    they're returned in GET responses for the respective resources, so we make
    sure they're strings here
    """
    updated_data = data.copy()
    if associated_prompts := data.get("associated_prompts"):
        updated_data["associated_prompts"] = [str(x) for x in associated_prompts]
    if associated_resources := data.get("associated_resources"):
        updated_data["associated_resources"] = [str(x) for x in associated_resources]
    return updated_data


def virtual_servers_list(
    active_only: bool = typer.Option(False, "--active-only", help="Show only active virtual servers"),
    json_output: bool = typer.Option(False, "--json", help="Output as JSON"),
) -> None:
    """List all virtual servers."""
    console = get_console()

    try:
        result = make_authenticated_request("GET", "/servers", params={"include_inactive": not active_only})

        if json_output:
            print_json(result, "Virtual Servers")
        else:
            servers = result if isinstance(result, list) else [result]
            if servers:
                print_table(
                    servers,
                    "Virtual Servers",
                    ["id", "name", "description", "enabled"],
                )
            else:
                console.print("[yellow]No virtual servers found[/yellow]")

    except Exception as e:
        handle_exception(e)


def virtual_servers_get(
    server_id: str = typer.Argument(..., help="Server ID"),
) -> None:
    """Get details of a specific virtual server."""
    try:
        result = make_authenticated_request("GET", f"/servers/{server_id}")
        print_json(result, f"Virtual Server {server_id}")

    except Exception as e:
        handle_exception(e)


def virtual_servers_create(
    data_file: Optional[Path] = typer.Argument(None, help="JSON file containing server data (interactive mode if not provided)"),
    name: Optional[str] = typer.Option(None, "--name", help="Virtual server name"),
    description: Optional[str] = typer.Option(None, "--description", help="Virtual server description"),
) -> None:
    """Create a new virtual server.

    Can be used in three ways:
    1. Provide a JSON file: cforge virtual-servers create data.json
    2. Provide partial data via options: cforge virtual-servers create --name myserver --description "My server"
    3. Use interactive mode: cforge virtual-servers create
    """
    console = get_console()

    try:
        # Collect prefilled values from options
        prefilled = {}
        if name:
            prefilled["name"] = name
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
            data = prompt_for_schema(ServerCreate, prefilled=prefilled if prefilled else None)

        data = _fixup_payload(data)
        result = make_authenticated_request("POST", "/servers", json_data={"server": data})

        console.print("[green]✓ Virtual server created successfully![/green]")
        print_json(result, "Created Virtual Server")

    except Exception as e:
        handle_exception(e)


def virtual_servers_update(
    server_id: str = typer.Argument(..., help="Server ID"),
    data_file: Optional[Path] = typer.Argument(None, help="JSON file containing updated server data"),
) -> None:
    """Update an existing virtual server."""
    console = get_console()

    try:
        if data_file:
            if not data_file.exists():
                console.print(f"[red]File not found: {data_file}[/red]")
                raise typer.Exit(1)
            data = json.loads(data_file.read_text())
        else:
            data = prompt_for_schema(ServerUpdate)

        data = _fixup_payload(data)
        result = make_authenticated_request("PUT", f"/servers/{server_id}", json_data=data)

        console.print("[green]✓ Virtual server updated successfully![/green]")
        print_json(result, "Updated Virtual Server")

    except Exception as e:
        handle_exception(e)


def virtual_servers_delete(
    server_id: str = typer.Argument(..., help="Server ID"),
    confirm: bool = typer.Option(False, "--yes", "-y", help="Skip confirmation"),
) -> None:
    """Delete a virtual server."""
    console = get_console()

    try:
        if not confirm:
            confirmed = typer.confirm(f"Are you sure you want to delete virtual server {server_id}?")
            if not confirmed:
                console.print("[yellow]Cancelled[/yellow]")
                raise typer.Exit(0)

        make_authenticated_request("DELETE", f"/servers/{server_id}")
        console.print(f"[green]✓ Virtual server {server_id} deleted successfully![/green]")

    except Exception as e:
        handle_exception(e)


def virtual_servers_toggle(
    server_id: str = typer.Argument(..., help="Server ID"),
) -> None:
    """Toggle virtual server active status."""
    console = get_console()

    try:
        current_status = make_authenticated_request("GET", f"/servers/{server_id}")
        assert isinstance(current_status, dict)
        if current_status["enabled"]:
            activate = False
        else:
            activate = True
        result = make_authenticated_request("POST", f"/servers/{server_id}/toggle", params={"activate": activate})
        assert isinstance(result, dict)
        console.print("[green]✓ Virtual server toggled successfully![/green]")
        print_json(result, "Virtual Server Status")

    except Exception as e:
        handle_exception(e)


def virtual_servers_tools(
    server_id: str = typer.Argument(..., help="Server ID"),
    json_output: bool = typer.Option(False, "--json", help="Output as JSON"),
) -> None:
    """List tools available in a virtual server."""
    console = get_console()

    try:
        result = make_authenticated_request("GET", f"/servers/{server_id}/tools")

        if json_output:
            print_json(result, f"Virtual Server {server_id} Tools")
        else:
            tools = result if isinstance(result, list) else [result]
            if tools:
                print_table(tools, f"Virtual Server {server_id} Tools", ["id", "name", "description"])
            else:
                console.print("[yellow]No tools found[/yellow]")

    except Exception as e:
        handle_exception(e)


def virtual_servers_resources(
    server_id: str = typer.Argument(..., help="Server ID"),
    json_output: bool = typer.Option(False, "--json", help="Output as JSON"),
) -> None:
    """List resources available in a virtual server."""
    console = get_console()

    try:
        result = make_authenticated_request("GET", f"/servers/{server_id}/resources")

        if json_output:
            print_json(result, f"Virtual Server {server_id} Resources")
        else:
            resources = result if isinstance(result, list) else [result]
            if resources:
                print_table(resources, f"Virtual Server {server_id} Resources", ["id", "name", "uri", "description"])
            else:
                console.print("[yellow]No resources found[/yellow]")

    except Exception as e:
        handle_exception(e)


def virtual_servers_prompts(
    server_id: str = typer.Argument(..., help="Server ID"),
    json_output: bool = typer.Option(False, "--json", help="Output as JSON"),
) -> None:
    """List prompts available in a virtual server."""
    console = get_console()

    try:
        result = make_authenticated_request("GET", f"/servers/{server_id}/prompts")

        if json_output:
            print_json(result, f"Virtual Server {server_id} Prompts")
        else:
            prompts = result if isinstance(result, list) else [result]
            if prompts:
                print_table(prompts, f"Virtual Server {server_id} Prompts", ["id", "name", "description"])
            else:
                console.print("[yellow]No prompts found[/yellow]")

    except Exception as e:
        handle_exception(e)
