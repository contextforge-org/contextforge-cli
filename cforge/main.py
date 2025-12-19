# -*- coding: utf-8 -*-
"""Location: ./cforge/main.py
Copyright 2025
SPDX-License-Identifier: Apache-2.0
Authors: Gabe Goodhart

Context Forge CLI - A comprehensive command-line interface for MCP Gateway operations.

This module provides a multi-action CLI using Typer for:
- Server management (serve command - uvicorn wrapper)
- Authentication (login command)
- Entity management (tools, resources, prompts, gateways, servers, a2a agents)
- Configuration export/import
- Metrics management
- Deployment operations (stub for future use)

Features:
- Beautiful output using Rich library
- Comprehensive command groups for all API endpoints
- Authentication token management
- Configuration validation
- Support bundle generation
"""

# Future
from __future__ import annotations

# Third-Party
import typer

# First-Party
from cforge.common import get_app
from cforge.commands.deploy.deploy import deploy
from cforge.commands.server.serve import serve
from cforge.commands.settings import profiles
from cforge.commands.settings.login import login
from cforge.commands.settings.logout import logout
from cforge.commands.settings.whoami import whoami
from cforge.commands.settings.export import export
from cforge.commands.settings.import_cmd import import_cmd
from cforge.commands.settings.config_schema import config_schema
from cforge.commands.settings.support_bundle import support_bundle
from cforge.commands.settings.version import version
from cforge.commands.metrics.metrics import metrics_get, metrics_reset
from cforge.commands.resources.tools import (
    tools_list,
    tools_get,
    tools_create,
    tools_update,
    tools_delete,
    tools_toggle,
)
from cforge.commands.resources.resources import (
    resources_list,
    resources_get,
    resources_create,
    resources_update,
    resources_delete,
    resources_toggle,
    resources_templates,
)
from cforge.commands.resources.prompts import (
    prompts_list,
    prompts_get,
    prompts_create,
    prompts_update,
    prompts_delete,
    prompts_toggle,
    prompts_execute,
)
from cforge.commands.resources.mcp_servers import (
    mcp_servers_list,
    mcp_servers_get,
    mcp_servers_create,
    mcp_servers_update,
    mcp_servers_delete,
    mcp_servers_toggle,
)
from cforge.commands.resources.virtual_servers import (
    virtual_servers_list,
    virtual_servers_get,
    virtual_servers_create,
    virtual_servers_update,
    virtual_servers_delete,
    virtual_servers_toggle,
    virtual_servers_tools,
    virtual_servers_resources,
    virtual_servers_prompts,
)
from cforge.commands.resources.a2a import (
    a2a_list,
    a2a_get,
    a2a_create,
    a2a_update,
    a2a_delete,
    a2a_toggle,
    a2a_invoke,
)

# Get the main app singleton
app = get_app()

# ---------------------------------------------------------------------------
# Server command
# ---------------------------------------------------------------------------

app.command(rich_help_panel="Server")(serve)

# ---------------------------------------------------------------------------
# Settings commands
# ---------------------------------------------------------------------------

app.command(rich_help_panel="Settings")(login)
app.command(rich_help_panel="Settings")(logout)
app.command(rich_help_panel="Settings")(whoami)
app.command(name="import", rich_help_panel="Settings")(import_cmd)
app.command(rich_help_panel="Settings")(export)
app.command(rich_help_panel="Settings")(config_schema)
app.command(rich_help_panel="Settings")(support_bundle)
app.command(rich_help_panel="Settings")(version)

# ---------------------------------------------------------------------------
# Profiles command group
# ---------------------------------------------------------------------------

profiles_app = typer.Typer(
    name="profiles",
    help="Manage user profiles for connecting to different Context Forge instances",
    rich_markup_mode="rich",
)
app.add_typer(profiles_app, name="profiles", rich_help_panel="Settings")
profiles_app.command("list")(profiles.profiles_list)
profiles_app.command("get")(profiles.profiles_get)
profiles_app.command("switch")(profiles.profiles_switch)
profiles_app.command("create")(profiles.profiles_create)

# ---------------------------------------------------------------------------
# Deploy command (hidden stub for future use)
# ---------------------------------------------------------------------------

app.command(hidden=True, rich_help_panel="Deployment")(deploy)

# ---------------------------------------------------------------------------
# Tools command group
# ---------------------------------------------------------------------------

