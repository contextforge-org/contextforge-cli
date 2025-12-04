# -*- coding: utf-8 -*-
"""Location: ./cforge/commands/deploy/whoami.py
Copyright 2025
SPDX-License-Identifier: Apache-2.0
Authors: Gabe Goodhart

CLI command: whoami
"""

# Third-Party
import typer

# First-Party
from cforge.common import get_console


def deploy() -> None:
    """Deploy MCP Gateway (placeholder for future deployment features)."""
    console = get_console()
    console.print("[yellow]Deploy command is not yet implemented.[/yellow]")
    console.print("This is a placeholder for future deployment automation features.")
    raise typer.Exit(0)
