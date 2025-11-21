# ContextForge CLI

<!--
TODO: Enable once pushed to PyPI
[![PyPI version](https://img.shields.io/pypi/v/cforge.svg)](https://pypi.org/project/cforge/)
-->
[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![License](https://img.shields.io/badge/License-Apache%202.0-blue.svg)](LICENSE)

**A command-line interface for managing [ContextForge MCP Gateway](https://github.com/IBM/mcp-context-forge)** — seamlessly manage local or hosted MCP servers, tools, resources, prompts, and Agent-to-Agent services.

> **Part of the [ContextForge](https://github.com/IBM/mcp-context-forge) ecosystem** by IBM

---

## Quick Start

### Installation

<!--
TODO: Enable once pushed to PyPI
```bash
# Using pip
pip install cforge

# Using uv (recommended)
uv pip install cforge
```
-->

```bash
pip install git+https://github.com/contextforge-org/contextforge-cli.git
```

### First Steps

```bash
# Authenticate with your gateway
cforge login

# List available tools
cforge tools list

# Start a local gateway server
cforge serve
```

---

## Features

| Capability | Description |
|------------|-------------|
| **MCP Server Management** | Register, configure, and monitor MCP server peers |
| **Tool Operations** | Create, update, toggle, and organize MCP tools |
| **Resource Management** | Manage MCP resources with subscription support |
| **Prompt Library** | Store, organize, and execute prompt templates |
| **Virtual Servers** | Build composite servers from multiple sources |
| **A2A Integration** | Manage and invoke Agent-to-Agent services |
| **Config Import/Export** | Backup and migrate gateway configurations |

---

## Commands

### Authentication & Settings

```bash
cforge login              # Authenticate with the gateway
cforge logout             # Clear saved credentials
cforge whoami             # Show current user
cforge version            # Display CLI version
```

### Resource Management

To see the full set of available comands, use `cforge --help`. To see the options for a sub command, use `cforge <command> --help`.

Here are some examples:

```bash
# Tools
cforge tools list [--mcp-server-id ID] [--json]
cforge tools get <tool-id>
cforge tools create [file.json]
cforge tools toggle <tool-id>

# Resources
cforge resources list
cforge resources create [file.json]

# Prompts
cforge prompts list
cforge prompts execute <prompt-id>

# MCP Servers
cforge mcp-servers list
cforge mcp-servers update <mcp-server-id> [file.json]
```

### Server Operations

```bash
# Start the gateway server
cforge serve [--host HOST] [--port PORT] [--reload]

# Configuration management
cforge export [--output file.json]
cforge import <file.json>
cforge support-bundle      # Generate diagnostics
```

### Output Options

Most commands support:
- `--json` — Output raw JSON instead of formatted tables
- `--mcp-server-id` — Filter by specific MCP server
- `--active-only` — Show only enabled items

---

## Configuration

### Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `CONTEXTFORGE_HOME` | `~/.contextforge` | Configuration directory |
| `MCG_HOST` | `localhost` | Gateway host |
| `MCG_PORT` | `8000` | Gateway port |

Additionally, all configuration in `mcpgateway` can be set via the environment or via `CONTEXTFORGE_HOME/.env`. For full details, see [the docs](https://ibm.github.io/mcp-context-forge/#complete-migration-guide).

---

## Development

### Setup

```bash
git clone https://github.com/contextforge-org/contextforge-cli.git
cd contextforge-cli
pip install -e ".[dev]"
```

### Running Tests

```bash
pytest
```

---

## Related Projects

- **[ContextForge MCP Gateway](https://github.com/IBM/mcp-context-forge)** — The gateway server this CLI manages
- **[MCP Specification](https://modelcontextprotocol.io/)** — Model Context Protocol documentation

---

## License

Apache 2.0 — See [LICENSE](LICENSE) for details.

---

## Contributing

Contributions welcome! Please see the [ContextForge contributing guidelines](https://github.com/IBM/mcp-context-forge/blob/main/CONTRIBUTING.md).
