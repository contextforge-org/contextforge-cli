# -*- coding: utf-8 -*-
"""Location: ./cforge/commands/settings/logout.py
Copyright 2025
SPDX-License-Identifier: Apache-2.0
Authors: Gabe Goodhart

CLI command: logout
"""

# First-Party
from cforge.common.console import get_console
from cforge.common.http import get_token_file


def logout() -> None:
    """Remove stored authentication token.

    This command removes the token saved in ~/.contextforge/token.
    """
    console = get_console()
    token_file = get_token_file()
    if token_file.exists():
        token_file.unlink()
        console.print(f"[green]✓ Token removed from {token_file}[/green]")
        console.print("[cyan]You will need to login again to use authenticated commands.[/cyan]")
    else:
        console.print("[yellow]No stored token found.[/yellow]")
