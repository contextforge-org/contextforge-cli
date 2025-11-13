# -*- coding: utf-8 -*-
"""Location: ./cforge/commands/resources/resources.py
Copyright 2025
SPDX-License-Identifier: Apache-2.0
Authors: Gabe Goodhart

CLI command group: resources
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
    make_authenticated_request,
    print_json,
    print_table,
    prompt_for_schema,
)
from mcpgateway.schemas import ResourceCreate


def resources_list(
    gateway_id: Optional[str] = typer.Option(None, "--gateway-id", help="Filter by gateway ID"),
    json_output: bool = typer.Option(False, "--json", help="Output as JSON"),
) -> None:
    """List all resources in the gateway."""
    console = get_console()

    try:
        params: Dict[str, Any] = {}
        if gateway_id:
            params["gateway_id"] = gateway_id

        result = make_authenticated_request("GET", "/resources", params=params)

        if json_output:
            print_json(result, "Resources")
        else:
            resources = result if isinstance(result, list) else [result]
            if resources:
                print_table(resources, "Resources", ["id", "name", "uri", "description", "gateway_id", "is_active"])
            else:
                console.print("[yellow]No resources found[/yellow]")

    except Exception as e:
        console.print(f"[red]Error: {str(e)}[/red]")
        raise typer.Exit(1)


def resources_get(
    resource_id: int = typer.Argument(..., help="Resource ID"),
) -> None:
    """Get details of a specific resource."""
    console = get_console()

    try:
        result = make_authenticated_request("GET", f"/resources/{resource_id}")
        print_json(result, f"Resource {resource_id}")

    except Exception as e:
        console.print(f"[red]Error: {str(e)}[/red]")
        raise typer.Exit(1)


def resources_create(
    data_file: Optional[Path] = typer.Argument(None, help="JSON file containing resource data (interactive mode if not provided)"),
    name: Optional[str] = typer.Option(None, "--name", help="Resource name"),
    uri: Optional[str] = typer.Option(None, "--uri", help="Resource URI"),
    description: Optional[str] = typer.Option(None, "--description", help="Resource description"),
) -> None:
    """Create a new resource.

    Can be used in three ways:
    1. Provide a JSON file: cforge resources create data.json
    2. Provide partial data via options: cforge resources create --name myresource --uri file:///path
    3. Use interactive mode: cforge resources create
    """
    console = get_console()

    try:
        # Collect prefilled values from options
        prefilled = {}
        if name:
            prefilled["name"] = name
        if uri:
            prefilled["uri"] = uri
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
            data = prompt_for_schema(ResourceCreate, prefilled=prefilled if prefilled else None)

        result = make_authenticated_request("POST", "/resources", json_data=data)

        console.print("[green]✓ Resource created successfully![/green]")
        print_json(result, "Created Resource")

    except Exception as e:
        console.print(f"[red]Error: {str(e)}[/red]")
        raise typer.Exit(1)


def resources_update(
    resource_id: int = typer.Argument(..., help="Resource ID"),
    data_file: Path = typer.Argument(..., help="JSON file containing updated resource data"),
) -> None:
    """Update an existing resource."""
    console = get_console()

    try:
        if not data_file.exists():
            console.print(f"[red]File not found: {data_file}[/red]")
            raise typer.Exit(1)

        data = json.loads(data_file.read_text())
        result = make_authenticated_request("PUT", f"/resources/{resource_id}", json_data=data)

        console.print("[green]✓ Resource updated successfully![/green]")
        print_json(result, "Updated Resource")

    except Exception as e:
        console.print(f"[red]Error: {str(e)}[/red]")
        raise typer.Exit(1)


def resources_delete(
    resource_id: int = typer.Argument(..., help="Resource ID"),
    confirm: bool = typer.Option(False, "--yes", "-y", help="Skip confirmation"),
) -> None:
    """Delete a resource."""
    console = get_console()

    try:
        if not confirm:
            confirmed = typer.confirm(f"Are you sure you want to delete resource {resource_id}?")
            if not confirmed:
                console.print("[yellow]Cancelled[/yellow]")
                raise typer.Exit(0)

        make_authenticated_request("DELETE", f"/resources/{resource_id}")
        console.print(f"[green]✓ Resource {resource_id} deleted successfully![/green]")

    except Exception as e:
        console.print(f"[red]Error: {str(e)}[/red]")
        raise typer.Exit(1)


def resources_toggle(
    resource_id: int = typer.Argument(..., help="Resource ID"),
) -> None:
    """Toggle resource active status."""
    console = get_console()

    try:
        result = make_authenticated_request("POST", f"/resources/{resource_id}/toggle")
        console.print("[green]✓ Resource toggled successfully![/green]")
        print_json(result, "Resource Status")

    except Exception as e:
        console.print(f"[red]Error: {str(e)}[/red]")
        raise typer.Exit(1)


def resources_templates() -> None:
    """List available resource templates."""
    console = get_console()

    try:
        result = make_authenticated_request("GET", "/resources/templates/list")
        print_json(result, "Resource Templates")

    except Exception as e:
        console.print(f"[red]Error: {str(e)}[/red]")
        raise typer.Exit(1)


def resources_subscribe(
    resource_id: int = typer.Argument(..., help="Resource ID"),
) -> None:
    """Subscribe to resource updates."""
    console = get_console()

    try:
        result = make_authenticated_request("POST", f"/resources/subscribe/{resource_id}")
        console.print("[green]✓ Subscribed to resource updates![/green]")
        print_json(result, "Subscription")

    except Exception as e:
        console.print(f"[red]Error: {str(e)}[/red]")
        raise typer.Exit(1)
