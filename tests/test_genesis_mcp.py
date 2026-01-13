"""Tests for MCP server integration via genesis artifacts.

Plan #28: Pre-seeded MCP Servers
TDD: Tests written first, then implementation.
"""

import pytest
from unittest.mock import Mock, patch


class TestMcpBridgeLifecycle:
    """Tests for MCP server subprocess lifecycle management."""

    def test_mcp_bridge_start_server(self) -> None:
        """Server subprocess starts correctly."""
        from src.world.mcp_bridge import GenesisMcpBridge

        bridge = GenesisMcpBridge(
            artifact_id="test_mcp",
            description="Test MCP bridge",
            server_command="echo",
            server_args=["test"],
        )

        # Server should not be running initially
        assert bridge._process is None

        # mock-ok: Testing subprocess lifecycle without actual MCP server
        with patch("src.world.mcp_bridge.subprocess.Popen") as mock_popen:
            mock_process = Mock()
            mock_process.poll.return_value = None  # Process is running
            mock_process.stdin = Mock()
            mock_process.stdout = Mock()
            mock_process.stdout.readline.return_value = b'{"jsonrpc": "2.0", "id": 1, "result": {}}\n'
            mock_popen.return_value = mock_process

            bridge.start_server()

            # Server should now be running
            assert bridge._process is not None
            mock_popen.assert_called_once()

    def test_mcp_bridge_stop_server(self) -> None:
        """Server subprocess stops cleanly."""
        from src.world.mcp_bridge import GenesisMcpBridge

        bridge = GenesisMcpBridge(
            artifact_id="test_mcp",
            description="Test MCP bridge",
            server_command="echo",
            server_args=["test"],
        )

        # mock-ok: Testing subprocess lifecycle without actual MCP server
        with patch("src.world.mcp_bridge.subprocess.Popen") as mock_popen:
            mock_process = Mock()
            mock_process.poll.return_value = None
            mock_process.terminate = Mock()
            mock_process.wait = Mock()
            mock_process.stdin = Mock()
            mock_process.stdout = Mock()
            mock_process.stdout.readline.return_value = b'{"jsonrpc": "2.0", "id": 1, "result": {}}\n'
            mock_popen.return_value = mock_process

            bridge.start_server()
            bridge.stop_server()

            mock_process.terminate.assert_called_once()
            assert bridge._process is None

    def test_mcp_bridge_call_tool(self) -> None:
        """Tool invocation works via JSON-RPC over stdio."""
        from src.world.mcp_bridge import GenesisMcpBridge

        bridge = GenesisMcpBridge(
            artifact_id="test_mcp",
            description="Test MCP bridge",
            server_command="echo",
            server_args=[],
        )

        # mock-ok: Testing JSON-RPC protocol without actual MCP server
        with patch.object(bridge, "_send_request") as mock_send:
            mock_send.return_value = {
                "jsonrpc": "2.0",
                "id": 1,
                "result": {"content": [{"type": "text", "text": "Hello"}]}
            }

            result = bridge.call_tool("test_tool", {"arg": "value"})

            assert result["success"] is True
            mock_send.assert_called_once()

    def test_mcp_bridge_error_handling(self) -> None:
        """Errors from MCP server are returned properly."""
        from src.world.mcp_bridge import GenesisMcpBridge

        bridge = GenesisMcpBridge(
            artifact_id="test_mcp",
            description="Test MCP bridge",
            server_command="echo",
            server_args=[],
        )

        # mock-ok: Testing error handling without actual MCP server
        with patch.object(bridge, "_send_request") as mock_send:
            mock_send.return_value = {
                "jsonrpc": "2.0",
                "id": 1,
                "error": {"code": -32600, "message": "Invalid Request"}
            }

            result = bridge.call_tool("bad_tool", {})

            assert result["success"] is False
            assert "error" in result


