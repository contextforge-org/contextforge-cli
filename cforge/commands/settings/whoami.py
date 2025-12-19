# -*- coding: utf-8 -*-
"""Location: ./cforge/commands/settings/whoami.py
Copyright 2025
SPDX-License-Identifier: Apache-2.0
Authors: Gabe Goodhart

CLI command: whoami
"""

# First-Party
from cforge.common import get_console, get_settings, get_token_file, load_token
from cforge.profile_utils import get_active_profile


def whoami() -> None:
    """Show current authentication status and token source.

    Displays where the authentication token is coming from (if any) and
    information about the active profile if one is set.
    """

    console = get_console()
    settings = get_settings()
    env_token = settings.mcpgateway_bearer_token
    stored_token = load_token()
    active_profile = get_active_profile()

    # Display active profile information
    console.print("[bold cyan]Active Profile:[/bold cyan]")
    console.print(f"  [cyan]Name:[/cyan] {active_profile.name}")
    console.print(f"  [cyan]ID:[/cyan] {active_profile.id}")
    console.print(f"  [cyan]Email:[/cyan] {active_profile.email}")
    console.print(f"  [cyan]API URL:[/cyan] {active_profile.api_url}")
    if active_profile.metadata and active_profile.metadata.environment:
        console.print(f"  [cyan]Environment:[/cyan] {active_profile.metadata.environment}")
    console.print()

    # Display authentication status
    if env_token:
        console.print("[green]✓ Authenticated via MCPGATEWAY_BEARER_TOKEN environment variable[/green]")
        console.print(f"[cyan]Token:[/cyan] {env_token[:10]}...")
    elif stored_token:
        token_file = get_token_file()
        console.print(f"[green]✓ Authenticated via stored token in {token_file}[/green]")
        console.print(f"[cyan]Token:[/cyan] {stored_token[:10]}...")
    else:
        console.print("[yellow]Not authenticated. Run 'cforge login' to authenticate.[/yellow]")
