# -*- coding: utf-8 -*-
"""Location: ./cforge/commands/server/run.py
Copyright 2025
SPDX-License-Identifier: Apache-2.0
Authors: Gabe Goodhart

CLI command: run

Run MCP servers locally and expose them via SSE or streamable HTTP protocols.
This command wraps the mcpgateway.translate functionality to provide a unified
interface for running and exposing MCP servers.
"""

# Standard
from typing import Any, List, Optional

# Third-Party
import typer
from typer.models import OptionInfo

# First-Party
from mcpgateway.translate import main as translate_main


def _get_value(value: Any) -> Any:
    """Extract the actual value from a Typer OptionInfo object or return as-is.

    When calling Typer commands directly in tests (not via CLI), parameters that
    aren't explicitly provided remain as OptionInfo objects instead of being
    converted to their default values. This helper extracts the default value.
    """
    if isinstance(value, OptionInfo):
        return value.default
    return value


def run(
    stdio: Optional[str] = typer.Option(None, "--stdio", help='Local command to run, e.g. "uvx mcp-server-git"'),
    grpc: Optional[str] = typer.Option(None, "--grpc", help="gRPC server target (host:port) to expose"),
    expose_sse: bool = typer.Option(False, "--expose-sse", help="Expose via SSE protocol (endpoints: /sse and /message)"),
    expose_streamable_http: bool = typer.Option(False, "--expose-streamable-http", help="Expose via streamable HTTP protocol (endpoint: /mcp)"),
    grpc_tls: bool = typer.Option(False, "--grpc-tls", help="Enable TLS for gRPC connection"),
    grpc_cert: Optional[str] = typer.Option(None, "--grpc-cert", help="Path to TLS certificate for gRPC"),
    grpc_key: Optional[str] = typer.Option(None, "--grpc-key", help="Path to TLS key for gRPC"),
    grpc_metadata: Optional[List[str]] = typer.Option(None, "--grpc-metadata", help="gRPC metadata (KEY=VALUE, repeatable)"),
    port: int = typer.Option(8000, "--port", help="HTTP port to bind"),
    host: str = typer.Option("127.0.0.1", "--host", help="Host interface to bind (default: 127.0.0.1)"),
    log_level: str = typer.Option(
        "info",
        "--log-level",
        help="Log level (debug, info, warning, error, critical)",
    ),
    cors: Optional[List[str]] = typer.Option(None, "--cors", help="CORS allowed origins (e.g., --cors https://app.example.com)"),
    oauth2_bearer: Optional[str] = typer.Option(None, "--oauth2-bearer", help="OAuth2 Bearer token for authentication"),
    sse_path: str = typer.Option("/sse", "--sse-path", help="SSE endpoint path (default: /sse)"),
    message_path: str = typer.Option("/message", "--message-path", help="Message endpoint path (default: /message)"),
    keep_alive: int = typer.Option(30, "--keep-alive", help="Keep-alive interval in seconds (default: 30)"),
    stdio_command: Optional[str] = typer.Option(
        None,
        "--stdio-command",
        help="Command to run when bridging SSE/streamableHttp to stdio (optional with --connect-sse or --connect-streamable-http)",
    ),
    enable_dynamic_env: bool = typer.Option(False, "--enable-dynamic-env", help="Enable dynamic environment variable injection from HTTP headers"),
    header_to_env: Optional[List[str]] = typer.Option(
        None,
        "--header-to-env",
        help="Map HTTP header to environment variable (format: HEADER=ENV_VAR, can be used multiple times)",
    ),
    stateless: bool = typer.Option(False, "--stateless", help="Use stateless mode for streamable HTTP (default: False)"),
    json_response: bool = typer.Option(False, "--json-response", help="Return JSON responses instead of SSE streams for streamable HTTP (default: False)"),
) -> None:
    """Run MCP servers locally and expose them via SSE or streamable HTTP.

    This command bridges between different MCP transport protocols: stdio/JSON-RPC,
    HTTP/SSE, and streamable HTTP. It enables exposing local MCP servers over HTTP
    or consuming remote endpoints as local stdio servers.

    Examples:

        # Expose a local MCP server via SSE
        cforge run --stdio "uvx mcp-server-git" --port 9000

        # Expose via both SSE and streamable HTTP
        cforge run --stdio "uvx mcp-server-git" --expose-sse --expose-streamable-http --port 9000

        # Expose via streamable HTTP with stateless mode
        cforge run --stdio "uvx mcp-server-git" --expose-streamable-http --stateless --port 9000
    """
    # Build argument list for translate_main
    args = []

    # Extract actual values (handles both CLI and test invocation)
    stdio_val = _get_value(stdio)
    grpc_val = _get_value(grpc)
    expose_sse_val = _get_value(expose_sse)
    expose_streamable_http_val = _get_value(expose_streamable_http)
    grpc_tls_val = _get_value(grpc_tls)
    grpc_cert_val = _get_value(grpc_cert)
    grpc_key_val = _get_value(grpc_key)
    grpc_metadata_val = _get_value(grpc_metadata)
    port_val = _get_value(port)
    host_val = _get_value(host)
    log_level_val = _get_value(log_level)
    cors_val = _get_value(cors)
    oauth2_bearer_val = _get_value(oauth2_bearer)
    sse_path_val = _get_value(sse_path)
    message_path_val = _get_value(message_path)
    keep_alive_val = _get_value(keep_alive)
    stdio_command_val = _get_value(stdio_command)
    enable_dynamic_env_val = _get_value(enable_dynamic_env)
    header_to_env_val = _get_value(header_to_env)
    stateless_val = _get_value(stateless)
    json_response_val = _get_value(json_response)

    # Source/destination options (only if provided)
    if stdio_val is not None:
        args.extend(["--stdio", stdio_val])
    if grpc_val is not None:
        args.extend(["--grpc", grpc_val])

    # Protocol exposure options (only if True)
    if expose_sse_val:
        args.append("--expose-sse")
    if expose_streamable_http_val:
        args.append("--expose-streamable-http")

    # gRPC configuration (only if provided)
    if grpc_tls_val:
        args.append("--grpc-tls")
    if grpc_cert_val is not None:
        args.extend(["--grpc-cert", grpc_cert_val])
    if grpc_key_val is not None:
        args.extend(["--grpc-key", grpc_key_val])
    if grpc_metadata_val is not None:
        for metadata in grpc_metadata_val:
            args.extend(["--grpc-metadata", metadata])

    # Server configuration (always pass)
    args.extend(["--port", str(port_val)])
    args.extend(["--host", host_val])
    args.extend(["--logLevel", log_level_val])

    # CORS configuration (only if provided)
    if cors_val is not None:
        args.append("--cors")
        args.extend(cors_val)

    # Authentication (only if provided)
    if oauth2_bearer_val is not None:
        args.extend(["--oauth2Bearer", oauth2_bearer_val])

    # SSE configuration (always pass)
    args.extend(["--ssePath", sse_path_val])
    args.extend(["--messagePath", message_path_val])
    args.extend(["--keepAlive", str(keep_alive_val)])

    # Stdio command for bridging (only if provided)
    if stdio_command_val is not None:
        args.extend(["--stdioCommand", stdio_command_val])

    # Dynamic environment injection (only if enabled)
    if enable_dynamic_env_val:
        args.append("--enable-dynamic-env")
    if header_to_env_val is not None:
        for mapping in header_to_env_val:
            args.extend(["--header-to-env", mapping])

    # Streamable HTTP options (only if True)
    if stateless_val:
        args.append("--stateless")
    if json_response_val:
        args.append("--jsonResponse")

    # Call the translate main function with constructed arguments
    translate_main(args)
