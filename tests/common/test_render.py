# -*- coding: utf-8 -*-
"""Tests for cforge.common.render."""

# Third-Party
from rich.panel import Panel
from rich.syntax import Syntax
from rich.table import Table

# First-Party
from cforge.common.render import LineLimit, print_json, print_table


class TestLineLimit:
    """Tests for LineLimit class that truncates rendered content."""

    def test_line_limit_basic_truncation(self) -> None:
        """Test that LineLimit truncates content to max_lines."""
        from rich.console import Console
        from rich.text import Text

        console = Console()
        # Create text with 5 lines
        text = Text("Line 1\nLine 2\nLine 3\nLine 4\nLine 5")
        limited = LineLimit(text, max_lines=3)

        # Render to string and verify truncation
        with console.capture() as capture:
            console.print(limited)

        output = capture.get()
        # Should contain first 3 lines
        assert "Line 1" in output
        assert "Line 2" in output
        assert "Line 3" in output
        # Should NOT contain lines 4 and 5
        assert "Line 4" not in output
        assert "Line 5" not in output
        # Should have ellipsis
        assert "..." in output

    def test_line_limit_no_truncation_needed(self) -> None:
        """Test that LineLimit doesn't truncate when content is within limit."""
        from rich.console import Console
        from rich.text import Text

        console = Console()
        # Create text with 2 lines, limit to 5
        text = Text("Line 1\nLine 2")
        limited = LineLimit(text, max_lines=5)

        with console.capture() as capture:
            console.print(limited)

        output = capture.get()
        # Should contain both lines
        assert "Line 1" in output
        assert "Line 2" in output
        # Should NOT have ellipsis since no truncation
        assert "..." not in output

    def test_line_limit_exact_match(self) -> None:
        """Test LineLimit when content exactly matches max_lines."""
        from rich.console import Console
        from rich.text import Text

        console = Console()
        # Create text with exactly 3 lines
        text = Text("Line 1\nLine 2\nLine 3")
        limited = LineLimit(text, max_lines=3)

        with console.capture() as capture:
            console.print(limited)

        output = capture.get()
        # Should contain all 3 lines
        assert "Line 1" in output
        assert "Line 2" in output
        assert "Line 3" in output
        # Should NOT have ellipsis since content fits exactly
        assert "..." not in output

    def test_line_limit_zero_lines(self) -> None:
        """Test LineLimit with max_lines=0 shows only ellipsis."""
        from rich.console import Console
        from rich.text import Text

        console = Console()
        text = Text("Line 1\nLine 2")
        limited = LineLimit(text, max_lines=0)

        with console.capture() as capture:
            console.print(limited)

        output = capture.get()
        # Should only show ellipsis, no content
        assert "..." in output
        assert "Line 1" not in output
        assert "Line 2" not in output

    def test_line_limit_one_line(self) -> None:
        """Test LineLimit with max_lines=1."""
        from rich.console import Console
        from rich.text import Text

        console = Console()
        text = Text("Line 1\nLine 2\nLine 3")
        limited = LineLimit(text, max_lines=1)

        with console.capture() as capture:
            console.print(limited)

        output = capture.get()
        # Should show only first line and ellipsis
        assert "Line 1" in output
        assert "..." in output
        assert "Line 2" not in output
        assert "Line 3" not in output

    def test_line_limit_with_long_single_line(self) -> None:
        """Test LineLimit with a single long line that wraps."""
        from rich.console import Console
        from rich.text import Text

        console = Console(width=80)  # Set fixed width for predictable wrapping
        # Create a very long line that will wrap
        long_text = "A" * 200
        text = Text(long_text)
        limited = LineLimit(text, max_lines=2)

        with console.capture() as capture:
            console.print(limited)

        output = capture.get()
        # Should contain some A's but be truncated
        assert "A" in output
        # Should have ellipsis since it wraps to more than 2 lines
        assert "..." in output

    def test_line_limit_measurement_passthrough(self) -> None:
        """Test that LineLimit passes through measurement to wrapped renderable."""
        from rich.console import Console
        from rich.text import Text

        console = Console()
        text = Text("Test content")
        limited = LineLimit(text, max_lines=3)

        # Get measurement using console's options
        measurement = console.measure(limited)

        # Should return a valid Measurement
        assert measurement is not None
        assert hasattr(measurement, "minimum")
        assert hasattr(measurement, "maximum")

    def test_line_limit_with_empty_content(self) -> None:
        """Test LineLimit with empty content."""
        from rich.console import Console
        from rich.text import Text

        console = Console()
        text = Text("")
        limited = LineLimit(text, max_lines=3)

        with console.capture() as capture:
            console.print(limited)

        output = capture.get()
        # Empty content should produce minimal output
        # Should not have ellipsis since there's nothing to truncate
        assert "..." not in output

    def test_line_limit_preserves_styling(self) -> None:
        """Test that LineLimit preserves rich styling in truncated content."""
        from rich.console import Console
        from rich.text import Text

        console = Console()
        # Create styled text
        text = Text()
        text.append("Line 1\n", style="bold red")
        text.append("Line 2\n", style="italic blue")
        text.append("Line 3\n", style="underline green")
        text.append("Line 4", style="bold yellow")

        limited = LineLimit(text, max_lines=2)

        with console.capture() as capture:
            console.print(limited)

        output = capture.get()
        # Should contain first 2 lines
        assert "Line 1" in output
        assert "Line 2" in output
        # Should NOT contain lines 3 and 4
        assert "Line 3" not in output
        assert "Line 4" not in output
        # Should have ellipsis
        assert "..." in output


