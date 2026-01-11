# Resource Model

This document describes how Agent Ecology models scarce resources to reflect actual physical constraints of the underlying system.

## Design Philosophy

The resource model serves two purposes:
1. **System Protection**: Prevent overloading actual infrastructure (disk, API limits, $ budget)
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
| **llm_budget** | API spending cap | dollars | Total $ for LLM calls |

**Characteristics:**
- Total is fixed at system initialization
- Doesn't refresh or renew
- Used capacity persists until freed
- Trading quota = permanent reallocation

### Flow Resources (Rate-Limited)

Resources that are **available per time period**. Capacity renews each tick because the underlying resource is available again.

| Resource | Physical Reality | Unit | Notes |
|----------|-----------------|------|-------|
| **compute** | LLM API tokens | tokens | Quota per tick for thinking |
| **bandwidth** | Network I/O | bytes/tick | If network access added (currently disabled) |

**Characteristics:**
- Capacity is *per tick*, not cumulative
- Refreshes each tick (use it or lose it)
- Reflects actual rate limits
- Trading quota = permanent change to per-tick allocation

---

## Generic Resource System

Resources are **configurable via config.yaml** - new resources can be added without code changes:

```yaml
resources:
  stock:  # Fixed pools
    llm_budget:
      total: 1.00
      unit: dollars
      distribution: equal
    disk:
      total: 50000
      unit: bytes
      distribution: equal

  flow:  # Per-tick quotas
    compute:
      per_tick: 1000
      unit: cycles
      distribution: equal
    bandwidth:
      per_tick: 0  # 0 = disabled
      unit: bytes
      distribution: equal
```

The ledger and rights registry handle any resource defined in config.

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
│  - Stored in RightsRegistry                                 │
│  - Generic: quotas[agent_id][resource] = amount             │
└─────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────┐
│                    CONSUMPTION LAYER                        │
│  Actual usage tracked in ledger                             │
│  - Generic: resources[agent_id][resource] = balance         │
│  - Scrip: separate economic currency                        │
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

## Implementation Mapping

| Concept | Code Location | Notes |
|---------|--------------|-------|
| **Quotas (rights)** | `rights_registry.quotas[agent_id]` | Dict of {resource: amount} |
| `get_quota(agent_id, resource)` | RightsRegistry | Get quota for any resource |
| **Balances (consumption)** | `ledger.resources[agent_id]` | Dict of {resource: balance} |
| `get_resource(agent_id, resource)` | Ledger | Get balance for any resource |
| `spend_resource(agent_id, resource, amount)` | Ledger | Consume a resource |
| `set_resource(agent_id, resource, amount)` | Ledger | Set balance (tick reset) |
| **Scrip** | `ledger.scrip[agent_id]` | Economic currency |
| **Disk used** | `artifact_store.get_owner_usage(agent_id)` | Current storage consumption |

### Internal vs External Names

| External (config/UI) | Internal (code) | Notes |
|---------------------|-----------------|-------|
| `compute` | `llm_tokens` | Ledger stores as "llm_tokens" |
| `disk` | `disk` | Direct mapping |
| `scrip` | `scrip` | Direct mapping |

---

## Tick Lifecycle

```
START OF TICK:
  For each agent:
    ledger.set_resource(agent, "llm_tokens", quota)  # Refresh flow resources
    # (disk_used unchanged - stock doesn't refresh)

DURING TICK:
  Agent thinks → ledger.spend_resource(agent, "llm_tokens", cost)
  Agent acts → ledger.spend_resource(agent, "llm_tokens", action_cost)
  Agent writes artifact → disk_used += artifact_size
  Agent invokes method → spend resource + pay scrip fee

END OF TICK:
  Unused flow resources are lost (use it or lose it)
  Scrip persists (economic state carries forward)
  Stock resources persist (don't reset)
```

---

## Trading Resources

### Via genesis_rights_registry

```json
// Transfer quota (permanent reallocation)
{"action_type": "invoke_artifact", "artifact_id": "genesis_rights_registry",
 "method": "transfer_quota", "args": ["target_agent", "compute", 20]}
```

### Via Contract Artifacts

Complex transfers (time-limited, conditional) can be handled by agent-written contract artifacts using the Gatekeeper pattern (see genesis_escrow).

---

## Failure States

| State | Cause | Effect | Recovery |
|-------|-------|--------|----------|
| **Out of Compute** | Used all compute this tick | Can't think or act until next tick | Wait for tick reset |
| **Out of Disk** | Used all disk_quota | Can't write new artifacts | Delete artifacts or buy quota |
| **Out of Scrip** | Spent all currency | Can't buy artifacts or pay prices | Sell tools, receive transfers |

Note: "Out of Compute" is temporary (resets next tick). "Out of Disk" and "Out of Scrip" persist until resolved through economic activity.

---

## API Reference

### Ledger (src/world/ledger.py)

```python
# Generic resource API
ledger.get_resource(agent_id, resource) -> float
ledger.spend_resource(agent_id, resource, amount) -> bool
ledger.credit_resource(agent_id, resource, amount) -> None
ledger.set_resource(agent_id, resource, amount) -> None
ledger.transfer_resource(from_id, to_id, resource, amount) -> bool
ledger.get_all_resources(agent_id) -> dict[str, float]

# Scrip API
ledger.get_scrip(agent_id) -> int
ledger.deduct_scrip(agent_id, amount) -> bool
ledger.credit_scrip(agent_id, amount) -> None
ledger.transfer_scrip(from_id, to_id, amount) -> bool

# Backward compat (deprecated)
ledger.get_compute(agent_id)  # Use get_resource(agent_id, "llm_tokens")
ledger.spend_compute(agent_id, amount)  # Use spend_resource()
```

### RightsRegistry (src/world/genesis.py)

```python
# Generic quota API
registry.get_quota(agent_id, resource) -> float
registry.set_quota(agent_id, resource, amount) -> None
registry.get_all_quotas(agent_id) -> dict[str, float]

# Backward compat
registry.get_compute_quota(agent_id)  # Use get_quota(agent_id, "compute")
registry.get_disk_quota(agent_id)  # Use get_quota(agent_id, "disk")
```
