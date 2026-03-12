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
import atexit
import multiprocessing
import os
import time
from typing import List, Optional

# Third-Party
import requests
import typer

# First-Party
from cforge.common.console import get_console
from cforge.common.http import make_authenticated_request


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
    register: bool = typer.Option(True, "--register/--no-register", help="Auto-register the server with the configured Context Forge gateway (default: True)"),
    register_timeout: float = typer.Option(10.0, "--register-timeout", help="Timeout for registration health check (default 10s)"),
    temporary: bool = typer.Option(False, "--temporary", help="Unregister the server on exit (only applies if --register is enabled)"),
    server_name: Optional[str] = typer.Option(None, "--server-name", help="Name for the registered server (auto-generated if not provided)"),
    server_description: Optional[str] = typer.Option(None, "--server-description", help="Description for the registered server"),
) -> None:
    """Run MCP servers locally and expose them via SSE or streamable HTTP.

    This command bridges between different MCP transport protocols: stdio/JSON-RPC,
    HTTP/SSE, and streamable HTTP. It enables exposing local MCP servers over HTTP
    or consuming remote endpoints as local stdio servers.

    By default, the server is automatically registered with the configured Context Forge
    gateway. Use --no-register to disable this behavior, or --temporary to automatically
    unregister the server when it exits.

    Examples:

        # Expose a local MCP server via SSE (auto-registered)
        cforge run --stdio "uvx mcp-server-git" --port 9000

        # Expose without registering with the gateway
        cforge run --stdio "uvx mcp-server-git" --port 9000 --no-register

        # Expose and auto-cleanup on exit
        cforge run --stdio "uvx mcp-server-git" --port 9000 --temporary

        # Expose via both SSE and streamable HTTP
        cforge run --stdio "uvx mcp-server-git" --expose-sse --expose-streamable-http --port 9000
    """
    console = get_console()

    # Handle registration if enabled
    if register and not temporary:
        # Validate that we have something to register
        if not stdio and not grpc:
            console.print("[yellow]Warning: --register requires either --stdio or --grpc to be specified[/yellow]")
            register = False

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

    # Import top-level translate here to avoid undesirable initialization
    # Third Party
    # First-Party
    from mcpgateway.translate import main as translate_main

    # Launch the translation wrapper in a subprocess
    proc = multiprocessing.Process(target=translate_main, args=(args,))
    proc.start()

    # Register if requested
    if register:

        # Default to SSE if no protocol specified
        is_sse = expose_sse or expose_streamable_http or (not expose_sse and not expose_streamable_http)

        registered_server_id: Optional[str] = None
        try:
            # Wait for the server to come up
            server_url_base = f"http://{host}:{port}"
            start_time = time.time()
            ready = False
            while time.time() - start_time <= register_timeout:
                try:
                    res = requests.get(f"{server_url_base}/healthz", timeout=0.1)
                    if res.status_code == 200:
                        ready = True
                        break
                except requests.exceptions.ConnectionError:
                    time.sleep(0.5)
            if not ready:
                console.print(f"[red]Failed to connect to server in {register_timeout}s[/red]")
                typer.exit(1)

            # Build the server URL based on the protocol
            server_url = f"{server_url_base}{sse_path}" if is_sse else f"{server_url_base}/mcp"

            # Generate a name if not provided
            if server_name is None:
                if stdio:
                    # Extract command name from stdio
                    cmd_parts = stdio.split()
                    cmd_name = "stdio-server"
                    for part in cmd_parts:
                        part = os.path.basename(part)
                        # Skip known runners, flags, and env vars
                        if part.replace("-", "").replace("_", "").isalnum() and not (part.startswith("-") or part in ["docker", "uvx", "npx", "python", "node", "run"] or "=" in part):
                            cmd_name = part
                            break
                    server_name = f"{cmd_name}-{port}"
                elif grpc:
                    server_name = f"grpc-{grpc.replace(':', '-')}"
                else:
                    server_name = f"server-{port}"

            # Build registration payload
            registration_data = {
                "name": server_name,
                "url": server_url,
                "transport": "SSE" if is_sse else "STREAMABLEHTTP",
            }

            if server_description:
                registration_data["description"] = server_description

            # Register the server
            console.print(f"[cyan]Registering server '{server_name}' at {server_url}...[/cyan]")
            result = make_authenticated_request("POST", "/gateways", json_data=registration_data)
            registered_server_id = result.get("id")
            console.print(f"[green]✓ Server registered successfully (ID: {registered_server_id})[/green]")

            # Set up cleanup for temporary servers
            if temporary and registered_server_id:

                def cleanup_server():
                    """Unregister the server on exit."""
                    try:
                        console.print(f"\n[cyan]Unregistering temporary server (ID: {registered_server_id})...[/cyan]")
                        make_authenticated_request("DELETE", f"/gateways/{registered_server_id}")
                        console.print("[green]✓ Server unregistered successfully[/green]")
                    except Exception as e:
                        console.print(f"[yellow]Warning: Failed to unregister server: {e}[/yellow]")

                # Register cleanup handlers
                atexit.register(cleanup_server)

        except Exception as e:
            console.print(f"[yellow]Warning: Failed to register server: {e}[/yellow]")
            console.print("[yellow]Continuing without registration...[/yellow]")

    # Wait for the process to terminate
    proc.join()