class TestPrettyPrinting:
    """Tests for pretty printing functions."""

    def test_print_json_with_title(self, mock_console) -> None:
        """Test print_json with a title."""
        test_data = {"key": "value", "number": 42}

        print_json(test_data, "Test Title")

        # Verify console.print was called
        mock_console.print.assert_called_once()
        call_args = mock_console.print.call_args[0]

        # Should be wrapped in a Panel
        assert isinstance(call_args[0], Panel)

    def test_print_json_without_title(self, mock_console) -> None:
        """Test print_json without a title."""
        test_data = {"key": "value"}

        print_json(test_data)

        # Verify console.print was called
        mock_console.print.assert_called_once()
        call_args = mock_console.print.call_args[0]

        # Should be Syntax object, not Panel
        assert isinstance(call_args[0], Syntax)

    def test_print_table(self, mock_console) -> None:
        """Test print_table with data."""
        test_data = [
            {"id": 1, "name": "Item 1", "value": "A"},
            {"id": 2, "name": "Item 2", "value": "B"},
        ]
        columns = ["id", "name", "value"]

        print_table(test_data, "Test Table", columns)

        # Verify console.print was called
        mock_console.print.assert_called_once()
        call_args = mock_console.print.call_args[0]

        # Should be a Table
        assert isinstance(call_args[0], Table)

    def test_print_table_missing_columns(self, mock_console) -> None:
        """Test print_table handles missing columns gracefully."""
        test_data = [
            {"id": 1, "name": "Item 1"},  # Missing 'value' column
        ]
        columns = ["id", "name", "value"]

        # Should not raise an error
        print_table(test_data, "Test Table", columns)
        mock_console.print.assert_called_once()

    def test_print_table_wraps_all_cells_with_line_limit(self) -> None:
        """Test that print_table wraps all cell values with LineLimit for truncation."""
        from unittest.mock import patch

        # Create test data with various types
        test_data = [
            {"id": 1, "name": "Item 1", "description": "Short text"},
            {"id": 2, "name": "Item 2", "description": "Line 1\nLine 2\nLine 3\nLine 4\nLine 5"},
        ]
        columns = ["id", "name", "description"]

        # Mock Table.add_row to capture what's passed to it
        with patch.object(Table, "add_row") as mock_add_row:
            print_table(test_data, "Test Table", columns)

            # Verify add_row was called for each data row
            assert mock_add_row.call_count == 2

            # Check that all arguments to add_row are LineLimit instances
            for call in mock_add_row.call_args_list:
                args = call[0]  # Get positional arguments
                for arg in args:
                    assert isinstance(arg, LineLimit), f"Expected LineLimit but got {type(arg)}"
                    # Verify max_lines is set to 4
                    assert arg.max_lines == 4

    def test_print_table_with_custom_max_lines(self, mock_settings) -> None:
        """Test that print_table respects custom table_max_lines configuration."""
        from unittest.mock import patch

        # Configure mock_settings with custom max_lines value
        mock_settings.table_max_lines = 2

        test_data = [
            {"id": 1, "name": "Item 1", "description": "Short text"},
            {"id": 2, "name": "Item 2", "description": "Line 1\nLine 2\nLine 3\nLine 4\nLine 5"},
        ]
        columns = ["id", "name", "description"]

        # Mock Table.add_row to capture what's passed to it
        with patch.object(Table, "add_row") as mock_add_row:
            print_table(test_data, "Test Table", columns)

            # Verify add_row was called for each data row
            assert mock_add_row.call_count == 2

            # Check that all arguments to add_row are LineLimit instances with custom max_lines
            for call in mock_add_row.call_args_list:
                args = call[0]  # Get positional arguments
                for arg in args:
                    assert isinstance(arg, LineLimit), f"Expected LineLimit but got {type(arg)}"
                    # Verify max_lines is set to custom value of 2
                    assert arg.max_lines == 2

    def test_print_table_with_disabled_line_limit(self, mock_settings) -> None:
        """Test that print_table skips LineLimit wrapping when table_max_lines is 0 or negative."""
        from unittest.mock import patch

        # Configure mock_settings with disabled max_lines value (0)
        mock_settings.table_max_lines = 0

        test_data = [
            {"id": 1, "name": "Item 1", "description": "Short text"},
            {"id": 2, "name": "Item 2", "description": "Line 1\nLine 2\nLine 3\nLine 4\nLine 5"},
        ]
        columns = ["id", "name", "description"]

        # Mock Table.add_row to capture what's passed to it
        with patch.object(Table, "add_row") as mock_add_row:
            print_table(test_data, "Test Table", columns)

            # Verify add_row was called for each data row
            assert mock_add_row.call_count == 2

            # Check that arguments to add_row are plain strings, NOT LineLimit instances
            for call in mock_add_row.call_args_list:
                args = call[0]  # Get positional arguments
                for arg in args:
                    assert isinstance(arg, str), f"Expected str but got {type(arg)}"
                    assert not isinstance(arg, LineLimit), "Should not wrap with LineLimit when disabled"
