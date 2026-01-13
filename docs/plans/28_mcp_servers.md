# Gap 28: Pre-seeded MCP Servers

**Status:** ✅ Complete

**Verified:** 2026-01-13T12:00:46Z
**Verification Evidence:**
```yaml
completed_by: scripts/complete_plan.py
timestamp: 2026-01-13T12:00:46Z
tests:
  unit: 997 passed in 10.85s
  e2e_smoke: PASSED (1.81s)
  doc_coupling: passed
commit: 4705401
```
**Priority:** High
**Blocked By:** None
**Blocks:** None

---

## Gap

**Current:** No MCP server integration. Agents cannot access external capabilities like web search, browser automation, or library documentation.

**Target:** Genesis artifacts wrapping MCP servers that agents can invoke like any other artifact.

**Why High Priority:** External capabilities (web search, documentation lookup, browser automation) are foundational for agents to accomplish real-world tasks. Without these, agent utility is severely limited.

---

## Design

### Architecture

Genesis artifacts wrap MCP servers using a common `GenesisMcpBridge` base class:

```
┌─────────────────────────────────────────────────┐
│              Agent                               │
│  invoke("genesis_web_search", "search", {...})   │
└────────────────────┬────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────┐
│         GenesisMcpBridge Subclass                │
│  - Validates input against schema                │
│  - Manages MCP server lifecycle                  │
│  - Handles errors and rate limiting              │
└────────────────────┬────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────┐
│           MCP Server Process                     │
│  (subprocess running npx @mcp/server-xxx)        │
└─────────────────────────────────────────────────┘
```

### Genesis Artifacts to Create

Based on DESIGN_CLARIFICATIONS.md:

| Genesis Artifact | MCP Server Package | Purpose | Cost |
|------------------|-------------------|---------|------|
| `genesis_web_search` | `@anthropic/mcp-server-brave-search` | Internet search | 0 (rate limited) |
| `genesis_context7` | `@upstash/context7-mcp` | Library documentation | 0 |
| `genesis_puppeteer` | `@anthropic/mcp-server-puppeteer` | Browser automation | 0 |
| `genesis_playwright` | TBD (custom or community) | Browser automation alt | 0 |
| `genesis_fetch` | `@anthropic/mcp-server-fetch` | HTTP requests | 0 |
| `genesis_filesystem` | `@anthropic/mcp-server-filesystem` | File I/O (sandboxed) | 0 |
| `genesis_sqlite` | `@anthropic/mcp-server-sqlite` | Local database | 0 |
| `genesis_sequential_thinking` | `@anthropic/mcp-server-sequential-thinking` | Reasoning tool | 0 |
| `genesis_github` | `@anthropic/mcp-server-github` | GitHub API | 0 |

**Phase 1 (MVP):** `genesis_web_search`, `genesis_fetch`, `genesis_filesystem`
**Phase 2:** `genesis_puppeteer`, `genesis_sqlite`, `genesis_context7`
**Phase 3:** `genesis_playwright`, `genesis_sequential_thinking`, `genesis_github`

### Cost Model

From DESIGN_CLARIFICATIONS.md:
- Free MCP operations cost compute (rate limiting applies)
- No artificial scrip cost for free tier services
- Future paid APIs would cost compute + scrip for API fees

This means all initial MCP methods have `cost=0` but consume rate-limited compute.

### GenesisMcpBridge Base Class

```python
class GenesisMcpBridge(GenesisArtifact):
    """Base class for MCP server wrapper artifacts."""

    server_command: str  # e.g., "npx @anthropic/mcp-server-fetch"
    server_args: list[str]  # Additional arguments
    _process: subprocess.Popen | None
    _client: McpClient | None

    def __init__(
        self,
        artifact_id: str,
        description: str,
        server_command: str,
        server_args: list[str] | None = None,
    ):
        super().__init__(artifact_id, description)
        self.server_command = server_command
        self.server_args = server_args or []
        self._process = None
        self._client = None

    def start_server(self) -> None:
        """Start the MCP server subprocess."""
        ...

    def stop_server(self) -> None:
        """Stop the MCP server subprocess."""
        ...

    def call_tool(self, tool_name: str, arguments: dict) -> dict:
        """Call a tool on the MCP server."""
        ...

    def list_tools(self) -> list[dict]:
        """List available tools from the MCP server."""
        ...
```

