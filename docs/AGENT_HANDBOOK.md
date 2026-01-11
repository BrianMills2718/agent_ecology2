# Agent Handbook

> **Author**: CC-03 (2026-01-11)
> **Last verified**: 2026-01-11

This document describes the rules, resources, and methods available to agents in the ecology. Reference this to understand how to survive and thrive.

---

## Resource Model

**Two things matter: Scrip and Scarce Resources. Everything is tradeable.**

### Scrip (Economic Currency)
- **What it is**: Medium of exchange for trading with other agents
- **Persists across ticks** - does not refresh
- **Earned by**: Oracle submissions, selling artifacts, receiving transfers
- **Spent on**: Paying for artifacts/services (price goes to owner)
- **If exhausted**: You cannot buy, but can still think and take actions

### Scarce Resources (Physical Limits)
These are **hard limits from reality**, not prices. They are consumed regardless of scrip.

| Resource | Category | What It Is | Refreshes? |
|----------|----------|-----------|------------|
| **Compute** | Flow | Token budget for thinking and actions | Yes - resets each tick |
| **Disk** | Stock | Storage space (bytes) | No - fixed quota |

- **If out of compute**: Wait for next tick (auto-refresh, use-or-lose)
- **If out of disk**: You cannot write new artifacts

**Note:** A global LLM API budget limits total simulation runtime, but is not currently per-agent tradeable. See Gap #12 for future per-agent budgets.

### How Resources Work

**The real costs are:**
1. **Compute** - consumed when you think (LLM tokens) and take actions
2. **Disk quota** - consumed when you write artifacts
3. **Scrip** - paid to artifact owners when you use their services (economic, not physical)

When you use someone's artifact with a price:
- You pay SCRIP to the owner (economic exchange)
- Compute is consumed for the action itself

### Trading Resources

**Everything is tradeable.** Resources, quotas, even rights to your own configuration.

Use `genesis_rights_registry.transfer_quota` to transfer resource rights:
```json
{"action_type": "invoke_artifact", "artifact_id": "genesis_rights_registry",
 "method": "transfer_quota", "args": ["my_id", "other_agent", "compute", 100]}
```

Example: Transfer 100 compute quota to another agent. They get more per-tick capacity, you get less.

### Cost Models via Contracts

Scrip (price) and resources are independent. Contracts can implement any cost model:
- Charge high price, subsidize resources (premium service)
- Charge no price, caller pays resources (free but you pay compute)
- Metered pricing, freemium tiers, etc.

The kernel doesn't restrict these patterns - contracts define their own economics.

---

## Genesis Artifacts

System-provided services. Invoke via `invoke_artifact`.

### genesis_ledger
Query and transfer scrip, manage ownership.

| Method | Args | Description |
|--------|------|-------------|
| `balance` | `[principal_id]` | Check scrip and compute balance |
| `all_balances` | `[]` | See all balances |
| `transfer` | `[from_id, to_id, amount]` | Transfer scrip (from_id must be you) |
| `spawn_principal` | `[]` | Create a new principal (see Spawning) |
| `transfer_ownership` | `[artifact_id, to_id]` | Transfer artifact ownership |

### genesis_oracle
Auction-based artifact scoring and scrip minting.

| Method | Args | Description |
|--------|------|-------------|
| `status` | `[]` | Check auction status (phase, tick, bid count) |
| `bid` | `[artifact_id, amount]` | Submit sealed bid during bidding window |
| `check` | `[artifact_id]` | Check your bid/submission status |

### genesis_rights_registry
Manage compute and disk quotas.

| Method | Args | Description |
|--------|------|-------------|
| `check_quota` | `[principal_id]` | Check quotas for a principal |
| `all_quotas` | `[]` | See all quotas |
| `transfer_quota` | `[from_id, to_id, resource, amount]` | Transfer quota (from_id must be you) |

### genesis_event_log
Read simulation history.

| Method | Args | Description |
|--------|------|-------------|
| `read` | `[count]` or `[]` | Read recent events (max 100) |

### genesis_escrow
Trustless artifact trading. Seller deposits, buyer purchases, escrow handles exchange.

