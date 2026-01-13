"""MCP Server Bridge - Genesis artifacts wrapping MCP servers.

Plan #28: Pre-seeded MCP Servers

This module provides:
1. GenesisMcpBridge: Base class for MCP server wrapper artifacts
2. GenesisFetch: HTTP fetch capability
3. GenesisFilesystem: File I/O (sandboxed)
4. GenesisWebSearch: Internet search

MCP servers run as subprocesses, communicating via JSON-RPC over stdio.
"""

from __future__ import annotations

import json
import subprocess
import threading
from dataclasses import dataclass
from typing import Any, cast

from .genesis import GenesisArtifact
from ..config_schema import McpConfig


@dataclass
class McpToolInfo:
    """Information about a tool available on an MCP server."""
    name: str
    description: str
    input_schema: dict[str, Any]


class GenesisMcpBridge(GenesisArtifact):
    """Base class for MCP server wrapper artifacts.

    Manages MCP server subprocess lifecycle and JSON-RPC communication.

    Attributes:
        server_command: Command to start MCP server (e.g., "npx")
        server_args: Arguments to pass to command
        server_env: Environment variables for server process
        _process: Subprocess handle when running
        _request_id: Counter for JSON-RPC request IDs
        _lock: Thread lock for subprocess communication
    """

    server_command: str
    server_args: list[str]
    server_env: dict[str, str]
    _process: subprocess.Popen[bytes] | None
    _request_id: int
    _lock: threading.Lock

    def __init__(
        self,
        artifact_id: str,
        description: str,
        server_command: str,
        server_args: list[str] | None = None,
        server_env: dict[str, str] | None = None,
    ) -> None:
        """Initialize MCP bridge.

        Args:
            artifact_id: Unique artifact identifier (e.g., "genesis_fetch")
            description: Human-readable description
            server_command: Command to start MCP server
            server_args: Additional command arguments
            server_env: Environment variables for server
        """
        super().__init__(artifact_id, description)
        self.server_command = server_command
        self.server_args = server_args or []
        self.server_env = server_env or {}
        self._process = None
        self._request_id = 0
        self._lock = threading.Lock()

    def start_server(self) -> None:
        """Start the MCP server subprocess.

        Uses JSON-RPC over stdio for communication.
        Server is started lazily on first tool invocation.
        """
        if self._process is not None and self._process.poll() is None:
            return  # Already running

        import os
        env = os.environ.copy()
        env.update(self.server_env)

        cmd = [self.server_command] + self.server_args

        self._process = subprocess.Popen(
            cmd,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            env=env,
        )

        # Send initialization request
        self._send_request("initialize", {
            "protocolVersion": "0.1.0",
            "clientInfo": {"name": "agent_ecology", "version": "0.1.0"},
            "capabilities": {}
        })

    def stop_server(self) -> None:
        """Stop the MCP server subprocess cleanly."""
        if self._process is None:
            return

        try:
            self._process.terminate()
            self._process.wait(timeout=5.0)
        except subprocess.TimeoutExpired:
            self._process.kill()
            self._process.wait()
        finally:
            self._process = None

    def _send_request(self, method: str, params: dict[str, Any]) -> dict[str, Any]:
        """Send a JSON-RPC request to the MCP server.

        Args:
            method: JSON-RPC method name
            params: Method parameters

        Returns:
            JSON-RPC response dict

        Raises:
            RuntimeError: If server not running or communication fails
        """
        if self._process is None or self._process.stdin is None or self._process.stdout is None:
            raise RuntimeError("MCP server not running")

        with self._lock:
            self._request_id += 1
            request = {
                "jsonrpc": "2.0",
                "id": self._request_id,
                "method": method,
                "params": params,
            }

            request_bytes = (json.dumps(request) + "\n").encode("utf-8")
            self._process.stdin.write(request_bytes)
            self._process.stdin.flush()

            # Read response line
            response_line = self._process.stdout.readline()
            if not response_line:
                raise RuntimeError("No response from MCP server")

            result: dict[str, Any] = json.loads(response_line.decode("utf-8"))
            return result

    def call_tool(self, tool_name: str, arguments: dict[str, Any]) -> dict[str, Any]:
        """Call a tool on the MCP server.

        Args:
            tool_name: Name of the tool to invoke
            arguments: Tool arguments

        Returns:
            Dict with 'success' and result/error
        """
        # Lazy start server if needed
        if self._process is None:
            try:
                self.start_server()
            except Exception as e:
                return {"success": False, "error": f"Failed to start MCP server: {e}"}

        try:
            response = self._send_request("tools/call", {
                "name": tool_name,
                "arguments": arguments,
            })

            if "error" in response:
                return {
                    "success": False,
                    "error": response["error"].get("message", "Unknown error"),
                    "code": response["error"].get("code"),
                }

            result = response.get("result", {})
            return {
                "success": True,
                "result": result,
            }

        except Exception as e:
            return {"success": False, "error": str(e)}

    def list_tools(self) -> list[McpToolInfo]:
        """List available tools from the MCP server.

        Returns:
            List of tool information dicts
        """
        if self._process is None:
            try:
                self.start_server()
            except Exception:
                return []

        try:
            response = self._send_request("tools/list", {})
            tools = response.get("result", {}).get("tools", [])
            return [
                McpToolInfo(
                    name=t["name"],
                    description=t.get("description", ""),
                    input_schema=t.get("inputSchema", {}),
                )
                for t in tools
            ]
        except Exception:
            return []

    def __del__(self) -> None:
        """Cleanup: stop server on garbage collection."""
        self.stop_server()


