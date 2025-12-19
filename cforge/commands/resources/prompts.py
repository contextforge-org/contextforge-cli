# -*- coding: utf-8 -*-
"""Location: ./cforge/commands/resources/prompts.py
Copyright 2025
SPDX-License-Identifier: Apache-2.0
Authors: Gabe Goodhart

CLI command group: prompts
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
from mcpgateway.schemas import PromptCreate, PromptUpdate


def prompts_list(
    mcp_server_id: Optional[str] = typer.Option(None, "--mcp-server-id", "-m", help="Filter by MCP Server ID"),
    active_only: bool = typer.Option(False, "--active-only", help="Show only active prompts"),
    json_output: bool = typer.Option(False, "--json", help="Output as JSON"),
) -> None:
    """List all prompts in the gateway."""
    console = get_console()

    try:
        params: Dict[str, Any] = {"include_inactive": not active_only}
        if mcp_server_id:
            params["gateway_id"] = mcp_server_id

        result = make_authenticated_request("GET", "/prompts", params=params)

        if json_output:
            print_json(result, "Prompts")
        else:
            prompts = result if isinstance(result, list) else [result]
            if prompts:
                print_table(
                    prompts,
                    "Prompts",
                    ["id", "name", "description", "arguments", "enabled"],
                )
            else:
                console.print("[yellow]No prompts found[/yellow]")

    except Exception as e:
        handle_exception(e)


def prompts_get(
    prompt_id: str = typer.Argument(..., help="Prompt ID"),
) -> None:
    """Get details of a specific prompt."""
    try:
        result = make_authenticated_request("GET", f"/prompts/{prompt_id}")
        print_json(result, f"Prompt {prompt_id}")

    except Exception as e:
        handle_exception(e)


def prompts_create(
    data_file: Optional[Path] = typer.Argument(None, help="JSON file containing prompt data (interactive mode if not provided)"),
    name: Optional[str] = typer.Option(None, "--name", help="Prompt name"),
    description: Optional[str] = typer.Option(None, "--description", help="Prompt description"),
) -> None:
    """Create a new prompt.

    Can be used in three ways:
    1. Provide a JSON file: cforge prompts create data.json
    2. Provide partial data via options: cforge prompts create --name myprompt --description "My prompt"
    3. Use interactive mode: cforge prompts create
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
            data = prompt_for_schema(PromptCreate, prefilled=prefilled if prefilled else None)

        result = make_authenticated_request("POST", "/prompts", json_data={"prompt": data})

        console.print("[green]✓ Prompt created successfully![/green]")
        print_json(result, "Created Prompt")

    except Exception as e:
        handle_exception(e)


def prompts_update(
    prompt_id: str = typer.Argument(..., help="Prompt ID"),
    data_file: Optional[Path] = typer.Argument(None, help="JSON file containing updated prompt data (interactive mode if not provided)"),
) -> None:
    """Update an existing prompt."""
    console = get_console()

    try:
        if data_file:
            if not data_file.exists():
                console.print(f"[red]File not found: {data_file}[/red]")
                raise typer.Exit(1)
            data = json.loads(data_file.read_text())
        else:
            data = prompt_for_schema(PromptUpdate)

        result = make_authenticated_request("PUT", f"/prompts/{prompt_id}", json_data=data)

        console.print("[green]✓ Prompt updated successfully![/green]")
        print_json(result, "Updated Prompt")

    except Exception as e:
        handle_exception(e)


def prompts_delete(
    prompt_id: str = typer.Argument(..., help="Prompt ID"),
    confirm: bool = typer.Option(False, "--yes", "-y", help="Skip confirmation"),
) -> None:
    """Delete a prompt."""
    console = get_console()

    try:
        if not confirm:
            confirmed = typer.confirm(f"Are you sure you want to delete prompt {prompt_id}?")
            if not confirmed:
                console.print("[yellow]Cancelled[/yellow]")
                raise typer.Exit(0)

        make_authenticated_request("DELETE", f"/prompts/{prompt_id}")
        console.print(f"[green]✓ Prompt {prompt_id} deleted successfully![/green]")

    except Exception as e:
        handle_exception(e)


def prompts_toggle(
    prompt_id: str = typer.Argument(..., help="Prompt ID"),
) -> None:
    """Toggle prompt active status."""
    console = get_console()

    try:
        current_status = make_authenticated_request("GET", "/prompts", params={"include_inactive": True})
        assert isinstance(current_status, list)
        this_status = [res for res in current_status if res.get("id") == prompt_id]
        if not this_status:
            console.print(f"[red]Prompt not found: {prompt_id}[/red]")
            raise typer.Exit(1)
        assert len(this_status) == 1, "Multiple prompts with same ID found"
        assert isinstance(this_status[0], dict)
        activate = not this_status[0].get("enabled")
        result = make_authenticated_request("POST", f"/prompts/{prompt_id}/toggle", params={"activate": activate})
        console.print("[green]✓ Prompt toggled successfully![/green]")
        print_json(result, "Prompt Status")

    except Exception as e:
        handle_exception(e)


def prompts_execute(
    prompt_id: str = typer.Argument(..., help="Prompt ID"),
    data_file: Optional[Path] = typer.Option(None, "--data", help="JSON file containing prompt arguments"),
) -> None:
    """Execute a prompt with optional arguments."""
    console = get_console()

    try:
        data: Dict[str, Any] = {}
        if data_file:
            if not data_file.exists():
                console.print(f"[red]File not found: {data_file}[/red]")
                raise typer.Exit(1)
            data = json.loads(data_file.read_text())

        result = make_authenticated_request("POST", f"/prompts/{prompt_id}", json_data=data)
        console.print("[green]✓ Prompt executed successfully![/green]")
        print_json(result, "Prompt Result")

    except Exception as e:
        handle_exception(e)
