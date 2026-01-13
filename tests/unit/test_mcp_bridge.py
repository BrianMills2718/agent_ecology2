"""Unit tests for MCP server bridge.

Plan #28: Pre-seeded MCP Servers
Tests for GenesisMcpBridge and MCP artifact implementations.
"""

import pytest
from unittest.mock import Mock, patch, MagicMock


class TestGenesisMcpBridgeInit:
    """Tests for GenesisMcpBridge initialization."""

    def test_init_sets_attributes(self) -> None:
        """Bridge initializes with correct attributes."""
        from src.world.mcp_bridge import GenesisMcpBridge

        bridge = GenesisMcpBridge(
            artifact_id="test_mcp",
            description="Test bridge",
            server_command="echo",
            server_args=["hello"],
            server_env={"FOO": "bar"},
        )

        assert bridge.id == "test_mcp"
        assert bridge.description == "Test bridge"
        assert bridge.server_command == "echo"
        assert bridge.server_args == ["hello"]
        assert bridge.server_env == {"FOO": "bar"}
        assert bridge._process is None

    def test_init_with_defaults(self) -> None:
        """Bridge uses empty defaults for optional args."""
        from src.world.mcp_bridge import GenesisMcpBridge

        bridge = GenesisMcpBridge(
            artifact_id="test",
            description="Test",
            server_command="npx",
        )

        assert bridge.server_args == []
        assert bridge.server_env == {}


class TestGenesisMcpBridgeLifecycle:
    """Tests for server lifecycle management."""

    def test_start_server_creates_process(self) -> None:
        """start_server creates subprocess with correct args."""
        from src.world.mcp_bridge import GenesisMcpBridge

        bridge = GenesisMcpBridge(
            artifact_id="test",
            description="Test",
            server_command="npx",
            server_args=["@test/server"],
        )

        # mock-ok: Testing subprocess lifecycle without actual MCP server
        with patch("src.world.mcp_bridge.subprocess.Popen") as mock_popen:
            mock_process = Mock()
            mock_process.poll.return_value = None
            mock_process.stdin = Mock()
            mock_process.stdout = Mock()
            mock_process.stdout.readline.return_value = b'{"jsonrpc": "2.0", "id": 1, "result": {}}\n'
            mock_popen.return_value = mock_process

            bridge.start_server()

            assert bridge._process is mock_process
            mock_popen.assert_called_once()
            call_args = mock_popen.call_args
            assert call_args[0][0] == ["npx", "@test/server"]

    def test_start_server_idempotent(self) -> None:
        """start_server does nothing if already running."""
        from src.world.mcp_bridge import GenesisMcpBridge

        bridge = GenesisMcpBridge(
            artifact_id="test",
            description="Test",
            server_command="npx",
        )

        # mock-ok: Testing idempotency without actual MCP server
        with patch("src.world.mcp_bridge.subprocess.Popen") as mock_popen:
            mock_process = Mock()
            mock_process.poll.return_value = None  # Still running
            mock_process.stdin = Mock()
            mock_process.stdout = Mock()
            mock_process.stdout.readline.return_value = b'{"jsonrpc": "2.0", "id": 1, "result": {}}\n'
            mock_popen.return_value = mock_process

            bridge.start_server()
            bridge.start_server()  # Second call

            # Should only create process once
            assert mock_popen.call_count == 1

    def test_stop_server_terminates_process(self) -> None:
        """stop_server terminates and clears process."""
        from src.world.mcp_bridge import GenesisMcpBridge

        bridge = GenesisMcpBridge(
            artifact_id="test",
            description="Test",
            server_command="echo",
        )

        # mock-ok: Testing termination without actual process
        mock_process = Mock()
        mock_process.terminate = Mock()
        mock_process.wait = Mock()
        bridge._process = mock_process

        bridge.stop_server()

        mock_process.terminate.assert_called_once()
        assert bridge._process is None

    def test_stop_server_noop_if_not_running(self) -> None:
        """stop_server does nothing if no process."""
        from src.world.mcp_bridge import GenesisMcpBridge

        bridge = GenesisMcpBridge(
            artifact_id="test",
            description="Test",
            server_command="echo",
        )

        # Should not raise
        bridge.stop_server()
        assert bridge._process is None


