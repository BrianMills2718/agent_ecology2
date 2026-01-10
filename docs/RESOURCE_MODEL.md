# Resource Model

This document describes how Agent Ecology models scarce resources to reflect actual physical constraints of the underlying system.

## Design Philosophy

The resource model serves two purposes:
1. **System Protection**: Prevent overloading actual infrastructure (disk, compute, API limits)
2. **Economic Relevance**: LLM agents optimize for efficiencies that matter in the real world

Resources are modeled to match their physical reality as closely as possible.

---

## Resource Categories

Resources fall into two categories based on their temporal behavior:

### Stock Resources (Fixed Pools)

Resources that are **constant over time**. Total capacity is fixed; allocation persists until explicitly freed.

| Resource | Physical Reality | Unit | Notes |
|----------|-----------------|------|-------|
| **disk** | Filesystem storage | bytes | Shared pool, allocated per agent |
| *(future: gpu_memory)* | GPU VRAM | bytes | If GPU compute added |

**Characteristics:**
- Total is fixed at system initialization
- Doesn't refresh or renew
- Used capacity persists until freed
- Trading quota = permanent reallocation

### Flow Resources (Rate-Limited)

Resources that are **available per time period**. Capacity renews each tick because the underlying resource is available again.

| Resource | Physical Reality | Unit | Notes |
|----------|-----------------|------|-------|
| **compute** | LLM API tokens | tokens | Rate-limited by API/budget |
| *(future: api_calls)* | External API calls | calls | Rate limits per period |
| *(future: bandwidth)* | Network I/O | bytes/tick | If network access added |

**Characteristics:**
- Capacity is *per tick*, not cumulative
- Refreshes each tick (use it or lose it)
- Reflects actual rate limits
- Trading quota = permanent change to per-tick allocation

---

## Three-Layer Model

```
┌─────────────────────────────────────────────────────────────┐
│                    PHYSICAL LAYER                           │
│  Actual constraints: disk space, API rate limits, $ budget  │
└─────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────┐
│                    RIGHTS LAYER                             │
│  Quotas allocated to agents (can be traded)                 │
│  - compute_quota: tokens/tick this agent is entitled to     │
│  - disk_quota: bytes this agent is entitled to              │
└─────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────┐
│                    CONSUMPTION LAYER                        │
│  Actual usage tracked in ledger                             │
│  - compute: tokens remaining this tick                      │
│  - disk_used: bytes currently stored                        │
└─────────────────────────────────────────────────────────────┘
```

---

## Scrip (Economic Currency)

**Scrip is NOT a resource** - it's the medium of exchange.

| Aspect | Description |
|--------|-------------|
| Purpose | Trade for rights, pay for artifacts, signal value |
| Scarcity | None inherent - it's information, not physical |
| Persistence | Accumulates/depletes based on economic activity |
| Sources | Oracle minting, selling tools, receiving transfers |
| Sinks | Buying rights, paying prices, transaction fees |

Scrip enables price discovery and economic signaling without modeling a physical constraint.

---

## Trading Flexibility

Agents can trade resource rights with flexible contract terms:

### Permanent Quota Transfer
```
"I give you 10 of my compute_quota forever"
Agent A: 50 → 40 compute/tick (permanent)
Agent B: 50 → 60 compute/tick (permanent)
```

### Time-Limited Quota Transfer
```
"You get +10 compute_quota for 5 ticks, then it reverts"
(Requires contract artifact to enforce)
```

### Spot Resource Transfer
```
"Here's 10 compute tokens right now from my current balance"
(Direct transfer of current-tick resources)
```

### Conditional Transfer
```
"You get my unused compute at tick end if I don't use it"
(Requires contract artifact to enforce)
```

Simple transfers (permanent quota) are handled by `genesis_rights_registry`.
Complex transfers (time-limited, conditional) are handled by agent-written contract artifacts.

---

## Implementation Mapping

| Concept | Code Location | Notes |
|---------|--------------|-------|
| compute_quota | `rights_registry.quotas[agent_id]["compute"]` | Right to compute/tick |
| disk_quota | `rights_registry.quotas[agent_id]["disk"]` | Right to disk bytes |
| compute (current) | `ledger.compute[agent_id]` | Remaining this tick |
| disk_used | `artifact_store.get_owner_usage(agent_id)` | Current consumption |
| scrip | `ledger.scrip[agent_id]` | Economic currency |

---

## Tick Lifecycle

```
START OF TICK:
  For each agent:
    compute = compute_quota  # Refresh flow resources
    # (disk_used unchanged - stock doesn't refresh)

DURING TICK:
  Agent thinks → compute -= thinking_cost
  Agent acts → compute -= action_cost
  Agent writes artifact → disk_used += artifact_size
  Agent invokes tool → compute -= gas_cost, scrip -= price

END OF TICK:
  Unused compute is lost (use it or lose it)
  Scrip persists (economic state carries forward)
  Disk persists (stock doesn't reset)
```

---

## Failure States

| State | Cause | Effect | Recovery |
|-------|-------|--------|----------|
| **Out of Compute** | Used all compute this tick | Can't think or act until next tick | Wait for tick reset |
| **Out of Disk** | Used all disk_quota | Can't write new artifacts | Delete artifacts or buy quota |
| **Out of Scrip** | Spent all currency | Can't buy artifacts or pay prices | Sell tools, receive transfers |

Note: "Out of Compute" is temporary (resets next tick). "Out of Disk" and "Out of Scrip" persist until resolved through economic activity.

---

## Future Extensions

### Additional Flow Resources
```yaml
flow_resources:
  compute:
    unit: tokens
    default_quota: 50000
  api_calls:
    unit: calls
    default_quota: 100
```

### Additional Stock Resources
```yaml
stock_resources:
  disk:
    unit: bytes
    default_quota: 10000
  gpu_memory:
    unit: bytes
    default_quota: 1000000
```

### Resource Markets
Agents could create market-maker artifacts that automatically trade resource rights at dynamic prices based on supply/demand.
