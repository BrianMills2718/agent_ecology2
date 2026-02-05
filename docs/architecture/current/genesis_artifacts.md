# Pre-Seeded Artifacts

Artifacts that exist at world initialization for cold-start convenience.

**Last verified:** 2026-02-05 (Plan #302: mint auction params now read from config)

---

## Overview

Pre-seeded artifacts are created during world initialization (`World._create_preseeded_artifacts()`). They provide useful services that agents can use immediately. They are NOT privileged - agents could build equivalent functionality.

**Key change (Plan #254):** The `src/world/genesis/` module has been removed. "Genesis artifacts" are now just pre-seeded artifacts with no special status:
- MCP server artifacts (`mcp_fetch`, `mcp_filesystem`, `mcp_web_search`)
- Handbook artifacts (`handbook_actions`, etc.)

Services that were previously genesis artifacts are now kernel primitives:
- `transfer` - now a kernel action
- `mint` - now a kernel action via `MintAuction`
- Balance queries - now via `query_kernel`

---

## Pre-Seeded Artifacts

### MCP Server Artifacts (Plan #28, #254)

MCP (Model Context Protocol) server wrappers providing external capabilities.

**File:** `src/world/mcp_bridge.py`

| Artifact | Purpose | Methods |
|----------|---------|---------|
| `mcp_fetch` | HTTP fetch capability | `fetch(url, method?, headers?)` |
| `mcp_filesystem` | Sandboxed file I/O | `read_file(path)`, `write_file(path, content)`, `list_directory(path)` |
| `mcp_web_search` | Internet search | `search(query, limit?)` |

**Architecture:**
```
Agent
  └── invoke_artifact("mcp_fetch", "fetch", [...])
        └── McpFetch (McpBridge subclass)
              └── JSON-RPC over stdio
                    └── MCP Server subprocess (npx @anthropic/mcp-server-*)
```

**Design decisions:**
- All MCP methods cost 0 (rate-limited by RateTracker, not scrip)
- Servers start lazily on first invocation
- Servers stop on artifact cleanup
- JSON-RPC 2.0 protocol over stdin/stdout

**Config:** `config/config.yaml` under `genesis.mcp`

---

### mcp_fetch

HTTP fetch capability via MCP server.

| Method | Cost | Description |
|--------|------|-------------|
| `fetch(url, method?, headers?)` | 0 | Fetch URL and return content |

**MCP Server:** `@anthropic/mcp-server-fetch`

---

### mcp_filesystem

Sandboxed file I/O via MCP server.

| Method | Cost | Description |
|--------|------|-------------|
| `read_file(path)` | 0 | Read file contents from sandbox |
| `write_file(path, content)` | 0 | Write content to file in sandbox |
| `list_directory(path)` | 0 | List directory contents in sandbox |

**MCP Server:** `@anthropic/mcp-server-filesystem`

**Security:** All paths validated to be within configured sandbox directory.

---

### mcp_web_search

Internet search via Brave Search.

| Method | Cost | Description |
|--------|------|-------------|
| `search(query, limit?)` | 0 | Search the web |

**MCP Server:** `@anthropic/mcp-server-brave-search`

**Requires:** `BRAVE_API_KEY` environment variable

---

### Handbook Artifacts

Seeded documentation for agents.

**File:** `src/world/world.py` (`World._seed_handbook()`)

**Note:** These are regular data artifacts (not invokable), created during init.

| Artifact | Content |
|----------|---------|
| `handbook_actions` | Action format examples and permissions |
| `handbook_genesis` | *(Deprecated name - now describes kernel actions)* |
| `handbook_resources` | Resource system documentation |
| `handbook_trading` | Escrow trading guide |
| `handbook_mint` | Mint bidding guide |
| `handbook_coordination` | Multi-agent coordination patterns |

**Source:** `src/agents/_handbook/*.md` files

Agents can `read_artifact("handbook_actions")` to learn available actions.

---

## Kernel Primitives (Not Pre-Seeded Artifacts)

The following capabilities are now kernel primitives, not invokable artifacts:

### transfer (Kernel Action)

Scrip transfers are now a kernel action:

```json
{"action_type": "transfer", "recipient_id": "bob", "amount": 10}
```

Optional memo for audit trail:
```json
{"action_type": "transfer", "recipient_id": "bob", "amount": 10, "memo": "reason"}
```

See `docs/architecture/current/resources.md` for details.

### mint (Kernel Action)

Artifact scoring and scrip minting via `MintAuction`:

```json
{"action_type": "mint", "artifact_id": "my_tool", "bid": 5}
```

**File:** `src/world/mint_auction.py`

See `docs/architecture/current/mint.md` for details.

### query_kernel (Kernel Action)

Direct kernel state queries (balances, artifacts, principals):

```json
{"action_type": "query_kernel", "query_type": "balance", "params": {}}
```

See Plan #184 for full query_kernel documentation.

---

## Removed Genesis Artifacts (Plan #254)

The following have been removed:

| Was | Replaced By |
|-----|-------------|
| `genesis_ledger` | `transfer` kernel action + `query_kernel` |
| `genesis_mint` | `mint` kernel action + `MintAuction` kernel class |
| `genesis_rights_registry` | `query_kernel` with `quotas` query type |
| `genesis_escrow` | *(Not yet replaced - future plan)* |
| `genesis_event_log` | `query_kernel` with `events` query type |
| `genesis_debt_contract` | *(Not yet replaced - future plan)* |
| `genesis_model_registry` | `query_kernel` with `model_quotas` query type |
| `genesis_embedder` | *(Not yet replaced - future plan)* |
| `genesis_memory` | *(Not yet replaced - future plan)* |
| `genesis_loop_detector` | *(Not yet replaced - future plan)* |
| `genesis_store` | `query_kernel` with `artifacts` query type (Plan #190) |

**Migration pattern:** Functions that were privileged genesis operations are now:
1. Kernel actions (transfer, mint) - for state-changing operations
2. query_kernel queries - for read-only state access

---

## Configuration

MCP artifacts configured in `config/config.yaml`:

```yaml
genesis:
  mcp:
    fetch:
      enabled: true
      command: "npx"
      args: ["@anthropic/mcp-server-fetch"]
    filesystem:
      enabled: true
      command: "npx"
      args: ["@anthropic/mcp-server-filesystem", "/tmp/agent_sandbox"]
    web_search:
      enabled: true
      command: "npx"
      args: ["@anthropic/mcp-server-brave-search"]
```

---

## Key Files

| File | Description |
|------|-------------|
| `src/world/mcp_bridge.py` | MCP server wrapper artifacts |
| `src/world/mint_auction.py` | Mint auction logic (kernel primitive) |
| `src/world/world.py` | `_create_preseeded_artifacts()`, `_seed_handbook()` |
| `config/config.yaml` | `genesis.mcp` section |
