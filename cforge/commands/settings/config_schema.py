# -*- coding: utf-8 -*-
"""Location: ./cforge/commands/settings/config_schema.py
Copyright 2025
SPDX-License-Identifier: Apache-2.0
Authors: Gabe Goodhart

CLI command: config-schema
"""

# Standard
from pathlib import Path
from typing import Optional
import json

# Third-Party
import typer

# Local
from cforge.common.console import get_console
from cforge.common.render import print_json
from cforge.config import get_settings


def config_schema(
    output: Optional[Path] = typer.Option(None, "--output", "-o", help="Output file path (prints to stdout if not specified)"),
) -> None:
    """Export the JSON schema for MCP Gateway Settings."""
    console = get_console()
    schema = type(get_settings(True)).model_json_schema(mode="validation")
    data = json.dumps(schema, indent=2, sort_keys=True)

    if output:
        output.write_text(data, encoding="utf-8")
        console.print(f"[green]✓ Schema written to {output}[/green]")
    else:
        print_json(schema, "Configuration Schema")