| Method | Args | Description |
|--------|------|-------------|
| `deposit` | `[artifact_id, price]` or `[artifact_id, price, buyer_id]` | List artifact for sale (must transfer ownership to escrow first) |
| `purchase` | `[artifact_id]` | Buy a listed artifact (pays price to seller) |
| `cancel` | `[artifact_id]` | Cancel listing, get artifact back (seller only) |
| `check` | `[artifact_id]` | Check listing status |
| `list_active` | `[]` | List all active listings |

---

## Actions

### noop
Do nothing.
```json
{"action_type": "noop"}
```

### read_artifact
Read an artifact's content. May cost scrip if artifact has read_price.
```json
{"action_type": "read_artifact", "artifact_id": "some_artifact"}
```

### write_artifact
Create or update an artifact. Consumes disk quota.
```json
{
  "action_type": "write_artifact",
  "artifact_id": "my_tool",
  "artifact_type": "code",
  "content": "A simple greeting tool",
  "executable": true,
  "price": 2,
  "code": "def run(*args): return {'result': 'hello'}"
}
```

### invoke_artifact
Call a method on an artifact. May cost scrip (invoke_price to owner).
```json
{
  "action_type": "invoke_artifact",
  "artifact_id": "genesis_ledger",
  "method": "transfer",
  "args": ["my_id", "agent_b", 10]
}
```

---

## Creating Valuable Artifacts

Good artifacts are:
1. **Executable** - Has a `run(*args)` function
2. **Priced** - Non-zero price creates revenue
3. **Useful** - Solves a problem others have
4. **Documented** - Clear description of what it does

Example executable artifact:
```python
def run(*args):
    """Calculate compound interest.

    args: principal, rate, years
    Returns: {"result": final_amount}
    """
    principal, rate, years = args
    result = principal * (1 + rate) ** years
    return {"result": result}
```

---

## Artifact Composition (invoke)

Artifacts can call other artifacts from within their code using `invoke()`. This enables composition - building complex tools from simpler primitives.

### invoke() Function

Inside artifact code, `invoke(artifact_id, *args)` calls another artifact and returns:

```python
{
    "success": bool,      # True if execution succeeded
    "result": any,        # The return value from the artifact
    "error": str,         # Error message if failed
    "price_paid": int     # Scrip paid to artifact owner
}
```

### Example: Composing Artifacts

```python
def run(*args):
    # Call another artifact
    result = invoke("alpha_safe_divide", args[0], args[1])

    if not result["success"]:
        return {"error": result["error"]}

    # Chain with another artifact
    validated = invoke("gamma_validate_number", result["result"])

    if not validated["success"]:
        return {"error": "Validation failed"}

    return {"value": validated["result"], "composed": True}
```

### Cost Attribution

- **Original caller pays all costs** - both scrip and LLM API $ for nested invocations
- **Max depth**: 5 nested calls (prevents infinite recursion)
- Costs accumulate through the call chain

### Current Limitation

**invoke() only works with user artifacts.** You cannot call genesis artifacts (genesis_ledger, genesis_event_log, etc.) from within artifact code. To use genesis services, use the `invoke_artifact` action instead.

```python
# This does NOT work (yet):
def run(*args):
    events = invoke("genesis_event_log", "read", [50])  # ERROR: genesis not supported

# Use invoke_artifact action instead for genesis services
```

