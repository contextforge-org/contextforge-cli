# -*- coding: utf-8 -*-
"""Location: ./cforge/commands/profiles.py
Copyright 2025
SPDX-License-Identifier: Apache-2.0
Authors: Gabe Goodhart

CLI commands for profile management
"""

# Standard
from datetime import datetime
from pathlib import Path
from typing import Optional
import json
import secrets
import string

# Third-Party
import typer

# First-Party
from cforge.common import get_console, print_table, print_json, prompt_for_schema
from cforge.config import get_settings
from cforge.profile_utils import (
    AuthProfile,
    ProfileStore,
    get_all_profiles,
    get_profile,
    get_active_profile,
    set_active_profile,
    load_profile_store,
    save_profile_store,
)


def profiles_list() -> None:
    """List all available profiles.

    Displays all profiles configured in the Desktop app, showing their name,
    email, API URL, and active status.
    """
    console = get_console()

    try:
        profiles = get_all_profiles()

        # Prepare data for table
        profile_data = []
        for profile in profiles:
            profile_data.append(
                {
                    "id": profile.id,
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
            ["id", "name", "email", "api_url", "environment", "active"],
        )

        # Show which profile is currently active
        active = get_active_profile()
        console.print(f"\n[green]Currently using profile:[/green] [cyan]{active.name}[/cyan] ({active.email})")
        console.print(f"[dim]Connected to: {active.api_url}[/dim]")

    except Exception as e:
        console.print(f"[red]Error listing profiles: {str(e)}[/red]")
        raise typer.Exit(1)


def profiles_get(
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


def profiles_switch(
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


def profiles_create(
    data_file: Optional[Path] = typer.Argument(None, help="JSON file containing prompt data (interactive mode if not provided)"),
) -> None:
    """Create a new profile interactively.

    Walks the user through creating a new profile by prompting for all required
    fields. The new profile will be created in an inactive state. After creation,
    you will be asked if you want to enable the new profile.
    """
    console = get_console()

    try:
        console.print("\n[bold cyan]Create New Profile[/bold cyan]")
        console.print("[dim]You will be prompted for profile information.[/dim]\n")

        # Generate a 16-character random ID (matching desktop app format)
        alphabet = string.ascii_letters + string.digits
        profile_id = "".join(secrets.choice(alphabet) for _ in range(16))
        created_at = datetime.now()

        # Pre-fill fields that should not be prompted
        prefilled = {
            "id": profile_id,
            "is_active": False,
            "created_at": created_at,
            "last_used": None,
        }

        if data_file:
            if not data_file.exists():
                console.print(f"[red]File not found: {data_file}[/red]")
                raise typer.Exit(1)
            profile_data = json.loads(data_file.read_text())
            profile_data.update(prefilled)
        else:
            profile_data = prompt_for_schema(AuthProfile, prefilled=prefilled)

        # Create the AuthProfile instance
        new_profile = AuthProfile.model_validate(profile_data)

        # Load or create the profile store
        store = load_profile_store()
        if not store:
            store = ProfileStore(profiles={}, active_profile_id=None)

        # Add the new profile to the store
        store.profiles[new_profile.id] = new_profile

        # Save the profile store
        save_profile_store(store)

        console.print("\n[green]✓ Profile created successfully![/green]")
        console.print(f"[dim]Profile ID:[/dim] {new_profile.id}")
        console.print(f"[dim]Name:[/dim] {new_profile.name}")
        console.print(f"[dim]Email:[/dim] {new_profile.email}")
        console.print(f"[dim]API URL:[/dim] {new_profile.api_url}")

        # Ask if the user wants to enable the new profile
        console.print("\n[yellow]Enable this profile now?[/yellow]", end=" ")
        if typer.confirm("", default=False):
            success = set_active_profile(new_profile.id)
            if success:
                console.print(f"[green]✓ Profile enabled:[/green] [cyan]{new_profile.name}[/cyan]")
                # Clear the settings cache so the new profile takes effect
                get_settings.cache_clear()
            else:
                console.print(f"[red]Failed to enable profile: {new_profile.id}[/red]")
        else:
            console.print("[dim]Profile created but not enabled. Use 'cforge profiles switch' to enable it later.[/dim]")

    except Exception as e:
        console.print(f"[red]Error creating profile: {str(e)}[/red]")
        raise typer.Exit(1)