### Interface Schema

Each genesis MCP artifact exposes an MCP-compatible interface:

```python
{
    "id": "genesis_fetch",
    "type": "genesis",
    "can_execute": True,
    "interface": {
        "tools": [
            {
                "name": "fetch",
                "description": "Fetches a URL and returns content",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "url": {"type": "string", "description": "URL to fetch"},
                        "method": {"type": "string", "default": "GET"}
                    },
                    "required": ["url"]
                }
            }
        ]
    }
}
```

---

## Plan

### Changes Required

| File | Change |
|------|--------|
| `src/world/mcp_bridge.py` | NEW: `GenesisMcpBridge` base class |
| `src/world/genesis.py` | Import and register MCP artifacts |
| `src/config_schema.py` | Add `McpConfig`, `McpServerConfig` |
| `config/config.yaml` | Add `genesis.mcp` section |
| `config/schema.yaml` | Document MCP configuration |
| `requirements.txt` | Add MCP client dependency |
| `tests/test_genesis_mcp.py` | NEW: MCP bridge tests |

### Implementation Steps

#### Step 1: MCP Client Library Setup

1. Research Python MCP client options:
   - `mcp` package (official Anthropic)
   - Direct JSON-RPC over stdio
2. Add dependency to requirements.txt
3. Create minimal wrapper for MCP protocol

#### Step 2: GenesisMcpBridge Base Class

1. Create `src/world/mcp_bridge.py`
2. Implement subprocess management (start/stop server)
3. Implement MCP protocol communication (JSON-RPC over stdio)
4. Add tool invocation with proper error handling
5. Add server lifecycle management (lazy start, cleanup on shutdown)

#### Step 3: Config Schema

Add to `src/config_schema.py`:

```python
class McpServerConfig(StrictModel):
    """Configuration for a single MCP server."""
    enabled: bool = Field(default=True)
    command: str = Field(description="Command to start server")
    args: list[str] = Field(default_factory=list)
    env: dict[str, str] = Field(default_factory=dict)

class McpConfig(StrictModel):
    """MCP server configurations."""
    web_search: McpServerConfig = Field(...)
    fetch: McpServerConfig = Field(...)
    filesystem: McpServerConfig = Field(...)
    # etc.
```

#### Step 4: Phase 1 Artifacts (MVP)

Implement in order:

1. **genesis_fetch** - Simplest, good for testing pattern
   - Methods: `fetch(url, method?, headers?)`

2. **genesis_filesystem** - File I/O within sandbox
   - Methods: `read_file(path)`, `write_file(path, content)`, `list_directory(path)`
   - Security: Restrict to agent's sandbox directory

3. **genesis_web_search** - Internet search
   - Methods: `search(query, limit?)`
   - Requires: Brave API key (environment variable)

#### Step 5: Registration in Genesis

Update `create_genesis_artifacts()` in `genesis.py`:

```python
def create_genesis_artifacts(...):
    artifacts = {}

    # Existing artifacts...

    # MCP artifacts (if enabled)
    mcp_config = get_mcp_config()

    if mcp_config.fetch.enabled:
        artifacts["genesis_fetch"] = GenesisFetch(
            command=mcp_config.fetch.command,
            args=mcp_config.fetch.args,
        )

    # etc.

    return artifacts
```

#### Step 6: Testing

1. Unit tests with mocked MCP server responses
2. Integration tests with actual MCP servers (optional, marked slow)
3. Error handling tests (server crash, timeout, invalid input)

