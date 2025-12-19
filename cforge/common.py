# -*- coding: utf-8 -*-
"""Location: ./cforge/common.py
Copyright 2025
SPDX-License-Identifier: Apache-2.0
Authors: Gabe Goodhart

Common utilities for Context Forge CLI.
"""

# Standard
from functools import lru_cache
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Union
import json

# Third-Party
from pydantic import BaseModel
from pydantic_core import PydanticUndefined
from rich.console import Console, ConsoleOptions, RenderResult, RenderableType
from rich.segment import Segment
from rich.measure import Measurement
from rich.table import Table
from rich.panel import Panel
from rich.syntax import Syntax
import requests
import typer

# First-Party
from cforge.profile_utils import DEFAULT_PROFILE_ID
from cforge.config import get_settings
from cforge.credential_store import load_profile_credentials
from cforge.profile_utils import get_active_profile

# ------------------------------------------------------------------------------
# Singletons
# ------------------------------------------------------------------------------


@lru_cache
def get_console() -> Console:
    """Get the console singleton.
    Returns:
        Console singleton
    """
    return Console()


@lru_cache
def get_app() -> typer.Typer:
    """Get the typer singleton.
    Returns:
        typer singleton
    """
    return typer.Typer(
        name="mcpgateway",
        help="MCP Gateway - Production-grade MCP Gateway & Proxy CLI",
        add_completion=True,
        rich_markup_mode="rich",
    )


# ------------------------------------------------------------------------------
# Error handling
# ------------------------------------------------------------------------------


class CLIError(Exception):
    """Base class for CLI-related errors."""


class AuthenticationError(CLIError):
    """Raised when authentication fails."""


def split_exception_details(exception: Exception) -> Tuple[str, Any]:
    """Try to get parsed details from the exception"""
    exc_str = str(exception)
    splits = exc_str.split(":", 1)
    if len(splits) == 2:
        try:
            parsed_details = json.loads(splits[1])
            return splits[0], parsed_details
        except json.JSONDecodeError:
            pass
    return exc_str, None


def handle_exception(exception: Exception) -> None:
    """Handle an exception and print a friendly error message."""
    e_str, e_detail = split_exception_details(exception)
    get_console().print(f"[red]Error: {e_str}[/red]")
    if e_detail:
        print_json(e_detail, "Error details")
    raise typer.Exit(1)


# ------------------------------------------------------------------------------
# Auth
# ------------------------------------------------------------------------------


def get_base_url() -> str:
    """Get the full base URL for the current profile's server

    TODO: This will need to support https in the future!

    Returns:
        The string URL base
    """
    return get_active_profile().api_url


def get_token_file() -> Path:
    """Get the path to the token file in contextforge_home.

    Uses the active profile if available, otherwise returns the default token file.
    For the virtual default profile, uses the unsuffixed token file.

    Returns:
        Path to the token file (profile-specific or default)
    """
    profile = get_active_profile()
    suffix = "" if profile.id == DEFAULT_PROFILE_ID else f".{profile.id}"
    return get_settings().contextforge_home / f"token{suffix}"


def save_token(token: str) -> None:
    """Save authentication token to contextforge_home/token file.

    Args:
        token: The JWT token to save
    """
    token_file = get_token_file()
    token_file.parent.mkdir(parents=True, exist_ok=True)
    token_file.write_text(token, encoding="utf-8")
    # Set restrictive permissions (readable only by owner)
    token_file.chmod(0o600)


def load_token() -> Optional[str]:
    """Load authentication token from contextforge_home/token file.

    Returns:
        Token string if found, None otherwise
    """
    token_file = get_token_file()
    if token_file.exists():
        return token_file.read_text(encoding="utf-8").strip()
    return None


def attempt_auto_login() -> Optional[str]:
    """Attempt to automatically login using stored credentials.

    This function tries to login using credentials stored by the desktop app
    in the encrypted credential store. If successful, it saves the token
    and returns it.

    Returns:
        Authentication token if auto-login succeeds, None otherwise
    """
    # Try to load credentials from the encrypted store
    profile = get_active_profile()
    credentials = load_profile_credentials(profile.id)
    if not credentials or not credentials.get("email") or not credentials.get("password"):
        return None

    # Attempt login
    try:
        gateway_url = get_base_url()
        response = requests.post(
            f"{gateway_url}/auth/email/login",
            json={"email": credentials["email"], "password": credentials["password"]},
            headers={"Content-Type": "application/json"},
        )

        if response.status_code == 200:
            data = response.json()
            token = data.get("access_token")
            if token:
                # Save the token for future use
                save_token(token)
                return token
    except Exception:
        # Silently fail - auto-login is best-effort
        pass

    return None


def get_auth_token() -> Optional[str]:
    """Get authentication token from multiple sources in priority order.

    Priority:
    1. MCPGATEWAY_BEARER_TOKEN environment variable
    2. Stored token in contextforge_home/token file
    3. Auto-login using stored credentials (if available)

    Returns:
        Authentication token string or None if not configured
    """
    # Try environment variable first (highest priority)
    token: Optional[str] = get_settings().mcpgateway_bearer_token
    if token:
        return token

    # Try stored token file
    token = load_token()
    if token:
        return token

    # Try auto-login with stored credentials
    token = attempt_auto_login()
    if token:
        return token

    return None


