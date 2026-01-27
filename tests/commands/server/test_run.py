# -*- coding: utf-8 -*-
"""Location: ./tests/commands/server/test_run.py
Copyright 2025
SPDX-License-Identifier: Apache-2.0
Authors: Gabe Goodhart

Tests for the run command.
"""

# Standard
from unittest.mock import patch

# First-Party
from cforge.commands.server.run import run
from tests.conftest import invoke_typer_command


class TestRunCommand:
    """Tests for run command."""

    def test_run_with_stdio_defaults(self) -> None:
        """Test run command with stdio and default parameters."""
        with patch("mcpgateway.translate.main") as mock_translate, patch("multiprocessing.Process") as mock_process:
            invoke_typer_command(run, stdio="uvx mcp-server-git", register=False)
            mock_process.assert_called_once()
            call_args = mock_process.call_args[1]
            assert call_args.get("target") is mock_translate
            args = call_args["args"][0]
            assert "--stdio" in args
            assert "uvx mcp-server-git" in args
            assert "--port" in args
            assert "8000" in args
            assert "--host" in args
            assert "127.0.0.1" in args

    def test_run_with_custom_port_and_host(self) -> None:
        """Test run command with custom port and host."""
        with patch("mcpgateway.translate.main") as mock_translate, patch("multiprocessing.Process") as mock_process:
            invoke_typer_command(run, stdio="cat", port=9000, host="0.0.0.0", register=False)
            mock_process.assert_called_once()
            call_args = mock_process.call_args[1]
            assert call_args.get("target") is mock_translate
            args = call_args["args"][0]
            assert "--port" in args
            assert "9000" in args
            assert "--host" in args
            assert "0.0.0.0" in args

    def test_run_with_expose_sse(self) -> None:
        """Test run command with SSE exposure enabled."""
        with patch("mcpgateway.translate.main") as mock_translate, patch("multiprocessing.Process") as mock_process:
            invoke_typer_command(run, stdio="cat", expose_sse=True, register=False)
            mock_process.assert_called_once()
            call_args = mock_process.call_args[1]
            assert call_args.get("target") is mock_translate
            args = call_args["args"][0]
            assert "--expose-sse" in args

    def test_run_with_expose_streamable_http(self) -> None:
        """Test run command with streamable HTTP exposure enabled."""
        with patch("mcpgateway.translate.main") as mock_translate, patch("multiprocessing.Process") as mock_process:
            invoke_typer_command(run, stdio="cat", expose_streamable_http=True, register=False)
            mock_process.assert_called_once()
            call_args = mock_process.call_args[1]
            assert call_args.get("target") is mock_translate
            args = call_args["args"][0]
            assert "--expose-streamable-http" in args

    def test_run_with_both_protocols(self) -> None:
        """Test run command with both SSE and streamable HTTP enabled."""
        with patch("mcpgateway.translate.main") as mock_translate, patch("multiprocessing.Process") as mock_process:
            invoke_typer_command(run, stdio="cat", expose_sse=True, expose_streamable_http=True, register=False)
            mock_process.assert_called_once()
            call_args = mock_process.call_args[1]
            assert call_args.get("target") is mock_translate
            args = call_args["args"][0]
            assert "--expose-sse" in args
            assert "--expose-streamable-http" in args

    def test_run_with_grpc(self) -> None:
        """Test run command with gRPC server exposure."""
        with patch("mcpgateway.translate.main") as mock_translate, patch("multiprocessing.Process") as mock_process:
            invoke_typer_command(run, grpc="localhost:50051", register=False)
            mock_process.assert_called_once()
            call_args = mock_process.call_args[1]
            assert call_args.get("target") is mock_translate
            args = call_args["args"][0]
            assert "--grpc" in args
            assert "localhost:50051" in args

    def test_run_with_grpc_tls(self) -> None:
        """Test run command with gRPC TLS enabled."""
        with patch("mcpgateway.translate.main") as mock_translate, patch("multiprocessing.Process") as mock_process:
            invoke_typer_command(run, grpc="localhost:50051", grpc_tls=True, grpc_cert="/path/to/cert", grpc_key="/path/to/key", register=False)
            mock_process.assert_called_once()
            call_args = mock_process.call_args[1]
            assert call_args.get("target") is mock_translate
            args = call_args["args"][0]
            assert "--grpc-tls" in args
            assert "--grpc-cert" in args
            assert "/path/to/cert" in args
            assert "--grpc-key" in args
            assert "/path/to/key" in args

    def test_run_with_grpc_metadata(self) -> None:
        """Test run command with gRPC metadata."""
        with patch("mcpgateway.translate.main") as mock_translate, patch("multiprocessing.Process") as mock_process:
            invoke_typer_command(run, grpc="localhost:50051", grpc_metadata=["key1=value1", "key2=value2"], register=False)
            mock_process.assert_called_once()
            call_args = mock_process.call_args[1]
            assert call_args.get("target") is mock_translate
            args = call_args["args"][0]
            assert "--grpc-metadata" in args
            assert "key1=value1" in args
            assert "key2=value2" in args

    def test_run_with_cors(self) -> None:
        """Test run command with CORS origins."""
        with patch("mcpgateway.translate.main") as mock_translate, patch("multiprocessing.Process") as mock_process:
            invoke_typer_command(run, stdio="cat", cors=["https://app.example.com", "https://web.example.com"], register=False)
            mock_process.assert_called_once()
            call_args = mock_process.call_args[1]
            assert call_args.get("target") is mock_translate
            args = call_args["args"][0]
            assert "--cors" in args
            assert "https://app.example.com" in args
            assert "https://web.example.com" in args

    def test_run_with_oauth2_bearer(self) -> None:
        """Test run command with OAuth2 bearer token."""
        with patch("mcpgateway.translate.main") as mock_translate, patch("multiprocessing.Process") as mock_process:
            invoke_typer_command(run, stdio="cat", oauth2_bearer="token123", register=False)
            mock_process.assert_called_once()
            call_args = mock_process.call_args[1]
            assert call_args.get("target") is mock_translate
            args = call_args["args"][0]
            assert "--oauth2Bearer" in args
            assert "token123" in args

    def test_run_with_custom_sse_paths(self) -> None:
        """Test run command with custom SSE paths."""
        with patch("mcpgateway.translate.main") as mock_translate, patch("multiprocessing.Process") as mock_process:
            invoke_typer_command(run, stdio="cat", sse_path="/events", message_path="/send", register=False)
            mock_process.assert_called_once()
            call_args = mock_process.call_args[1]
            assert call_args.get("target") is mock_translate
            args = call_args["args"][0]
            assert "--ssePath" in args
            assert "/events" in args
            assert "--messagePath" in args
            assert "/send" in args

    def test_run_with_custom_keep_alive(self) -> None:
        """Test run command with custom keep-alive interval."""
        with patch("mcpgateway.translate.main") as mock_translate, patch("multiprocessing.Process") as mock_process:
            invoke_typer_command(run, stdio="cat", keep_alive=60, register=False)
            mock_process.assert_called_once()
            call_args = mock_process.call_args[1]
            assert call_args.get("target") is mock_translate
            args = call_args["args"][0]
            assert "--keepAlive" in args
            assert "60" in args

    def test_run_with_stdio_command(self) -> None:
        """Test run command with stdio command for bridging."""
        with patch("mcpgateway.translate.main") as mock_translate, patch("multiprocessing.Process") as mock_process:
            invoke_typer_command(run, stdio="cat", stdio_command="uvx mcp-client", register=False)
            mock_process.assert_called_once()
            call_args = mock_process.call_args[1]
            assert call_args.get("target") is mock_translate
            args = call_args["args"][0]
            assert "--stdioCommand" in args
            assert "uvx mcp-client" in args

    def test_run_with_dynamic_env(self) -> None:
        """Test run command with dynamic environment injection."""
        with patch("mcpgateway.translate.main") as mock_translate, patch("multiprocessing.Process") as mock_process:
            invoke_typer_command(run, stdio="cat", enable_dynamic_env=True, header_to_env=["Authorization=AUTH_TOKEN", "X-API-Key=API_KEY"], register=False)
            mock_process.assert_called_once()
            call_args = mock_process.call_args[1]
            assert call_args.get("target") is mock_translate
            args = call_args["args"][0]
            assert "--enable-dynamic-env" in args
            assert "--header-to-env" in args
            assert "Authorization=AUTH_TOKEN" in args
            assert "X-API-Key=API_KEY" in args

    def test_run_with_stateless_mode(self) -> None:
        """Test run command with stateless mode for streamable HTTP."""
        with patch("mcpgateway.translate.main") as mock_translate, patch("multiprocessing.Process") as mock_process:
            invoke_typer_command(run, stdio="cat", expose_streamable_http=True, stateless=True, register=False)
            mock_process.assert_called_once()
            call_args = mock_process.call_args[1]
            assert call_args.get("target") is mock_translate
            args = call_args["args"][0]
            assert "--stateless" in args

    def test_run_with_json_response(self) -> None:
        """Test run command with JSON response mode."""
        with patch("mcpgateway.translate.main") as mock_translate, patch("multiprocessing.Process") as mock_process:
            invoke_typer_command(run, stdio="cat", expose_streamable_http=True, json_response=True, register=False)
            mock_process.assert_called_once()
            call_args = mock_process.call_args[1]
            assert call_args.get("target") is mock_translate
            args = call_args["args"][0]
            assert "--jsonResponse" in args

    def test_run_with_log_level(self) -> None:
        """Test run command with custom log level."""
        with patch("mcpgateway.translate.main") as mock_translate, patch("multiprocessing.Process") as mock_process:
            invoke_typer_command(run, stdio="cat", log_level="debug", register=False)
            mock_process.assert_called_once()
            call_args = mock_process.call_args[1]
            assert call_args.get("target") is mock_translate
            args = call_args["args"][0]
            assert "--logLevel" in args
            assert "debug" in args

    def test_run_with_all_options(self) -> None:
        """Test run command with all options enabled."""
        with patch("mcpgateway.translate.main") as mock_translate, patch("multiprocessing.Process") as mock_process, patch("cforge.commands.server.run.make_authenticated_request") as mock_request:

            mock_request.return_value = {"id": "test-server-id"}

            invoke_typer_command(
                run,
                stdio="uvx mcp-server-git",
                expose_sse=True,
                expose_streamable_http=True,
                port=9000,
                host="0.0.0.0",
                log_level="debug",
                cors=["https://app.example.com"],
                sse_path="/events",
                message_path="/send",
                keep_alive=60,
                enable_dynamic_env=True,
                header_to_env=["Authorization=AUTH_TOKEN"],
                stateless=True,
                json_response=True,
                register=False,
            )
            mock_process.assert_called_once()
            call_args = mock_process.call_args[1]
            assert call_args.get("target") is mock_translate
            args = call_args["args"][0]
            # Verify key arguments are present
            assert "--stdio" in args
            assert "uvx mcp-server-git" in args
            assert "--expose-sse" in args
            assert "--expose-streamable-http" in args
            assert "--port" in args
            assert "9000" in args
            assert "--host" in args
            assert "0.0.0.0" in args
            assert "--logLevel" in args
            assert "debug" in args
            assert "--cors" in args
            assert "https://app.example.com" in args
            assert "--ssePath" in args
            assert "/events" in args
            assert "--messagePath" in args
            assert "/send" in args
            assert "--keepAlive" in args
            assert "60" in args
            assert "--enable-dynamic-env" in args
            assert "--header-to-env" in args
            assert "Authorization=AUTH_TOKEN" in args
            assert "--stateless" in args
            assert "--jsonResponse" in args