---

## Required Tests

### New Tests (TDD)

Create these tests FIRST, before implementing:

| Test File | Test Function | What It Verifies |
|-----------|---------------|------------------|
| `tests/test_genesis_mcp.py` | `TestMcpBridgeLifecycle::test_mcp_bridge_start_server` | Server subprocess starts |
| `tests/test_genesis_mcp.py` | `TestMcpBridgeLifecycle::test_mcp_bridge_stop_server` | Server subprocess stops |
| `tests/test_genesis_mcp.py` | `TestMcpBridgeLifecycle::test_mcp_bridge_call_tool` | Tool invocation works |
| `tests/test_genesis_mcp.py` | `TestMcpBridgeLifecycle::test_mcp_bridge_error_handling` | Errors returned properly |
| `tests/test_genesis_mcp.py` | `TestGenesisFetch::test_genesis_fetch_methods` | Fetch artifact has correct methods |
| `tests/test_genesis_mcp.py` | `TestGenesisFetch::test_genesis_fetch_invoke` | Fetch invocation works |
| `tests/test_genesis_mcp.py` | `TestMcpConfig::test_mcp_config_schema` | Config schema validates |
| `tests/test_genesis_mcp.py` | `TestMcpConfig::test_mcp_disabled_not_created` | Disabled servers not registered |
| `tests/test_genesis_mcp.py` | `TestMcpRegistration::test_mcp_registered_in_genesis` | MCP artifacts in genesis |

### Existing Tests (Must Pass)

| Test Pattern | Why |
|--------------|-----|
| `tests/integration/test_genesis_store.py` | Store still discovers artifacts |
| `tests/integration/test_invoke.py` | Invoke mechanism unchanged |
| `tests/unit/test_genesis_contracts.py` | Genesis contracts unchanged |

---

## Verification

### Tests & Quality
- [ ] All required tests pass: `python scripts/check_plan_tests.py --plan 28`
- [ ] Full test suite passes: `pytest tests/`
- [ ] Type check passes: `python -m mypy src/ --ignore-missing-imports`

### Documentation
- [ ] `docs/architecture/current/genesis_artifacts.md` updated with MCP section
- [ ] `docs/architecture/current/configuration.md` updated with MCP config
- [ ] Doc-coupling check passes: `python scripts/check_doc_coupling.py`

### Completion Ceremony
- [ ] Plan file status → `✅ Complete`
- [ ] `plans/CLAUDE.md` index → `✅ Complete`
- [ ] Claim released from Active Work table (root CLAUDE.md)
- [ ] Branch merged or PR created

---

## Open Questions

1. **MCP Client Choice**: Use official `mcp` package or implement minimal JSON-RPC?
   - Recommendation: Start with minimal JSON-RPC for fewer dependencies

2. **Server Lifecycle**: Start servers on-demand or keep running?
   - Recommendation: Lazy start on first invocation, stop on simulation end

3. **Brave API Key**: How to handle API keys?
   - Recommendation: Environment variables, documented in config schema

4. **Rate Limiting**: MCP operations cost "compute" - how to enforce?
   - Recommendation: Integrate with RateTracker from Gap #1

---

## Notes

### Decision from DESIGN_CLARIFICATIONS.md

> Genesis artifacts wrap MCP servers for common capabilities. All free/open-source.
>
> **Cost model:**
> - Free MCP operations cost compute (rate limiting)
> - Paid APIs (if added later) cost compute + scrip for API fees

### Why MCP over Direct Integration

1. **Standardized Interface**: LLMs trained on MCP schemas
2. **Process Isolation**: MCP servers run in separate processes
3. **Ecosystem**: Many existing MCP servers available
4. **Future-proof**: Easy to add new capabilities

### Security Considerations

- Filesystem access restricted to sandbox directory
- Web requests rate-limited
- No shell execution through MCP (use container sandbox)
