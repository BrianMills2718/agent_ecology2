# Glossary (Current Implementation)

Terminology for what IS implemented. For target terminology, see [GLOSSARY_TARGET.md](GLOSSARY_TARGET.md).

**Last updated:** 2026-01-12

---

## Core Ontology

Everything is an artifact. Other entity types are artifacts with specific properties.

| Term | Definition | Properties |
|------|------------|------------|
| **Artifact** | Any persistent, addressable object in the system | `id`, `content`, `access_contract_id` |
| **Agent** | Artifact that can hold resources, execute code, and call LLM | `has_standing=true`, `can_execute=true` |
| **Principal** | Any artifact with standing (can hold resources, bear costs) | `has_standing=true` |
| **Contract** | Executable artifact that answers permission questions | `can_execute=true`, implements `check_permission` |
| **Genesis Artifact** | Artifact created at system initialization | Prefixed with `genesis_`, solves cold-start |

**Key relationships:**
- Agent ⊂ Principal ⊂ Artifact
- Contract ⊂ Artifact (contracts don't need standing)
- All artifacts have an `access_contract_id` pointing to their governing contract

---

## Resource Taxonomy

Three categories based on how resources behave over time:

### Depletable (Consumed Forever)

| Resource | What It Is | Unit | Notes |
|----------|------------|------|-------|
| **llm_budget** | Real $ for LLM API calls | dollars | External boundary; when exhausted, simulation pauses |

### Allocatable (Finite But Reusable)

| Resource | What It Is | Unit | Notes |
|----------|------------|------|-------|
| **disk** | Storage space for artifacts | bytes | Per-principal quota; freed when artifacts deleted |
| **memory** | RAM for execution | bytes | Container limit; freed after use |

### Renewable (Replenishes Over Time)

| Resource | What It Is | Unit | Notes |
|----------|------------|------|-------|
| **cpu_rate** | CPU-seconds per rolling window | CPU-seconds | Per-agent rate limit |
| **llm_rate** | LLM tokens per rolling window | tokens/min | Per-agent rate limit |

Renewable resources use a **rolling window rate tracker**: usage tracked over time window. **No debt** - agents are blocked until window has capacity.

---

## Currency

| Term | Definition | Notes |
|------|------------|-------|
| **Scrip** | Internal economic currency | NOT a physical resource. Coordination signal. |

**Key distinction:**
- **Resources** = Physical constraints (compute, disk, memory, bandwidth, llm_budget)
- **Scrip** = Economic signal (prices, payments, coordination)

---

## Actions (Narrow Waist)

Only 3 action types (plus noop):

| Action | Purpose | Costs |
|--------|---------|-------|
| **read_artifact** | Read artifact content | May cost scrip (read_price) |
| **write_artifact** | Create/update artifact | Disk quota |
| **invoke_artifact** | Call method on artifact | Scrip fee + compute |

**No direct transfer action.** Transfers happen via: `invoke_artifact("genesis_ledger", "transfer", [...])`

---

## Contracts

**Contracts can do anything.** Invoker pays all costs.

| Term | Definition |
|------|------------|
| **access_contract_id** | Field on every artifact pointing to its governing contract |
| **check_permission** | Required method contracts implement to answer permission questions |

Common patterns: Freeware, Self-owned, Gatekeeper, Escrow, Paywall.

---

## Genesis Artifacts (Current)

| Artifact | Purpose | Key Methods | Status |
|----------|---------|-------------|--------|
| **genesis_ledger** | Scrip balances, transfers | `balance`, `transfer` | Implemented |
| **genesis_mint** | Score artifacts, mint scrip | `status`, `bid`, `check` | Implemented |
| **genesis_escrow** | Trustless artifact trading | `deposit`, `purchase`, `cancel` | Implemented |
| **genesis_event_log** | Simulation history | `read` | Implemented |
| **genesis_handbook** | Documentation for agents | `read` | Implemented |
| **genesis_freeware** | Permissive access contract | `check_permission` (always true) | Implemented |
| **genesis_self_owned** | Self-only access contract | `check_permission` (owner only) | Implemented |
| **genesis_store** | Artifact discovery | `search`, `get_interface` | Partial |
| **genesis_rights_registry** | Resource quota management | `check_quota`, `transfer_quota` | Partial |

---

## System Primitives (Current)

Part of the world itself—agents cannot replace these:

- Action execution (read, write, invoke)
- Resource accounting (balances for all resource types)
- Scrip ledger
- Artifact store
- Tick/time progression

Genesis artifacts provide *interfaces* to some primitives, but the underlying state is system-level.

---

## Execution Model (Current)

| Term | Definition | Notes |
|------|------------|-------|
| **Tick** | One simulation step | Agents act synchronously per tick |

Current implementation uses tick-based execution where agents observe then act each tick.

---

## Code References

| Config Term | Code Variable | File |
|-------------|---------------|------|
| `genesis.mint.*` | `GenesisMint` | `src/world/genesis.py` |
| Mint scoring | `MintScorer` | `src/world/mint_scorer.py` |
| Rate limiting | `RateTracker` | `src/world/rate_tracker.py` |

---

## Deprecated Terms

| Don't Use | Use Instead | Reason |
|-----------|-------------|--------|
| credits | scrip | Consistency |
| account | principal | Principals include non-agents |
| turn | tick | Consistency |
| flow (as resource name) | compute | Use specific name |
| stock (as resource name) | disk | Use specific name |
| transfer (as action) | invoke_artifact | No direct transfer action |
| pure contract | contract | Contracts can do anything now |
