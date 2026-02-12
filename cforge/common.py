# -*- coding: utf-8 -*-
"""Location: ./cforge/common.py
Copyright 2025
SPDX-License-Identifier: Apache-2.0
Authors: Gabe Goodhart

Common utilities for Context Forge CLI.
"""

# Standard
from enum import Enum
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


class CaseInsensitiveEnum(str, Enum):
    """Enum that supports case-insensitive parsing for CLI options."""

    @classmethod
    def _missing_(cls, value: object) -> Optional["CaseInsensitiveEnum"]:
        """Resolve unknown values by matching enum values case-insensitively."""
        if not isinstance(value, str):
            return None
        value_folded = value.casefold()
        for member in cls:
            if member.value.casefold() == value_folded:
                return member
        return None


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


def prompt_for_schema(schema_class: type[BaseModel], prefilled: Optional[Dict[str, Any]] = None, indent: str = "") -> Dict[str, Any]:
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


def prompt_for_json_schema(
    schema: Dict[str, Any],
    prefilled: Optional[Dict[str, Any]] = None,
    indent: str = "",
    prompt_optional: bool = True,
) -> Dict[str, Any]:
    """Interactively prompt user for fields based on a JSON Schema object.

    Args:
        schema: JSON Schema dictionary describing expected input shape
        prefilled: Optional dictionary with pre-filled values
        indent: Indentation string for nested fields
        prompt_optional: If False, prompt only for missing required fields

    Returns:
        Dictionary with prompted values merged into prefilled values
    """

    def _format_indent(indt: str) -> str:
        """Render indentation in a dim style for readability."""
        return f"[dim]{indt}[/dim]" if indt else indt

    def _next_indent(indt: str) -> str:
        """Return next indentation level."""
        if not indt:
            return "|-"
        return f"{indt}-"

    def _resolve_json_pointer(ref: str) -> Dict[str, Any]:
        """Resolve a local JSON Pointer reference against the root schema."""
        if not ref.startswith("#/"):
            raise CLIError(f"Only local schema references are supported: {ref}")

        pointer_tokens = ref[2:].split("/")
        current: Any = schema

        for raw_token in pointer_tokens:
            token = raw_token.replace("~1", "/").replace("~0", "~")

            if isinstance(current, dict):
                if token not in current:
                    raise CLIError(f"Schema reference not found: {ref}")
                current = current[token]
                continue

            if isinstance(current, list):
                try:
                    index = int(token)
                except ValueError:
                    raise CLIError(f"Invalid array index in schema reference: {ref}")
                if index < 0 or index >= len(current):
                    raise CLIError(f"Schema reference index out of bounds: {ref}")
                current = current[index]
                continue

            raise CLIError(f"Schema reference path is invalid: {ref}")

        if not isinstance(current, dict):
            raise CLIError(f"Schema reference does not resolve to an object schema: {ref}")

        return current

    def _resolve_ref_schema(field_schema: Dict[str, Any], resolving: Tuple[str, ...] = ()) -> Dict[str, Any]:
        """Resolve $ref in schema and merge sibling keys as overrides."""
        if not isinstance(field_schema, dict):
            return {}

        ref_value = field_schema.get("$ref")
        if not isinstance(ref_value, str):
            return field_schema

        if ref_value in resolving:
            ref_chain = " -> ".join([*resolving, ref_value])
            raise CLIError(f"Cyclic schema reference detected: {ref_chain}")

        resolved_schema = _resolve_ref_schema(_resolve_json_pointer(ref_value), resolving + (ref_value,))
        merged_schema = resolved_schema.copy()
        merged_schema.update({k: v for k, v in field_schema.items() if k != "$ref"})
        return merged_schema

    def _resolve_schema_type(field_schema: Dict[str, Any]) -> str:
        """Resolve schema type from JSON Schema type fields and hints."""
        field_schema = _resolve_ref_schema(field_schema)
        raw_type = field_schema.get("type")
        if isinstance(raw_type, str):
            return raw_type
        if isinstance(raw_type, list):
            valid_types = [item for item in raw_type if isinstance(item, str)]
            non_null_types = [item for item in valid_types if item != "null"]
            if non_null_types:
                return non_null_types[0]
            if "null" in valid_types:
                return "null"
        if isinstance(field_schema.get("properties"), dict):
            return "object"
        if "required" in field_schema:
            return "object"
        if isinstance(field_schema.get("items"), dict):
            return "array"
        if isinstance(field_schema.get("enum"), list):
            return "string"
        return "string"

    def _as_schema_dict(value: Any) -> Dict[str, Any]:
        """Return a schema dictionary, coercing unknown values to an empty schema."""
        return value if isinstance(value, dict) else {}

    def _prompt_text(field_name: str, field_schema: Dict[str, Any], is_required: bool) -> str:
        """Build prompt text for a field."""
        description = field_schema.get("description")
        default = field_schema.get("default")
        prompt_text = field_name
        if isinstance(description, str) and description and description != field_name:
            prompt_text += f" ({description})"
        if default not in (None, ""):
            prompt_text += f" [default: {default}]"
        if not is_required:
            prompt_text += " [optional]"
        return prompt_text

    if not isinstance(schema, dict):
        raise CLIError("Input schema must be a JSON object")

    resolved_root_schema = _resolve_ref_schema(schema)
    _MISSING = object()
    console = get_console()
    formatted_indent = _format_indent(indent)
    display_name = resolved_root_schema.get("title", "Tool Arguments")
    if not isinstance(display_name, str) or not display_name:
        display_name = "Tool Arguments"

    console.print(f"\n{formatted_indent}[bold cyan]Creating {display_name}[/bold cyan]")
    if prompt_optional:
        console.print(f"{formatted_indent}[dim]Press Enter to skip optional fields[/dim]\n{formatted_indent}")
    else:
        console.print(f"{formatted_indent}[dim]Prompting for missing required fields only[/dim]\n{formatted_indent}")

    def _prompt_field_value(
        field_name: str,
        field_schema: Dict[str, Any],
        is_required: bool,
        field_indent: str,
        prefilled_value: Any = _MISSING,
    ) -> Tuple[Any, bool]:
        """Prompt for a single field value.

        Returns:
            tuple[value, included] where included indicates if field should be set.
        """
        field_schema = _resolve_ref_schema(field_schema)
        schema_type = _resolve_schema_type(field_schema)
        formatted_field_indent = _format_indent(field_indent)
        prompt_text = _prompt_text(field_name, field_schema, is_required)

        if prefilled_value is not _MISSING:
            if schema_type == "object" and isinstance(prefilled_value, dict):
                console.print(f"{formatted_field_indent}[dim]{field_name}: (pre-filled object)[/dim]")
                return _prompt_object(field_schema, prefilled=prefilled_value, object_indent=_next_indent(field_indent)), True
            if schema_type == "array" and isinstance(prefilled_value, list):
                console.print(f"{formatted_field_indent}[dim]{field_name}: (pre-filled array)[/dim]")
                arr, include_arr = _prompt_array(field_name, field_schema, is_required, field_indent, prefilled=prefilled_value)
                return arr, include_arr
            console.print(f"{formatted_field_indent}[dim]{field_name}: {prefilled_value} (pre-filled)[/dim]")
            return prefilled_value, True

        if not is_required and not prompt_optional:
            return None, False

        enum_values = field_schema.get("enum")
        if isinstance(enum_values, list) and enum_values:
            enum_text = ", ".join(json.dumps(v) for v in enum_values)
            console.print(f"{formatted_field_indent}{prompt_text} [choices: {enum_text}]", end="")

            default_value = field_schema.get("default")
            default_text = ""
            show_default = False
            if default_value is not None:
                default_text = default_value if isinstance(default_value, str) else json.dumps(default_value)
                show_default = True

            raw_value = typer.prompt("", type=str, default=default_text, show_default=show_default)
            if raw_value == "":
                if is_required:
                    raise CLIError(f"Field '{field_name}' is required")
                return None, False

            parsed_value: Any
            try:
                parsed_value = json.loads(raw_value)
            except json.JSONDecodeError:
                parsed_value = raw_value

            if parsed_value in enum_values:
                return parsed_value, True
            if raw_value in enum_values:
                return raw_value, True

            raise CLIError(f"Field '{field_name}' must be one of: {enum_text}")

        if schema_type == "object":
            if not is_required and prompt_optional:
                console.print(f"{formatted_field_indent}[dim]Include {field_name}?[/dim] ", end="")
                if not typer.confirm("", default=False):
                    return None, False
            console.print(f"{formatted_field_indent}[yellow]{prompt_text}[/yellow]")
            return _prompt_object(field_schema, prefilled=None, object_indent=_next_indent(field_indent)), True

        if schema_type == "array":
            return _prompt_array(field_name, field_schema, is_required, field_indent)

        if schema_type == "boolean":
            if not is_required and prompt_optional:
                console.print(f"{formatted_field_indent}[dim]Include {field_name}?[/dim] ", end="")
                if not typer.confirm("", default=False):
                    return None, False
            default_val = field_schema.get("default")
            show_default = isinstance(default_val, bool)
            bool_default = bool(default_val) if show_default else False
            console.print(f"{formatted_field_indent}{prompt_text}", end="")
            return typer.prompt("", default=bool_default, type=bool, show_default=show_default), True

        if schema_type == "integer":
            default_val = field_schema.get("default")
            default_prompt: Any = "" if is_required else _INT_SENTINEL_DEFAULT
            show_default = False
            if isinstance(default_val, int):
                default_prompt = default_val
                show_default = True
            console.print(f"{formatted_field_indent}{prompt_text}", end="")
            value = typer.prompt("", type=int, default=default_prompt, show_default=show_default)
            if value == _INT_SENTINEL_DEFAULT:
                if is_required:
                    raise CLIError(f"Field '{field_name}' is required")
                return None, False
            return value, True

        if schema_type == "number":
            default_val = field_schema.get("default")
            default_text = ""
            show_default = False
            if isinstance(default_val, (int, float)):
                default_text = str(float(default_val))
                show_default = True
            console.print(f"{formatted_field_indent}{prompt_text}", end="")
            raw_value = typer.prompt("", type=str, default=default_text, show_default=show_default)
            if raw_value == "":
                if is_required:
                    raise CLIError(f"Field '{field_name}' is required")
                return None, False
            try:
                return float(raw_value), True
            except ValueError:
                raise CLIError(f"Field '{field_name}' must be a number")

        if schema_type == "null":
            return None, True

        default_val = field_schema.get("default")
        default_text = ""
        show_default = False
        if default_val is not None:
            default_text = default_val if isinstance(default_val, str) else json.dumps(default_val)
            show_default = True
        console.print(f"{formatted_field_indent}{prompt_text}", end="")
        value = typer.prompt("", type=str, default=default_text, show_default=show_default)
        if value == "":
            if is_required:
                raise CLIError(f"Field '{field_name}' is required")
            return None, False
        return value, True

    def _prompt_array(
        field_name: str,
        field_schema: Dict[str, Any],
        is_required: bool,
        field_indent: str,
        prefilled: Optional[List[Any]] = None,
    ) -> Tuple[List[Any], bool]:
        """Prompt for array values."""
        field_schema = _resolve_ref_schema(field_schema)
        formatted_field_indent = _format_indent(field_indent)
        item_schema = _resolve_ref_schema(_as_schema_dict(field_schema.get("items")))
        include_field = is_required

        if prefilled is None and not is_required and prompt_optional:
            console.print(f"{formatted_field_indent}[dim]Include {field_name}?[/dim] ", end="")
            if not typer.confirm("", default=False):
                return [], False
            include_field = True

        values: List[Any] = []

        if prefilled is not None:
            item_type = _resolve_schema_type(item_schema)
            nested_indent = _next_indent(field_indent)
            for idx, entry in enumerate(prefilled):
                if item_type == "object" and isinstance(entry, dict):
                    values.append(_prompt_object(item_schema, prefilled=entry, object_indent=nested_indent))
                elif item_type == "array" and isinstance(entry, list):
                    nested_values, _ = _prompt_array(f"{field_name}[{idx}]", item_schema, is_required=True, field_indent=nested_indent, prefilled=entry)
                    values.append(nested_values)
                else:
                    values.append(entry)
            return values, True

        nested_indent = _next_indent(field_indent)
        while True:
            console.print(f"{formatted_field_indent}[dim]Add an entry to {field_name}?[/dim] ", end="")
            if not typer.confirm("", default=False):
                break
            entry, include_entry = _prompt_field_value("item", item_schema, is_required=True, field_indent=nested_indent)
            if include_entry:
                values.append(entry)

        if values:
            return values, True
        if include_field or is_required:
            return [], True
        return [], False

    def _prompt_object(field_schema: Dict[str, Any], prefilled: Optional[Dict[str, Any]], object_indent: str) -> Dict[str, Any]:
        """Prompt for object fields recursively."""
        field_schema = _resolve_ref_schema(field_schema)
        data = prefilled.copy() if prefilled else {}
        properties = field_schema.get("properties")
        required = field_schema.get("required")
        properties_dict = properties if isinstance(properties, dict) else {}
        required_fields = {field for field in required if isinstance(field, str)} if isinstance(required, list) else set()

        for field_name, field_details in properties_dict.items():
            field_def = _resolve_ref_schema(_as_schema_dict(field_details))
            has_prefilled = field_name in data
            current_value = data[field_name] if has_prefilled else _MISSING
            value, include_value = _prompt_field_value(
                field_name=field_name,
                field_schema=field_def,
                is_required=field_name in required_fields,
                field_indent=object_indent,
                prefilled_value=current_value,
            )
            if include_value:
                data[field_name] = value
            if field_name in required_fields and field_name not in data:
                raise CLIError(f"Field '{field_name}' is required")

        additional_properties = field_schema.get("additionalProperties")
        if isinstance(additional_properties, dict) and prompt_optional:
            additional_properties_schema = _resolve_ref_schema(additional_properties)
            while True:
                formatted_object_indent = _format_indent(object_indent)
                next_indent = _next_indent(object_indent)
                formatted_next_indent = _format_indent(next_indent)
                console.print(f"{formatted_object_indent}[dim]Add an extra field?[/dim] ", end="")
                if not typer.confirm("", default=False):
                    break
                console.print(f"{formatted_next_indent}Enter key", end="")
                key = typer.prompt("", type=str)
                value, include_value = _prompt_field_value(key, additional_properties_schema, is_required=True, field_indent=next_indent)
                if include_value:
                    data[key] = value
        elif additional_properties is True and prompt_optional:
            while True:
                formatted_object_indent = _format_indent(object_indent)
                next_indent = _next_indent(object_indent)
                formatted_next_indent = _format_indent(next_indent)
                console.print(f"{formatted_object_indent}[dim]Add an extra field?[/dim] ", end="")
                if not typer.confirm("", default=False):
                    break
                console.print(f"{formatted_next_indent}Enter key", end="")
                key = typer.prompt("", type=str)
                console.print(f"{formatted_next_indent}Enter JSON value", end="")
                raw_value = typer.prompt("", type=str)
                try:
                    data[key] = json.loads(raw_value)
                except json.JSONDecodeError:
                    data[key] = raw_value

        return data

    root_type = _resolve_schema_type(resolved_root_schema)
    if root_type != "object":
        raise CLIError("Input schema must be an object schema")

    if prefilled is not None and not isinstance(prefilled, dict):
        raise CLIError("Prefilled input must be a JSON object")

    return _prompt_object(resolved_root_schema, prefilled=prefilled, object_indent=indent)