class GenesisFetch(GenesisMcpBridge):
    """Genesis artifact for HTTP fetch capability.

    Wraps the @anthropic/mcp-server-fetch MCP server.

    Methods:
        fetch(url, method?, headers?): Fetch a URL and return content
    """

    def __init__(
        self,
        command: str = "npx",
        args: list[str] | None = None,
        env: dict[str, str] | None = None,
    ) -> None:
        """Initialize genesis_fetch.

        Args:
            command: Command to run MCP server (default: npx)
            args: Server arguments (default: @anthropic/mcp-server-fetch)
            env: Environment variables
        """
        super().__init__(
            artifact_id="genesis_fetch",
            description="HTTP fetch capability via MCP server",
            server_command=command,
            server_args=args or ["@anthropic/mcp-server-fetch"],
            server_env=env or {},
        )

        # Register the fetch method
        self.register_method(
            name="fetch",
            handler=self._fetch,
            cost=0,  # Free, but rate-limited
            description="Fetch a URL and return its content"
        )

    def _fetch(self, args: list[Any], invoker_id: str) -> dict[str, Any]:
        """Fetch a URL.

        Args format: [url, method?, headers?]
        - url: URL to fetch (required)
        - method: HTTP method (default: GET)
        - headers: Optional headers dict
        """
        if not args or len(args) < 1:
            return {"success": False, "error": "fetch requires [url]"}

        url = str(args[0])
        method = str(args[1]) if len(args) > 1 else "GET"
        headers = args[2] if len(args) > 2 and isinstance(args[2], dict) else {}

        return self.call_tool("fetch", {
            "url": url,
            "method": method,
            "headers": headers,
        })


