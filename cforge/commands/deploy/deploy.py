# -*- coding: utf-8 -*-
"""
Location: ./cforge/commands/deploy/deploy.py
Copyright 2025
SPDX-License-Identifier: Apache-2.0
Authors: Teryl Taylor

MCP Stack Deployment Tool - Hybrid Dagger/Python Implementation

This script can run in two modes:
1. Plain Python mode (default) - No external dependencies
2. Dagger mode (opt-in) - Requires dagger-io package, auto-downloads CLI

Usage:
    # Local execution (plain Python mode)
    cforge deploy run deploy.yaml

    # Use Dagger mode for optimization (requires dagger-io, auto-downloads CLI)
    cforge --dagger deploy run deploy.yaml

Features:
    - Validates deploy.yaml configuration
    - Builds plugin containers from git repos
    - Generates mTLS certificates
    - Deploys to Kubernetes or Docker Compose
    - Integrates with CI/CD vault secrets
"""

# Standard
import asyncio
from pathlib import Path
from typing import Optional

# Third-Party
from rich.panel import Panel
import typer
from typing_extensions import Annotated

# First-Party
from cforge.commands.deploy.builder.factory import DeployFactory
from cforge.common import get_console, handle_exception
from cforge.config import get_settings


def shared_callback(
    ctx: typer.Context,
    dagger: Annotated[bool, typer.Option("--dagger", help="Use Dagger mode (requires dagger-io package)")] = False,
    verbose: Annotated[bool, typer.Option("--verbose", "-v", help="Verbose output")] = False,
):
    """MCP Stack deployment tool

    Deploys MCP Gateway + external plugins from a single YAML configuration.

    By default, uses plain Python mode. Use --dagger to enable Dagger optimization.

    Args:
        ctx: Typer context object
        dagger: Enable Dagger mode (requires dagger-io package and auto-downloads CLI)
        verbose: Enable verbose output
    """
    ctx.ensure_object(dict)
    ctx.obj["verbose"] = verbose
    ctx.obj["dagger"] = dagger

    # Show execution mode - default to Python, opt-in to Dagger
    mode = "dagger" if dagger else "python"
    ctx.obj["deployer"], ctx.obj["mode"] = DeployFactory.create_deployer(mode, verbose)
    mode_color = "green" if ctx.obj["mode"] == "dagger" else "yellow"
    env_text = "container" if get_settings().in_container else "local"

    if verbose:
        get_console().print(Panel(f"[bold]Mode:[/bold] [{mode_color}]{ctx.obj['mode']}[/{mode_color}]\n" f"[bold]Environment:[/bold] {env_text}\n", title="MCP Deploy", border_style=mode_color))


def validate(ctx: typer.Context, config_file: Annotated[Path, typer.Argument(help="The deployment configuration file.")]):
    """Validate mcp-stack.yaml configuration

    Args:
        ctx: Typer context object
        config_file: Path to the deployment configuration file
    """
    impl = ctx.obj["deployer"]

    try:
        impl.validate(config_file)
        get_console().print("[green]✓ Configuration valid[/green]")
    except Exception as e:
        handle_exception(e)


def build(
    ctx: typer.Context,
    config_file: Annotated[Path, typer.Argument(help="The deployment configuration file")],
    plugins_only: Annotated[bool, typer.Option("--plugins-only", help="Only build plugin containers")] = False,
    plugin: Annotated[Optional[list[str]], typer.Option("--plugin", "-p", help="Build specific plugin(s)")] = None,
    no_cache: Annotated[bool, typer.Option("--no-cache", help="Disable build cache")] = False,
    copy_env_templates: Annotated[bool, typer.Option("--copy-env-templates", help="Copy .env.template files from plugin repos")] = True,
):
    """Build containers

    Args:
        ctx: Typer context object
        config_file: Path to the deployment configuration file
        plugins_only: Only build plugin containers, skip gateway
        plugin: List of specific plugin names to build
        no_cache: Disable build cache
        copy_env_templates: Copy .env.template files from plugin repos
    """
    impl = ctx.obj["deployer"]

    try:
        asyncio.run(impl.build(config_file, plugins_only=plugins_only, specific_plugins=list(plugin) if plugin else None, no_cache=no_cache, copy_env_templates=copy_env_templates))
        get_console().print("[green]✓ Build complete[/green]")

        if copy_env_templates:
            get_console().print("[yellow]⚠ IMPORTANT: Review .env files in deploy/env/ before deploying![/yellow]")
            get_console().print("[yellow]   Update any required configuration values.[/yellow]")
    except Exception as e:
        handle_exception(e)


