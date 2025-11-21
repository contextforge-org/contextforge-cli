# -*- coding: utf-8 -*-
"""Location: ./cforge/settings/common.py
Copyright 2025
SPDX-License-Identifier: Apache-2.0
Authors: Gabe Goodhart

CLI-specific superset of core settings
"""

# Standard
from functools import lru_cache
from pathlib import Path
from typing import Optional, Self

# Third-Party
from pydantic import Field, model_validator

# First-Party
from mcpgateway.config import Settings


class CLISettings(Settings):
    """CLI-specific superset of core settings."""

    contextforge_home: Path = Field(default_factory=lambda: Path.home() / ".contextforge")

    @model_validator(mode="after")
    def _set_database_url_default(self) -> Self:
        """Set database URL to contextforge_home/mcp.db if not set.

        TODO: Support user overrides by detecting the difference with the
            default better.

        Returns:
            Self: The settings instance.
        """
        self.database_url = f"sqlite:///{self.contextforge_home}/mcp.db"
        return self

    mcpgateway_bearer_token: Optional[str] = None


@lru_cache
def get_settings() -> CLISettings:
    """Retrieve the cached instance of settings with env overrides.
    Returns:
        CLISettings: The settings instance.
    """
    return CLISettings()
