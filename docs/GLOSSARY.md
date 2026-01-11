# Glossary

Canonical terminology for Agent Ecology. Use these terms consistently across code and documentation.

**Last updated:** 2026-01-11

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

Rights to depletable resources are distributed and tradeable like any other resource. The total pool is an external parameter.

### Allocatable (Finite But Reusable)

| Resource | What It Is | Unit | Notes |
|----------|------------|------|-------|
| **disk** | Storage space for artifacts | bytes | Per-principal quota; freed when artifacts deleted |
| **memory** | RAM for execution | bytes | Container limit; freed after use |

Allocatable resources are finite but can be reclaimed. Deleting an artifact frees its disk. Ending execution frees memory.

### Renewable (Replenishes Over Time)

| Resource | What It Is | Unit | Notes |
|----------|------------|------|-------|
| **compute** | Rate limit on actions/tokens | token_units | Token bucket model: accumulates to capacity |
| **bandwidth** | Network I/O | bytes/tick | Rate limited per time window |

Renewable resources use a **token bucket model**: accumulate at a fixed rate up to a capacity limit. Can go into debt (negative balance = frozen until recovery).

---

## Currency

| Term | Definition | Notes |
|------|------------|-------|
| **Scrip** | Internal economic currency | NOT a physical resource. Coordination signal. |

**Key distinction:**
- **Resources** = Physical constraints (compute, disk, memory, bandwidth, llm_budget)
- **Scrip** = Economic signal (prices, payments, coordination)

An agent can be rich in scrip but starved of compute, or vice versa.

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

### Core Concepts

| Term | Definition |
|------|------------|
| **access_contract_id** | Field on every artifact pointing to its governing contract |
| **check_permission** | Required method contracts implement to answer permission questions |

### Contract Capabilities (Revised 2026-01-11)

**Contracts can do anything.** Invoker pays all costs.

- Can call LLM (invoker pays)
- Can invoke other artifacts (invoker pays)
- Can make external API calls (invoker pays)
- Cannot directly mutate state (return decisions, kernel applies)

### Contract Types

Contracts can implement any pattern. Common patterns include:

| Pattern | Description |
|---------|-------------|
| **Freeware** | Always allows access (e.g., `genesis_freeware`) |
| **Self-owned** | Only owner can access (e.g., `genesis_self_owned`) |
| **Gatekeeper** | Manages access for multiple stakeholders |
| **Escrow** | Holds resources pending conditions |
| **Paywall** | Requires payment for access |

**Note:** These are patterns, not required types. Contracts are infinitely flexible.

### Executable vs Voluntary Contracts

| Type | Enforcement | Example |
|------|-------------|---------|
| **Executable** | Enforced automatically by code | Escrow releases on payment |
| **Voluntary** | Depends on parties choosing to comply | Handshake agreements |

There is no government of last resort. Defection is possible. Reputation and repeated interaction are the only enforcement for voluntary contracts.

---

## Genesis Artifacts

System-provided artifacts for bootstrapping. Theoretically replaceable—agents could build alternatives.

| Artifact | Purpose | Key Methods |
|----------|---------|-------------|
| **genesis_oracle** | Score artifacts, mint scrip | `submit`, `bid`, `process` |
| **genesis_escrow** | Trustless artifact trading | `deposit`, `purchase`, `cancel` |
| **genesis_event_log** | Simulation history | `read` |
| **genesis_handbook** | Documentation for agents | `read` |
| **genesis_freeware** | Permissive access contract | `check_permission` (always true) |
| **genesis_self_owned** | Self-only access contract | `check_permission` (owner only) |

**Genesis artifacts solve cold-start.** They're not the only way to coordinate—just the initial way.

---

## System Primitives

Part of the world itself—agents cannot replace these:

- Action execution (read, write, invoke)
- Resource accounting (balances for all resource types)
- Scrip ledger
- Artifact store
- Tick/time progression

Genesis artifacts provide *interfaces* to some primitives, but the underlying state is system-level.

---

## External Feedback

How value enters the system from outside:

| Term | Definition |
|------|------------|
| **Minting** | Creating new scrip based on external validation |
| **External validation** | Value judgments from outside the system (upvotes, bounties, API outcomes) |
| **User bounty** | Human posts task with reward; pays winner if satisfied |

The oracle is the interface for minting—but the *source* of value judgments is external.

---

## Organizational Structures

Agents can create any organizational structure:

| Structure | How It Works |
|-----------|--------------|
| **Hierarchy** | One agent owns/controls others via config ownership |
| **Flat coordination** | Peers cooperating via contracts |
| **Market** | Price-mediated exchange via escrow/trading |
| **Firm** | Group coordinating internally to reduce transaction costs |

---

## Evolution

| Term | Definition |
|------|------------|
| **Intelligent evolution** | Deliberate self-modification, not random mutation |
| **Self-rewriting** | Agent modifies its own config (prompt, model, policies) |
| **Config trading** | Buying/selling control of agent configurations |
| **Selection** | Configs that work persist; those that don't fade |

Unlike biological evolution, changes aren't random or incremental. Agents can analyze performance, reason about improvements, and rewrite entirely.

---

## Memory

Agent memory is a separate artifact from agent configuration.

| Term | Definition |
|------|------------|
| **memory_artifact_id** | Field on agent pointing to its memory collection artifact |
| **Memory collection** | Data artifact storing agent's memories (experiences, context, learned patterns) |
| **Memory trading** | Buying/selling access to agent memories independently from config |

**Key distinction:**
- **Config** = Goals and behavior (prompt, model, policies)
- **Memory** = Knowledge (experiences, context, learned patterns)

Both are artifacts. Both have `access_contract_id`. Both can be traded. This enables:
- "Factory reset" (sell config, keep/delete memory)
- Full identity transfer (sell both)
- Knowledge transfer (sell only memory)

**Implementation:** Memory artifact points to external storage (Qdrant) via `content.collection_id`. The artifact provides ownership semantics; actual vectors remain in Qdrant for efficiency.

---

## Time

| Term | Definition | Notes |
|------|------------|-------|
| **Tick** | One simulation step | Used for observation/metrics |

**Current implementation:** Tick-based execution (observe, then act).

**Target architecture:** Continuous autonomous loops. Ticks remain useful for metrics but agents aren't tick-synchronized.

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

---

## Code vs Config Mapping

| Config Term | Code Variable | Notes |
|-------------|---------------|-------|
| `resources.flow.compute` | `llm_tokens` | Legacy naming in code |
| `resources.stock.disk` | `disk` | Consistent |
| `resources.stock.llm_budget` | `llm_budget` | Consistent |
| `scrip.starting_amount` | `scrip[id]` | Ledger field |
