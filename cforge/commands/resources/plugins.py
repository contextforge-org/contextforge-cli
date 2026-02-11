# -*- coding: utf-8 -*-
"""Location: ./cforge/commands/resources/plugins.py
Copyright 2025
SPDX-License-Identifier: Apache-2.0
Authors: Matthew Grigsby

CLI command group: plugins

Note:
    The CLI currently exposes read-only operations (list/get/stats) for plugins.
    This matches the current capabilities of the gateway admin API: plugin
    configuration is loaded from a YAML file at gateway startup, and the gateway
    does not yet provide write endpoints for plugin CRUD/management. When
    mcp-context-forge adds server-side write operations, this CLI can be extended
    to support them.
"""

# Standard
from enum import Enum
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


class _CaseInsensitiveEnum(str, Enum):
    """Enum that supports case-insensitive parsing for CLI options."""

    @classmethod
    def _missing_(cls, value: object) -> Optional["_CaseInsensitiveEnum"]:
        if not isinstance(value, str):
            return None
        value_folded = value.casefold()
        for member in cls:
            if member.value.casefold() == value_folded:
                return member
        return None


class PluginMode(_CaseInsensitiveEnum):
    """Valid plugin mode filters supported by the gateway admin API."""

    ENFORCE = "enforce"
    PERMISSIVE = "permissive"
    DISABLED = "disabled"


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
    mode: Optional[PluginMode] = typer.Option(None, "--mode", help="Filter by mode"),
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
            params["mode"] = mode.value
        if hook:
            params["hook"] = hook
        if tag:
            params["tag"] = tag

        result = make_authenticated_request("GET", "/admin/plugins", params=params if params else None)

        if json_output:
            print_json(result, "Plugins")
        else:
            plugins: list[dict[str, Any]] = result["plugins"]

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
