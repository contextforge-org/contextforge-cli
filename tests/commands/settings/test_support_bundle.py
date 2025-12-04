# -*- coding: utf-8 -*-
"""Location: ./tests/commands/settings/test_support_bundle.py
Copyright 2025
SPDX-License-Identifier: Apache-2.0
Authors: Gabe Goodhart

Tests for the support-bundle command.
"""

# Standard
import tempfile
from pathlib import Path
from unittest.mock import Mock, patch

# Third-Party
import pytest
import typer

# First-Party
from cforge.commands.settings.support_bundle import support_bundle


class TestSupportBundleCommand:
    """Tests for support-bundle command."""

    def test_support_bundle_success(self, mock_console) -> None:
        """Test successful support bundle generation."""
        with tempfile.TemporaryDirectory() as temp_dir:
            bundle_path = Path(temp_dir) / "support_bundle.zip"
            bundle_path.write_text("fake bundle content")

            mock_service = Mock()
            mock_service.generate_bundle.return_value = bundle_path

            with patch("cforge.commands.settings.support_bundle.get_console", return_value=mock_console):
                with patch("mcpgateway.services.support_bundle_service.SupportBundleService", return_value=mock_service):
                    with patch("mcpgateway.services.support_bundle_service.SupportBundleConfig"):
                        support_bundle(output_dir=None, log_lines=1000, no_logs=False, no_env=False, no_system=False)

            # Verify service was called
            mock_service.generate_bundle.assert_called_once()

            # Verify console output
            assert any("Support bundle created" in str(call) for call in mock_console.print.call_args_list)
            assert any("Security Notice" in str(call) for call in mock_console.print.call_args_list)

    def test_support_bundle_with_custom_options(self, mock_console) -> None:
        """Test support bundle with custom options."""
        with tempfile.TemporaryDirectory() as temp_dir:
            output_dir = Path(temp_dir)
            bundle_path = output_dir / "support_bundle.zip"
            bundle_path.write_text("fake bundle content")

            mock_service = Mock()
            mock_service.generate_bundle.return_value = bundle_path

            with patch("cforge.commands.settings.support_bundle.get_console", return_value=mock_console):
                with patch("mcpgateway.services.support_bundle_service.SupportBundleService", return_value=mock_service):
                    with patch("mcpgateway.services.support_bundle_service.SupportBundleConfig") as mock_config:
                        support_bundle(output_dir=output_dir, log_lines=500, no_logs=True, no_env=True, no_system=True)

            # Verify config was created with custom options
            mock_config.assert_called_once()
            call_kwargs = mock_config.call_args[1]
            assert call_kwargs["include_logs"] is False
            assert call_kwargs["include_env"] is False
            assert call_kwargs["include_system_info"] is False
            assert call_kwargs["log_tail_lines"] == 500

    def test_support_bundle_exception(self, mock_console) -> None:
        """Test support bundle generation failure."""
        mock_service = Mock()
        mock_service.generate_bundle.side_effect = Exception("Bundle generation failed")

        with patch("cforge.commands.settings.support_bundle.get_console", return_value=mock_console):
            with patch("mcpgateway.services.support_bundle_service.SupportBundleService", return_value=mock_service):
                with patch("mcpgateway.services.support_bundle_service.SupportBundleConfig"):
                    with pytest.raises(typer.Exit) as exc_info:
                        support_bundle(output_dir=None, log_lines=1000, no_logs=False, no_env=False, no_system=False)

        # Should exit with code 1
        assert exc_info.value.exit_code == 1

        # Verify error message
        assert any("Failed to create support bundle" in str(call) for call in mock_console.print.call_args_list)
