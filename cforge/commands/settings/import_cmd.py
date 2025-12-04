# -*- coding: utf-8 -*-
"""Location: ./cforge/commands/settings/import_cmd.py
Copyright 2025
SPDX-License-Identifier: Apache-2.0
Authors: Gabe Goodhart

CLI command: import
"""

# Standard
import json
from pathlib import Path
from typing import Optional

# Third-Party
import typer

# First-Party
from cforge.common import get_console, make_authenticated_request


def import_cmd(
    input_file: Path = typer.Argument(..., help="Input file containing export data"),
    conflict_strategy: str = typer.Option("update", "--conflict-strategy", help="How to handle naming conflicts (skip, update, rename, fail)"),
    dry_run: bool = typer.Option(False, "--dry-run", help="Validate but don't make changes"),
    rekey_secret: Optional[str] = typer.Option(None, "--rekey-secret", help="New encryption secret for cross-environment imports"),
    include: Optional[str] = typer.Option(None, "--include", help="Selective import: entity_type:name1,name2;entity_type2:name3"),
    verbose: bool = typer.Option(False, "--verbose", "-v", help="Verbose output"),
) -> None:
    """Import gateway configuration from a JSON file."""
    console = get_console()

    try:
        if not input_file.exists():
            console.print(f"[red]Input file not found: {input_file}[/red]")
            raise typer.Exit(1)

        console.print(f"[cyan]Importing configuration from {input_file}[/cyan]")

        # Load import data
        with open(input_file, "r", encoding="utf-8") as f:
            import_data = json.load(f)

        # Build request data
        request_data = {
            "import_data": import_data,
            "conflict_strategy": conflict_strategy,
            "dry_run": dry_run,
        }

        if rekey_secret:
            request_data["rekey_secret"] = rekey_secret

        if include:
            # Parse include parameter: "tool:tool1,tool2;server:server1"
            selected_entities = {}
            for selection in include.split(";"):
                if ":" in selection:
                    entity_type, entity_list = selection.split(":", 1)
                    entities = [e.strip() for e in entity_list.split(",") if e.strip()]
                    selected_entities[entity_type] = entities
            request_data["selected_entities"] = selected_entities

        # Make import request
        result = make_authenticated_request("POST", "/import", json_data=request_data)

        # Print results
        status = result.get("status", "unknown")
        progress = result.get("progress", {})

        if dry_run:
            console.print("[cyan]Dry-run validation completed![/cyan]")
        else:
            console.print(f"[green]✓ Import {status}![/green]")

        console.print("[cyan]Results:[/cyan]")
        console.print(f"   • Total entities: {progress.get('total', 0)}")
        console.print(f"   • Processed: {progress.get('processed', 0)}")
        console.print(f"   • Created: {progress.get('created', 0)}")
        console.print(f"   • Updated: {progress.get('updated', 0)}")
        console.print(f"   • Skipped: {progress.get('skipped', 0)}")
        console.print(f"   • Failed: {progress.get('failed', 0)}")

        # Show warnings if any
        warnings = result.get("warnings", [])
        if warnings:
            console.print(f"\n[yellow]Warnings ({len(warnings)}):[/yellow]")
            for warning in warnings[:5]:
                console.print(f"   • {warning}")
            if len(warnings) > 5:
                console.print(f"   • ... and {len(warnings) - 5} more warnings")

        # Show errors if any
        errors = result.get("errors", [])
        if errors:
            console.print(f"\n[red]Errors ({len(errors)}):[/red]")
            for error in errors[:5]:
                console.print(f"   • {error}")
            if len(errors) > 5:
                console.print(f"   • ... and {len(errors) - 5} more errors")

        if verbose:
            console.print("\n[cyan]Import details:[/cyan]")
            console.print(f"   • Import ID: {result.get('import_id')}")
            console.print(f"   • Started at: {result.get('started_at')}")
            console.print(f"   • Completed at: {result.get('completed_at')}")

        # Exit with error code if there were failures
        if progress.get("failed", 0) > 0:
            raise typer.Exit(1)

    except Exception as e:
        console.print(f"[red]Error: {str(e)}[/red]")
        raise typer.Exit(1)
