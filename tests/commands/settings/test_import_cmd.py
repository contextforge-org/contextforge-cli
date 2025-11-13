# -*- coding: utf-8 -*-
"""Location: ./tests/commands/settings/test_import_cmd.py
Copyright 2025
SPDX-License-Identifier: Apache-2.0
Authors: Gabe Goodhart

Tests for the import command.
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
from cforge.commands.settings.import_cmd import import_cmd


class TestImportCommand:
    """Tests for import command."""

    def test_import_success(self, mock_console) -> None:
        """Test successful import."""
        mock_result = {
            "status": "completed",
            "progress": {"total": 10, "processed": 10, "created": 8, "updated": 2, "skipped": 0, "failed": 0},
        }

        with tempfile.TemporaryDirectory() as temp_dir:
            input_file = Path(temp_dir) / "import.json"
            input_file.write_text(json.dumps({"version": "1.0", "data": []}))

            with patch("cforge.commands.settings.import_cmd.get_console", return_value=mock_console):
                with patch("cforge.commands.settings.import_cmd.make_authenticated_request", return_value=mock_result):
                    import_cmd(input_file=input_file, conflict_strategy="update", dry_run=False, rekey_secret=None, include=None, verbose=False)

            # Verify success messages
            assert any("Import completed" in str(call) for call in mock_console.print.call_args_list)

    def test_import_file_not_found(self, mock_console) -> None:
        """Test import with missing file."""
        with patch("cforge.commands.settings.import_cmd.get_console", return_value=mock_console):
            with pytest.raises(typer.Exit) as exc_info:
                import_cmd(input_file=Path("/nonexistent/file.json"), conflict_strategy="update", dry_run=False, rekey_secret=None, include=None, verbose=False)

            assert exc_info.value.exit_code == 1

        # Verify error message
        assert any("Input file not found" in str(call) for call in mock_console.print.call_args_list)

    def test_import_with_failures(self, mock_console) -> None:
        """Test import with some failures."""
        mock_result = {"status": "completed", "progress": {"total": 10, "processed": 10, "failed": 5}}

        with tempfile.TemporaryDirectory() as temp_dir:
            input_file = Path(temp_dir) / "import.json"
            input_file.write_text(json.dumps({"version": "1.0"}))

            with patch("cforge.commands.settings.import_cmd.get_console", return_value=mock_console):
                with patch("cforge.commands.settings.import_cmd.make_authenticated_request", return_value=mock_result):
                    with pytest.raises(typer.Exit) as exc_info:
                        import_cmd(input_file=input_file, conflict_strategy="update", dry_run=False, rekey_secret=None, include=None, verbose=False)

                    assert exc_info.value.exit_code == 1

    def test_import_dry_run(self, mock_console) -> None:
        """Test import dry-run mode."""
        mock_result = {"status": "validated", "progress": {"total": 10, "processed": 0, "failed": 0}}

        with tempfile.TemporaryDirectory() as temp_dir:
            input_file = Path(temp_dir) / "import.json"
            input_file.write_text(json.dumps({"version": "1.0"}))

            with patch("cforge.commands.settings.import_cmd.get_console", return_value=mock_console):
                with patch("cforge.commands.settings.import_cmd.make_authenticated_request", return_value=mock_result):
                    import_cmd(input_file=input_file, conflict_strategy="update", dry_run=True, rekey_secret=None, include=None, verbose=False)

            # Verify dry-run message
            assert any("Dry-run validation completed" in str(call) for call in mock_console.print.call_args_list)

    def test_import_with_rekey_secret(self, mock_console) -> None:
        """Test import with rekey secret."""
        mock_result = {"status": "completed", "progress": {"failed": 0}}

        with tempfile.TemporaryDirectory() as temp_dir:
            input_file = Path(temp_dir) / "import.json"
            input_file.write_text(json.dumps({"version": "1.0"}))

            with patch("cforge.commands.settings.import_cmd.get_console", return_value=mock_console):
                with patch("cforge.commands.settings.import_cmd.make_authenticated_request", return_value=mock_result) as mock_request:
                    import_cmd(input_file=input_file, conflict_strategy="skip", dry_run=False, rekey_secret="new_secret", include=None, verbose=False)

                # Verify rekey_secret was passed
                call_args = mock_request.call_args
                assert call_args[1]["json_data"]["rekey_secret"] == "new_secret"

    def test_import_with_selective_include(self, mock_console) -> None:
        """Test import with selective entity inclusion."""
        mock_result = {"status": "completed", "progress": {"failed": 0}}

        with tempfile.TemporaryDirectory() as temp_dir:
            input_file = Path(temp_dir) / "import.json"
            input_file.write_text(json.dumps({"version": "1.0"}))

            with patch("cforge.commands.settings.import_cmd.get_console", return_value=mock_console):
                with patch("cforge.commands.settings.import_cmd.make_authenticated_request", return_value=mock_result) as mock_request:
                    import_cmd(
                        input_file=input_file,
                        conflict_strategy="update",
                        dry_run=False,
                        rekey_secret=None,
                        include="tool:tool1,tool2;server:server1",
                        verbose=False,
                    )

                # Verify selected_entities was parsed correctly
                call_args = mock_request.call_args
                selected = call_args[1]["json_data"]["selected_entities"]
                assert "tool" in selected
                assert "tool1" in selected["tool"]
                assert "tool2" in selected["tool"]
                assert "server" in selected
                assert "server1" in selected["server"]

    def test_import_with_warnings(self, mock_console) -> None:
        """Test import with warnings."""
        mock_result = {
            "status": "completed",
            "progress": {"failed": 0},
            "warnings": ["Warning 1", "Warning 2", "Warning 3"],
        }

        with tempfile.TemporaryDirectory() as temp_dir:
            input_file = Path(temp_dir) / "import.json"
            input_file.write_text(json.dumps({"version": "1.0"}))

            with patch("cforge.commands.settings.import_cmd.get_console", return_value=mock_console):
                with patch("cforge.commands.settings.import_cmd.make_authenticated_request", return_value=mock_result):
                    import_cmd(input_file=input_file, conflict_strategy="update", dry_run=False, rekey_secret=None, include=None, verbose=False)

            # Verify warnings were printed
            assert any("Warnings" in str(call) for call in mock_console.print.call_args_list)

    def test_import_with_errors(self, mock_console) -> None:
        """Test import with errors."""
        mock_result = {
            "status": "completed",
            "progress": {"failed": 0},
            "errors": ["Error 1", "Error 2"],
        }

        with tempfile.TemporaryDirectory() as temp_dir:
            input_file = Path(temp_dir) / "import.json"
            input_file.write_text(json.dumps({"version": "1.0"}))

            with patch("cforge.commands.settings.import_cmd.get_console", return_value=mock_console):
                with patch("cforge.commands.settings.import_cmd.make_authenticated_request", return_value=mock_result):
                    import_cmd(input_file=input_file, conflict_strategy="update", dry_run=False, rekey_secret=None, include=None, verbose=False)

            # Verify errors were printed
            assert any("Errors" in str(call) for call in mock_console.print.call_args_list)

    def test_import_with_many_warnings(self, mock_console) -> None:
        """Test import with more than 5 warnings (tests truncation)."""
        warnings_list = [f"Warning {i}" for i in range(10)]
        mock_result = {
            "status": "completed",
            "progress": {"failed": 0},
            "warnings": warnings_list,
        }

        with tempfile.TemporaryDirectory() as temp_dir:
            input_file = Path(temp_dir) / "import.json"
            input_file.write_text(json.dumps({"version": "1.0"}))

            with patch("cforge.commands.settings.import_cmd.get_console", return_value=mock_console):
                with patch("cforge.commands.settings.import_cmd.make_authenticated_request", return_value=mock_result):
                    import_cmd(input_file=input_file, conflict_strategy="update", dry_run=False, rekey_secret=None, include=None, verbose=False)

            # Verify "and N more warnings" message
            output_str = str(mock_console.print.call_args_list)
            assert "5 more warnings" in output_str

    def test_import_verbose_mode(self, mock_console) -> None:
        """Test import with verbose output."""
        mock_result = {
            "status": "completed",
            "progress": {"failed": 0},
            "import_id": "test_id",
            "started_at": "2025-01-01T00:00:00",
            "completed_at": "2025-01-01T00:01:00",
        }

        with tempfile.TemporaryDirectory() as temp_dir:
            input_file = Path(temp_dir) / "import.json"
            input_file.write_text(json.dumps({"version": "1.0"}))

            with patch("cforge.commands.settings.import_cmd.get_console", return_value=mock_console):
                with patch("cforge.commands.settings.import_cmd.make_authenticated_request", return_value=mock_result):
                    import_cmd(input_file=input_file, conflict_strategy="update", dry_run=False, rekey_secret=None, include=None, verbose=True)

            # Verify verbose output
            assert any("Import details" in str(call) for call in mock_console.print.call_args_list)
            assert any("Import ID:" in str(call) for call in mock_console.print.call_args_list)

    def test_import_exception_handling(self, mock_console) -> None:
        """Test import exception handling."""
        with tempfile.TemporaryDirectory() as temp_dir:
            input_file = Path(temp_dir) / "import.json"
            input_file.write_text(json.dumps({"version": "1.0"}))

            with patch("cforge.commands.settings.import_cmd.get_console", return_value=mock_console):
                with patch("cforge.commands.settings.import_cmd.make_authenticated_request", side_effect=Exception("Import failed")):
                    with pytest.raises(typer.Exit) as exc_info:
                        import_cmd(input_file=input_file, conflict_strategy="update", dry_run=False, rekey_secret=None, include=None, verbose=False)

                    assert exc_info.value.exit_code == 1

            # Verify error message
            assert any("Error:" in str(call) for call in mock_console.print.call_args_list)

    def test_import_with_many_errors(self, mock_console) -> None:
        """Test import with more than 5 errors (tests truncation)."""
        errors_list = [f"Error {i}" for i in range(10)]
        mock_result = {
            "status": "completed",
            "progress": {"failed": 0},
            "errors": errors_list,
        }

        with tempfile.TemporaryDirectory() as temp_dir:
            input_file = Path(temp_dir) / "import.json"
            input_file.write_text(json.dumps({"version": "1.0"}))

            with patch("cforge.commands.settings.import_cmd.get_console", return_value=mock_console):
                with patch("cforge.commands.settings.import_cmd.make_authenticated_request", return_value=mock_result):
                    import_cmd(input_file=input_file, conflict_strategy="update", dry_run=False, rekey_secret=None, include=None, verbose=False)

            # Verify "and N more errors" message
            output_str = str(mock_console.print.call_args_list)
            assert "5 more errors" in output_str

    def test_import_with_invalid_include_format(self, mock_console) -> None:
        """Test import with invalid include format (no colon)."""
        mock_result = {
            "status": "completed",
            "progress": {"failed": 0},
        }

        with tempfile.TemporaryDirectory() as temp_dir:
            input_file = Path(temp_dir) / "import.json"
            input_file.write_text(json.dumps({"version": "1.0"}))

            with patch("cforge.commands.settings.import_cmd.get_console", return_value=mock_console):
                with patch("cforge.commands.settings.import_cmd.make_authenticated_request", return_value=mock_result) as mock_request:
                    # Pass invalid format without colon
                    import_cmd(input_file=input_file, conflict_strategy="update", dry_run=False, rekey_secret=None, include="invalid_format", verbose=False)

                # Verify selected_entities is empty (invalid format is skipped)
                call_args = mock_request.call_args
                selected = call_args[1]["json_data"].get("selected_entities", {})
                # Should be empty dict since invalid format was skipped
                assert selected == {}
