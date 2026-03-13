# -*- coding: utf-8 -*-
"""
SPDX-License-Identifier: Apache-2.0

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
from typing import Any, Dict, Optional

# Third-Party
import typer

# Local
from cforge.common.console import get_console
from cforge.common.errors import AuthenticationError, CaseInsensitiveEnum, CLIError, handle_exception
from cforge.common.http import make_authenticated_request
from cforge.common.render import print_json, print_table


class PluginMode(CaseInsensitiveEnum):
    """Valid plugin mode filters supported by the gateway admin API."""

    ENFORCE = "enforce"
    PERMISSIVE = "permissive"
    DISABLED = "disabled"


def _parse_plugin_mode(mode: Optional[str]) -> Optional[PluginMode]:
    """Parse plugin mode with case-insensitive enum matching."""
    if mode is None:
        return None
    try:
        return PluginMode(mode)
    except ValueError as exc:
        choices = ", ".join(member.value for member in PluginMode)
        raise CLIError(f"Invalid value for '--mode': {mode!r}. Must be one of: {choices}.") from exc


def _handle_plugins_exception(exception: Exception, operation: str, plugin_name: Optional[str] = None) -> None:
    """Provide plugin-specific hints and raise a CLI error."""
    console = get_console()

    if isinstance(exception, AuthenticationError):
        console.print("[yellow]Access denied. Requires admin.plugins permission.[/yellow]")
    elif isinstance(exception, CLIError):
        error_str = str(exception)
        if "(404)" in error_str:
            error_str_folded = error_str.casefold()
            if operation == "get" and "plugin" in error_str_folded and "not found" in error_str_folded:
                plugin_label = plugin_name or "requested plugin"
                console.print(f"[yellow]Plugin not found: {plugin_label}[/yellow]")
            else:
                console.print("[yellow]Admin plugin API unavailable. Ensure MCPGATEWAY_ADMIN_API_ENABLED=true and gateway version supports /admin/plugins.[/yellow]")

    handle_exception(exception)


def plugins_list(
    search: Optional[str] = typer.Option(None, "--search", help="Search by plugin name, description, or author"),
    mode: Optional[str] = typer.Option(None, "--mode", help="Filter by mode"),
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
        parsed_mode = _parse_plugin_mode(mode)
        if parsed_mode:
            params["mode"] = parsed_mode.value
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
        _handle_plugins_exception(e, operation="list")


def plugins_get(
    name: str = typer.Argument(..., help="Plugin name"),
) -> None:
    """Get details for a specific plugin."""
    try:
        result = make_authenticated_request("GET", f"/admin/plugins/{name}")
        print_json(result, f"Plugin {name}")

    except Exception as e:
        _handle_plugins_exception(e, operation="get", plugin_name=name)


def plugins_stats() -> None:
    """Get plugin statistics."""
    try:
        result = make_authenticated_request("GET", "/admin/plugins/stats")
        print_json(result, "Plugin Statistics")

    except Exception as e:
        _handle_plugins_exception(e, operation="stats")
