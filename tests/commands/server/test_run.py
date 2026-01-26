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
        with patch("cforge.commands.server.run.translate_main") as mock_translate:
            invoke_typer_command(run, stdio="uvx mcp-server-git")
            mock_translate.assert_called_once()
            args = mock_translate.call_args[0][0]
            assert "--stdio" in args
            assert "uvx mcp-server-git" in args
            assert "--port" in args
            assert "8000" in args
            assert "--host" in args
            assert "127.0.0.1" in args

    def test_run_with_custom_port_and_host(self) -> None:
        """Test run command with custom port and host."""
        with patch("cforge.commands.server.run.translate_main") as mock_translate:
            invoke_typer_command(run, stdio="cat", port=9000, host="0.0.0.0")
            mock_translate.assert_called_once()
            args = mock_translate.call_args[0][0]
            assert "--port" in args
            assert "9000" in args
            assert "--host" in args
            assert "0.0.0.0" in args

    def test_run_with_expose_sse(self) -> None:
        """Test run command with SSE exposure enabled."""
        with patch("cforge.commands.server.run.translate_main") as mock_translate:
            invoke_typer_command(run, stdio="cat", expose_sse=True)
            mock_translate.assert_called_once()
            args = mock_translate.call_args[0][0]
            assert "--expose-sse" in args

    def test_run_with_expose_streamable_http(self) -> None:
        """Test run command with streamable HTTP exposure enabled."""
        with patch("cforge.commands.server.run.translate_main") as mock_translate:
            invoke_typer_command(run, stdio="cat", expose_streamable_http=True)
            mock_translate.assert_called_once()
            args = mock_translate.call_args[0][0]
            assert "--expose-streamable-http" in args

    def test_run_with_both_protocols(self) -> None:
        """Test run command with both SSE and streamable HTTP enabled."""
        with patch("cforge.commands.server.run.translate_main") as mock_translate:
            invoke_typer_command(run, stdio="cat", expose_sse=True, expose_streamable_http=True)
            mock_translate.assert_called_once()
            args = mock_translate.call_args[0][0]
            assert "--expose-sse" in args
            assert "--expose-streamable-http" in args

    def test_run_with_grpc(self) -> None:
        """Test run command with gRPC server exposure."""
        with patch("cforge.commands.server.run.translate_main") as mock_translate:
            invoke_typer_command(run, grpc="localhost:50051")
            mock_translate.assert_called_once()
            args = mock_translate.call_args[0][0]
            assert "--grpc" in args
            assert "localhost:50051" in args

    def test_run_with_grpc_tls(self) -> None:
        """Test run command with gRPC TLS enabled."""
        with patch("cforge.commands.server.run.translate_main") as mock_translate:
            invoke_typer_command(run, grpc="localhost:50051", grpc_tls=True, grpc_cert="/path/to/cert", grpc_key="/path/to/key")
            mock_translate.assert_called_once()
            args = mock_translate.call_args[0][0]
            assert "--grpc-tls" in args
            assert "--grpc-cert" in args
            assert "/path/to/cert" in args
            assert "--grpc-key" in args
            assert "/path/to/key" in args

    def test_run_with_grpc_metadata(self) -> None:
        """Test run command with gRPC metadata."""
        with patch("cforge.commands.server.run.translate_main") as mock_translate:
            invoke_typer_command(run, grpc="localhost:50051", grpc_metadata=["key1=value1", "key2=value2"])
            mock_translate.assert_called_once()
            args = mock_translate.call_args[0][0]
            assert "--grpc-metadata" in args
            assert "key1=value1" in args
            assert "key2=value2" in args

    def test_run_with_cors(self) -> None:
        """Test run command with CORS origins."""
        with patch("cforge.commands.server.run.translate_main") as mock_translate:
            invoke_typer_command(run, stdio="cat", cors=["https://app.example.com", "https://web.example.com"])
            mock_translate.assert_called_once()
            args = mock_translate.call_args[0][0]
            assert "--cors" in args
            assert "https://app.example.com" in args
            assert "https://web.example.com" in args

    def test_run_with_oauth2_bearer(self) -> None:
        """Test run command with OAuth2 bearer token."""
        with patch("cforge.commands.server.run.translate_main") as mock_translate:
            invoke_typer_command(run, stdio="cat", oauth2_bearer="token123")
            mock_translate.assert_called_once()
            args = mock_translate.call_args[0][0]
            assert "--oauth2Bearer" in args
            assert "token123" in args

    def test_run_with_custom_sse_paths(self) -> None:
        """Test run command with custom SSE paths."""
        with patch("cforge.commands.server.run.translate_main") as mock_translate:
            invoke_typer_command(run, stdio="cat", sse_path="/events", message_path="/send")
            mock_translate.assert_called_once()
            args = mock_translate.call_args[0][0]
            assert "--ssePath" in args
            assert "/events" in args
            assert "--messagePath" in args
            assert "/send" in args

    def test_run_with_custom_keep_alive(self) -> None:
        """Test run command with custom keep-alive interval."""
        with patch("cforge.commands.server.run.translate_main") as mock_translate:
            invoke_typer_command(run, stdio="cat", keep_alive=60)
            mock_translate.assert_called_once()
            args = mock_translate.call_args[0][0]
            assert "--keepAlive" in args
            assert "60" in args

    def test_run_with_stdio_command(self) -> None:
        """Test run command with stdio command for bridging."""
        with patch("cforge.commands.server.run.translate_main") as mock_translate:
            invoke_typer_command(run, stdio="cat", stdio_command="uvx mcp-client")
            mock_translate.assert_called_once()
            args = mock_translate.call_args[0][0]
            assert "--stdioCommand" in args
            assert "uvx mcp-client" in args

    def test_run_with_dynamic_env(self) -> None:
        """Test run command with dynamic environment injection."""
        with patch("cforge.commands.server.run.translate_main") as mock_translate:
            invoke_typer_command(run, stdio="cat", enable_dynamic_env=True, header_to_env=["Authorization=AUTH_TOKEN", "X-API-Key=API_KEY"])
            mock_translate.assert_called_once()
            args = mock_translate.call_args[0][0]
            assert "--enable-dynamic-env" in args
            assert "--header-to-env" in args
            assert "Authorization=AUTH_TOKEN" in args
            assert "X-API-Key=API_KEY" in args

    def test_run_with_stateless_mode(self) -> None:
        """Test run command with stateless mode for streamable HTTP."""
        with patch("cforge.commands.server.run.translate_main") as mock_translate:
            invoke_typer_command(run, stdio="cat", expose_streamable_http=True, stateless=True)
            mock_translate.assert_called_once()
            args = mock_translate.call_args[0][0]
            assert "--stateless" in args

    def test_run_with_json_response(self) -> None:
        """Test run command with JSON response mode."""
        with patch("cforge.commands.server.run.translate_main") as mock_translate:
            invoke_typer_command(run, stdio="cat", expose_streamable_http=True, json_response=True)
            mock_translate.assert_called_once()
            args = mock_translate.call_args[0][0]
            assert "--jsonResponse" in args

    def test_run_with_log_level(self) -> None:
        """Test run command with custom log level."""
        with patch("cforge.commands.server.run.translate_main") as mock_translate:
            invoke_typer_command(run, stdio="cat", log_level="debug")
            mock_translate.assert_called_once()
            args = mock_translate.call_args[0][0]
            assert "--logLevel" in args
            assert "debug" in args

    def test_run_with_all_options(self) -> None:
        """Test run command with all options enabled."""
        with patch("cforge.commands.server.run.translate_main") as mock_translate:
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
            )
            mock_translate.assert_called_once()
            args = mock_translate.call_args[0][0]
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


