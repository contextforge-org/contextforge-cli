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

# ---------------------------------------------------------------------------
# Configuration defaults
# ---------------------------------------------------------------------------
DEFAULT_APP = "mcpgateway.main:app"
DEFAULT_HOST = os.getenv("MCG_HOST", "127.0.0.1")
DEFAULT_PORT = int(os.getenv("MCG_PORT", "4444"))


def serve(
    host: str = typer.Option(DEFAULT_HOST, "--host", help="Host to bind to"),
    port: int = typer.Option(DEFAULT_PORT, "--port", help="Port to bind to"),
    reload: bool = typer.Option(False, "--reload", help="Enable auto-reload for development"),
    workers: int = typer.Option(1, "--workers", help="Number of worker processes"),
    log_level: str = typer.Option("info", "--log-level", help="Log level (debug, info, warning, error, critical)"),
) -> None:
    """Start the MCP Gateway server using Uvicorn.

    This is the main server command that runs the FastAPI application.
    """
    uvicorn.run(
        DEFAULT_APP,
        host=host,
        port=port,
        reload=reload,
        workers=workers,
        log_level=log_level,
    )
