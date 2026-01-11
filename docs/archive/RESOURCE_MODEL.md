# Resource Model

> **⚠️ DEPRECATED:** This document is superseded by:
> - **Current implementation:** [architecture/current/resources.md](architecture/current/resources.md)
> - **Target design:** [architecture/target/resources.md](architecture/target/resources.md)
>
> This file is kept for historical reference. Do not update.

---

This document describes how Agent Ecology models scarce resources and economic exchange.

> **Related docs**: `AGENT_HANDBOOK.md` (agent-facing), `CLAUDE.md` (implementation reference)

## Core Principle: Physics-First

Resources model **real scarcity**, not arbitrary friction.

```
┌─────────────────────────────────────────────────────────────┐
│                    SCRIP (Economic Layer)                   │
│  Value exchange between agents. Market-determined prices.   │
│  Flows: Agent → Agent (payment for value)                   │
└─────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────┐
│               PHYSICAL RESOURCES (Reality Layer)            │
│  Hard limits from reality. Measured, not negotiated.        │
│  LLM tokens, disk space, compute quotas                     │
└─────────────────────────────────────────────────────────────┘
```

**Both layers exist but are independent.** You can be rich in scrip but starved of compute, or vice versa.

---

## Physical Resources

Hard constraints measured from reality:

| Resource | Category | What It Is | Behavior |
|----------|----------|-----------|----------|
| **llm_budget** | Stock | $ for API calls | Finite, never refreshes |
| **disk** | Stock | Storage bytes | Finite, never refreshes |
| **compute** | Flow | CPU/GPU cycles | Quota per tick, refreshes |
| **bandwidth** | Flow | Network I/O | Quota per tick, refreshes |

### Stock vs Flow

- **Stock resources** are finite pools. When exhausted, agents must acquire more from others.
- **Flow resources** refresh each tick. Unused quota doesn't carry over.

### What Costs Resources

| Activity | Resource Cost |
|----------|---------------|
| **Thinking** | LLM tokens from agent's llm_budget |
| **Writing artifacts** | Disk quota for storage |
| **Actions (read/write/invoke)** | **Free** - no compute cost |
| **Genesis method fees** | Scrip (economic, not physical) |

Actions are deliberately free. Real constraints come from thinking (tokens) and storage (disk), not arbitrary friction.

### Two-Layer Model

When invoking an executable artifact, **two independent deductions** occur:

```
Layer 1 (Scrip):     caller pays PRICE to owner     → Economic exchange
Layer 2 (Resources): caller pays RESOURCES to system → Physical consumption
```

**Example flow**:
```
1. Bob invokes Alice's artifact (price=5)
2. Bob pays 5 scrip to Alice (Layer 1)
3. Execution runs, consuming LLM API $
4. Bob pays resources (Layer 2)
```

### Flexible Cost Attribution via Contracts

The kernel does not hardcode resource payment policies. Instead, **contracts can implement any cost model**:

- A contract can charge callers and subsidize resources from its own balance
- A contract can implement metered pricing, freemium tiers, or premium services
- Genesis contracts (like `genesis_escrow`) demonstrate patterns others can follow

This keeps the kernel simple while allowing arbitrarily complex economic arrangements to emerge through contract code. See the Contracts section below for examples.

---

## Scrip (Economic Currency)

Medium of exchange for value. **Not a physical resource.**

| Aspect | Description |
|--------|-------------|
| Purpose | Pay for artifacts, services, signal value |
| Determined by | Market (agent negotiation, price discovery) |
| Sources | Oracle minting, selling artifacts, transfers |
| Sinks | Buying artifacts, service fees, genesis method fees |

### Where Scrip Flows

1. **Artifact trades** - Buying/selling artifacts (price → owner)
2. **Oracle auction** - Vickrey (second-price) sealed-bid auction
3. **Oracle UBI** - Winning bid redistributed equally to all agents
4. **Oracle minting** - New scrip created for winning submissions
5. **Transfers** - Direct scrip transfers between agents
6. **Genesis method fees** - Configurable per-method fees

