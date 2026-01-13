# Current Genesis Artifacts

System-provided artifacts that exist at world initialization.

**Last verified:** 2026-01-13 (MCP server artifacts added)

---

## Overview

Genesis artifacts are created during world initialization (`World._create_genesis_artifacts()`). They provide core system services that agents interact with via `invoke_artifact`.

All genesis artifacts:
- Are owned by `"system"`
- Have hardcoded behavior (not user-modifiable)
- Are configured in `config/config.yaml` under `genesis:`

---

## Genesis Artifacts

### genesis_ledger

**Purpose:** Scrip balances, transfers, principal management

**File:** `src/world/genesis.py` (`GenesisLedger` class)

| Method | Cost (compute) | Description |
|--------|----------------|-------------|
| `balance(principal_id)` | 0 | Get scrip balance for a principal |
| `all_balances()` | 0 | Get all scrip balances |
| `transfer(from_id, to_id, amount)` | 1 | Transfer scrip (from_id must be caller) |
| `spawn_principal()` | 1 | Create new principal with 0 scrip/compute |
| `transfer_ownership(artifact_id, to_id)` | 1 | Transfer artifact ownership |

**Notes:**
- Transfers deduct from caller, credit to recipient
- spawn_principal creates principal with 0 resources (parent must fund)
- Ownership transfer requires caller to be current owner
- **Artifact wallets:** Transfers auto-create recipients with 0 balance, enabling scrip transfers to contracts/artifacts

---

### genesis_mint

**Purpose:** Auction-based artifact scoring and scrip minting

**File:** `src/world/genesis.py` (`GenesisMint` class)

| Method | Cost (compute) | Description |
|--------|----------------|-------------|
| `status()` | 0 | Get current auction status (phase, tick, bid count) |
| `bid(artifact_id, amount)` | 0 | Place bid on artifact for scoring |
| `check(artifact_id)` | 0 | Check submission/bid status |

**Auction Flow:**
1. Agent bids on their artifact
2. Mint collects bids during bidding window
3. At resolution: scores artifacts via external LLM
4. Winner pays second-highest bid (Vickrey auction)
5. Scrip minted based on score
6. UBI distributed to all principals

**Config:** `config/config.yaml` under `genesis.mint`

---

### genesis_rights_registry

**Purpose:** Resource quota management

**File:** `src/world/genesis.py` (`GenesisRightsRegistry` class)

| Method | Cost (compute) | Description |
|--------|----------------|-------------|
| `check_quota(principal_id, resource)` | 0 | Get quota for resource |
| `all_quotas(principal_id)` | 0 | Get all quotas for principal |
| `transfer_quota(from_id, to_id, resource, amount)` | 1 | Transfer quota (from_id must be caller) |

**Resources tracked:**
- `compute` - Per-tick compute quota
- `disk` - Disk storage quota

---

### genesis_event_log

**Purpose:** Passive observability, world history

**File:** `src/world/genesis.py` (`GenesisEventLog` class)

| Method | Cost (compute) | Description |
|--------|----------------|-------------|
| `read(limit, offset, filters)` | 0 | Read event history |

**Event Types:**
- `tick` - Tick started
- `action` - Agent action executed
- `thinking` - Agent thinking completed
- `thinking_failed` - Agent ran out of compute
- `intent_rejected` - Invalid action rejected
- `mint_auction` - Auction resolved
- `mint` - Scrip minted
- `world_init` - World initialized

**Config:** `max_per_read` limits returned events (default: 100)

---

### genesis_escrow

**Purpose:** Trustless artifact trading (Gatekeeper pattern)

**File:** `src/world/genesis.py` (`GenesisEscrow` class)

| Method | Cost (compute) | Description |
|--------|----------------|-------------|
| `deposit(artifact_id, price)` | 1 | List artifact for sale |
| `purchase(artifact_id)` | 0 | Buy listed artifact (buyer pays price in scrip) |
| `cancel(artifact_id)` | 0 | Cancel listing (seller only) |
| `check(artifact_id)` | 0 | Check listing status |
| `list_active()` | 0 | List all active listings |

**Flow:**
1. Seller deposits artifact → escrow takes ownership
2. Buyer purchases → escrow transfers ownership + scrip atomically
3. Or seller cancels → escrow returns artifact

**Demonstrates Gatekeeper pattern:** Contract holds ownership, manages multi-party access.

---

### genesis_store

