# -*- coding: utf-8 -*-
"""Location: ./cforge/commands/resources/mcp_servers.py
Copyright 2025
SPDX-License-Identifier: Apache-2.0
Authors: Gabe Goodhart

CLI command group: mcp-servers
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
from mcpgateway.schemas import GatewayCreate, GatewayUpdate


def mcp_servers_list(
    active_only: bool = typer.Option(False, "--active-only", help="Show only active MCP servers"),
    json_output: bool = typer.Option(False, "--json", help="Output as JSON"),
) -> None:
    """List all MCP server peers."""
    console = get_console()

    try:
        result = make_authenticated_request("GET", "/gateways", params={"include_inactive": not active_only})

        if json_output:
            print_json(result, "MCP Servers")
        else:
            gateways = result if isinstance(result, list) else [result]
            if gateways:
                print_table(gateways, "MCP Servers", ["id", "name", "url", "description", "enabled"])
            else:
                console.print("[yellow]No MCP servers found[/yellow]")

    except Exception as e:
        handle_exception(e)


def mcp_servers_get(
    mcp_server_id: str = typer.Argument(..., help="MCP Server ID"),
) -> None:
    """Get details of a specific MCP server."""
    try:
        result = make_authenticated_request("GET", f"/gateways/{mcp_server_id}")
        print_json(result, f"MCP Server {mcp_server_id}")

    except Exception as e:
        handle_exception(e)


def mcp_servers_create(
    data_file: Optional[Path] = typer.Argument(None, help="JSON file containing gateway data (interactive mode if not provided)"),
    name: Optional[str] = typer.Option(None, "--name", help="Gateway name"),
    url: Optional[str] = typer.Option(None, "--url", help="Gateway endpoint URL"),
    description: Optional[str] = typer.Option(None, "--description", help="Gateway description"),
) -> None:
    """Register a new MCP server peer.

    Can be used in three ways:
    1. Provide a JSON file: cforge mcp-servers create data.json
    2. Provide partial data via options: cforge mcp-servers create --name myserver --url http://example.com
    3. Use interactive mode: cforge mcp-servers create
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
            # File-based mode
            if not data_file.exists():
                console.print(f"[red]File not found: {data_file}[/red]")
                raise typer.Exit(1)

            data = json.loads(data_file.read_text())
            # Merge prefilled values (command-line options override file)
            data.update(prefilled)
        else:
            # Interactive mode
            data = prompt_for_schema(GatewayCreate, prefilled=prefilled if prefilled else None)

        result = make_authenticated_request("POST", "/gateways", json_data=data)

        console.print("[green]✓ MCP server registered successfully![/green]")
        print_json(result, "Registered MCP Server")

    except Exception as e:
        handle_exception(e)


def mcp_servers_update(
    mcp_server_id: str = typer.Argument(..., help="MCP Server ID"),
    data_file: Optional[Path] = typer.Argument(None, help="JSON file containing updated gateway data (interactive mode if not provided)"),
) -> None:
    """Update an existing MCP server."""
    console = get_console()

    try:
        if data_file:
            if not data_file.exists():
                console.print(f"[red]File not found: {data_file}[/red]")
                raise typer.Exit(1)
            data = json.loads(data_file.read_text())
        else:
            data = prompt_for_schema(GatewayUpdate)

        result = make_authenticated_request("PUT", f"/gateways/{mcp_server_id}", json_data=data)

        console.print("[green]✓ MCP server updated successfully![/green]")
        print_json(result, "Updated MCP Server")

    except Exception as e:
        handle_exception(e)


def mcp_servers_delete(
    mcp_server_id: str = typer.Argument(..., help="MCP Server ID"),
    confirm: bool = typer.Option(False, "--yes", "-y", help="Skip confirmation"),
) -> None:
    """Delete an MCP server."""
    console = get_console()

    try:
        if not confirm:
            confirmed = typer.confirm(f"Are you sure you want to delete MCP server {mcp_server_id}?")
            if not confirmed:
                console.print("[yellow]Cancelled[/yellow]")
                raise typer.Exit(0)

        make_authenticated_request("DELETE", f"/gateways/{mcp_server_id}")
        console.print(f"[green]✓ MCP server {mcp_server_id} deleted successfully![/green]")

    except Exception as e:
        handle_exception(e)


def mcp_servers_toggle(
    mcp_server_id: str = typer.Argument(..., help="MCP Server ID"),
) -> None:
    """Toggle MCP server active status."""
    console = get_console()

    try:
        current_status = make_authenticated_request("GET", f"/gateways/{mcp_server_id}")
        assert isinstance(current_status, dict)
        if current_status["enabled"]:
            activate = False
        else:
            activate = True
        result = make_authenticated_request("POST", f"/gateways/{mcp_server_id}/toggle", params={"activate": activate})
        assert isinstance(result, dict)
        assert result["gateway"]["enabled"] == activate, "Failed to toggle MCP server"
        console.print("[green]✓ MCP server toggled successfully![/green]")
        print_json(result, "MCP Server Status")

    except Exception as e:
        handle_exception(e)
