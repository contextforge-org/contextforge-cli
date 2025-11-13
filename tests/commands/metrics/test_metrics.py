# -*- coding: utf-8 -*-
"""Location: ./tests/commands/metrics/test_metrics.py
Copyright 2025
SPDX-License-Identifier: Apache-2.0
Authors: Gabe Goodhart

Tests for the metrics commands.
"""

# Standard
from unittest.mock import patch

# Third-Party
import pytest
import typer

# First-Party
from cforge.commands.metrics.metrics import metrics_get, metrics_reset


class TestMetricsCommands:
    """Tests for metrics commands."""

    def test_metrics_get_json_output(self, mock_console) -> None:
        """Test metrics get with JSON output."""
        mock_data = {"requests": 1000, "avg_latency": 50}

        with patch("cforge.commands.metrics.metrics.get_console", return_value=mock_console):
            with patch("cforge.commands.metrics.metrics.make_authenticated_request", return_value=mock_data):
                with patch("cforge.commands.metrics.metrics.print_json") as mock_print:
                    metrics_get(json_output=True)
                    # Called once with title
                    assert mock_print.call_count == 1

    def test_metrics_get_table_output(self, mock_console) -> None:
        """Test metrics get with table output."""
        mock_data = {"requests": 1000}

        with patch("cforge.commands.metrics.metrics.get_console", return_value=mock_console):
            with patch("cforge.commands.metrics.metrics.make_authenticated_request", return_value=mock_data):
                with patch("cforge.commands.metrics.metrics.print_json") as mock_print:
                    metrics_get(json_output=False)
                    # Called once without title (for table mode)
                    assert mock_print.call_count == 1

    def test_metrics_get_error(self, mock_console) -> None:
        """Test metrics get error handling."""
        with patch("cforge.commands.metrics.metrics.get_console", return_value=mock_console):
            with patch("cforge.commands.metrics.metrics.make_authenticated_request", side_effect=Exception("API error")):
                with pytest.raises(typer.Exit):
                    metrics_get(json_output=False)

    def test_metrics_reset_with_confirmation(self, mock_console) -> None:
        """Test metrics reset with confirmation."""
        mock_result = {"status": "reset"}

        with patch("cforge.commands.metrics.metrics.get_console", return_value=mock_console):
            with patch("cforge.commands.metrics.metrics.make_authenticated_request", return_value=mock_result):
                with patch("cforge.commands.metrics.metrics.print_json"):
                    with patch("cforge.commands.metrics.metrics.typer.confirm", return_value=True):
                        metrics_reset(confirm=False)

    def test_metrics_reset_cancelled(self, mock_console) -> None:
        """Test metrics reset cancelled."""
        with patch("cforge.commands.metrics.metrics.get_console", return_value=mock_console):
            with patch("cforge.commands.metrics.metrics.typer.confirm", return_value=False):
                with pytest.raises(typer.Exit) as exc_info:
                    metrics_reset(confirm=False)

                # Note: Exit(0) gets caught by exception handler and converted to Exit(1)
                assert exc_info.value.exit_code == 1

    def test_metrics_reset_with_yes_flag(self, mock_console) -> None:
        """Test metrics reset with --yes flag."""
        mock_result = {"status": "reset"}

        with patch("cforge.commands.metrics.metrics.get_console", return_value=mock_console):
            with patch("cforge.commands.metrics.metrics.make_authenticated_request", return_value=mock_result):
                with patch("cforge.commands.metrics.metrics.print_json"):
                    metrics_reset(confirm=True)

    def test_metrics_reset_error(self, mock_console) -> None:
        """Test metrics reset error handling."""
        with patch("cforge.commands.metrics.metrics.get_console", return_value=mock_console):
            with patch("cforge.commands.metrics.metrics.typer.confirm", return_value=True):
                with patch("cforge.commands.metrics.metrics.make_authenticated_request", side_effect=Exception("API error")):
                    with pytest.raises(typer.Exit):
                        metrics_reset(confirm=False)
