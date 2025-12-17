# -*- coding: utf-8 -*-
"""Location: ./cforge/commands/profiles.py
Copyright 2025
SPDX-License-Identifier: Apache-2.0
Authors: Gabe Goodhart

CLI commands for profile management
"""

# Standard
from typing import Optional

# Third-Party
import typer

# First-Party
from cforge.common import get_console, print_table, print_json
from cforge.config import get_settings
from cforge.profile_utils import (
    get_all_profiles,
    get_profile,
    get_active_profile,
    set_active_profile,
)


app = typer.Typer(
    name="profiles",
    help="Manage user profiles for connecting to different Context Forge instances",
    rich_markup_mode="rich",
)


@app.command("list")
def list_profiles() -> None:
    """List all available profiles.

    Displays all profiles configured in the Desktop app, showing their name,
    email, API URL, and active status.
    """
    console = get_console()

    try:
        profiles = get_all_profiles()

        if not profiles:
            console.print("[yellow]No profiles found.[/yellow]")
            console.print("[dim]Profiles are managed through the Context Forge Desktop app.[/dim]")
            return

        # Prepare data for table
        profile_data = []
        for profile in profiles:
            profile_data.append(
                {
                    "id": profile.id[:8] + "...",  # Truncate ID for display
                    "name": profile.name,
                    "email": profile.email,
                    "api_url": profile.api_url,
                    "active": "✓" if profile.is_active else "",
                    "environment": profile.metadata.environment if profile.metadata else "",
                }
            )

        print_table(
            profile_data,
            "Available Profiles",
            ["name", "email", "api_url", "environment", "active"],
            col_name_map={
                "name": "Name",
                "email": "Email",
                "api_url": "API URL",
                "environment": "Environment",
                "active": "Active",
            },
        )

        # Show which profile is currently active
        active = get_active_profile()
        if active:
            console.print(f"\n[green]Currently using profile:[/green] [cyan]{active.name}[/cyan] ({active.email})")
            console.print(f"[dim]Connected to: {active.api_url}[/dim]")

    except Exception as e:
        console.print(f"[red]Error listing profiles: {str(e)}[/red]")
        raise typer.Exit(1)


@app.command("get")
def get_profile_cmd(
    profile_id: Optional[str] = typer.Argument(
        None,
        help="Profile ID to retrieve. If not provided, shows the active profile.",
    ),
    json_output: bool = typer.Option(
        False,
        "--json",
        help="Output in JSON format",
    ),
) -> None:
    """Get details of a specific profile or the active profile.

    If no profile ID is provided, displays information about the currently
    active profile.
    """
    console = get_console()

    try:
        if profile_id:
            profile = get_profile(profile_id)
            if not profile:
                console.print(f"[red]Profile not found: {profile_id}[/red]")
                raise typer.Exit(1)
        else:
            profile = get_active_profile()
            if not profile:
                console.print("[yellow]No active profile set.[/yellow]")
                console.print("[dim]Use 'cforge profiles switch <profile-id>' to set an active profile.[/dim]")
                raise typer.Exit(1)

        if json_output:
            # Output as JSON
            print_json(profile.model_dump(by_alias=True), title="Profile Details")
        else:
            # Pretty print profile details
            console.print(f"\n[bold cyan]Profile: {profile.name}[/bold cyan]")
            console.print(f"[dim]ID:[/dim] {profile.id}")
            console.print(f"[dim]Email:[/dim] {profile.email}")
            console.print(f"[dim]API URL:[/dim] {profile.api_url}")
            console.print(f"[dim]Active:[/dim] {'[green]Yes[/green]' if profile.is_active else '[yellow]No[/yellow]'}")
            console.print(f"[dim]Created:[/dim] {profile.created_at}")
            if profile.last_used:
                console.print(f"[dim]Last Used:[/dim] {profile.last_used}")

            if profile.metadata:
                console.print("\n[bold]Metadata:[/bold]")
                if profile.metadata.description:
                    console.print(f"  [dim]Description:[/dim] {profile.metadata.description}")
                if profile.metadata.environment:
                    console.print(f"  [dim]Environment:[/dim] {profile.metadata.environment}")
                if profile.metadata.icon:
                    console.print(f"  [dim]Icon:[/dim] {profile.metadata.icon}")

    except Exception as e:
        console.print(f"[red]Error retrieving profile: {str(e)}[/red]")
        raise typer.Exit(1)


@app.command("switch")
def switch_profile(
    profile_id: str = typer.Argument(
        ...,
        help="Profile ID to switch to. Use 'cforge profiles list' to see available profiles.",
    ),
) -> None:
    """Switch to a different profile.

    Sets the specified profile as the active profile. All subsequent CLI
    commands will use this profile's API URL for connections.

    Note: This only changes which profile the CLI uses. To fully authenticate
    and manage profiles, use the Context Forge Desktop app.
    """
    console = get_console()

    try:
        # Check if profile exists
        profile = get_profile(profile_id)
        if not profile:
            console.print(f"[red]Profile not found: {profile_id}[/red]")
            console.print("[dim]Use 'cforge profiles list' to see available profiles.[/dim]")
            raise typer.Exit(1)

        # Switch to the profile
        success = set_active_profile(profile_id)
        if not success:
            console.print(f"[red]Failed to switch to profile: {profile_id}[/red]")
            raise typer.Exit(1)

        console.print(f"[green]✓ Switched to profile:[/green] [cyan]{profile.name}[/cyan]")
        console.print(f"[dim]Email:[/dim] {profile.email}")
        console.print(f"[dim]API URL:[/dim] {profile.api_url}")

        # Clear the settings cache so the new profile takes effect
        get_settings.cache_clear()

        console.print("\n[yellow]Note:[/yellow] Profile switched successfully. " "The CLI will now connect to the selected profile's API URL.")

    except Exception as e:
        console.print(f"[red]Error switching profile: {str(e)}[/red]")
        raise typer.Exit(1)


@app.command("current")
def current_profile() -> None:
    """Show the currently active profile.

    Displays information about which profile is currently being used by the CLI.
    """
    console = get_console()

    try:
        profile = get_active_profile()
        if not profile:
            console.print("[yellow]No active profile set.[/yellow]")
            console.print("[dim]Use 'cforge profiles switch <profile-id>' to set an active profile.[/dim]")
            return

        console.print(f"\n[bold green]Current Profile:[/bold green] [cyan]{profile.name}[/cyan]")
        console.print(f"[dim]Email:[/dim] {profile.email}")
        console.print(f"[dim]API URL:[/dim] {profile.api_url}")
        if profile.metadata and profile.metadata.environment:
            console.print(f"[dim]Environment:[/dim] {profile.metadata.environment}")

    except Exception as e:
        console.print(f"[red]Error retrieving current profile: {str(e)}[/red]")
        raise typer.Exit(1)
