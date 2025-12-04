# -*- coding: utf-8 -*-
"""Location: ./cforge/commands/settings/whoami.py
Copyright 2025
SPDX-License-Identifier: Apache-2.0
Authors: Gabe Goodhart

CLI command: whoami
"""

# First-Party
from cforge.common import get_console, get_settings, get_token_file, load_token


def whoami() -> None:
    """Show current authentication status and token source.

    Displays where the authentication token is coming from (if any).
    """
    console = get_console()
    settings = get_settings()
    env_token = settings.mcpgateway_bearer_token
    stored_token = load_token()

    if env_token:
        console.print("[green]✓ Authenticated via MCPGATEWAY_BEARER_TOKEN environment variable[/green]")
        console.print(f"[cyan]Token:[/cyan] {env_token[:10]}...")
    elif stored_token:
        token_file = get_token_file()
        console.print(f"[green]✓ Authenticated via stored token in {token_file}[/green]")
        console.print(f"[cyan]Token:[/cyan] {stored_token[:10]}...")
    else:
        console.print("[yellow]Not authenticated. Run 'cforge login' to authenticate.[/yellow]")
