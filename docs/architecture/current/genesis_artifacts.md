# Current Genesis Artifacts

System-provided artifacts that exist at world initialization.

**Last verified:** 2026-01-11 (costs updated to match config)

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

### genesis_oracle

**Purpose:** Auction-based artifact scoring and scrip minting

**File:** `src/world/genesis.py` (`GenesisOracle` class)

| Method | Cost (compute) | Description |
|--------|----------------|-------------|
| `status()` | 0 | Get current auction status (phase, tick, bid count) |
| `bid(artifact_id, amount)` | 0 | Place bid on artifact for scoring |
| `check(artifact_id)` | 0 | Check submission/bid status |

**Auction Flow:**
1. Agent bids on their artifact
2. Oracle collects bids during bidding window
3. At resolution: scores artifacts via external LLM
4. Winner pays second-highest bid (Vickrey auction)
5. Scrip minted based on score
6. UBI distributed to all principals

**Config:** `config/config.yaml` under `genesis.oracle`

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
- `intent_rejected` - Invalid action rejected
- `oracle_auction` - Auction resolved

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

### Handbook Artifacts

**Purpose:** Seeded documentation for agents

**File:** `src/world/world.py` (`World._seed_handbook()`, seeded during init)

**Note:** These are regular data artifacts (not genesis artifacts), but documented here as they are system-provided.

**Artifacts created:**
- `handbook_actions` - Action format examples and permissions
- `handbook_genesis` - Genesis artifact method reference
- `handbook_resources` - Resource system documentation
- `handbook_trading` - Escrow trading guide
- `handbook_oracle` - Oracle bidding guide

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
    oracle:
      enabled: true
    rights_registry:
      enabled: true
    event_log:
      enabled: true
    escrow:
      enabled: true
  # Note: handbook_* artifacts are seeded separately from _handbook/*.md files

  ledger:
    methods:
      balance: { cost: 0, description: "Get balance" }
      transfer: { cost: 1, description: "Transfer scrip" }
      # ...

  oracle:
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