tools_app = typer.Typer(help="Manage MCP tools")
app.add_typer(tools_app, name="tools", rich_help_panel="Resources")

tools_app.command("list")(tools_list)
tools_app.command("get")(tools_get)
tools_app.command("create")(tools_create)
tools_app.command("update")(tools_update)
tools_app.command("delete")(tools_delete)
tools_app.command("toggle")(tools_toggle)

# ---------------------------------------------------------------------------
# Resources command group
# ---------------------------------------------------------------------------

resources_app = typer.Typer(help="Manage MCP resources")
app.add_typer(resources_app, name="resources", rich_help_panel="Resources")

resources_app.command("list")(resources_list)
resources_app.command("get")(resources_get)
resources_app.command("create")(resources_create)
resources_app.command("update")(resources_update)
resources_app.command("delete")(resources_delete)
resources_app.command("toggle")(resources_toggle)
resources_app.command("templates")(resources_templates)

# ---------------------------------------------------------------------------
# Prompts command group
# ---------------------------------------------------------------------------

prompts_app = typer.Typer(help="Manage MCP prompts")
app.add_typer(prompts_app, name="prompts", rich_help_panel="Resources")

prompts_app.command("list")(prompts_list)
prompts_app.command("get")(prompts_get)
prompts_app.command("create")(prompts_create)
prompts_app.command("update")(prompts_update)
prompts_app.command("delete")(prompts_delete)
prompts_app.command("toggle")(prompts_toggle)
prompts_app.command("execute")(prompts_execute)

# ---------------------------------------------------------------------------
# MCP Servers (Gateways) command group
# ---------------------------------------------------------------------------

mcp_servers_app = typer.Typer(help="Manage MCP servers (gateway peers)")
app.add_typer(mcp_servers_app, name="mcp-servers", rich_help_panel="Resources")

mcp_servers_app.command("list")(mcp_servers_list)
mcp_servers_app.command("get")(mcp_servers_get)
mcp_servers_app.command("create")(mcp_servers_create)
mcp_servers_app.command("update")(mcp_servers_update)
mcp_servers_app.command("delete")(mcp_servers_delete)
mcp_servers_app.command("toggle")(mcp_servers_toggle)

# ---------------------------------------------------------------------------
# Virtual Servers command group
# ---------------------------------------------------------------------------

virtual_servers_app = typer.Typer(help="Manage virtual servers (composite MCP servers)")
app.add_typer(virtual_servers_app, name="virtual-servers", rich_help_panel="Resources")

virtual_servers_app.command("list")(virtual_servers_list)
virtual_servers_app.command("get")(virtual_servers_get)
virtual_servers_app.command("create")(virtual_servers_create)
virtual_servers_app.command("update")(virtual_servers_update)
virtual_servers_app.command("delete")(virtual_servers_delete)
virtual_servers_app.command("toggle")(virtual_servers_toggle)
virtual_servers_app.command("tools")(virtual_servers_tools)
virtual_servers_app.command("resources")(virtual_servers_resources)
virtual_servers_app.command("prompts")(virtual_servers_prompts)

# ---------------------------------------------------------------------------
# A2A Agents command group
# ---------------------------------------------------------------------------

a2a_app = typer.Typer(help="Manage Agent-to-Agent (A2A) agents")
app.add_typer(a2a_app, name="a2a", rich_help_panel="Resources")

a2a_app.command("list")(a2a_list)
a2a_app.command("get")(a2a_get)
a2a_app.command("create")(a2a_create)
a2a_app.command("update")(a2a_update)
a2a_app.command("delete")(a2a_delete)
a2a_app.command("toggle")(a2a_toggle)
a2a_app.command("invoke")(a2a_invoke)

# ---------------------------------------------------------------------------
# Metrics command group
# ---------------------------------------------------------------------------

metrics_app = typer.Typer(help="View and manage metrics")
app.add_typer(metrics_app, name="metrics", rich_help_panel="Resources")

metrics_app.command("get")(metrics_get)
metrics_app.command("reset")(metrics_reset)

# ---------------------------------------------------------------------------
# Main entry point
# ---------------------------------------------------------------------------


def main() -> None:
    """Entry point for the mcpgateway console script."""
    app()  # pragma: no cover


if __name__ == "__main__":
    main()