class TestRunCommandIntegration:
    """Integration tests for the run command.

    Note: These tests verify that the run command properly delegates to
    mcpgateway.translate.main with the correct arguments. They do not
    actually start servers as that would require complex setup and teardown.
    """

    def test_run_delegates_to_translate_main(self) -> None:
        """Test that run command properly delegates to translate_main."""
        with patch("cforge.commands.server.run.translate_main") as mock_translate:
            # Simulate what would happen in a real scenario
            invoke_typer_command(run, stdio="echo hello", port=9000, host="127.0.0.1", log_level="error")

            # Verify translate_main was called
            mock_translate.assert_called_once()
            args = mock_translate.call_args[0][0]

            # Verify the arguments are correct
            assert "--stdio" in args
            assert "echo hello" in args
            assert "--port" in args
            assert "9000" in args
            assert "--host" in args
            assert "127.0.0.1" in args
            assert "--logLevel" in args
            assert "error" in args

    def test_run_with_multiple_protocols(self) -> None:
        """Test that run command handles multiple protocol flags correctly."""
        with patch("cforge.commands.server.run.translate_main") as mock_translate:
            invoke_typer_command(
                run,
                stdio="echo hello",
                expose_sse=True,
                expose_streamable_http=True,
                port=9000,
            )

            mock_translate.assert_called_once()
            args = mock_translate.call_args[0][0]

            # Verify both protocol flags are present
            assert "--expose-sse" in args
            assert "--expose-streamable-http" in args

    def test_run_with_custom_paths(self) -> None:
        """Test that run command passes custom SSE paths correctly."""
        with patch("cforge.commands.server.run.translate_main") as mock_translate:
            invoke_typer_command(
                run,
                stdio="echo hello",
                sse_path="/custom-sse",
                message_path="/custom-message",
                port=9000,
            )

            mock_translate.assert_called_once()
            args = mock_translate.call_args[0][0]

            # Verify custom paths are present
            assert "--ssePath" in args
            assert "/custom-sse" in args
            assert "--messagePath" in args
            assert "/custom-message" in args
