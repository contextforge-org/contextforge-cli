# -*- coding: utf-8 -*-
"""Location: ./cforge/commands/settings/version.py
Copyright 2025
SPDX-License-Identifier: Apache-2.0
Authors: Gabe Goodhart

CLI command: version
"""

# First-Party
from cforge.common import get_console, make_authenticated_request
from mcpgateway import __version__


def version() -> None:
    """Display version information."""
    console = get_console()
    client_version = __version__
    server_version = "UNREACHABLE"
    try:
        server_version_response = make_authenticated_request("GET", "/version")
        server_version = server_version_response.get("app", {}).get("version", "unknown")
    except Exception as e:
        console.print(f"[yellow]Unable to reach server: {e}[/yellow]")

    console.print(f"[cyan]Client version:[/cyan] {client_version}")
    console.print(f"[cyan]Server version:[/cyan] {server_version}")
