# -*- coding: utf-8 -*-
"""
SPDX-License-Identifier: Apache-2.0

Console and CLI application factories.

This module centralizes creation of the shared Rich console and Typer app.
Both are cached so commands across the process use consistent output and app
configuration without repeated construction.
"""

# Standard
from functools import lru_cache

# Third-Party
from rich.console import Console

import typer


@lru_cache
def get_console() -> Console:
    """Get the console singleton."""
    return Console()


@lru_cache
def get_app() -> typer.Typer:
    """Get the typer singleton."""
    return typer.Typer(
        name="mcpgateway",
        help="MCP Gateway - Production-grade MCP Gateway & Proxy CLI",
        add_completion=True,
        rich_markup_mode="rich",
    )
