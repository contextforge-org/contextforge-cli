# -*- coding: utf-8 -*-
"""Location: ./cforge/commands/metrics/metrics.py
Copyright 2025
SPDX-License-Identifier: Apache-2.0
Authors: Gabe Goodhart

CLI command group: metrics
"""

# Third-Party
import typer

# First-Party
from cforge.common import (
    get_console,
    make_authenticated_request,
    print_json,
)


def metrics_get(
    json_output: bool = typer.Option(False, "--json", help="Output as JSON"),
) -> None:
    """Get current metrics."""
    console = get_console()

    try:
        result = make_authenticated_request("GET", "/metrics")

        if json_output:
            print_json(result, "Metrics")
        else:
            console.print("[cyan]Current Metrics:[/cyan]")
            print_json(result)

    except Exception as e:
        console.print(f"[red]Error: {str(e)}[/red]")
        raise typer.Exit(1)


def metrics_reset(
    confirm: bool = typer.Option(False, "--yes", "-y", help="Skip confirmation"),
) -> None:
    """Reset metrics counters."""
    console = get_console()

    try:
        if not confirm:
            confirmed = typer.confirm("Are you sure you want to reset all metrics?")
            if not confirmed:
                console.print("[yellow]Cancelled[/yellow]")
                raise typer.Exit(0)

        result = make_authenticated_request("POST", "/metrics/reset")
        console.print("[green]✓ Metrics reset successfully![/green]")
        print_json(result, "Reset Result")

    except Exception as e:
        console.print(f"[red]Error: {str(e)}[/red]")
        raise typer.Exit(1)