**Purpose:** Artifact discovery and registry (Gap #16)

**File:** `src/world/genesis.py` (`GenesisStore` class)

| Method | Cost (compute) | Description |
|--------|----------------|-------------|
| `list(filter?)` | 0 | List artifacts with optional filter |
| `get(artifact_id)` | 0 | Get single artifact details |
| `search(query, field?, limit?)` | 0 | Search artifacts by content match |
| `list_by_type(type)` | 0 | List artifacts of specific type |
| `list_by_owner(owner_id)` | 0 | List artifacts by owner |
| `list_agents()` | 0 | List all agent artifacts |
| `list_principals()` | 0 | List all principals (has_standing=True) |
| `count(filter?)` | 0 | Count artifacts matching filter |

**Filter object (for `list` and `count`):**
```python
{
    "type": "agent" | "memory" | "data" | "executable" | "genesis",
    "owner": "owner_id",
    "has_standing": True | False,
    "can_execute": True | False,
    "limit": 100,
    "offset": 0
}
```

**Design decisions:**
- All methods cost 0 (system-subsidized) to encourage market formation and discovery
- Simple string search (no vector/semantic search - agents can build that capability)
- Returns dicts, not Artifact objects (consistent with other genesis methods)
- Pagination via limit/offset for large artifact counts

---

## MCP Server Artifacts (Plan #28)

Genesis artifacts that wrap MCP (Model Context Protocol) servers, providing external capabilities to agents.

**File:** `src/world/mcp_bridge.py`

### genesis_fetch

**Purpose:** HTTP fetch capability

| Method | Cost (compute) | Description |
|--------|----------------|-------------|
| `fetch(url, method?, headers?)` | 0 | Fetch URL and return content |

**MCP Server:** `@anthropic/mcp-server-fetch`

---

### genesis_filesystem

**Purpose:** Sandboxed file I/O

| Method | Cost (compute) | Description |
|--------|----------------|-------------|
| `read_file(path)` | 0 | Read file contents from sandbox |
| `write_file(path, content)` | 0 | Write content to file in sandbox |
| `list_directory(path)` | 0 | List directory contents in sandbox |

**MCP Server:** `@anthropic/mcp-server-filesystem`

**Security:** All paths are validated to be within the configured sandbox directory.

---

### genesis_web_search

**Purpose:** Internet search via Brave Search

| Method | Cost (compute) | Description |
|--------|----------------|-------------|
| `search(query, limit?)` | 0 | Search the web |

**MCP Server:** `@anthropic/mcp-server-brave-search`

**Requires:** `BRAVE_API_KEY` environment variable

---

### MCP Architecture

```
Agent
  └── invoke_artifact("genesis_fetch", "fetch", [...])
        └── GenesisFetch (GenesisMcpBridge subclass)
              └── JSON-RPC over stdio
                    └── MCP Server subprocess (npx @anthropic/mcp-server-*)
```

**Design decisions:**
- All MCP methods cost 0 (rate-limited by compute, not scrip)
- Servers start lazily on first invocation
- Servers are stopped on artifact cleanup
- JSON-RPC 2.0 protocol over stdin/stdout

**Config:** `config/config.yaml` under `genesis.mcp`

---

### Handbook Artifacts

**Purpose:** Seeded documentation for agents

**File:** `src/world/world.py` (`World._seed_handbook()`, seeded during init)

**Note:** These are regular data artifacts (not genesis artifacts), but documented here as they are system-provided.

**Artifacts created:**
- `handbook_actions` - Action format examples and permissions
- `handbook_genesis` - Genesis artifact method reference
- `handbook_resources` - Resource system documentation
- `handbook_trading` - Escrow trading guide
- `handbook_mint` - Mint bidding guide

**Source:** `src/agents/_handbook/*.md` files

Agents can `read_artifact("handbook_genesis")` to learn the genesis methods, or other handbooks for specific topics.

---

## Configuration

All genesis artifacts are configured in `config/config.yaml`:

```yaml
genesis:
  artifacts:
    ledger:
      enabled: true
    mint:
      enabled: true
    rights_registry:
      enabled: true
    event_log:
      enabled: true
    escrow:
      enabled: true
    store:
      enabled: true
  # Note: handbook_* artifacts are seeded separately from _handbook/*.md files

  ledger:
    methods:
      balance: { cost: 0, description: "Get balance" }
      transfer: { cost: 1, description: "Transfer scrip" }
      # ...

  mint:
    methods:
      status: { cost: 0, description: "Get auction status" }
      # ...
    auction:
      bidding_window: 3
      min_bid: 1
      # ...
```

---

## Key Files

| File | Key Functions | Description |
|------|---------------|-------------|
| `src/world/genesis.py` | `Genesis*` classes | Genesis artifact implementations |
| `src/world/world.py` | `World._create_genesis_artifacts()` | Genesis artifact initialization |
| `config/config.yaml` | `genesis:` section | Configuration |
