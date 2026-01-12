# Target Architecture

What we're building toward. Design decisions from clarification discussions.

**Last verified:** 2026-01-12

**See current:** [../current/README.md](../current/README.md)

**Design rationale:** [../DESIGN_CLARIFICATIONS.md](../DESIGN_CLARIFICATIONS.md) - Start with the [Executive Summary](../DESIGN_CLARIFICATIONS.md#executive-summary-for-external-review) for decisions needing review.

---

## Purpose

This is **mechanism design for real resource allocation**, not a simulation or model.

**Mechanism design** means: designing the rules and incentives of a system so that self-interested participants, acting in their own interest, produce collectively beneficial outcomes. Like auction design, but for a multi-agent economy.

**Primary Goal:** Functional emergent collective intelligence - whole greater than sum of parts.

**Design Goals:**
- Operate within real-world constraints (computer capacity, API budget)
- Create markets that optimally allocate scarce resources among agents
- Resources ARE the real constraints, not proxies for them
- No artificial constraints on agent productivity

**Non-Goals:**
- Research reproducibility (doesn't matter)
- Simulating human societies or other systems
- Deterministic behavior

---

## Documents

| Document | Description |
|----------|-------------|
| [02_execution_model.md](02_execution_model.md) | Continuous autonomous loops |
| [03_agents.md](03_agents.md) | Self-managed agents, rights tradability |
| [04_resources.md](04_resources.md) | Rate allocation, resource tracking |
| [05_contracts.md](05_contracts.md) | Access control via contract artifacts |
| [06_mint.md](06_mint.md) | Bids anytime, periodic resolution, minting |
| [07_infrastructure.md](07_infrastructure.md) | Docker isolation, real constraints |

---

## Key Changes from Current

| Aspect | Current | Target |
|--------|---------|--------|
| Execution | Tick-synchronized | Continuous autonomous loops |
| Renewable resources | Discrete per-tick refresh | Rolling window rate tracking |
| Rate limiting | Discrete per-tick | Rolling window, wait for capacity |
| Agent control | System-triggered | Self-triggered with sleep |
| Ticks | Execution trigger | Metrics window only |
| Resource limits | Configured abstract numbers | Docker container limits |
| Access control | Policy fields on artifacts | Contract artifacts (check_permission) |

---

## Architectural Principles

### Agents Are Autonomous
- Agents decide when to act
- Continuous loops, not tick-triggered
- Can self-sleep and wake on conditions

### Markets Allocate Resources
- No hardcoded limits on agents
- Flow rate limits total throughput
- Agents compete via markets for resources

### Constraints Are Real
- Docker limits = actual resource constraints
- LLM budget = actual $ spent
- No abstract "compute tokens" disconnected from reality

### Conflict Resolution in Artifacts
- Race conditions handled by genesis artifacts
- Ledger, escrow ensure atomic operations
- Orchestration layer doesn't resolve conflicts

---

## System vs Genesis: The Ontological Distinction

Two layers exist with fundamentally different properties:

### System Mechanisms (The "Physics")

Hardcoded in Python/Docker. Not addressable by agents. Defines the execution space itself.

| Mechanism | What It Does |
|-----------|--------------|
| Execution engine | Runs agent loops, handles async |
| Rate tracker | Enforces rolling window limits |
| `invoke()` primitive | Dispatches calls to artifacts |
| Worker pool | Measures CPU/memory per action |
| Docker container | Hard resource ceilings |

**Privilege:** Absolute. If the system says "you're blocked," there's no appeal.

### Genesis Artifacts (The "Infrastructure")

Pre-seeded artifacts created at T=0. Addressable, replaceable, evolvable. Agents could build alternatives.

| Artifact | Purpose |
|----------|---------|
| `genesis_ledger` | Balances, transfers |
| `genesis_store` | Artifact registry, discovery |
| `genesis_escrow` | Trustless trading |
| `genesis_mint` | Scoring, scrip creation |
| `genesis_rights_registry` | Quota management |
| `genesis_freeware` | Default open contract |

**Privilege:** Semantic only. They're trusted because initial agent prompts reference them. Agents could migrate to alternatives if they collectively agree.

### Why This Matters

```
System: "You cannot invoke() something that doesn't exist in the store."
        → This is physics. Unchangeable by agents.

Genesis: "Use genesis_escrow for trades."
        → This is convention. Agents could build better_escrow and migrate.
```

The system defines what's *possible*. Genesis artifacts define what's *convenient*.

---

## genesis_store Interface

**Note:** Current implementation has basic artifact storage in `World.artifacts` but lacks the discovery interface below. This is target architecture (see Gap #16).

The artifact registry with discovery methods. Enables agents to "window shop" without burning resources on trial-and-error.

### Discovery Layers

| Layer | Method | Cost | Returns |
|-------|--------|------|---------|
| Directory | `search(query, type_filter)` | Low | List of artifact IDs with interface summaries |
| Signboard | `get_metadata(artifact_id)` | Low | Owner, creation date, size, access_contract_id |
| Interface | `get_interface(artifact_id)` | Low | MCP-compatible schema (tools, inputs, costs) |
| Full Read | `read(artifact_id)` | High | Full artifact content |

### Methods

```python
genesis_store = {
    "id": "genesis_store",
    "interface": {
        "tools": [
            {
                "name": "search",
                "description": "Find artifacts by query",
                "inputSchema": {
                    "query": "string",
                    "type_filter": "enum[agent, tool, data, contract]"
                }
            },
            {
                "name": "get_metadata",
                "description": "Get artifact metadata without content",
                "inputSchema": {"artifact_id": "string"}
            },
            {
                "name": "get_interface",
                "description": "Get MCP-style interface schema",
                "inputSchema": {"artifact_id": "string"}
            },
            {
                "name": "create",
                "description": "Register new artifact",
                "inputSchema": {
                    "content": "any",
                    "interface": "dict",
                    "has_standing": "bool",
                    "can_execute": "bool",
                    "access_contract_id": "string"
                }
            },
            {
                "name": "delete",
                "description": "Remove artifact from current state",
                "inputSchema": {"artifact_id": "string"}
            }
        ]
    }
}
```

### Metadata Schema

What `get_metadata()` returns (without reading content):

| Field | Type | Description |
|-------|------|-------------|
| `id` | string | Artifact ID |
| `owner_id` | string | Current owner |
| `has_standing` | bool | Can hold resources |
| `can_execute` | bool | Has runnable code |
| `interface_summary` | string | Brief description from interface |
| `created_at` | timestamp | Creation time |
| `size_bytes` | int | Content size |
| `access_contract_id` | string | Governing contract |

### Why Layered Discovery

Prevents "trial-and-error bankruptcy":
1. Agent searches for "weather tool" → gets list of candidates
2. Agent calls `get_interface("weather_tool")` → sees it costs 0.5 scrip per call
3. Agent decides it's too expensive → moves on without ever invoking
4. No resources wasted on failed invocations

---

## Glossary

| Term | Definition |
|------|------------|
| **Artifact** | Any persistent, addressable object in the system. Everything is an artifact: agents, contracts, data, tools. |
| **Agent** | An artifact with `has_standing=true` and `can_execute=true`. Can think (call LLM), act, and bear costs. |
| **Standing** | The property (`has_standing=true`) that allows an artifact to hold resources, enter contracts, and bear costs. Artifacts with standing are "principals" in the economic sense. |
| **Principal** | Any artifact with standing. Can hold scrip, own other artifacts, and be held accountable. |
| **Scrip** | The internal currency. Minted by oracle based on artifact quality scores. Used to pay for actions, trade, and coordinate. |
| **Contract** | An artifact that answers permission questions. Every artifact has an `access_contract_id` pointing to the contract that governs access to it. |
| **Genesis Artifact** | Artifacts created at system initialization (before agents). Examples: `genesis_ledger`, `genesis_store`, `genesis_freeware`, `genesis_rights_registry`. They bootstrap the system but have no special mechanical privileges. |
| **genesis_rights_registry** | Genesis artifact that manages resource quotas. Provides `check_quota`, `transfer_quota` methods. Enforces per-agent resource limits. |
| **Rate Tracker** | The renewable resource model. Tracks usage in a rolling time window. No burst, no debt - agents wait when over limit. |
| **Renewable Resource** | A resource with a rate limit (CPU-seconds, LLM tokens/min). Usage tracked in rolling window. |
| **Depletable Resource** | A resource that depletes forever (LLM budget in $). Once spent, gone. |
| **Allocatable Resource** | A resource with quota that can be reclaimed (disk, memory). |
| **Blocked** | An agent that has exceeded their rate limit. Must wait until rolling window has capacity. |
| **Mint** | The system primitive that scores artifacts and creates new scrip. Agents bid via `genesis_mint` to submit artifacts for scoring; winners get their artifacts evaluated and scrip minted based on score. |
| **Invoke** | Call an executable artifact. `invoke(artifact_id, args)` runs the artifact's code and returns results. |
| **access_contract_id** | The field on every artifact pointing to the contract that governs permissions. The contract is the ONLY authority for access decisions. |
| **Vulture Capitalist Pattern** | Market-driven rescue of frozen agents. Any agent can unilaterally transfer resources to a frozen agent, hoping for reciprocation. |

---

## Related Documents

| Document | Purpose |
|----------|---------|
| [DESIGN_CLARIFICATIONS.md](../DESIGN_CLARIFICATIONS.md) | Why decisions were made, certainty levels, open questions |
| [GAPS.md](../GAPS.md) | Implementation gaps between current and target |
| [SPEC_REVIEW.md](../../archive/SPEC_REVIEW.md) | Comparison to original specification (archived) |
