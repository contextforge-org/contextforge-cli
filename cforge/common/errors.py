# -*- coding: utf-8 -*-
"""
SPDX-License-Identifier: Apache-2.0

Error domain for CLI execution.

This module defines CLI-facing exception types and helpers that normalize
exception payloads into user-friendly terminal output. It is the shared
boundary between internal failures and surfaced command errors.
"""

# Standard
from enum import Enum
import json
from typing import Any, Optional, Tuple

# Third-Party
import typer

# First-Party
from cforge.common.console import get_console


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
    """Try to parse JSON details from an exception string."""
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
    # First-Party
    from cforge.common.render import print_json

    e_str, e_detail = split_exception_details(exception)
    get_console().print(f"[red]Error: {e_str}[/red]")
    if e_detail:
        print_json(e_detail, "Error details")
    raise typer.Exit(1)
