# -*- coding: utf-8 -*-
"""Location: ./cforge/settings/common.py
Copyright 2025
SPDX-License-Identifier: Apache-2.0
Authors: Gabe Goodhart

CLI-specific superset of core settings
"""

# Standard
from contextlib import contextmanager
from functools import lru_cache
from pathlib import Path
from typing import Generator, Optional, Self
import os

# Third-Party
from pydantic import model_validator

# First-Party
from mcpgateway.config import Settings
from mcpgateway.config import get_settings as cf_get_settings


HOME_DIR_NAME = ".contextforge"
DEFAULT_HOME = Path.home() / HOME_DIR_NAME


@contextmanager
def _chdir(path: Path) -> Generator[None, None, None]:
    """Change the current working directory to the given path for the duration
    of the context
    """
    cwd = os.getcwd()
    os.chdir(path)
    try:
        yield
    finally:
        os.chdir(cwd)


class CLISettings(Settings):
    """CLI-specific superset of core settings."""

    contextforge_home: Path = DEFAULT_HOME

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

    # Max number of lines for printed tables (<1 => infinite)
    table_max_lines: int = 4


@lru_cache
def get_settings() -> CLISettings:
    """Retrieve the cached instance of settings with env overrides.
    Returns:
        CLISettings: The settings instance.
    """

    # Figure out the home directory from the env or default
    # NOTE: This duplicates the source of truth for the env var slightly so that
    #   we can use home as the source for the .env file as a 2-phase init.
    home = Path(os.getenv("CONTEXTFORGE_HOME", DEFAULT_HOME))
    home.mkdir(exist_ok=True)
    with _chdir(home):

        settings = CLISettings(client_mode=True)

        # Explicitly instantiate the singleton in the base library so all of the
        # libraries there use the override values
        cf_settings = cf_get_settings(client_mode=True)
        cf_settings.database_url = settings.database_url

    return settings


def set_serve_settings(**kwargs) -> None:
    """Reset the settings singleton to be server-side. This should only be used
    for server-side commands.
    """
    cforge_settings = get_settings()
    with _chdir(cforge_settings.contextforge_home):
        cf_get_settings.cache_clear()
        cf_settings = cf_get_settings()
        cf_settings.database_url = cforge_settings.database_url
        for k, v in kwargs.items():
            setattr(cf_settings, k, v)
