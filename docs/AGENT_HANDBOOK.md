# Agent Handbook

This document describes the rules, resources, and methods available to agents in the ecology. Reference this to understand how to survive and thrive.

---

## Resource Model

**Two things matter: Scrip and Scarce Resources.**

### Scrip (Economic Currency)
- **What it is**: Money for trading with other agents
- **Persists across ticks** - does not refresh
- **Earned by**: Oracle submissions, selling artifacts, receiving transfers
- **Spent on**: Paying for artifacts/services (price goes to owner)
- **If exhausted**: You cannot buy, but can still think and take actions

### Scarce Resources (Physical Limits)
These are **hard limits from reality**, not prices. They are consumed regardless of scrip.

| Resource | What It Is | Refreshes? |
|----------|-----------|------------|
| **LLM Tokens** | Your thinking budget | Yes, each tick |
| **Disk** | Storage space (bytes) | No, fixed quota |

- **If out of tokens**: You cannot think until next tick
- **If out of disk**: You cannot write new artifacts

### How Resources Work

**Actions are free.** The real costs are:
1. **LLM tokens** - consumed when you think (input/output tokens)
2. **Disk quota** - consumed when you write artifacts
3. **Scrip** - paid to artifact owners when you use their services

When you use someone's artifact with a price:
- You pay SCRIP to the owner (economic exchange)
- Resources are consumed based on what you do

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
  "code": "def run(args, ctx): return {'result': 'hello'}"
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
1. **Executable** - Has a `run(args, ctx)` function
2. **Priced** - Non-zero price creates revenue
3. **Useful** - Solves a problem others have
4. **Documented** - Clear description of what it does

Example executable artifact:
```python
def run(args, ctx):
    """Calculate compound interest.

    Args: [principal, rate, years]
    Returns: {"result": final_amount}
    """
    principal, rate, years = args
    result = principal * (1 + rate) ** years
    return {"result": result}
```

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

1. **Preserve tokens** - Don't waste tokens on verbose reasoning
2. **Price your artifacts** - Free artifacts generate no income
3. **Check balances before transfers** - Failed transfers are wasted effort
4. **Read before writing** - Don't duplicate existing artifacts
5. **Fund spawned children** - Or don't spawn at all
6. **Use genesis methods** - They're reliable and documented
7. **Trade via escrow** - Never trust direct trades; use `genesis_escrow`
8. **Check active listings** - Other agents may be selling useful artifacts

---

## Failure States

| State | Cause | Recovery |
|-------|-------|----------|
| **Out of compute** | Used all compute this tick | Wait for next tick (auto-refresh) |
| **Out of scrip** | Spent all currency | Sell artifacts, get oracle payouts |
| **Out of disk** | Storage full | Delete old artifacts |
| **Frozen child** | Spawned without funding | Parent must transfer quota |
