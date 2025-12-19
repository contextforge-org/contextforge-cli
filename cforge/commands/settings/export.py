# -*- coding: utf-8 -*-
"""Location: ./cforge/commands/settings/export.py
Copyright 2025
SPDX-License-Identifier: Apache-2.0
Authors: Gabe Goodhart

CLI command: export
"""

# Standard
from datetime import datetime
import json
from pathlib import Path
from typing import Any, Dict, Optional

# Third-Party
import typer

# First-Party
from cforge.common import get_base_url, get_console, make_authenticated_request


def export(
    output: Optional[Path] = typer.Option(None, "--output", "-o", help="Output file path (default: cforge-export-YYYYMMDD-HHMMSS.json)"),
    types: Optional[str] = typer.Option(None, "--types", help="Comma-separated entity types to include"),
    exclude_types: Optional[str] = typer.Option(None, "--exclude-types", help="Comma-separated entity types to exclude"),
    tags: Optional[str] = typer.Option(None, "--tags", help="Comma-separated tags to filter by"),
    include_inactive: bool = typer.Option(False, "--include-inactive", help="Include inactive entities"),
    no_dependencies: bool = typer.Option(False, "--no-dependencies", help="Don't include dependent entities"),
    verbose: bool = typer.Option(False, "--verbose", "-v", help="Verbose output"),
) -> None:
    """Export gateway configuration to a JSON file."""
    console = get_console()

    try:
        console.print(f"[cyan]Exporting configuration from gateway at {get_base_url()}[/cyan]")

        # Build API parameters
        params: Dict[str, Any] = {}
        if types:
            params["types"] = types
        if exclude_types:
            params["exclude_types"] = exclude_types
        if tags:
            params["tags"] = tags
        if include_inactive:
            params["include_inactive"] = "true"
        if no_dependencies:
            params["include_dependencies"] = "false"

        # Make export request
        export_data = make_authenticated_request("GET", "/export", params=params)

        # Determine output file
        if output:
            output_file = output
        else:
            timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
            output_file = Path(f"cforge-export-{timestamp}.json")

        # Write export data
        output_file.parent.mkdir(parents=True, exist_ok=True)
        with open(output_file, "w", encoding="utf-8") as f:
            json.dump(export_data, f, indent=2, ensure_ascii=False)

        # Print summary
        metadata = export_data.get("metadata", {})
        entity_counts = metadata.get("entity_counts", {})
        total_entities = sum(entity_counts.values())

        console.print("[green]✓ Export completed successfully![/green]")
        console.print(f"[cyan]Output file:[/cyan] {output_file}")
        console.print(f"[cyan]Exported {total_entities} total entities:[/cyan]")
        for entity_type, count in entity_counts.items():
            if count > 0:
                console.print(f"   • {entity_type}: {count}")

        if verbose:
            console.print("\n[cyan]Export details:[/cyan]")
            console.print(f"   • Version: {export_data.get('version')}")
            console.print(f"   • Exported at: {export_data.get('exported_at')}")
            console.print(f"   • Exported by: {export_data.get('exported_by')}")
            console.print(f"   • Source: {export_data.get('source_gateway')}")

    except Exception as e:
        console.print(f"[red]Error: {str(e)}[/red]")
        raise typer.Exit(1)
