# -*- coding: utf-8 -*-
"""
SPDX-License-Identifier: Apache-2.0

Rich rendering helpers for structured CLI output.

This module contains reusable output primitives for JSON and tabular data.
It keeps formatting decisions in one place so resource commands can focus on
data retrieval while sharing a consistent terminal presentation.
"""

# Standard
import json
from typing import Any, Dict, List, Optional

# Third-Party
from rich.console import Console, ConsoleOptions, RenderableType, RenderResult
from rich.measure import Measurement
from rich.panel import Panel
from rich.segment import Segment
from rich.syntax import Syntax
from rich.table import Table

# First-Party
from cforge.common.console import get_console
from cforge.config import get_settings


class LineLimit:
    """A renderable that limits the number of lines after rich wrapping."""

    def __init__(self, renderable: RenderableType, max_lines: int):
        """Initialize with the wrapped renderable and max lines to render."""
        self.renderable = renderable
        self.max_lines = max_lines

    def __rich_console__(self, console: Console, options: ConsoleOptions) -> RenderResult:
        """Render with line truncation applied after wrapping."""
        lines = console.render_lines(self.renderable, options, pad=False)
        for index, line in enumerate(lines):
            if index >= self.max_lines:
                yield Segment("...")
                break
            yield from line
            yield Segment.line()

    def __rich_measure__(self, console: Console, options: ConsoleOptions) -> Measurement:
        """Measure by delegating to the wrapped renderable."""
        return Measurement.get(console, options, self.renderable)


def print_json(data: Any, title: Optional[str] = None) -> None:
    """Pretty print JSON data with Rich."""
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
    """Print data as a Rich table."""
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
