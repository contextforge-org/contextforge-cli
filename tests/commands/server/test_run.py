# -*- coding: utf-8 -*-
"""Location: ./tests/commands/server/test_run.py
Copyright 2025
SPDX-License-Identifier: Apache-2.0
Authors: Gabe Goodhart

Tests for the run command.
"""

# Standard
from unittest.mock import MagicMock, patch

# Local
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

    def test_run_with_registration_enabled(self) -> None:
        """Test run command with auto-registration enabled (default)."""
        with (
            patch("mcpgateway.translate.main") as mock_translate,
            patch("multiprocessing.Process") as mock_process,
            patch("cforge.commands.server.run.requests") as mock_requests,
            patch("cforge.commands.server.run.make_authenticated_request") as mock_request,
        ):

            # Mock returning a 200 on health
            mock_get_res = MagicMock()
            mock_get_res.status_code = 200
            mock_requests.get = MagicMock(return_value=mock_get_res)

            mock_request.return_value = {"id": "test-server-id", "name": "test-server"}

            invoke_typer_command(run, stdio="uvx mcp-server-git", port=9000, register=True)

            # Verify registration was attempted
            mock_request.assert_called_once()
            call_args = mock_request.call_args
            assert call_args[0][0] == "POST"
            assert call_args[0][1] == "/gateways"

            # Verify registration data
            json_data = call_args[1]["json_data"]
            assert "name" in json_data
            assert "url" in json_data
            assert "http://127.0.0.1:9000/sse" in json_data["url"]
            assert json_data["transport"] == "SSE"

            # Verify translate_main was called via Process
            mock_process.assert_called_once()
            proc_call_args = mock_process.call_args[1]
            assert proc_call_args.get("target") is mock_translate

    def test_run_with_registration_disabled(self) -> None:
        """Test run command with registration explicitly disabled."""
        with patch("mcpgateway.translate.main") as mock_translate, patch("multiprocessing.Process") as mock_process, patch("cforge.commands.server.run.make_authenticated_request") as mock_request:

            invoke_typer_command(run, stdio="uvx mcp-server-git", port=9000, register=False)

            # Verify registration was NOT attempted
            mock_request.assert_not_called()

            # Verify translate_main was still called via Process
            mock_process.assert_called_once()
            call_args = mock_process.call_args[1]
            assert call_args.get("target") is mock_translate

    def test_run_with_temporary_registration(self) -> None:
        """Test run command with temporary registration (auto-cleanup)."""
        with (
            patch("mcpgateway.translate.main") as mock_translate,
            patch("multiprocessing.Process") as mock_process,
            patch("cforge.commands.server.run.requests") as mock_requests,
            patch("cforge.commands.server.run.make_authenticated_request") as mock_request,
            patch("cforge.commands.server.run.atexit") as mock_atexit,
        ):

            # Mock returning a 200 on health
            mock_get_res = MagicMock()
            mock_get_res.status_code = 200
            mock_requests.get = MagicMock(return_value=mock_get_res)

            mock_request.return_value = {"id": "temp-server-id", "name": "temp-server"}

            invoke_typer_command(run, stdio="uvx mcp-server-git", port=9000, temporary=True)

            # Verify registration was attempted
            assert mock_request.call_count >= 1
            first_call = mock_request.call_args_list[0]
            assert first_call[0][0] == "POST"
            assert first_call[0][1] == "/gateways"

            # Verify cleanup handlers were registered
            mock_atexit.register.assert_called_once()

            # Verify translate_main was called via Process
            mock_process.assert_called_once()
            call_args = mock_process.call_args[1]
            assert call_args.get("target") is mock_translate

    def test_run_with_custom_server_name_and_description(self) -> None:
        """Test run command with custom server name and description."""
        with (
            patch("mcpgateway.translate.main") as mock_translate,
            patch("multiprocessing.Process") as mock_process,
            patch("cforge.commands.server.run.requests") as mock_requests,
            patch("cforge.commands.server.run.make_authenticated_request") as mock_request,
        ):

            # Mock returning a 200 on health
            mock_get_res = MagicMock()
            mock_get_res.status_code = 200
            mock_requests.get = MagicMock(return_value=mock_get_res)

            mock_request.return_value = {"id": "custom-server-id"}

            invoke_typer_command(
                run,
                stdio="uvx mcp-server-git",
                port=9000,
                server_name="my-custom-server",
                server_description="A custom MCP server for testing",
                register=True,
            )

            # Verify registration data includes custom name and description
            call_args = mock_request.call_args
            json_data = call_args[1]["json_data"]
            assert json_data["name"] == "my-custom-server"
            assert json_data["description"] == "A custom MCP server for testing"

            # Verify translate_main was called via Process
            mock_process.assert_called_once()
            proc_call_args = mock_process.call_args[1]
            assert proc_call_args.get("target") is mock_translate

    def test_run_with_registration_failure(self) -> None:
        """Test run command handles registration failure gracefully."""
        with (
            patch("mcpgateway.translate.main") as mock_translate,
            patch("multiprocessing.Process") as mock_process,
            patch("cforge.commands.server.run.requests") as mock_requests,
            patch("cforge.commands.server.run.make_authenticated_request") as mock_request,
            patch("cforge.commands.server.run.get_console") as mock_console,
        ):

            # Mock returning a 200 on health
            mock_get_res = MagicMock()
            mock_get_res.status_code = 200
            mock_requests.get = MagicMock(return_value=mock_get_res)

            # Simulate registration failure
            mock_request.side_effect = Exception("Registration failed")
            mock_console_instance = MagicMock()
            mock_console.return_value = mock_console_instance

            invoke_typer_command(run, stdio="uvx mcp-server-git", port=9000, register=True)

            # Verify warning was printed
            assert any("Warning" in str(call) for call in mock_console_instance.print.call_args_list)

            # Verify translate_main was still called via Process (server runs despite registration failure)
            mock_process.assert_called_once()
            call_args = mock_process.call_args[1]
            assert call_args.get("target") is mock_translate

    def test_run_registration_auto_generates_name_from_stdio(self) -> None:
        """Test that server name is auto-generated from stdio command."""
        with (
            patch("mcpgateway.translate.main") as mock_translate,
            patch("multiprocessing.Process") as mock_process,
            patch("cforge.commands.server.run.requests") as mock_requests,
            patch("cforge.commands.server.run.make_authenticated_request") as mock_request,
        ):

            # Mock returning a 200 on health
            mock_get_res = MagicMock()
            mock_get_res.status_code = 200
            mock_requests.get = MagicMock(return_value=mock_get_res)

            mock_request.return_value = {"id": "auto-named-server"}

            invoke_typer_command(run, stdio="uvx mcp-server-git", port=9000, register=True)

            # Verify name was auto-generated
            call_args = mock_request.call_args
            json_data = call_args[1]["json_data"]
            assert "mcp-server-git" in json_data["name"] or "9000" in json_data["name"]

            # Verify translate_main was called via Process
            mock_process.assert_called_once()
            proc_call_args = mock_process.call_args[1]
            assert proc_call_args.get("target") is mock_translate

    def test_run_registration_with_grpc_source(self) -> None:
        """Test registration with gRPC source instead of stdio."""
        with (
            patch("mcpgateway.translate.main") as mock_translate,
            patch("multiprocessing.Process") as mock_process,
            patch("cforge.commands.server.run.requests") as mock_requests,
            patch("cforge.commands.server.run.make_authenticated_request") as mock_request,
        ):

            # Mock returning a 200 on health
            mock_get_res = MagicMock()
            mock_get_res.status_code = 200
            mock_requests.get = MagicMock(return_value=mock_get_res)

            mock_request.return_value = {"id": "grpc-server-id"}

            invoke_typer_command(run, grpc="localhost:50051", port=9000, register=True)

            # Verify registration was attempted
            mock_request.assert_called_once()
            call_args = mock_request.call_args
            json_data = call_args[1]["json_data"]

            # Verify name includes grpc reference
            assert "grpc" in json_data["name"].lower()

            # Verify translate_main was called via Process
            mock_process.assert_called_once()
            call_args = mock_process.call_args[1]
            assert call_args.get("target") is mock_translate

    def test_run_register_without_source_warns(self) -> None:
        """Test that register=True without stdio or grpc prints a warning."""
        with (
            patch("mcpgateway.translate.main"),
            patch("multiprocessing.Process") as mock_process,
            patch("cforge.commands.server.run.get_console") as mock_console,
            patch("cforge.commands.server.run.make_authenticated_request") as mock_request,
        ):
            mock_console_instance = MagicMock()
            mock_console.return_value = mock_console_instance

            # No stdio or grpc, but register=True
            invoke_typer_command(run, register=True)

            # Verify warning was printed about needing stdio or grpc
            assert any("Warning" in str(call) and "register" in str(call).lower() for call in mock_console_instance.print.call_args_list)

            # Verify registration was NOT attempted (since it was disabled)
            mock_request.assert_not_called()

            # Verify translate_main was still called via Process
            mock_process.assert_called_once()

    def test_run_health_check_connection_error_retry(self) -> None:
        """Test that health check retries on connection errors."""
        # Third-Party
        import requests as real_requests

        with (
            patch("mcpgateway.translate.main"),
            patch("multiprocessing.Process") as mock_process,
            patch("cforge.commands.server.run.requests") as mock_requests,
            patch("cforge.commands.server.run.make_authenticated_request") as mock_request,
            patch("cforge.commands.server.run.time") as mock_time,
        ):
            # First call raises ConnectionError, second succeeds
            mock_get_res = MagicMock()
            mock_get_res.status_code = 200
            mock_requests.get = MagicMock(
                side_effect=[
                    real_requests.exceptions.ConnectionError("Connection refused"),
                    mock_get_res,
                ]
            )
            mock_requests.exceptions = real_requests.exceptions

            # Mock time to control the loop
            mock_time.time = MagicMock(side_effect=[0, 0.5, 1])
            mock_time.sleep = MagicMock()

            mock_request.return_value = {"id": "test-server-id"}

            invoke_typer_command(run, stdio="uvx mcp-server-git", port=9000, register=True)

            # Verify health check was retried
            assert mock_requests.get.call_count == 2

            # Verify sleep was called after connection error
            mock_time.sleep.assert_called_once_with(0.5)

            # Verify registration succeeded after retry
            mock_request.assert_called_once()
            mock_process.assert_called_once()

    def test_run_health_check_timeout(self) -> None:
        """Test that health check timeout exits with error."""
        # Third-Party
        import requests as real_requests
        import typer

        with (
            patch("mcpgateway.translate.main"),
            patch("multiprocessing.Process"),
            patch("cforge.commands.server.run.requests") as mock_requests,
            patch("cforge.commands.server.run.make_authenticated_request") as mock_request,
            patch("cforge.commands.server.run.time") as mock_time,
            patch("cforge.commands.server.run.get_console") as mock_console,
            patch("cforge.commands.server.run.typer.exit", side_effect=typer.Exit(1)) as mock_exit,
        ):
            # Always raise ConnectionError
            mock_requests.get = MagicMock(side_effect=real_requests.exceptions.ConnectionError("Connection refused"))
            mock_requests.exceptions = real_requests.exceptions

            # Mock time to simulate timeout
            mock_time.time = MagicMock(side_effect=[0, 5, 11])  # Start, after first try, after timeout
            mock_time.sleep = MagicMock()

            mock_console_instance = MagicMock()
            mock_console.return_value = mock_console_instance

            invoke_typer_command(run, stdio="uvx mcp-server-git", port=9000, register=True, register_timeout=10.0)

            # Verify timeout error message was printed
            assert any("Failed to connect" in str(call) for call in mock_console_instance.print.call_args_list)

            # Verify typer.exit was called with error code
            mock_exit.assert_called_once_with(1)

            # Registration should not have been attempted
            mock_request.assert_not_called()

    def test_run_temporary_cleanup_success(self) -> None:
        """Test that temporary server cleanup function works correctly."""
        with (
            patch("mcpgateway.translate.main"),
            patch("multiprocessing.Process"),
            patch("cforge.commands.server.run.requests") as mock_requests,
            patch("cforge.commands.server.run.make_authenticated_request") as mock_request,
            patch("cforge.commands.server.run.atexit") as mock_atexit,
            patch("cforge.commands.server.run.get_console") as mock_console,
        ):
            # Mock returning a 200 on health
            mock_get_res = MagicMock()
            mock_get_res.status_code = 200
            mock_requests.get = MagicMock(return_value=mock_get_res)

            mock_request.return_value = {"id": "temp-server-id", "name": "temp-server"}

            mock_console_instance = MagicMock()
            mock_console.return_value = mock_console_instance

            invoke_typer_command(run, stdio="uvx mcp-server-git", port=9000, temporary=True)

            # Verify cleanup handler was registered
            mock_atexit.register.assert_called_once()

            # Get the cleanup function and call it
            cleanup_fn = mock_atexit.register.call_args[0][0]

            # Reset mock_request to track cleanup call
            mock_request.reset_mock()

            # Call cleanup function
            cleanup_fn()

            # Verify unregistration was attempted
            mock_request.assert_called_once()
            call_args = mock_request.call_args
            assert call_args[0][0] == "DELETE"
            assert "/gateways/temp-server-id" in call_args[0][1]

    def test_run_temporary_cleanup_failure(self) -> None:
        """Test that temporary server cleanup handles errors gracefully."""
        with (
            patch("mcpgateway.translate.main"),
            patch("multiprocessing.Process"),
            patch("cforge.commands.server.run.requests") as mock_requests,
            patch("cforge.commands.server.run.make_authenticated_request") as mock_request,
            patch("cforge.commands.server.run.atexit") as mock_atexit,
            patch("cforge.commands.server.run.get_console") as mock_console,
        ):
            # Mock returning a 200 on health
            mock_get_res = MagicMock()
            mock_get_res.status_code = 200
            mock_requests.get = MagicMock(return_value=mock_get_res)

            mock_request.return_value = {"id": "temp-server-id", "name": "temp-server"}

            mock_console_instance = MagicMock()
            mock_console.return_value = mock_console_instance

            invoke_typer_command(run, stdio="uvx mcp-server-git", port=9000, temporary=True)

            # Get the cleanup function
            cleanup_fn = mock_atexit.register.call_args[0][0]

            # Make the DELETE request fail
            mock_request.reset_mock()
            mock_request.side_effect = Exception("Network error")

            # Call cleanup function - should not raise
            cleanup_fn()

            # Verify warning was printed
            assert any("Warning" in str(call) and "unregister" in str(call).lower() for call in mock_console_instance.print.call_args_list)

    def test_run_health_check_retries_on_non_200(self) -> None:
        """Test that health check retries when server returns non-200 status."""
        with (
            patch("mcpgateway.translate.main"),
            patch("multiprocessing.Process") as mock_process,
            patch("cforge.commands.server.run.requests") as mock_requests,
            patch("cforge.commands.server.run.make_authenticated_request") as mock_request,
            patch("cforge.commands.server.run.time") as mock_time,
        ):
            # First call returns 503, second returns 200
            mock_get_res_503 = MagicMock()
            mock_get_res_503.status_code = 503
            mock_get_res_200 = MagicMock()
            mock_get_res_200.status_code = 200
            mock_requests.get = MagicMock(side_effect=[mock_get_res_503, mock_get_res_200])

            # Mock time to control the loop
            mock_time.time = MagicMock(side_effect=[0, 0.5, 1])
            mock_time.sleep = MagicMock()

            mock_request.return_value = {"id": "test-server-id"}

            invoke_typer_command(run, stdio="uvx mcp-server-git", port=9000, register=True)

            # Verify health check was retried (called twice)
            assert mock_requests.get.call_count == 2

            # Verify registration succeeded
            mock_request.assert_called_once()
            mock_process.assert_called_once()

    def test_run_registration_name_fallback_for_filtered_command(self) -> None:
        """Test that server name falls back to stdio-server when all parts are filtered."""
        with (
            patch("mcpgateway.translate.main"),
            patch("multiprocessing.Process") as mock_process,
            patch("cforge.commands.server.run.requests") as mock_requests,
            patch("cforge.commands.server.run.make_authenticated_request") as mock_request,
        ):
            # Mock returning a 200 on health
            mock_get_res = MagicMock()
            mock_get_res.status_code = 200
            mock_requests.get = MagicMock(return_value=mock_get_res)

            mock_request.return_value = {"id": "test-server-id"}

            # Use a command where all parts get filtered (uvx, python, node, etc.)
            invoke_typer_command(run, stdio="uvx python node", port=9000, register=True)

            # Verify name falls back to stdio-server-{port}
            call_args = mock_request.call_args
            json_data = call_args[1]["json_data"]
            assert json_data["name"] == "stdio-server-9000"

            mock_process.assert_called_once()

    def test_run_temporary_without_source_uses_fallback_name(self) -> None:
        """Test that temporary registration without stdio/grpc uses fallback server name."""
        with (
            patch("mcpgateway.translate.main"),
            patch("multiprocessing.Process") as mock_process,
            patch("cforge.commands.server.run.requests") as mock_requests,
            patch("cforge.commands.server.run.make_authenticated_request") as mock_request,
            patch("cforge.commands.server.run.atexit") as mock_atexit,
        ):
            # Mock returning a 200 on health
            mock_get_res = MagicMock()
            mock_get_res.status_code = 200
            mock_requests.get = MagicMock(return_value=mock_get_res)

            mock_request.return_value = {"id": "temp-server-id"}

            # temporary=True bypasses the stdio/grpc check, allowing registration without source
            invoke_typer_command(run, port=9000, temporary=True)

            # Verify fallback name server-{port} was used
            call_args = mock_request.call_args
            json_data = call_args[1]["json_data"]
            assert json_data["name"] == "server-9000"

            # Verify cleanup was registered
            mock_atexit.register.assert_called_once()
            mock_process.assert_called_once()
