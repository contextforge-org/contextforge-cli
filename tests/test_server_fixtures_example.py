# -*- coding: utf-8 -*-
"""Location: ./tests/test_server_fixtures_example.py
Copyright 2025
SPDX-License-Identifier: Apache-2.0
Authors: Gabe Goodhart

Example tests demonstrating different server testing approaches.
This file shows how to use the various server testing fixtures.
"""

# Third-Party
import requests
from fastapi.testclient import TestClient


class TestServerFixturesExample:
    """Example tests showing different testing approaches."""

    # ==========================================================================
    # TestClient Approach (Recommended - Fast, No Network)
    # ==========================================================================

    def test_with_test_client(self, test_client: TestClient) -> None:
        """Example: Test using FastAPI TestClient (recommended).

        This is the fastest approach and doesn't require network binding.
        Use this for most API endpoint tests.
        """
        response = test_client.get("/health")
        assert response.status_code == 200

    def test_with_authenticated_client(self, authenticated_test_client: TestClient) -> None:
        """Example: Test using authenticated TestClient.

        Use this when testing protected endpoints that require authentication.
        """
        # The client already has auth headers set
        response = authenticated_test_client.get("/some-protected-endpoint")
        # Note: This will fail if the endpoint doesn't exist, just an example
        assert response.status_code in [200, 404]  # 404 is ok for this example

    # ==========================================================================
    # Real Server Approach (Integration Tests Only)
    # ==========================================================================

    def test_with_real_server(self, test_server: dict) -> None:
        """Example: Test using a real server (slower, for integration tests).

        Use this only when you need to test actual HTTP communication,
        client-server interaction, or CLI commands that connect to the server.
        """
        # Server is running and test_server contains connection info
        response = requests.get(f"{test_server['base_url']}/health")
        assert response.status_code == 200
        assert test_server["host"] == "127.0.0.1"
        assert isinstance(test_server["port"], int)

    def test_cli_against_real_server(self, test_server: dict, cli_runner, mock_settings, monkeypatch) -> None:
        """Example: Test CLI commands against a real running server.

        This demonstrates testing CLI commands that need to connect
        to an actual running server. The mock_settings fixture provides
        a real CLISettings instance with an ephemeral port.
        """
        from cforge.main import app

        # Override settings to point to test server
        monkeypatch.setenv("MCG_HOST", test_server["host"])
        monkeypatch.setenv("MCG_PORT", str(test_server["port"]))

        # Now CLI commands will connect to our test server
        # (This is just an example - you'd test actual commands)
        result = cli_runner.invoke(app, ["version"])
        assert result.exit_code == 0

    # ==========================================================================
    # Dynamic Port Allocation
    # ==========================================================================

    def test_get_open_port(self, get_open_port_fixture: callable) -> None:
        """Example: Using the get_open_port function directly.

        Use this when you need to dynamically allocate ports for custom tests.
        """
        port1 = get_open_port_fixture()
        port2 = get_open_port_fixture()

        assert isinstance(port1, int)
        assert isinstance(port2, int)
        assert 1024 < port1 < 65535  # Ephemeral port range
        assert 1024 < port2 < 65535
        # Usually different, but might collide occasionally
        # (race condition, but acceptable for testing)


class TestServerTestingBestPractices:
    """Examples showing best practices for different testing scenarios."""

    def test_api_endpoint_logic(self, test_client: TestClient) -> None:
        """Use TestClient for testing API endpoint logic."""
        # Fast, no network, perfect for unit testing endpoints
        response = test_client.get("/health")
        assert response.status_code == 200

    def test_end_to_end_workflow(self, test_server: dict) -> None:
        """Use real server for end-to-end integration tests.

        Mark slow tests with @pytest.mark.slow so they can be
        skipped during rapid development: pytest -m "not slow"
        """
        # This starts a real server, so it's slower
        # Use only for true integration tests
        base_url = test_server["base_url"]

        # Test a complete workflow
        health_response = requests.get(f"{base_url}/health")
        assert health_response.status_code == 200

        # Could test more complex multi-step workflows here
        # that require actual HTTP communication
