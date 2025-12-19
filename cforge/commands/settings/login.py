# -*- coding: utf-8 -*-
"""Location: ./cforge/commands/settings/login.py
Copyright 2025
SPDX-License-Identifier: Apache-2.0
Authors: Gabe Goodhart

CLI command: login
"""

# Third-Party
import requests
import typer

# First-Party
from cforge.common import get_base_url, get_console, get_token_file, save_token


def login(
    email: str = typer.Option(..., "--email", "-e", prompt=True, help="Email for authentication"),
    password: str = typer.Option(..., "--password", "-p", prompt=True, hide_input=True, help="Password for authentication"),
    save: bool = typer.Option(True, "--save/--no-save", help="Save token to contextforge_home for future use"),
) -> None:
    """Authenticate with the MCP Gateway and obtain a token.

    The token will be saved to ~/.contextforge/token and automatically used for subsequent CLI operations.
    """
    console = get_console()

    try:
        # Make login request
        gateway_url = get_base_url()
        full_url = f"{gateway_url}/auth/login"

        response = requests.post(full_url, json={"email": email, "password": password})
        if response.status_code >= 400:
            error_text = response.text
            console.print(f"[red]Login failed ({response.status_code}): {error_text}[/red]")
            raise typer.Exit(1)

        result = response.json()
        token: str | None = result.get("access_token")

        if not token:
            console.print("[red]No token received from server[/red]")
            raise typer.Exit(1)

        console.print("[green]✓ Login successful![/green]")

        if save:
            # Save to contextforge_home/token file
            save_token(token)
            token_file = get_token_file()
            console.print(f"[green]✓ Token saved to {token_file}[/green]")
            console.print("[cyan]The token will be automatically used for future CLI commands.[/cyan]")
        else:
            console.print(f"[cyan]Token:[/cyan] {token}")
            console.print("[yellow]Token not saved. Set MCPGATEWAY_BEARER_TOKEN to use it:[/yellow]")
            console.print(f"[yellow]export MCPGATEWAY_BEARER_TOKEN={token}[/yellow]")

    except requests.ConnectionError as e:
        console.print(f"[red]Failed to connect: {str(e)}[/red]")
        raise typer.Exit(1)
