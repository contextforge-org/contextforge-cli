# -*- coding: utf-8 -*-
"""Location: ./tests/commands/deploy/test_deploy.py
Copyright 2025
SPDX-License-Identifier: Apache-2.0
Authors: Gabe Goodhart

Tests for the deploy command.
"""

# Standard
from unittest.mock import patch

# Third-Party
import pytest
import typer

# First-Party
from cforge.commands.deploy.deploy import deploy


class TestDeployCommand:
    """Tests for deploy command."""

    def test_deploy_stub(self, mock_console) -> None:
        """Test deploy command (placeholder stub)."""
        with patch("cforge.commands.deploy.deploy.get_console", return_value=mock_console):
            with pytest.raises(typer.Exit) as exc_info:
                deploy()

            assert exc_info.value.exit_code == 0

        # Verify stub message was printed
        assert any("not yet implemented" in str(call) for call in mock_console.print.call_args_list)