class TestGenesisMcpBridgeCallTool:
    """Tests for tool invocation."""

    def test_call_tool_success(self) -> None:
        """call_tool returns success on valid response."""
        from src.world.mcp_bridge import GenesisMcpBridge

        bridge = GenesisMcpBridge(
            artifact_id="test",
            description="Test",
            server_command="echo",
        )

        # mock-ok: Testing JSON-RPC without actual MCP server
        with patch.object(bridge, "_send_request") as mock_send:
            mock_send.return_value = {
                "jsonrpc": "2.0",
                "id": 1,
                "result": {"data": "test"}
            }
            bridge._process = Mock()  # Pretend running

            result = bridge.call_tool("test_tool", {"arg": "value"})

            assert result["success"] is True
            assert result["result"] == {"data": "test"}

    def test_call_tool_error_response(self) -> None:
        """call_tool returns error from server."""
        from src.world.mcp_bridge import GenesisMcpBridge

        bridge = GenesisMcpBridge(
            artifact_id="test",
            description="Test",
            server_command="echo",
        )

        # mock-ok: Testing error handling without actual MCP server
        with patch.object(bridge, "_send_request") as mock_send:
            mock_send.return_value = {
                "jsonrpc": "2.0",
                "id": 1,
                "error": {"code": -32600, "message": "Invalid"}
            }
            bridge._process = Mock()

            result = bridge.call_tool("bad_tool", {})

            assert result["success"] is False
            assert "Invalid" in result["error"]


class TestGenesisFetch:
    """Tests for genesis_fetch artifact."""

    def test_fetch_registers_method(self) -> None:
        """GenesisFetch registers fetch method."""
        from src.world.mcp_bridge import GenesisFetch

        fetch = GenesisFetch()

        methods = fetch.list_methods()
        names = [m["name"] for m in methods]
        assert "fetch" in names

    def test_fetch_method_validates_args(self) -> None:
        """Fetch method requires URL argument."""
        from src.world.mcp_bridge import GenesisFetch

        fetch = GenesisFetch()
        method = fetch.get_method("fetch")
        assert method is not None

        # Empty args should fail
        result = method.handler([], "test_agent")
        assert result["success"] is False
        assert "requires" in result["error"]


class TestGenesisFilesystem:
    """Tests for genesis_filesystem artifact."""

    def test_filesystem_registers_methods(self) -> None:
        """GenesisFilesystem registers file methods."""
        from src.world.mcp_bridge import GenesisFilesystem

        fs = GenesisFilesystem(sandbox_root="/tmp/test")

        methods = fs.list_methods()
        names = [m["name"] for m in methods]
        assert "read_file" in names
        assert "write_file" in names
        assert "list_directory" in names

    def test_path_validation_blocks_escape(self) -> None:
        """Path validation prevents sandbox escape."""
        from src.world.mcp_bridge import GenesisFilesystem

        fs = GenesisFilesystem(sandbox_root="/tmp/sandbox")

        # Attempt to escape sandbox
        error = fs._validate_path("../etc/passwd")
        assert error is not None
        assert "escapes" in error


class TestGenesisWebSearch:
    """Tests for genesis_web_search artifact."""

    def test_web_search_registers_method(self) -> None:
        """GenesisWebSearch registers search method."""
        from src.world.mcp_bridge import GenesisWebSearch

        search = GenesisWebSearch()

        methods = search.list_methods()
        names = [m["name"] for m in methods]
        assert "search" in names


class TestMcpConfig:
    """Tests for MCP configuration."""

    def test_mcp_server_config_defaults(self) -> None:
        """McpServerConfig has correct defaults."""
        from src.config_schema import McpServerConfig

        config = McpServerConfig()

        assert config.enabled is False
        assert config.command == "npx"
        assert config.args == []
        assert config.env == {}

    def test_mcp_config_all_disabled_by_default(self) -> None:
        """McpConfig has all servers disabled by default."""
        from src.config_schema import McpConfig

        config = McpConfig()

        assert config.fetch.enabled is False
        assert config.filesystem.enabled is False
        assert config.web_search.enabled is False


class TestCreateMcpArtifacts:
    """Tests for MCP artifact factory."""

    def test_creates_only_enabled(self) -> None:
        """Factory only creates enabled artifacts."""
        from src.world.mcp_bridge import create_mcp_artifacts
        from src.config_schema import McpConfig, McpServerConfig

        config = McpConfig(
            fetch=McpServerConfig(enabled=True, command="npx", args=["fetch"]),
            filesystem=McpServerConfig(enabled=False),
            web_search=McpServerConfig(enabled=False),
        )

        artifacts = create_mcp_artifacts(config)

        assert "genesis_fetch" in artifacts
        assert "genesis_filesystem" not in artifacts
        assert "genesis_web_search" not in artifacts

    def test_creates_none_when_all_disabled(self) -> None:
        """Factory returns empty dict when all disabled."""
        from src.world.mcp_bridge import create_mcp_artifacts
        from src.config_schema import McpConfig

        config = McpConfig()  # All disabled by default

        artifacts = create_mcp_artifacts(config)

        assert artifacts == {}
