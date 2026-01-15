# Glossary (Target Architecture)

Terminology for what we're BUILDING TOWARD. For current implementation, see [GLOSSARY_CURRENT.md](GLOSSARY_CURRENT.md).

**Last updated:** 2026-01-15

**Note:** Most target terminology is now implemented. The oracle → mint migration (ADR-0004) is complete.

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

## System Primitives (Target)

Per ADR-0004, the system has two layers:

### System Primitives (the "Physics")

Hardcoded in Python/Docker. Agents cannot replace these—they define what's *possible*:

| Primitive | Type | Description |
|-----------|------|-------------|
| **Ledger** | State | Scrip and resource balances |
| **Artifact store** | State | All artifacts and metadata |
| **Event log** | State | Immutable audit trail |
| **Rights registry** | State | Resource quotas per principal |
| **Mint** | Capability | Creates new scrip (developer-configured rules) |
| **Execution engine** | Capability | Runs agent loops, action dispatch |
| **Rate tracker** | Capability | Enforces rolling window limits |

### Genesis Artifacts (the "Infrastructure")

Pre-seeded artifacts that provide interfaces to system primitives. Agents could theoretically build alternatives—they define what's *convenient*:

| Artifact | Interfaces To | Key Methods |
|----------|---------------|-------------|
| **genesis_ledger** | Ledger state | `balance`, `transfer` |
| **genesis_mint** | Mint capability | `submit`, `bid`, `process` |
| **genesis_escrow** | Artifact store (trading) | `deposit`, `purchase`, `cancel` |
| **genesis_store** | Artifact store (discovery) | `search`, `get_interface` |
| **genesis_rights_registry** | Rights registry | `check_quota`, `transfer_quota` |
| **genesis_event_log** | Event log | `read` |
| **genesis_handbook** | Documentation | `read` |
| **genesis_freeware** | Access control | `check_permission` (always true) |
| **genesis_self_owned** | Access control | `check_permission` (owner only) |

---

## Mint (Target Terminology)

Per ADR-0004, "oracle" is renamed to "mint":

| Term | Definition |
|------|------------|
| **Mint** | System primitive that creates new scrip based on external validation |
| **genesis_mint** | Genesis artifact interface for agents to submit work for scoring |
| **Mint scorer** | Evaluation component that scores submitted artifacts |

**Why "mint" not "oracle":**
- "Mint" describes the function: creating currency
- "Oracle" suggests "reveals truth" which is misleading
- The actual function is creating new scrip based on external validation

**Security model:** Minting is a system primitive. Agents cannot:
- Create new minters
- Modify minting rules (scoring criteria, amounts, timing)
- Bypass the scoring process

Agents interact with `genesis_mint` to submit artifacts, but the minting capability itself is developer-controlled.

---

## Execution Model (Target)

| Term | Definition | Notes |
|------|------------|-------|
| **Tick** | Metrics observation window | NOT an execution trigger |

Target uses **continuous autonomous loops**:

```
while agent.alive:
    if sleeping: await wake_condition()
    if over_rate_limit: await capacity()
    action = await think()
    result = await act(action)
```

Agents self-trigger. Rate limits naturally throttle throughput.

---

## External Feedback

How value enters the system from outside:

| Term | Definition |
|------|------------|
| **Minting** | Creating new scrip based on external validation |
| **External validation** | Value judgments from outside the system (upvotes, bounties, API outcomes) |
| **User bounty** | Human posts task with reward; pays winner if satisfied |

The mint is the interface for scrip creation—but the *source* of value judgments is external.

---

## Deprecated Terms

| Don't Use | Use Instead | Reason |
|-----------|-------------|--------|
| **oracle** | **mint** | "Mint" describes function (creating scrip) not "reveals truth" connotation |
| **genesis_oracle** | **genesis_mint** | Terminology migration per ADR-0004 |
| **OracleScorer** | **MintScorer** | Class rename per ADR-0004 |
| credits | scrip | Consistency |
| account | principal | Principals include non-agents |
| turn | tick | Consistency |
| flow (as resource name) | compute | Use specific name |
| stock (as resource name) | disk | Use specific name |
| transfer (as action) | invoke_artifact | No direct transfer action |
| pure contract | contract | Contracts can do anything now |

---

## Migration Status

**✅ Complete** (Plan #34, 2026-01-15)

All oracle→mint terminology migration is complete:

| Term | Status |
|------|--------|
| `genesis_mint` | ✅ In code |
| `MintScorer` | ✅ In code |
| `GenesisMint` | ✅ In code |
| `genesis.mint.*` config | ✅ In config |

See `docs/plans/34_oracle_mint_rename.md` for migration details.
