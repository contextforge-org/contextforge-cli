# -*- coding: utf-8 -*-
"""Location: ./cforge/commands/server/serve.py
Copyright 2025
SPDX-License-Identifier: Apache-2.0
Authors: Gabe Goodhart

CLI command: serve
"""

# Standard
import os

# Third-Party
import typer
import uvicorn

# First-Party
from cforge.config import get_settings, set_serve_settings

# ---------------------------------------------------------------------------
# Configuration defaults
# ---------------------------------------------------------------------------
settings = get_settings()

DEFAULT_APP = "mcpgateway.main:app"
DEFAULT_HOST = os.getenv("MCG_HOST", settings.host)
DEFAULT_PORT = int(os.getenv("MCG_PORT", settings.port))


def serve(
    host: str = typer.Option(DEFAULT_HOST, "--host", help="Host to bind to"),
    port: int = typer.Option(DEFAULT_PORT, "--port", help="Port to bind to"),
    reload: bool = typer.Option(False, "--reload", help="Enable auto-reload for development"),
    headless: bool = typer.Option(False, "--headless", help="Run without the admin UI"),
    workers: int = typer.Option(1, "--workers", help="Number of worker processes"),
    log_level: str = typer.Option("info", "--log-level", help="Log level (debug, info, warning, error, critical)"),
) -> None:
    """Start the MCP Gateway server using Uvicorn.

    This is the main server command that runs the FastAPI application.
    """
    set_serve_settings(
        mcpgateway_ui_enabled=not headless,
        mcpgateway_admin_api_enabled=not headless,
    )
    uvicorn.run(
        DEFAULT_APP,
        host=host,
        port=port,
        reload=reload,
        workers=workers,
        log_level=log_level,
    )
