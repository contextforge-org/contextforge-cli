# -*- coding: utf-8 -*-
"""Location: ./cforge/commands/tools/tools.py
Copyright 2025
SPDX-License-Identifier: Apache-2.0
Authors: Gabe Goodhart

CLI command group: tools
"""

# Standard
import json
from pathlib import Path
from typing import Any, Dict, Optional

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
from mcpgateway.schemas import ToolCreate, ToolUpdate


def tools_list(
    mcp_server_id: Optional[str] = typer.Option(None, "--mcp-server-id", "-m", help="Filter by MCP Server ID"),
    active_only: bool = typer.Option(False, "--active-only", help="Show only active tools"),
    json_output: bool = typer.Option(False, "--json", help="Output as JSON"),
) -> None:
    """List all tools in the gateway."""
    console = get_console()

    try:
        params: Dict[str, Any] = {"include_inactive": not active_only}
        if mcp_server_id:
            params["gateway_id"] = mcp_server_id

        result = make_authenticated_request("GET", "/tools", params=params)

        if json_output:
            print_json(result, "Tools")
        else:
            tools = result if isinstance(result, list) else [result]
            if tools:
                print_table(
                    tools,
                    "Tools",
                    ["id", "name", "description", "gatewayId", "enabled"],
                    {"gatewayId": "mcp_server_id"},
                )
            else:
                console.print("[yellow]No tools found[/yellow]")

    except Exception as e:
        handle_exception(e)


def tools_get(
    tool_id: str = typer.Argument(..., help="Tool ID"),
    json_output: bool = typer.Option(False, "--json", help="Output as JSON"),
) -> None:
    """Get details of a specific tool."""
    try:
        result = make_authenticated_request("GET", f"/tools/{tool_id}")
        print_json(result, f"Tool {tool_id}")

    except Exception as e:
        handle_exception(e)


def tools_create(
    data_file: Optional[Path] = typer.Argument(None, help="JSON file containing tool data (interactive mode if not provided)"),
    name: Optional[str] = typer.Option(None, "--name", help="Tool name"),
    description: Optional[str] = typer.Option(None, "--description", help="Tool description"),
) -> None:
    """Create a new tool.

    Can be used in three ways:
    1. Provide a JSON file: cforge tools create data.json
    2. Provide partial data via options: cforge tools create --name mytool --description "My tool"
    3. Use interactive mode: cforge tools create
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
            data = prompt_for_schema(ToolCreate, prefilled=prefilled if prefilled else None)

        result = make_authenticated_request("POST", "/tools", json_data={"tool": data})

        console.print("[green]✓ Tool created successfully![/green]")
        print_json(result, "Created Tool")

    except Exception as e:
        handle_exception(e)


def tools_update(
    tool_id: str = typer.Argument(..., help="Tool ID"),
    data_file: Optional[Path] = typer.Argument(None, help="JSON file containing updated tool data"),
) -> None:
    """Update an existing tool."""
    console = get_console()

    try:
        if data_file:
            if not data_file.exists():
                console.print(f"[red]File not found: {data_file}[/red]")
                raise typer.Exit(1)
            data = json.loads(data_file.read_text())
        else:
            data = prompt_for_schema(ToolUpdate)

        result = make_authenticated_request("PUT", f"/tools/{tool_id}", json_data=data)

        console.print("[green]✓ Tool updated successfully![/green]")
        print_json(result, "Updated Tool")

    except Exception as e:
        handle_exception(e)


def tools_delete(
    tool_id: str = typer.Argument(..., help="Tool ID"),
    confirm: bool = typer.Option(False, "--yes", "-y", help="Skip confirmation"),
) -> None:
    """Delete a tool."""
    console = get_console()

    try:
        if not confirm:
            confirmed = typer.confirm(f"Are you sure you want to delete tool {tool_id}?")
            if not confirmed:
                console.print("[yellow]Cancelled[/yellow]")
                raise typer.Exit(0)

        make_authenticated_request("DELETE", f"/tools/{tool_id}")
        console.print(f"[green]✓ Tool {tool_id} deleted successfully![/green]")

    except Exception as e:
        handle_exception(e)


def tools_toggle(
    tool_id: str = typer.Argument(..., help="Tool ID"),
) -> None:
    """Toggle tool active status."""
    console = get_console()

    try:
        current_status = make_authenticated_request("GET", f"/tools/{tool_id}")
        assert isinstance(current_status, dict)
        if current_status["enabled"]:
            activate = False
        else:
            activate = True
        result = make_authenticated_request("POST", f"/tools/{tool_id}/toggle", params={"activate": activate})
        console.print("[green]✓ Tool toggled successfully![/green]")
        print_json(result, "Tool Status")

    except Exception as e:
        handle_exception(e)