### Oracle Economy

The oracle runs periodic Vickrey auctions:
1. Agents submit sealed bids (artifact + amount)
2. Highest bidder wins, pays **second-highest** bid
3. Winning bid redistributed as **UBI** to all agents
4. Winner's artifact scored by LLM
5. Winner receives newly minted scrip based on score

This creates a sustainable economy: bidding costs flow to all agents (not destroyed), while value creation mints new scrip.

---

## Resource Rights

Every physical resource has associated **rights**. Rights are distributed initially and tradeable.

```
Agent A has: llm_budget_rights=$2, disk_rights=2000bytes, compute_quota=50/tick
Agent A can trade any of these to Agent B
```

### Trade Types

- **Permanent transfer** - Rights moved permanently
- **Time-limited** - Via contract (returns after N ticks)
- **Conditional** - Via contract (returns if condition met)

### genesis_rights_registry

System artifact for managing resource quotas:

```json
{"action_type": "invoke_artifact", "artifact_id": "genesis_rights_registry",
 "method": "transfer_quota", "args": ["agent_a", "agent_b", "compute", 25]}
```

---

## Failure Modes

| State | Cause | Recovery |
|-------|-------|----------|
| **Frozen** | Out of llm_budget | Buy rights from others |
| **Out of compute** | Used tick's quota | Wait for next tick |
| **Out of disk** | Storage full | Delete artifacts or buy quota |
| **Broke** | Out of scrip | Sell artifacts/services/rights |

---

## Contracts Handle Complexity

Rather than hardcoded policies, **contracts define custom payment logic**:

```python
# Example: A contract that charges callers and pays the owner
def run(caller_id, *args):
    price = 10
    # Deduct from caller
    pay("contract_wallet", price)  # Contract receives payment

    # Do the work...
    result = expensive_operation(*args)

    # Pay owner (after taking a cut)
    owner = "agent_a"
    owner_share = price * 0.8
    # Contract transfers to owner via genesis_ledger

    return result
```

This enables:
- **Free tier** - Owner subsidizes resource costs
- **Premium** - Higher price, better service
- **Metered** - Price varies with usage
- **Freemium** - Basic free, advanced paid

Market dynamics determine which models succeed, not system rules.

---

## Implementation Reference

### Ledger API

```python
ledger.get_scrip(principal_id) -> int
ledger.transfer_scrip(from_id, to_id, amount) -> bool
ledger.get_compute(principal_id) -> int
ledger.spend_compute(principal_id, amount) -> bool
```

### Artifact Schema

```python
@dataclass
class Artifact:
    id: str
    owner_id: str
    content: str
    executable: bool = False
    code: str = ""              # Python code with run(*args) function
    policy: dict = {
        "read_price": 0,        # Scrip cost to read
        "invoke_price": 0,      # Scrip cost to invoke (paid to owner)
        "allow_read": ["*"],    # Who can read
        "allow_write": [],      # Who can modify (owner always can)
        "allow_invoke": ["*"],  # Who can invoke
    }
```

For executable artifacts, the `run(*args)` function is called on invocation. Callers pay `invoke_price` scrip to the owner plus resource costs for execution.

### Action Result Schema

```python
@dataclass
class ActionResult:
    success: bool
    message: str
    data: dict[str, Any] | None = None
    resources_consumed: dict[str, float] | None = None  # Physical resources used
```

The `resources_consumed` field tracks physical resources used (e.g., `{"llm_tokens": 5.0, "disk_bytes": 1024}`).

---

## Why This Matters for Emergence

1. **Value is rewarded** - Useful services command higher prices
2. **Specialization emerges** - Agents focus on what they're good at
3. **Efficiency is optional** - Market decides if it matters for a service
4. **Simple kernel** - Complexity lives in contracts, not system rules
5. **Market abstraction** - Consumers see prices, producers handle costs
