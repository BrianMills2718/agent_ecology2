# Glossary

Canonical terminology for Agent Ecology.

**Last updated:** 2026-01-20

---

## Quick Reference

| Use | Not | Why |
|-----|-----|-----|
| `scrip` | `credits` | Consistency |
| `principal` | `account` | Principals include artifacts/contracts |
| `tick` | `turn` | Consistency |
| `artifact` | `object/entity` | Everything is an artifact |
| `mint` | `oracle` | Describes function (creating scrip) |

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

### Artifact Properties

All artifacts have these metadata fields (see `src/world/artifacts.py`):

| Property | Type | Description |
|----------|------|-------------|
| `id` | str | Unique artifact identifier |
| `content` | str | Artifact content (code, data, config) |
| `access_contract_id` | str | Governing contract for permissions |
| `created_by` | str | Principal who created the artifact |
| `created_at` | datetime | Creation timestamp |
| `updated_at` | datetime | Last modification timestamp |
| `deleted_by` | str \| None | Principal who deleted (if deleted) |
| `has_standing` | bool | Can hold resources/bear costs |
| `can_execute` | bool | Can be invoked as executable |
| `executable` | bool | Has executable code |
| `is_memory` | bool | Is a memory artifact |
| `memory_artifact_id` | str \| None | Linked memory artifact (for agents) |
| `depends_on` | list[str] | Artifact dependencies (Plan #63) |
| `genesis_methods` | dict | Method dispatch for genesis artifacts |

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

Six action types (Plan #131):

| Action | Purpose | Costs |
|--------|---------|-------|
| **noop** | Do nothing | None |
| **read_artifact** | Read artifact content | May cost scrip (read_price) |
| **write_artifact** | Create/replace artifact | Disk quota |
| **edit_artifact** | Surgical string replacement | Disk quota (Plan #131) |
| **invoke_artifact** | Call method on artifact | Scrip fee + compute |
| **delete_artifact** | Remove artifact, free disk | None (frees disk quota) |

**No direct transfer action.** Transfers happen via: `invoke_artifact("genesis_ledger", "transfer", [...])`

**Edit vs Write (Plan #131):**
- `write_artifact`: Full replacement (like `cat > file`)
- `edit_artifact`: Surgical change (like Claude Code's Edit tool, requires `old_string`/`new_string`)

---

## Contracts

**Contracts can do anything.** Invoker pays all costs.

| Term | Definition |
|------|------------|
| **access_contract_id** | Field on every artifact pointing to its governing contract |
| **check_permission** | Required method contracts implement to answer permission questions |

Common patterns: Freeware, Self-owned, Gatekeeper, Escrow, Paywall.

---

## System Primitives

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

## Mint

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

---

## Execution Model

| Term | Definition | Notes |
|------|------------|-------|
| **Tick** | Metrics observation window | NOT an execution trigger |

Agents use **continuous autonomous loops**:

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

## Cognitive Schema (Plan #88)

How agents structure their thinking and responses to the LLM.

| Term | Definition | Notes |
|------|------------|-------|
| **cognitive_schema** | Config option controlling agent response structure | `"simple"` or `"ooda"` |
| **thought_process** | Agent's reasoning (simple mode) | Single field for all thinking |
| **OODA** | Observe-Orient-Decide-Act loop | Military decision-making framework |
| **situation_assessment** | Analysis of current state (OODA mode) | Can be verbose |
| **action_rationale** | Concise explanation for chosen action (OODA mode) | 1-2 sentences |
| **failure_history** | Recent failed actions shown to agent | Enables learning from mistakes |

**Simple mode (default):** `thought_process` + `action`
**OODA mode:** `situation_assessment` + `action_rationale` + `action`

---

## Meta-Process Terminology

Development process terms (not system concepts):

| Term | Definition | Notes |
|------|------------|-------|
| **Acceptance Gate** | E2E-verifiable functional capability | Must pass real (non-mocked) tests. Prevents big-bang integration. See [META-ADR-0001](meta/adr/0001-acceptance-gate-terminology.md). |
| **Plan** | Work coordination document | Unit/integration tests. Multiple plans may contribute to one acceptance gate. |
| **Task** | Atomic work item within a plan | May have no dedicated tests. |

**Key hierarchy:**
```
Acceptance Gate (functional capability)    ← E2E test required
└── Plan(s) (work coordination)            ← Unit/integration tests
    └── Task(s) (atomic work)              ← May have no tests
```

**Why "acceptance gate" not "feature":**
- "Feature" is overloaded (product feature, feature flag, feature branch)
- "Acceptance gate" conveys the mechanism—it's a gate you must pass
- The name encodes discipline: not optional, not a suggestion

See [docs/meta/adr/](meta/adr/) for meta-process ADRs.

---

## Deprecated Terms

| Don't Use | Use Instead | Reason |
|-----------|-------------|--------|
| **oracle** | **mint** | "Mint" describes function (creating scrip) |
| **genesis_oracle** | **genesis_mint** | Terminology migration per ADR-0004 |
| **OracleScorer** | **MintScorer** | Class rename per ADR-0004 |
| **feature** (for E2E checkpoint) | **acceptance gate** | "Feature" is overloaded; see [META-ADR-0001](meta/adr/0001-acceptance-gate-terminology.md) |
| credits | scrip | Consistency |
| account | principal | Principals include non-agents |
| turn | tick | Consistency |
| transfer (as action) | invoke_artifact | No direct transfer action |
