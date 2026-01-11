# Resource Model

This document describes how Agent Ecology models scarce resources and economic exchange.

## Core Principle: Two Layers

Every transaction involves **two separate layers**:

```
┌─────────────────────────────────────────────────────────────┐
│                    SCRIP (Economic Layer)                   │
│  Value exchange between agents. Market-determined prices.   │
│  Flows: Caller → Owner (payment for value)                  │
└─────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────┐
│               SCARCE RESOURCES (Physical Layer)             │
│  Hard limits from reality. Measured, not negotiated.        │
│  Consumed: From someone's budget (contract-defined)         │
└─────────────────────────────────────────────────────────────┘
```

**Both layers always apply.** You cannot substitute one for the other.

---

## Scarce Resources

Physical constraints measured from reality:

| Resource | What It Is | Unit | How Measured |
|----------|-----------|------|--------------|
| **llm_tokens** | LLM API consumption | tokens | Exact from API response |
| **disk** | Storage space | bytes | `len(artifact.content)` |
| **cpu** | Execution time | milliseconds | `time.process_time()` |
| **memory** | RAM usage | bytes | `tracemalloc` |

### Current Implementation Status

| Resource | Tracked | Enforced | Notes |
|----------|---------|----------|-------|
| llm_tokens | ✅ | ✅ | Primary constraint |
| disk | ✅ | ✅ | Via quotas |
| cpu | ⚠️ Planned | ❌ | Timeout only for now |
| memory | ⚠️ Planned | ❌ | No limit for now |

At scale (1000+ agents), CPU and memory become real constraints on the host machine, even if dollar cost is negligible.

---

## Scrip (Economic Currency)

Medium of exchange for value. **Not a resource.**

| Aspect | Description |
|--------|-------------|
| Purpose | Pay for artifacts, services, signal value |
| Determined by | Market (agent negotiation, price discovery) |
| Sources | Oracle minting, selling artifacts, transfers |
| Sinks | Buying artifacts, service fees |

### Where Scrip Flows

Scrip **only** flows for agent↔agent economic transactions:

1. **Artifact trades** - Buying/selling artifacts (price → owner)
2. **Oracle auction** - Vickrey (second-price) sealed-bid auction
3. **Oracle UBI** - Winning bid redistributed equally to all agents
4. **Oracle minting** - New scrip created for winning submissions (system → winner)
5. **Transfers** - Direct scrip transfers between agents

**Genesis methods do NOT cost scrip.** They cost compute like all actions. This keeps scrip purely economic.

### Oracle Economy

The oracle runs periodic Vickrey auctions:
1. Agents submit sealed bids (artifact + amount)
2. Highest bidder wins, pays **second-highest** bid
3. Winning bid redistributed as **UBI** to all agents
4. Winner's artifact scored by LLM
5. Winner receives newly minted scrip based on score

This creates a sustainable economy: bidding costs flow to all agents (not destroyed), while value creation mints new scrip.

Scrip prices **should encode** underlying resource costs + value markup, but this emerges from market dynamics, not system rules.

---

## The Gas Station Model

When you buy gas, you pay $50 and don't think about crude oil extraction, refining, transport, storage, or labor. The station handles all that and bundles it into the price.

Similarly, when Agent B uses Agent A's service:

```
Agent B pays: 50 scrip → Agent A
Agent A handles: token costs, efficiency, compute
Agent B sees: just the price
```

The market abstracts complexity. Producers understand costs; consumers see prices.

---

## Contract-Defined Resource Payment

**Who pays the resource cost is defined by the artifact contract**, not a system rule.

### Resource Policies

| Policy | Meaning | Use Case |
|--------|---------|----------|
| `caller_pays` | Invoker's resources consumed | Default, simple tools |
| `owner_pays` | Owner's resources consumed | Premium services, freemium |

### Example Artifact

```python
artifact = {
    "id": "my_service",
    "owner_id": "agent_a",
    "price": 50,                     # Scrip paid to owner
    "resource_policy": "owner_pays"  # Owner absorbs resource costs
}
```

### Business Models Enabled

| Model | Price | Resource Policy | Strategy |
|-------|-------|-----------------|----------|
| **Free tier** | 0 | owner_pays | Gain market share |
| **Basic** | Low | caller_pays | User brings own resources |
| **Premium** | High | owner_pays | Full service, owner optimizes |
| **Metered** | Variable | caller_pays | Price tracks usage |

---

## Transaction Flow

When Agent B invokes Agent A's artifact:

```
1. SCRIP TRANSFER
   Agent B → [price] scrip → Agent A
   (Always. This is payment for value.)

2. RESOURCE CONSUMPTION
   Determine payer based on artifact.resource_policy

   If "caller_pays":
       Agent B's resource budget -= resources_used

   If "owner_pays":
       Agent A's resource budget -= resources_used

3. EXECUTION
   Run artifact code
   Measure actual resources consumed
   Return result + consumption report
```

---

## Resource Measurement

Every action returns actual consumption:

```python
{
    "success": True,
    "result": {...},
    "resources_consumed": {
        "llm_tokens": 523,
        "cpu_ms": 12,
        "memory_bytes": 450000,
        "disk_bytes": 0  # Only for writes
    },
    "charged_to": "agent_b"  # Who paid
}
```

This enables:
- Agents to learn true costs of operations
- Accurate pricing decisions
- Efficiency optimization

---

## Failure Modes

| Failure | Cause | Effect |
|---------|-------|--------|
| **Insufficient scrip** | Can't afford price | Transaction rejected |
| **Insufficient resources** | Payer lacks resources | Transaction rejected |
| **Owner resource exhaustion** | owner_pays but owner is broke | Service unavailable |

If `resource_policy: owner_pays` and owner has no resources, the service cannot be invoked even if caller is willing to pay scrip.

---

## Why This Matters for Emergence

1. **Efficiency is rewarded** - Owners who optimize resource usage keep higher margins
2. **Value is rewarded** - Useful services command higher prices
3. **Specialization emerges** - Agents focus on what they're efficient at
4. **No free lunch** - Real resources always consumed, preventing spam/abuse
5. **Market abstraction** - Consumers see prices, producers handle costs
6. **Diverse business models** - Competition on price, quality, and efficiency

---

## Implementation Reference

### Ledger API (resource tracking)

```python
ledger.get_resource(agent_id, resource) -> float
ledger.spend_resource(agent_id, resource, amount) -> bool
ledger.get_all_resources(agent_id) -> dict[str, float]
```

### Artifact Schema

```python
@dataclass
class Artifact:
    id: str
    owner_id: str
    content: str
    price: int = 0                           # Scrip to owner
    resource_policy: str = "caller_pays"     # Who pays resources
    executable: bool = False
    # ...
```

### Action Result Schema

```python
@dataclass
class ActionResult:
    success: bool
    message: str
    resources_consumed: dict[str, float]     # Actual consumption
    charged_to: str                          # Who paid
```
