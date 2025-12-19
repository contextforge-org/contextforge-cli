# -*- coding: utf-8 -*-
"""Location: ./tests/commands/settings/test_export.py
Copyright 2025
SPDX-License-Identifier: Apache-2.0
Authors: Gabe Goodhart

Tests for the export command.
"""

# Standard
import json
import tempfile
from pathlib import Path
from unittest.mock import patch

# Third-Party
import pytest
import typer

# First-Party
from cforge.commands.settings.export import export


class TestExportCommand:
    """Tests for export command."""

    def test_export_with_custom_output(self, mock_base_url, mock_console) -> None:
        """Test export with custom output file."""
        mock_export_data = {
            "version": "1.0",
            "exported_at": "2025-01-01T00:00:00",
            "metadata": {"entity_counts": {"tools": 5, "prompts": 3}},
        }

        with tempfile.TemporaryDirectory() as temp_dir:
            output_file = Path(temp_dir) / "export.json"

            with patch("cforge.commands.settings.export.get_console", return_value=mock_console):
                with patch("cforge.commands.settings.export.get_base_url", return_value=mock_base_url):
                    with patch("cforge.commands.settings.export.make_authenticated_request", return_value=mock_export_data):
                        export(output=output_file, types=None, exclude_types=None, tags=None, include_inactive=False, no_dependencies=False, verbose=False)

            # Verify file was created
            assert output_file.exists()
            data = json.loads(output_file.read_text())
            assert data["version"] == "1.0"
            assert data["metadata"]["entity_counts"]["tools"] == 5

    def test_export_with_default_filename(self, mock_base_url, mock_console) -> None:
        """Test export with auto-generated filename."""
        mock_export_data = {"metadata": {"entity_counts": {}}}
        import os

        with tempfile.TemporaryDirectory() as temp_dir:
            orig_dir = os.getcwd()
            try:
                os.chdir(temp_dir)
                with patch("cforge.commands.settings.export.get_console", return_value=mock_console):
                    with patch("cforge.commands.settings.export.get_base_url", return_value=mock_base_url):
                        with patch("cforge.commands.settings.export.make_authenticated_request", return_value=mock_export_data):
                            export(output=None, types=None, exclude_types=None, tags=None, include_inactive=False, no_dependencies=False, verbose=False)

                # Verify a file starting with "cforge-export-" was created
                export_files = list(Path(temp_dir).glob("cforge-export-*.json"))
                assert len(export_files) > 0
            finally:
                os.chdir(orig_dir)

    def test_export_with_filters(self, mock_base_url, mock_console) -> None:
        """Test export with filter parameters."""
        mock_export_data = {"metadata": {"entity_counts": {}}}

        with tempfile.TemporaryDirectory() as temp_dir:
            output_file = Path(temp_dir) / "export.json"

            with patch("cforge.commands.settings.export.get_console", return_value=mock_console):
                with patch("cforge.commands.settings.export.get_base_url", return_value=mock_base_url):
                    with patch("cforge.commands.settings.export.make_authenticated_request", return_value=mock_export_data) as mock_request:
                        export(
                            output=output_file,
                            types="tools,prompts",
                            exclude_types="servers",
                            tags="test",
                            include_inactive=True,
                            no_dependencies=True,
                            verbose=False,
                        )

                    # Verify params were passed correctly
                    call_args = mock_request.call_args
                    params = call_args[1]["params"]
                    assert params["types"] == "tools,prompts"
                    assert params["exclude_types"] == "servers"
                    assert params["tags"] == "test"
                    assert params["include_inactive"] == "true"
                    assert params["include_dependencies"] == "false"

    def test_export_verbose_mode(self, mock_base_url, mock_console) -> None:
        """Test export with verbose output."""
        mock_export_data = {
            "version": "1.0",
            "exported_at": "2025-01-01T00:00:00",
            "exported_by": "test_user",
            "source_gateway": "test_gateway",
            "metadata": {"entity_counts": {"tools": 10}},
        }

        with tempfile.TemporaryDirectory() as temp_dir:
            output_file = Path(temp_dir) / "export.json"

            with patch("cforge.commands.settings.export.get_console", return_value=mock_console):
                with patch("cforge.commands.settings.export.get_base_url", return_value=mock_base_url):
                    with patch("cforge.commands.settings.export.make_authenticated_request", return_value=mock_export_data):
                        export(output=output_file, types=None, exclude_types=None, tags=None, include_inactive=False, no_dependencies=False, verbose=True)

            # Verify verbose output was printed
            assert any("Export details" in str(call) for call in mock_console.print.call_args_list)
            assert any("Version:" in str(call) for call in mock_console.print.call_args_list)

    def test_export_with_entity_counts(self, mock_base_url, mock_console) -> None:
        """Test export with non-zero entity counts."""
        mock_export_data = {"metadata": {"entity_counts": {"tools": 5, "prompts": 3, "servers": 0}}}

        with tempfile.TemporaryDirectory() as temp_dir:
            output_file = Path(temp_dir) / "export.json"

            with patch("cforge.commands.settings.export.get_console", return_value=mock_console):
                with patch("cforge.commands.settings.export.get_base_url", return_value=mock_base_url):
                    with patch("cforge.commands.settings.export.make_authenticated_request", return_value=mock_export_data):
                        export(output=output_file, types=None, exclude_types=None, tags=None, include_inactive=False, no_dependencies=False, verbose=False)

            # Verify only non-zero counts were printed
            output_str = str(mock_console.print.call_args_list)
            assert "tools: 5" in output_str
            assert "prompts: 3" in output_str
            # servers: 0 should not be printed (covered by if count > 0)

    def test_export_error_handling(self, mock_base_url, mock_console) -> None:
        """Test export error handling."""
        with patch("cforge.commands.settings.export.get_console", return_value=mock_console):
            with patch("cforge.commands.settings.export.get_base_url", return_value=mock_base_url):
                with patch("cforge.commands.settings.export.make_authenticated_request", side_effect=Exception("Export failed")):
                    with pytest.raises(typer.Exit) as exc_info:
                        export(output=None, types=None, exclude_types=None, tags=None, include_inactive=False, no_dependencies=False, verbose=False)

                    assert exc_info.value.exit_code == 1

            # Verify error message was printed
            assert any("Error:" in str(call) for call in mock_console.print.call_args_list)