def make_authenticated_request(
    method: str,
    url: str,
    json_data: Optional[Dict[str, Any]] = None,
    params: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """Make an authenticated HTTP request to the gateway API.

    Supports both authenticated and unauthenticated servers. Will attempt
    the request without authentication if no token is configured, and only
    fail if the server requires authentication.

    Args:
        method: HTTP method (GET, POST, etc.)
        url: URL path for the request
        json_data: Optional JSON data for request body
        params: Optional query parameters

    Returns:
        JSON response from the API

    Raises:
        AuthenticationError: If the server requires authentication but none is configured
        CLIError: If the API request fails
    """
    token = get_auth_token()

    headers = {"Content-Type": "application/json"}
    # Only add Authorization header if a token is available
    if token:
        if token.startswith("Basic "):
            headers["Authorization"] = token
        else:
            headers["Authorization"] = f"Bearer {token}"

    gateway_url = get_base_url()
    full_url = f"{gateway_url}{url}"

    try:
        response = requests.request(method=method, url=full_url, json=json_data, params=params, headers=headers)

        # Handle authentication errors specifically
        if response.status_code in (401, 403):
            raise AuthenticationError("Authentication required but not configured. " "Set MCPGATEWAY_BEARER_TOKEN environment variable or run 'cforge login'.")

        if response.status_code >= 400:
            raise CLIError(f"API request failed ({response.status_code}): {response.text}")

        return response.json()

    except requests.RequestException as e:
        raise CLIError(f"Failed to connect to gateway at {gateway_url}: {str(e)}")


# ------------------------------------------------------------------------------
# Pretty Printing
# ------------------------------------------------------------------------------


class LineLimit:
    """A renderable that limits the number of lines after rich's wrapping."""

    def __init__(self, renderable: RenderableType, max_lines: int):
        """Implement with the wrapped renderable and the max lines to render"""
        self.renderable = renderable
        self.max_lines = max_lines

    def __rich_console__(self, console: Console, options: ConsoleOptions) -> RenderResult:
        """Hook the actual rendering to perform the per-line truncation"""

        # Let rich render the content with proper wrapping
        lines = console.render_lines(self.renderable, options, pad=False)

        # Limit to max_lines
        for i, line in enumerate(lines):
            if i >= self.max_lines:
                # Optionally add an ellipsis indicator
                yield Segment("...")
                break
            yield from line
            yield Segment.line()

    def __rich_measure__(self, console: Console, options: ConsoleOptions) -> Measurement:
        """Hook the measurement of this entry to pass through to the wrapped
        renderable
        """

        return Measurement.get(console, options, self.renderable)


def print_json(data: Any, title: Optional[str] = None) -> None:
    """Pretty print JSON data with Rich.

    Args:
        data: Data to print
        title: Optional title for the output
    """
    console = get_console()
    json_str = json.dumps(data, indent=2, ensure_ascii=False)
    syntax = Syntax(json_str, "json", theme="monokai", line_numbers=True)
    if title:
        console.print(Panel(syntax, title=title, border_style="green"))
    else:
        console.print(syntax)


def print_table(
    data: List[Dict],
    title: str,
    columns: List[str],
    col_name_map: Optional[Dict[str, str]] = None,
) -> None:
    """Print data as a Rich table.

    Args:
        data: List of dictionaries to display
        title: Title for the table
        columns: List of column names to display
        col_name_map: Optional mapping of column names to display
    """
    console = get_console()
    table = Table(title=title, show_header=True, header_style="bold magenta")
    col_name_map = col_name_map or {}
    max_lines = get_settings().table_max_lines

    for column in columns:
        table.add_column(col_name_map.get(column, column), style="cyan")

    for item in data:
        row = [str(item.get(col, "")) for col in columns]
        if max_lines > 0:
            row = [LineLimit(cell, max_lines=max_lines) for cell in row]
        table.add_row(*row)

    console.print(table)


# ------------------------------------------------------------------------------
# Structure Guidance
# ------------------------------------------------------------------------------

# Very unlikely number for any valid int param
_INT_SENTINEL_DEFAULT = -4231415


def prompt_for_schema(schema_class: type, prefilled: Optional[Dict[str, Any]] = None, indent: str = "") -> Dict[str, Any]:
    """Interactively prompt user for fields based on a Pydantic schema.

    Args:
        schema_class: The Pydantic model class to use for prompting
        prefilled: Optional dictionary of pre-filled values to skip prompting for
        indent: Indentation string for nested fields

    Returns:
        Dictionary with the user's input data (includes prefilled values)
    """
    from typing import get_args, get_origin

    def _format_indent(indt: str) -> str:
        """Format the indentation as dim"""
        return f"[dim]{indt}[/dim]" if indt else indt

    formatted_indent = _format_indent(indent)
    next_indent = indent
    if not next_indent:
        next_indent = "|"
    next_indent += "-"
    formatted_next_indent = _format_indent(next_indent)

    console = get_console()
    console.print(f"\n{formatted_indent}[bold cyan]Creating {schema_class.__name__}[/bold cyan]")
    console.print(f"{formatted_indent}[dim]Press Enter to skip optional fields[/dim]\n{formatted_indent}")

    data = prefilled.copy() if prefilled else {}
    model_fields = schema_class.model_fields

    for field_name, field_info in model_fields.items():
        # Skip if already provided
        if field_name in data:
            console.print(f"{formatted_indent}[dim]{field_name}: {data[field_name]} (pre-filled)[/dim]")
            continue

        # Skip internal fields
        if field_name in ["model_config", "auth_value"]:
            continue

        # Get field metadata
        annotation = field_info.annotation
        description = field_info.description or field_name
        is_required = field_info.is_required()
        default = field_info.default if field_info.default is not PydanticUndefined else None

        # Get the actual type (handle Optional, Union, etc.)
        origin = get_origin(annotation)
        args = get_args(annotation)

        # Determine the base type
        if origin is Union:
            # Handle Optional[T] which is Union[T, None]
            actual_type = args[0] if len(args) > 0 and type(None) in args else annotation
        else:
            actual_type = annotation

        # Create prompt text
        prompt_text = f"{field_name}"
        if description and description != field_name:
            prompt_text += f" ({description})"
        if default and default != "":
            prompt_text += f" [default: {default}]"
        if not is_required:
            prompt_text += " [optional]"

        # Handle different types
        if actual_type is bool or str(actual_type) == "bool":
            if not is_required:
                console.print(f"{formatted_indent}Include {field_name}?", end="")
            if is_required or typer.confirm("", default=False):
                console.print(f"{formatted_indent}{prompt_text}", end="")
                data[field_name] = typer.prompt("", default=bool(default) if default else False, type=bool)

        elif actual_type is int or str(actual_type) == "int":
            default_val = default
            if default is None:
                default_val = "" if is_required else _INT_SENTINEL_DEFAULT
            console.print(f"{formatted_indent}{prompt_text}", end="")
            value = typer.prompt("", type=int, default=default_val, show_default=default_val not in ["", _INT_SENTINEL_DEFAULT])
            if value != _INT_SENTINEL_DEFAULT:
                data[field_name] = value

        elif isinstance(actual_type, type) and issubclass(actual_type, BaseModel):
            console.print(f"{formatted_indent}[yellow]{prompt_text}[/yellow]")
            data[field_name] = prompt_for_schema(actual_type, indent=next_indent)

        elif get_origin(actual_type) is list or str(actual_type).startswith("list"):
            list_type = get_args(actual_type)[0]
            console.print(f"{formatted_indent}[yellow]{prompt_text}[/yellow]")
            if isinstance(list_type, type) and issubclass(list_type, BaseModel):
                # Loop collecting more arguments until the user wants to stop
                entries = []
                while True:
                    console.print(f"{formatted_indent}[dim]Add an entry?[/dim] ", end="")
                    if not typer.confirm("", default=False):
                        break
                    if not indent:
                        indent = "|"
                    indent += "-"
                    entries.append(prompt_for_schema(list_type, indent=indent))
                data[field_name] = entries

            # Assume string
            else:
                console.print(f"{formatted_indent}[dim]Enter comma-separated values, or press Enter to skip[/dim] ", end="")
                value = typer.prompt("", default="", show_default=False)
                if value:
                    # Parse comma-separated values
                    data[field_name] = [v.strip() for v in value.split(",") if v.strip()]

        elif get_origin(actual_type) is dict:
            dict_key_type, dict_value_type = get_args(actual_type)
            console.print(f"{formatted_indent}[yellow]{prompt_text}[/yellow]")
            assert dict_key_type is str, "Only string keys are supported"
            data[field_name] = {}
            while True:
                console.print(f"{formatted_indent}[dim]Add an entry?[/dim] ", end="")
                if not typer.confirm("", default=False):
                    break
                console.print(f"{formatted_next_indent}Enter key", end="")
                key = typer.prompt("")
                if isinstance(dict_value_type, type) and issubclass(dict_value_type, BaseModel):
                    val = prompt_for_schema(dict_value_type, indent=next_indent)
                else:
                    console.print(f"{formatted_next_indent}Enter value", end="")
                    parse_type = dict_value_type if dict_value_type is not Any else str
                    val = typer.prompt("", type=parse_type)

                    # If the value type is Any, try to parse it as JSON
                    if dict_value_type is Any:
                        val = json.loads(val)
                data[field_name][key] = val

        else:  # Treat as string
            console.print(f"{formatted_indent}{prompt_text}", end="")
            value = typer.prompt(
                "",
                type=str,
                default=default if default is not None else "",
                show_default=default is not None and default != "",
            )
            if value and value != "":
                data[field_name] = value
            if is_required and not value:
                raise CLIError(f"Field '{field_name}' is required")

    return data
