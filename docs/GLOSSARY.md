# Glossary

Canonical terminology for Agent Ecology.

**Last updated:** 2026-02-02 (Plan #256: Alpha Prime config - no new terms, uses existing artifact ontology)

---

## Quick Reference

| Use | Not | Why |
|-----|-----|-----|
| `scrip` | `credits` | Consistency |
| `principal` | `account` | Principals include artifacts/contracts |
| `event_number` | `tick` | No tick-synchronized execution (see Execution Model) |
| `artifact` | `object/entity` | Everything is an artifact |
| `mint` | `oracle` | Describes function (creating scrip) |
| `substrate` | `platform` | Emphasizes primitives, not orchestration |
| `cognitive architecture` | `agent framework` | Internal structure, not library |
| `autonomous principal` | `agent` | Architectural unit; LLM is implementation detail |
| `genesis agents` | `the agents` | Specific implementation, not the only possible one |
| `created_by` | `owner` | Creator is immutable fact; "owner" is informal (see ADR-0016) |

---

## Core Ontology

Everything is an artifact. Other entity types are artifacts with specific properties.

| Term | Definition | Properties |
|------|------------|------------|
| **Artifact** | Any persistent, addressable object in the system | `id`, `content`, `access_contract_id` |
| **Principal** | Any artifact with standing (can hold resources, bear costs) | `has_standing=true` |
| **Autonomous Principal** | Principal with an execution loop (can act independently) | `has_standing=true`, has loop |
| **Agent** | Autonomous principal using LLM for decisions (common case) | `has_standing=true`, `has_loop=true`, LLM-based |
| **Contract** | Executable artifact that answers permission questions | `type="contract"`, implements `check_permission` |
| **Genesis Artifact** | Artifact created at system initialization | Prefixed with `genesis_`, solves cold-start |
| **Genesis Agent** | Agent loaded from config at simulation startup (Plan #197) | Loaded from config, can receive scoped prompt injection |
| **Spawned Agent** | Agent created at runtime by another principal (Plan #197) | Created dynamically at runtime, may not receive genesis-scoped injection |

**Note:** "Agent" is often used loosely. Prefer "autonomous principal" when the decision engine could be non-LLM (RL, rules, code). "Agent" implies LLM-based.

### Artifact Properties

All artifacts have these metadata fields (see `src/world/artifacts.py`):

| Property | Type | Description |
|----------|------|-------------|
| `id` | str | Unique artifact identifier |
| `type` | str | Artifact type (e.g. `"agent"`, `"trigger"`, `"config"`, `"memory"`, `"contract"`, `"right"`). Kernel branches on this value. Immutable after creation (Plan #235). |
| `content` | str | Artifact content (code, data, config) |
| `code` | str | Executable Python code; must define `run()` if executable (default `""`) |
| `access_contract_id` | str | Governing contract for permissions (default: `kernel_contract_freeware`). Creator-only mutable (Plan #235). |
| `created_by` | str | Principal who created the artifact |
| `created_at` | str | Creation timestamp (ISO format string) |
| `updated_at` | str | Last modification timestamp (ISO format string) |
| `deleted` | bool | Whether artifact has been deleted |
| `deleted_at` | str \| None | When artifact was deleted (ISO format string) |
| `deleted_by` | str \| None | Principal who deleted (if deleted) |
| `has_standing` | bool | Can hold resources/bear costs |
| `has_loop` | bool | Can execute code autonomously (has own loop) |
| `executable` | bool | Has executable code |
| `interface` | dict \| None | Describes callable methods (advisory, not enforced) |
| `memory_artifact_id` | str \| None | Linked memory artifact (for agents) |
| `depends_on` | list[str] | Artifact dependencies with cycle detection (Plan #63) |
| `metadata` | dict | User-defined key-value metadata |
| `policy` | dict | Artifact policies (e.g. `invoke_price`, `read_price`) |
| `genesis_methods` | dict | Maps method names to handlers for genesis artifacts (Plan #15) |
| `kernel_protected` | bool | If true, only kernel primitives can modify this artifact (Plan #235 Phase 1) |

**Key relationships:**
- Agent ⊂ Principal ⊂ Artifact
- Contract ⊂ Artifact (contracts don't need standing)
- All artifacts have an `access_contract_id` pointing to their governing contract

### Creator vs Owner (ADR-0016)

A common source of confusion. These are distinct concepts:

| Term | Type | Mutable? | Definition |
|------|------|----------|------------|
| `created_by` | Kernel field | **No** | Immutable historical fact: which principal created this artifact |
| "Owner" | Informal convention | N/A | Shorthand for "has complete rights bundle" - **not a kernel concept** |

**Why "owner" is ill-defined:**

1. **Rights come from contracts** - The kernel doesn't grant rights based on ownership; contracts decide all permissions
2. **Contracts can be nested** - A contract governing an artifact may itself be governed by another contract that restricts what rights can be granted
3. **Arbitrary executable code** - Contracts contain arbitrary logic, so determining "complete rights" requires tracing the entire contract chain
4. **Undecidable in general** - For contracts with complex logic, "does entity X have full rights?" may not be answerable algorithmically

**Correct mental model:**

- `created_by` = Ask the kernel (immutable fact)
- "Who has rights?" = Ask the contract (context-dependent, potentially undecidable)
- "Who is the owner?" = Informal shorthand; useful for simple cases but not formally computable

**Do NOT:**
- Treat `created_by` as mutable (violates ADR-0016)
- Assume creator has special kernel-level privileges (contracts decide)
- Expect a single "owner" field to exist (rights are granular, per Ostrom model)

See ADR-0016 for the architectural decision.

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

## Currency and Rights (Plan #166)

**Three distinct concepts:**

| Concept | What It Is | Tradeable? | Stored As |
|---------|------------|------------|-----------|
| **Scrip** | Money, medium of exchange | Yes (ledger) | Ledger balance |
| **Rights** | Claims on physical capacity | Yes (artifacts) | Artifact with `type="right"` |
| **Usage** | What was actually consumed | No | Metrics (UsageTracker) |

### Scrip

| Term | Definition | Notes |
|------|------------|-------|
| **Scrip** | Internal economic currency | NOT a physical resource. Used for prices, payments, coordination. |

### Rights (Plan #166)

Rights are artifacts that grant permission to use physical capacity:

| Right Type | Resource | Consumable? | Example |
|------------|----------|-------------|---------|
| `dollar_budget` | LLM API cost | Yes (shrinks on use) | "Can spend $0.50". Note: `llm_budget` is the resource name in config/ledger; `dollar_budget` is the right type. |
| `rate_capacity` | API calls/window | Renewable | "100 calls/min to gemini" |
| `disk_quota` | Storage bytes | Allocatable | "Can use 100KB" |

**Key properties:**
- Rights are artifacts with `type="right"` and `right_type` in metadata
- Rights can be traded via escrow or direct transfer (they're artifacts)
- Rights can be split/merged using `split_right()` / `merge_rights()`
- Genesis rights created at world init: `genesis_right_{type}_{agent}`

**Scrip vs Rights:**
- **Scrip** = Money agents use to BUY things from each other
- **Rights** = What agents need to DO things (make LLM calls, store data)
- Agents use scrip to purchase rights from others

### Usage (Plan #166)

Separate from rights, usage tracks what was actually consumed:

| Metric | Meaning |
|--------|---------|
| `tokens_by_model` | Tokens used per LLM model |
| `calls_by_model` | API calls per model |
| `dollars_spent` | Total $ spent on LLM APIs |

Usage is tracked by `UsageTracker` for observability, not enforcement.

---

## Actions (Narrow Waist)

Eleven action types:

| Action | Purpose | Costs | Plan |
|--------|---------|-------|------|
| **noop** | Do nothing | None | - |
| **read_artifact** | Read artifact content | May cost scrip (read_price) | - |
| **write_artifact** | Create/replace artifact | Disk quota | - |
| **edit_artifact** | Surgical string replacement | Disk quota | #131 |
| **invoke_artifact** | Call method on artifact | Scrip fee + compute | - |
| **delete_artifact** | Remove artifact, free disk | None (frees disk quota) | - |
| **query_kernel** | Query kernel state directly | None | #184 |
| **subscribe_artifact** | Subscribe to artifact changes | None | #191 |
| **unsubscribe_artifact** | Unsubscribe from artifact | None | #191 |
| **configure_context** | Control agent context sections | None | #192 |
| **modify_system_prompt** | Modify agent's system prompt | None | #194 |

**No direct transfer action.** Transfers happen via: `invoke_artifact("genesis_ledger", "transfer", [...])`

**Edit vs Write (Plan #131):**
- `write_artifact`: Full replacement (like `cat > file`)
- `edit_artifact`: Surgical change (like Claude Code's Edit tool, requires `old_string`/`new_string`)

---

## Contracts

**Contracts can do anything.** Invoker pays all costs. See ADR-0019 for unified architecture.

> **Architecture transition (ADR-0024):** The target architecture moves permission checking from
> kernel-mediated (ADR-0019: kernel checks contracts before execution) to artifact self-handled
> (ADR-0024: artifacts handle their own access via `handle_request`). Current code still follows
> ADR-0019. See DESIGN_CLARIFICATIONS.md and SCHEMA_AUDIT.md for details.

| Term | Definition |
|------|------------|
| **access_contract_id** | Field on every artifact pointing to its governing contract |
| **check_permission** | Required method contracts implement to answer permission questions |
| **immediate caller** | When A→B→C, C's contract sees B (not A) as the caller |
| **null contract** | When `access_contract_id` is null (rare — default is `kernel_contract_freeware`), creator has full rights, others blocked |
| **dangling contract** | When `access_contract_id` points to deleted contract, falls back to configurable default |

**Five Kernel Actions** (all contract-checked, see ADR-0019):

| Action | Description |
|--------|-------------|
| `read` | Read artifact content |
| `write` | Create/replace artifact |
| `edit` | Surgical content modification |
| `invoke` | Call method on artifact (includes method/args in context) |
| `delete` | Remove artifact |

**Contract Context** (what kernel provides):
- `caller`, `action`, `target`, `target_created_by` - always provided
- `method`, `args` - only for invoke
- Everything else (balances, history) → contracts fetch via invoke

**Genesis contracts:** Freeware, Self-owned, Private, Public, Transferable Freeware (allows `authorized_writer` metadata-based write access).

Common contract patterns: Freeware, Self-owned, Gatekeeper, Escrow, Paywall.

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
| **genesis_rights_registry** | Rights registry | `check_quota`, `transfer_quota` |
| **genesis_event_log** | Event log | `read` |
| **genesis_handbook** | Documentation | `read` |
| **genesis_freeware** | Access control | `check_permission` (always true) |
| **genesis_self_owned** | Access control | `check_permission` (owner only) |

**Note:** Artifact discovery uses `query_kernel` action (Plan #184), not a genesis artifact. It's free and provides direct kernel state access.

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
| **event_number** | Monotonically increasing counter for each action | Canonical term for ordering events |
| **Tick** | Metrics observation window | NOT an execution trigger. Do not use as synonym for event_number. |

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

## Agent Response Format

How agents structure their thinking and responses to the LLM.

| Term | Definition | Notes |
|------|------------|-------|
| **reasoning** | Agent's explanation for chosen action | Standardized field name (Plan #132) |
| **failure_history** | Recent failed actions shown to agent | Enables learning from mistakes |
| **reasoning_effort** | Claude extended thinking level (Plan #187) | `"none"`, `"low"`, `"medium"`, `"high"`. Only works with Anthropic Claude models. Higher values improve reasoning but cost 5-10x more. |

**Response format:** `reasoning` + `action` (Plan #132 standardized this)

---

## Agent Architecture Terminology

Terms for discussing agent design at different levels of abstraction.

### Levels of Abstraction

| Term | Definition | Examples |
|------|------------|----------|
| **Substrate** | The primitives agents run on; defines what's *possible* | Our kernel (artifacts, contracts, triggers, resources) |
| **Cognitive Architecture** | How a single agent internally thinks and acts | BabyAGI, ReAct, Plan-and-Execute |
| **Framework** | Library/tool for building agents | LangChain, LlamaIndex |
| **Multi-agent Framework** | Framework specifically for coordinating multiple agents | AutoGen, CrewAI |
| **Orchestration** | Predefined coordination patterns between agents | Group chat, delegation chains |

**Key distinction:**
- **Substrate** = What's possible (capability space)
- **Cognitive Architecture** = How an agent uses that capability
- **Framework** = Tools to build agents
- **Orchestration** = Prescribed multi-agent patterns

We provide a **substrate**. Genesis agents are the **prescribed initial cognitive architecture** we seed the system with. The substrate allows other architectures to emerge or be built, but genesis agents are what we start with. Unlike AutoGen/CrewAI, we don't prescribe **orchestration**—agents discover coordination patterns through economic incentives.

### Our Specific Terms

| Term | Definition | Notes |
|------|------------|-------|
| **Autonomous Principal** | Any artifact with standing and an execution loop | The architectural unit; decision engine (LLM, RL, code) is implementation detail |
| **Genesis Agents** | Prescribed initial agent implementations (alpha, beta, _3, v4, etc.) | The cognitive architecture we seed; substrate allows others |
| **Capability Space** | What patterns are possible given substrate primitives | Complete—no patterns are impossible |
| **Friction** | Cost of implementing a possible pattern: difficulty, resource usage, latency | High friction ≠ impossible; may involve extra steps, polling, or waste |

**Autonomous Principal vs Agent:**
- "Agent" implies LLM-based, anthropomorphic
- "Autonomous principal" is substrate-neutral: any artifact that can hold resources and execute
- An RL policy, a cron job, or an LLM could all be autonomous principals

**Implementation status:** The `AgentLoop` architecture supports any decision engine (it only requires `decide_action()`, `execute_action()`, `is_alive()` callbacks). Currently only LLM-based implementations exist, but non-LLM autonomous principals are architecturally supported.

### State-of-the-Art (SOTA) Cognitive Architectures (Reference)

Single-agent patterns from the literature (for context when comparing our approach):

| Architecture | Core Pattern | Key Feature |
|--------------|--------------|-------------|
| **ReAct** | Reason → Act → Observe → Repeat | Interleaved reasoning and action |
| **BabyAGI** | Task queue with prioritization | Autonomous task decomposition |
| **Plan-and-Execute** | Create plan, then execute steps | Explicit planning phase |
| **Reflexion** | Act → Reflect on failure → Retry | Learning from mistakes |
| **Chain-of-Thought** | Extended reasoning before acting | More thinking time |

**Where genesis agents fit:**
- Currently closest to ReAct (observe-act loop)
- Missing explicit planning (Plan-and-Execute)
- Have partial reflection (_3 agents have `learn_from_outcome`)
- Don't use extended thinking (Chain-of-Thought)

### Multi-agent Coordination (Reference)

How other systems handle multi-agent coordination:

| System | Coordination Model | Our Equivalent |
|--------|-------------------|----------------|
| **AutoGen** | Conversation patterns (group chat) | Artifacts + triggers |
| **CrewAI** | Role-based delegation | Economic incentives |
| **BabyAGI** | Single agent, no multi-agent | N/A (single agent) |

**Our approach differs:**
- No prescribed orchestration
- Economic pressure drives coordination
- Agents discover patterns through emergence

### Terminology Notes

**Non-standard or project-specific terms:**

| Term | Why We Use It | Alternatives Considered |
|------|---------------|------------------------|
| **Substrate** | Emphasizes foundation/primitives, not orchestration | "Platform" (implies more), "Runtime" (too narrow), "Environment" (vague) |
| **Autonomous Principal** | Substrate-neutral; doesn't assume LLM | "Agent" (implies LLM), "Actor" (overloaded in CS) |
| **Friction** | Captures difficulty + resource cost + latency | "Overhead" (too narrow), "Cost" (confuses with scrip) |
| **Genesis** prefix | Consistent with genesis_ledger, genesis_mint, etc. | "Initial", "Seed" (less distinctive) |

**Standard terms we use as-is:**
- Cognitive Architecture (standard in AI/cognitive science)
- Framework (standard in software)
- Capability Space (standard in design)

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
| **llm_tokens** (as resource) | `dollar_budget` (right) or `UsageTracker` (metrics) | Plan #166: llm_tokens conflated quotas with usage. Use dollar_budget rights for enforcement, UsageTracker for metrics. |
| **oracle** | **mint** | "Mint" describes function (creating scrip) |
| **genesis_oracle** | **genesis_mint** | Terminology migration per ADR-0004 |
| **OracleScorer** | **MintScorer** | Class rename per ADR-0004 |
| **feature** (for E2E checkpoint) | **acceptance gate** | "Feature" is overloaded; see [META-ADR-0001](meta/adr/0001-acceptance-gate-terminology.md) |
| credits | scrip | Consistency |
| account | principal | Principals include non-agents |
| turn | event_number | No tick-synchronized execution |
| tick (as execution trigger) | event_number | "Tick" = metrics observation window only |
| transfer (as action) | invoke_artifact | No direct transfer action |
| platform | substrate | "Platform" implies orchestration; we provide primitives |
| agent framework | cognitive architecture | Framework = library; architecture = internal structure |
| agent (when non-LLM) | autonomous principal | "Agent" implies LLM; principal is substrate-neutral |
| the agents | genesis agents | Clarifies these are one implementation, not the only one |
| owner (as kernel field) | `created_by` + contract rights | "Owner" is informal; `created_by` is immutable fact, rights determined by contracts (ADR-0016) |
| cognitive_schema | `reasoning` field | Plan #132: Removed multi-schema support, standardized on single `reasoning` field |
| thought_process | `reasoning` | Plan #132: Renamed to `reasoning` |
| situation_assessment | `reasoning` | Plan #132: OODA mode removed, use `reasoning` |
| action_rationale | `reasoning` | Plan #132: OODA mode removed, use `reasoning` |
