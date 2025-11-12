# -*- coding: utf-8 -*-
"""Location: ./cforge/commands/settings/version.py
Copyright 2025
SPDX-License-Identifier: Apache-2.0
Authors: Gabe Goodhart

CLI command: version
"""

# First-Party
from cforge.common import get_console
from mcpgateway import __version__


def version() -> None:
    """Display version information."""
    console = get_console()
    console.print(f"[cyan]MCP Gateway version:[/cyan] {__version__}")
