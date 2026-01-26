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
from typing import List, Optional

# Third-Party
import typer

# First-Party
from mcpgateway.translate import main as translate_main


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

    # Source/destination options (only if provided)
    if stdio is not None:
        args.extend(["--stdio", stdio])
    if grpc is not None:
        args.extend(["--grpc", grpc])

    # Protocol exposure options (only if True)
    if expose_sse:
        args.append("--expose-sse")
    if expose_streamable_http:
        args.append("--expose-streamable-http")

    # gRPC configuration (only if provided)
    if grpc_tls:
        args.append("--grpc-tls")
    if grpc_cert is not None:
        args.extend(["--grpc-cert", grpc_cert])
    if grpc_key is not None:
        args.extend(["--grpc-key", grpc_key])
    if grpc_metadata is not None:
        for metadata in grpc_metadata:
            args.extend(["--grpc-metadata", metadata])

    # Server configuration (always pass)
    args.extend(["--port", str(port)])
    args.extend(["--host", host])
    args.extend(["--logLevel", log_level])

    # CORS configuration (only if provided)
    if cors is not None:
        args.append("--cors")
        args.extend(cors)

    # Authentication (only if provided)
    if oauth2_bearer is not None:
        args.extend(["--oauth2Bearer", oauth2_bearer])

    # SSE configuration (always pass)
    args.extend(["--ssePath", sse_path])
    args.extend(["--messagePath", message_path])
    args.extend(["--keepAlive", str(keep_alive)])

    # Stdio command for bridging (only if provided)
    if stdio_command is not None:
        args.extend(["--stdioCommand", stdio_command])

    # Dynamic environment injection (only if enabled)
    if enable_dynamic_env:
        args.append("--enable-dynamic-env")
    if header_to_env is not None:
        for mapping in header_to_env:
            args.extend(["--header-to-env", mapping])

    # Streamable HTTP options (only if True)
    if stateless:
        args.append("--stateless")
    if json_response:
        args.append("--jsonResponse")

    # Call the translate main function with constructed arguments
    translate_main(args)