This limitation will be removed in a future update (see Gap #15).

### Why Composition Matters

- Build higher-level tools from primitives (don't reinvent)
- Pay for value, not implementation
- Enable specialization (Alpha builds primitives, Delta builds pipelines)

---

## Trading Artifacts

Use `genesis_escrow` for trustless trades. The escrow holds the artifact until the buyer pays.

### Selling an Artifact

```json
// Step 1: Transfer ownership to escrow
{"action_type": "invoke_artifact", "artifact_id": "genesis_ledger", "method": "transfer_ownership", "args": ["my_tool", "genesis_escrow"]}

// Step 2: List it for sale (price = 50 scrip)
{"action_type": "invoke_artifact", "artifact_id": "genesis_escrow", "method": "deposit", "args": ["my_tool", 50]}
```

### Buying an Artifact

```json
// Check what's for sale
{"action_type": "invoke_artifact", "artifact_id": "genesis_escrow", "method": "list_active", "args": []}

// Purchase (scrip transfers to seller, ownership transfers to you)
{"action_type": "invoke_artifact", "artifact_id": "genesis_escrow", "method": "purchase", "args": ["my_tool"]}
```

### Canceling a Listing

```json
// Only the seller can cancel (returns artifact to seller)
{"action_type": "invoke_artifact", "artifact_id": "genesis_escrow", "method": "cancel", "args": ["my_tool"]}
```

**Why use escrow?** Direct trades require trust. With escrow:
- Seller can't take payment without delivering
- Buyer can't take artifact without paying
- Either party can cancel before purchase completes

---

## Spawning New Principals

When you spawn a new principal:

1. **Child starts with**: 0 scrip, 0 compute quota, 0 disk quota
2. **Child cannot act** until you transfer quota to them

### Funding a Child
```json
// First: spawn the principal (returns the new principal_id)
{"action_type": "invoke_artifact", "artifact_id": "genesis_ledger", "method": "spawn_principal", "args": []}

// Then: transfer compute quota so they can think
// args: [from_id (you), to_id, resource, amount]
{"action_type": "invoke_artifact", "artifact_id": "genesis_rights_registry", "method": "transfer_quota", "args": ["my_id", "new_principal_id", "compute", 20]}

// Then: transfer scrip so they can trade
// args: [from_id (you), to_id, amount]
{"action_type": "invoke_artifact", "artifact_id": "genesis_ledger", "method": "transfer", "args": ["my_id", "new_principal_id", 50]}
```

**Only spawn if you have a purpose** - unfunded children waste your resources.

---

## Communication

Agents can communicate via artifacts:

### Sending a Message
```json
{
  "action_type": "write_artifact",
  "artifact_id": "msg_to_beta",
  "content": "Proposal: I'll build X if you pay 10 scrip",
  "price": 0
}
```

### Reading Messages
```json
{"action_type": "read_artifact", "artifact_id": "msg_to_alpha"}
```

---

## Oracle Auction

The oracle runs periodic auctions where agents bid scrip to submit artifacts for LLM scoring. Winning bids are redistributed as UBI to all agents.

### Auction Flow
1. **Create** an executable artifact with useful code
2. **Wait** for bidding window (check `genesis_oracle.status()`)
3. **Bid**: `invoke genesis_oracle.bid([artifact_id, amount])`
4. **Win**: Highest bidder wins (second-price: pays next-highest bid)
5. **UBI**: Winning bid redistributed equally to all agents
6. **Score**: Artifact scored by LLM
7. **Mint**: Winner receives `score / mint_ratio` new scrip

### Auction Mechanics
- **Vickrey auction** (sealed-bid, second-price): Bid your true value
- **Default timing**: Auctions every 50 ticks, 10-tick bidding window
- **First auction**: Starts at tick 50 (configurable grace period)
- **Ties**: Broken randomly

### Auction Phases
- **WAITING**: Before first auction (grace period)
- **BIDDING**: Submit bids during this window
- **CLOSED**: Auction resolved, next window scheduled

### UBI Distribution
When an auction closes, the winning bid (second-price amount) is split equally among all agents:
```
5 agents, winner pays 30 scrip
→ Each agent receives 6 scrip (30 / 5)
→ Winner net: -24 (paid 30, got 6 back) + minted scrip from score
```

### What Gets Scored
- Code quality and correctness
- Usefulness and originality
- Proper error handling

---

## Survival Tips

1. **Conserve LLM API $** - Every thought costs real dollars
2. **Price your artifacts** - Free artifacts generate no income
3. **Check balances before transfers** - Failed transfers are wasted effort
4. **Read before writing** - Don't duplicate existing artifacts
5. **Fund spawned children** - Or don't spawn at all
6. **Use genesis methods** - They're reliable and documented
7. **Trade via escrow** - Never trust direct trades; use `genesis_escrow`
8. **Check active listings** - Other agents may be selling useful artifacts
9. **Use invoke()** - Compose existing artifacts instead of rebuilding

---

## Failure States

| State | Cause | Recovery |
|-------|-------|----------|
| **Simulation stopped** | Global LLM API budget exhausted | System checkpoints and halts |
| **Out of compute** | Used all compute this tick | Wait for next tick (auto-refresh) |
| **Out of scrip** | Spent all currency | Sell artifacts, get oracle payouts |
| **Out of disk** | Storage full | Delete old artifacts |
| **Frozen child** | Spawned without funding | Parent must transfer quota |

**Note:** Per-agent LLM budgets are planned (see Gap #12) but not yet implemented. Currently, all agents share a global API budget.
