# -*- coding: utf-8 -*-
"""Location: ./tests/commands/settings/test_config_schema.py
Copyright 2025
SPDX-License-Identifier: Apache-2.0
Authors: Gabe Goodhart

Tests for the config-schema command.
"""

# Standard
import json
import tempfile
from pathlib import Path
from unittest.mock import patch

# First-Party
from cforge.commands.settings.config_schema import config_schema


class TestConfigSchemaCommand:
    """Tests for config-schema command."""

    def test_config_schema_to_stdout(self, mock_settings, mock_console) -> None:
        """Test config_schema prints to stdout when no output file specified."""
        # mock_schema = {"type": "object", "properties": {"test": {"type": "string"}}}

        with patch("cforge.commands.settings.config_schema.get_console", return_value=mock_console):
            with patch("cforge.commands.settings.config_schema.get_settings", return_value=mock_settings):
                with patch("cforge.commands.settings.config_schema.print_json") as mock_print_json:
                    config_schema(output=None)

        # Verify print_json was called with schema and title
        mock_print_json.assert_called_once()
        call_args = mock_print_json.call_args
        assert "Configuration Schema" in call_args[0]

    def test_config_schema_to_file(self, mock_settings, mock_console) -> None:
        """Test config_schema writes to file when output specified."""
        with tempfile.TemporaryDirectory() as temp_dir:
            output_file = Path(temp_dir) / "schema.json"

            with patch("cforge.commands.settings.config_schema.get_console", return_value=mock_console):
                with patch("cforge.commands.settings.config_schema.get_settings", return_value=mock_settings):
                    config_schema(output=output_file)

            # Verify file was created
            assert output_file.exists()

            # Verify it's valid JSON
            data = json.loads(output_file.read_text())
            assert isinstance(data, dict)

            # Verify console output
            assert any("Schema written" in str(call) for call in mock_console.print.call_args_list)