def certs(ctx: typer.Context, config_file: Annotated[Path, typer.Argument(help="The deployment configuration file")]):
    """Generate mTLS certificates

    Args:
        ctx: Typer context object
        config_file: Path to the deployment configuration file
    """
    impl = ctx.obj["deployer"]

    try:
        asyncio.run(impl.generate_certificates(config_file))
        get_console().print("[green]✓ Certificates generated[/green]")
    except Exception as e:
        handle_exception(e)


def deploy(
    ctx: typer.Context,
    config_file: Annotated[Path, typer.Argument(help="The deployment configuration file")],
    output_dir: Annotated[Optional[Path], typer.Option("--output-dir", "-o", help="The deployment configuration file")] = None,
    dry_run: Annotated[bool, typer.Option("--dry-run", help="Generate manifests without deploying")] = False,
    skip_build: Annotated[bool, typer.Option("--skip-build", help="Skip building containers")] = False,
    skip_certs: Annotated[bool, typer.Option("--skip-certs", help="Skip certificate generation")] = False,
):
    """Deploy MCP stack

    Args:
        ctx: Typer context object
        config_file: Path to the deployment configuration file
        output_dir: Custom output directory for manifests
        dry_run: Generate manifests without deploying
        skip_build: Skip building containers
        skip_certs: Skip certificate generation
    """
    impl = ctx.obj["deployer"]

    try:
        asyncio.run(impl.deploy(config_file, dry_run=dry_run, skip_build=skip_build, skip_certs=skip_certs, output_dir=output_dir))
        if dry_run:
            get_console().print("[yellow]✓ Dry-run complete (no changes made)[/yellow]")
        else:
            get_console().print("[green]✓ Deployment complete[/green]")
    except Exception as e:
        handle_exception(e)


def verify(
    ctx: typer.Context,
    config_file: Annotated[Path, typer.Argument(help="The deployment configuration file")],
    wait: Annotated[bool, typer.Option("--wait", help="Wait for deployment to be ready")] = True,
    timeout: Annotated[int, typer.Option("--timeout", help="Wait timeout in seconds")] = 300,
):
    """Verify deployment health

    Args:
        ctx: Typer context object
        config_file: Path to the deployment configuration file
        wait: Wait for deployment to be ready
        timeout: Wait timeout in seconds
    """
    impl = ctx.obj["deployer"]

    try:
        asyncio.run(impl.verify(config_file, wait=wait, timeout=timeout))
        get_console().print("[green]✓ Deployment healthy[/green]")
    except Exception as e:
        handle_exception(e)


def destroy(
    ctx: typer.Context,
    config_file: Annotated[Path, typer.Argument(help="The deployment configuration file")],
    force: Annotated[bool, typer.Option("--force", help="Force destruction without confirmation")] = False,
):
    """Destroy deployed MCP stack

    Args:
        ctx: Typer context object
        config_file: Path to the deployment configuration file
        force: Force destruction without confirmation
    """
    impl = ctx.obj["deployer"]

    if not force:
        if not typer.confirm("Are you sure you want to destroy the deployment?"):
            get_console().print("[yellow]Aborted[/yellow]")
            return

    try:
        asyncio.run(impl.destroy(config_file))
        get_console().print("[green]✓ Deployment destroyed[/green]")
    except Exception as e:
        handle_exception(e)


def generate(
    ctx: typer.Context,
    config_file: Annotated[Path, typer.Argument(help="The deployment configuration file")],
    output: Annotated[Optional[Path], typer.Option("--output", "-o", help="Output directory for manifests")] = None,
):
    """Generate deployment manifests (k8s or compose)

    Args:
        ctx: Typer context object
        config_file: Path to the deployment configuration file
        output: Output directory for manifests
    """
    impl = ctx.obj["deployer"]

    try:
        manifests_dir = impl.generate_manifests(config_file, output_dir=output)
        get_console().print(f"[green]✓ Manifests generated: {manifests_dir}[/green]")
    except Exception as e:
        handle_exception(e)
