# -*- coding: utf-8 -*-
"""Location: ./cforge/commands/resources/plugins.py
Copyright 2025
SPDX-License-Identifier: Apache-2.0
Authors: Matthew Grigsby

CLI command group: plugins
"""

# Standard
from typing import Any, Dict, Optional

# Third-Party
import typer

# First-Party
from cforge.common import (
    AuthenticationError,
    CLIError,
    get_console,
    handle_exception,
    make_authenticated_request,
    print_json,
    print_table,
)


def _handle_plugins_exception(exception: Exception) -> None:
    """Provide plugin-specific hints and raise a CLI error."""
    console = get_console()

    if isinstance(exception, AuthenticationError):
        console.print("[yellow]Access denied. Requires admin.plugins permission.[/yellow]")
    elif isinstance(exception, CLIError) and "(404)" in str(exception):
        console.print("[yellow]Admin plugin API unavailable. Ensure MCPGATEWAY_ADMIN_API_ENABLED=true and gateway version supports /admin/plugins.[/yellow]")

    handle_exception(exception)


def plugins_list(
    search: Optional[str] = typer.Option(None, "--search", help="Search by plugin name, description, or author"),
    mode: Optional[str] = typer.Option(None, "--mode", help="Filter by mode (enforce, permissive, disabled)"),
    hook: Optional[str] = typer.Option(None, "--hook", help="Filter by hook type"),
    tag: Optional[str] = typer.Option(None, "--tag", help="Filter by plugin tag"),
    json_output: bool = typer.Option(False, "--json", help="Output as JSON"),
) -> None:
    """List all plugins with optional filtering."""
    console = get_console()

    try:
        params: Dict[str, Any] = {}
        if search:
            params["search"] = search
        if mode:
            params["mode"] = mode
        if hook:
            params["hook"] = hook
        if tag:
            params["tag"] = tag

        result = make_authenticated_request("GET", "/admin/plugins", params=params if params else None)

        if json_output:
            print_json(result, "Plugins")
        else:
            plugins: list[dict[str, Any]] = []
            if isinstance(result, dict):
                if "plugins" in result:
                    raw_plugins = result.get("plugins", [])
                    if isinstance(raw_plugins, list):
                        plugins = raw_plugins
                    elif isinstance(raw_plugins, dict):
                        plugins = [raw_plugins]
                else:
                    plugins = [result]
            elif isinstance(result, list):
                plugins = result

            if plugins:
                print_table(plugins, "Plugins", ["name", "version", "author", "mode", "status", "priority", "hooks", "tags"])
            else:
                console.print("[yellow]No plugins found[/yellow]")

    except Exception as e:
        _handle_plugins_exception(e)


def plugins_get(
    name: str = typer.Argument(..., help="Plugin name"),
) -> None:
    """Get details for a specific plugin."""
    try:
        result = make_authenticated_request("GET", f"/admin/plugins/{name}")
        print_json(result, f"Plugin {name}")

    except Exception as e:
        _handle_plugins_exception(e)


def plugins_stats() -> None:
    """Get plugin statistics."""
    try:
        result = make_authenticated_request("GET", "/admin/plugins/stats")
        print_json(result, "Plugin Statistics")

    except Exception as e:
        _handle_plugins_exception(e)
