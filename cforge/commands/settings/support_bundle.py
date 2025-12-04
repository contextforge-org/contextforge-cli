# -*- coding: utf-8 -*-
"""Location: ./cforge/commands/settings/support_bundle.py
Copyright 2025
SPDX-License-Identifier: Apache-2.0
Authors: Gabe Goodhart

CLI command: support-bundle
"""

# Standard
from pathlib import Path
from typing import Optional

# Third-Party
import typer

# First-Party
from cforge.common import get_console


def support_bundle(
    output_dir: Optional[Path] = typer.Option(None, "--output-dir", help="Output directory (default: /tmp)"),
    log_lines: int = typer.Option(1000, "--log-lines", help="Number of log lines to include (0 = all)"),
    no_logs: bool = typer.Option(False, "--no-logs", help="Exclude log files"),
    no_env: bool = typer.Option(False, "--no-env", help="Exclude environment config"),
    no_system: bool = typer.Option(False, "--no-system", help="Exclude system info"),
) -> None:
    """Generate a support bundle containing diagnostics and logs."""
    # First-Party
    from mcpgateway.services.support_bundle_service import SupportBundleConfig, SupportBundleService

    console = get_console()

    try:
        config = SupportBundleConfig(
            include_logs=not no_logs,
            include_env=not no_env,
            include_system_info=not no_system,
            log_tail_lines=log_lines,
            output_dir=output_dir if output_dir else None,
        )

        service = SupportBundleService()
        bundle_path = service.generate_bundle(config)

        console.print(f"[green]✓ Support bundle created: {bundle_path}[/green]")
        console.print(f"[cyan]Bundle size: {bundle_path.stat().st_size / 1024:.2f} KB[/cyan]")
        console.print()
        console.print("[yellow]Security Notice:[/yellow]")
        console.print("   The bundle has been sanitized, but please review before sharing.")
        console.print("   Sensitive data (passwords, tokens, secrets) have been redacted.")

    except Exception as exc:
        console.print(f"[red]Failed to create support bundle: {exc}[/red]")
        raise typer.Exit(1)
