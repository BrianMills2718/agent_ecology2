# Current Genesis Artifacts

System-provided artifacts that exist at world initialization.

**Last verified:** 2026-01-23 (Plan #160 - Clarified genesis artifacts vs genesis contracts)

---

## Overview

Genesis artifacts are created during world initialization (`World._create_genesis_artifacts()`). They provide core system services that agents interact with via `invoke_artifact`.

All genesis artifacts:
- Have `created_by: "system"` (metadata only, not privileged)
- Are cold-start conveniences - agents could build equivalent functionality
- Are configured in `config/config.yaml` under `genesis:`

**Note:** Genesis contracts (freeware, private, etc.) are NOT artifacts at all - they're Python classes stored in a dict, not in the artifact store. See `contracts.md` for details. They are also cold-start conveniences, but they're permission presets, not invokable services.

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
| `transfer_budget(to_id, amount)` | 1 | Transfer LLM budget to another agent (Plan #30) |
| `get_budget(agent_id)` | 0 | Get LLM budget for an agent (Plan #30) |

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
1. Agent bids on their artifact (accepted anytime)
2. Mint collects bids until next auction resolution
3. At resolution: scores artifacts via external LLM
4. Winner pays second-highest bid (Vickrey auction)
5. Scrip minted based on score
6. UBI distributed to all principals

**Anytime Bidding (Plan #5):** Bids are accepted at any tick, not just
during a specific bidding window. Auctions still resolve on schedule.

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

### genesis_debt_contract

**Purpose:** Non-privileged credit/lending example (Plan #9)

**File:** `src/world/genesis.py` (`GenesisDebtContract` class)

| Method | Cost (compute) | Description |
|--------|----------------|-------------|
| `issue(creditor, principal, rate, due_tick)` | 1 | Create debt request (debtor initiates) |
| `accept(debt_id)` | 0 | Creditor accepts debt |
| `repay(debt_id, amount)` | 0 | Debtor pays back (partial or full) |
| `collect(debt_id)` | 0 | Creditor collects after due_tick |
| `transfer_creditor(debt_id, new_creditor)` | 1 | Sell debt rights to another |
| `check(debt_id)` | 0 | Get debt status with current_owed |
| `list_debts(principal_id)` | 0 | List debts for a principal |
| `list_all()` | 0 | List all debts in system |

**Flow:**
1. Debtor issues debt request → status="pending"
2. Creditor accepts → status="active", interest starts accruing
3. Debtor repays (partial or full) → transfers scrip to creditor
4. After due_tick: creditor can collect remaining (forced transfer)
5. If debtor broke: status="defaulted" (no magic enforcement)

**Interest:** Simple interest: `current_owed = principal + (principal * rate * ticks_elapsed) - amount_paid`

**Tradeable debt:** Creditor can sell debt rights via `transfer_creditor()`. Payment goes to whoever currently holds the debt.

**Key insight:** No kernel-level enforcement. Bad debtors observable via event log. Reputation emerges from observed behavior.

**Demonstrates:** How credit/lending can work without privileged kernel support - just a genesis artifact example.

---

### genesis_store

**Purpose:** Artifact discovery and registry (Gap #16)

**File:** `src/world/genesis.py` (`GenesisStore` class)

| Method | Cost (compute) | Description |
|--------|----------------|-------------|
| `list(filter?)` | 0 | List artifacts with optional filter (includes `interface` field) |
| `get(artifact_id)` | 0 | Get single artifact details (includes `interface` field) |
| `get_interface(artifact_id)` | 0 | Get interface schema for an artifact (Plan #114) |
| `search(query, field?, limit?)` | 0 | Search artifacts by content match (includes `interface` field) |
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
- Interface discovery enabled (Plan #114): `get()`, `list()`, `search()` all return `interface` field
- Dedicated `get_interface()` method for quick schema lookup before invocation

---

### genesis_model_registry

**Purpose:** LLM model access management as tradeable resource (Plan #113)

**File:** `src/world/genesis/model_registry.py` (`GenesisModelRegistry` class)

| Method | Cost (compute) | Description |
|--------|----------------|-------------|
| `list_models()` | 0 | List all available models with properties |
| `get_quota(agent_id, model_id)` | 0 | Get remaining quota for agent on model |
| `transfer_quota(to_agent, model_id, amount)` | 0 | Transfer model quota to another agent |
| `get_available_models(agent_id)` | 0 | Get models agent has quota for |

**Design:**
- Transforms LLM model access into a scarce, tradeable resource
- Enables emergence of model markets and access trading
- Agents can specialize (e.g., one agent accumulates GPT-4 quota for complex tasks)
- Quota transfers use same pattern as scrip transfers

**Config:** Model quotas configured in `config/config.yaml` under agent settings.

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
- `handbook_coordination` - Multi-agent coordination patterns

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
    debt_contract:
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
      period: 10       # Ticks between auction resolutions
      minimum_bid: 1   # Lowest accepted bid
      # ...
```

---

## Key Files

| File | Key Functions | Description |
|------|---------------|-------------|
| `src/world/genesis.py` | `Genesis*` classes | Genesis artifact implementations |
| `src/world/world.py` | `World._create_genesis_artifacts()` | Genesis artifact initialization |
| `config/config.yaml` | `genesis:` section | Configuration |