class GenesisFilesystem(GenesisMcpBridge):
    """Genesis artifact for sandboxed file I/O.

    Wraps the @anthropic/mcp-server-filesystem MCP server.
    Access is restricted to the agent's sandbox directory.

    Methods:
        read_file(path): Read file contents
        write_file(path, content): Write to a file
        list_directory(path): List directory contents
    """

    sandbox_root: str

    def __init__(
        self,
        sandbox_root: str = "/tmp/agent_sandbox",
        command: str = "npx",
        args: list[str] | None = None,
        env: dict[str, str] | None = None,
    ) -> None:
        """Initialize genesis_filesystem.

        Args:
            sandbox_root: Root directory for sandboxed access
            command: Command to run MCP server
            args: Server arguments
            env: Environment variables
        """
        # Pass sandbox root as allowed directory
        server_args = args or ["@anthropic/mcp-server-filesystem", sandbox_root]

        super().__init__(
            artifact_id="genesis_filesystem",
            description="Sandboxed file I/O via MCP server",
            server_command=command,
            server_args=server_args,
            server_env=env or {},
        )

        self.sandbox_root = sandbox_root

        # Register file methods
        self.register_method(
            name="read_file",
            handler=self._read_file,
            cost=0,
            description="Read file contents from sandbox"
        )

        self.register_method(
            name="write_file",
            handler=self._write_file,
            cost=0,
            description="Write content to file in sandbox"
        )

        self.register_method(
            name="list_directory",
            handler=self._list_directory,
            cost=0,
            description="List directory contents in sandbox"
        )

    def _validate_path(self, path: str) -> str | None:
        """Validate path is within sandbox. Returns error message if invalid."""
        import os
        abs_path = os.path.abspath(os.path.join(self.sandbox_root, path))
        if not abs_path.startswith(os.path.abspath(self.sandbox_root)):
            return f"Path escapes sandbox: {path}"
        return None

    def _read_file(self, args: list[Any], invoker_id: str) -> dict[str, Any]:
        """Read file contents."""
        if not args or len(args) < 1:
            return {"success": False, "error": "read_file requires [path]"}

        path = str(args[0])
        if error := self._validate_path(path):
            return {"success": False, "error": error}

        return self.call_tool("read_file", {"path": path})

    def _write_file(self, args: list[Any], invoker_id: str) -> dict[str, Any]:
        """Write to file."""
        if not args or len(args) < 2:
            return {"success": False, "error": "write_file requires [path, content]"}

        path = str(args[0])
        content = str(args[1])

        if error := self._validate_path(path):
            return {"success": False, "error": error}

        return self.call_tool("write_file", {"path": path, "content": content})

    def _list_directory(self, args: list[Any], invoker_id: str) -> dict[str, Any]:
        """List directory contents."""
        if not args or len(args) < 1:
            return {"success": False, "error": "list_directory requires [path]"}

        path = str(args[0])
        if error := self._validate_path(path):
            return {"success": False, "error": error}

        return self.call_tool("list_directory", {"path": path})


class GenesisWebSearch(GenesisMcpBridge):
    """Genesis artifact for internet search.

    Wraps the @anthropic/mcp-server-brave-search MCP server.
    Requires BRAVE_API_KEY environment variable.

    Methods:
        search(query, limit?): Search the web
    """

    def __init__(
        self,
        command: str = "npx",
        args: list[str] | None = None,
        env: dict[str, str] | None = None,
    ) -> None:
        """Initialize genesis_web_search.

        Args:
            command: Command to run MCP server
            args: Server arguments
            env: Environment variables (should include BRAVE_API_KEY)
        """
        super().__init__(
            artifact_id="genesis_web_search",
            description="Internet search via Brave Search MCP server",
            server_command=command,
            server_args=args or ["@anthropic/mcp-server-brave-search"],
            server_env=env or {},
        )

        # Register search method
        self.register_method(
            name="search",
            handler=self._search,
            cost=0,  # Free, but rate-limited
            description="Search the web using Brave Search"
        )

    def _search(self, args: list[Any], invoker_id: str) -> dict[str, Any]:
        """Search the web.

        Args format: [query, limit?]
        - query: Search query (required)
        - limit: Max results (default: 10)
        """
        if not args or len(args) < 1:
            return {"success": False, "error": "search requires [query]"}

        query = str(args[0])
        limit = int(args[1]) if len(args) > 1 else 10

        return self.call_tool("brave_web_search", {
            "query": query,
            "count": limit,
        })


def create_mcp_artifacts(
    mcp_config: McpConfig,
) -> dict[str, GenesisMcpBridge]:
    """Factory function to create enabled MCP artifacts.

    Args:
        mcp_config: MCP configuration from config schema

    Returns:
        Dict mapping artifact_id -> GenesisMcpBridge
    """
    artifacts: dict[str, GenesisMcpBridge] = {}

    # Create fetch if enabled
    if mcp_config.fetch.enabled:
        artifacts["genesis_fetch"] = GenesisFetch(
            command=mcp_config.fetch.command,
            args=mcp_config.fetch.args,
            env=mcp_config.fetch.env,
        )

    # Create filesystem if enabled
    if mcp_config.filesystem.enabled:
        artifacts["genesis_filesystem"] = GenesisFilesystem(
            command=mcp_config.filesystem.command,
            args=mcp_config.filesystem.args,
            env=mcp_config.filesystem.env,
        )

    # Create web search if enabled
    if mcp_config.web_search.enabled:
        artifacts["genesis_web_search"] = GenesisWebSearch(
            command=mcp_config.web_search.command,
            args=mcp_config.web_search.args,
            env=mcp_config.web_search.env,
        )

    return artifacts