class TestGenesisFetch:
    """Tests for genesis_fetch artifact."""

    def test_genesis_fetch_methods(self) -> None:
        """Fetch artifact has correct methods registered."""
        from src.world.mcp_bridge import GenesisFetch

        # mock-ok: Testing method registration without actual MCP server
        with patch("subprocess.Popen"):
            fetch = GenesisFetch()

            methods = fetch.list_methods()
            method_names = [m["name"] for m in methods]

            assert "fetch" in method_names
            # All methods should have cost 0 (rate limited)
            for method in methods:
                assert method["cost"] == 0

    def test_genesis_fetch_invoke(self) -> None:
        """Fetch invocation works through genesis method."""
        from src.world.mcp_bridge import GenesisFetch

        # mock-ok: Testing invocation flow without actual HTTP request
        with patch("subprocess.Popen"):
            fetch = GenesisFetch()

            with patch.object(fetch, "call_tool") as mock_call:
                mock_call.return_value = {
                    "success": True,
                    "content": "Response body"
                }

                method = fetch.get_method("fetch")
                assert method is not None

                result = method.handler(
                    ["https://example.com"],
                    "test_agent"
                )

                assert result["success"] is True


class TestMcpConfig:
    """Tests for MCP configuration schema."""

    def test_mcp_config_schema(self) -> None:
        """Config schema validates MCP server settings."""
        from src.config_schema import McpServerConfig, McpConfig

        # Valid config
        server_config = McpServerConfig(
            enabled=True,
            command="npx",
            args=["@anthropic/mcp-server-fetch"],
            env={"API_KEY": "test"}
        )

        assert server_config.enabled is True
        assert server_config.command == "npx"

        # Full MCP config
        mcp_config = McpConfig(
            fetch=McpServerConfig(enabled=True, command="npx", args=["fetch"]),
            filesystem=McpServerConfig(enabled=False, command="npx", args=["fs"]),
            web_search=McpServerConfig(enabled=True, command="npx", args=["search"]),
        )

        assert mcp_config.fetch.enabled is True
        assert mcp_config.filesystem.enabled is False

    def test_mcp_disabled_not_created(self) -> None:
        """Disabled MCP servers are not registered in genesis."""
        from src.world.mcp_bridge import create_mcp_artifacts
        from src.config_schema import McpServerConfig, McpConfig

        mcp_config = McpConfig(
            fetch=McpServerConfig(enabled=True, command="npx", args=["fetch"]),
            filesystem=McpServerConfig(enabled=False, command="npx", args=["fs"]),
            web_search=McpServerConfig(enabled=False, command="npx", args=["search"]),
        )

        # mock-ok: Testing artifact creation logic without actual subprocess
        with patch("subprocess.Popen"):
            artifacts = create_mcp_artifacts(mcp_config)

            # Only enabled artifacts should be created
            assert "genesis_fetch" in artifacts
            assert "genesis_filesystem" not in artifacts
            assert "genesis_web_search" not in artifacts


class TestMcpRegistration:
    """Tests for MCP artifact registration in genesis."""

    def test_mcp_registered_in_genesis(self) -> None:
        """MCP artifacts appear in genesis artifact list when enabled."""
        from src.world.genesis import create_genesis_artifacts
        from src.world.ledger import Ledger
        from src.world.artifacts import ArtifactStore
        from src.config_schema import GenesisConfig, McpConfig, McpServerConfig

        ledger = Ledger()
        artifact_store = ArtifactStore()

        # Create config with MCP fetch enabled
        mcp_config = McpConfig(
            fetch=McpServerConfig(enabled=True, command="npx", args=["fetch"]),
            filesystem=McpServerConfig(enabled=False, command="npx", args=["fs"]),
            web_search=McpServerConfig(enabled=False, command="npx", args=["search"]),
        )
        genesis_config = GenesisConfig(mcp=mcp_config)

        # mock-ok: Testing artifact registration without actual subprocess
        with patch("src.world.mcp_bridge.subprocess.Popen"):
            artifacts = create_genesis_artifacts(
                ledger=ledger,
                mint_callback=lambda a, b: None,
                artifact_store=artifact_store,
                genesis_config=genesis_config,
            )

            # Standard genesis artifacts should exist
            assert "genesis_ledger" in artifacts
            # MCP fetch should be registered since it's enabled
            assert "genesis_fetch" in artifacts
            # Disabled MCP artifacts should not be registered
            assert "genesis_filesystem" not in artifacts
