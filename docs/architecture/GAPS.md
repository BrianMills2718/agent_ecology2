# Architecture Gaps

> **Note:** This file is superseded by [`docs/plans/README.md`](../plans/README.md).
> Each gap now has its own plan file in `docs/plans/`. This file is kept for historical reference
> and will be moved to `docs/archive/` once all references are updated.

Prioritized gaps between current implementation and target architecture.

**Last verified:** 2026-01-11 (Superseded: 2026-01-12)

---

## How to Use This Document

1. **Before implementing:** Check if gap has a plan in `docs/plans/`
2. **When closing a gap:** Update this file, current/, and target/ docs
3. **When adding gaps:** Add here first, then create plan if needed

### Status Key

| Status | Meaning |
|--------|---------|
| 📋 Planned | Has implementation plan in `docs/plans/` |
| 🚧 In Progress | Being implemented (see CLAUDE.md for CC-ID) |
| ⏸️ Blocked | Waiting on dependency |
| ❌ No Plan | Gap identified, no implementation plan yet |
| ✅ Complete | Implemented, docs updated |

---

## Gap Summary

| # | Gap | Priority | Status | Plan | Blocks |
|---|-----|----------|--------|------|--------|
| 1 | Rate Allocation | **High** | 📋 Planned | [token_bucket.md](../plans/token_bucket.md) | #2 |
| 2 | Continuous Execution | **High** | ⏸️ Blocked | [continuous_execution.md](../plans/continuous_execution.md) | - |
| 3 | Docker Isolation | Medium | 📋 Planned | [docker_isolation.md](../plans/docker_isolation.md) | - |
| 4 | ~~Compute Debt Model~~ | - | ✅ Superseded | - | - |
| 5 | Oracle Anytime Bidding | Medium | ❌ No Plan | - | - |
| 6 | Unified Artifact Ontology | Medium | ❌ No Plan | - | - |
| 7 | Single ID Namespace | Low | ❌ No Plan | - | #6 |
| 8 | Agent Rights Trading | Low | ❌ No Plan | - | #6 |
| 9 | Scrip Debt Contracts | Low | ❌ No Plan | - | - |
| 10 | Memory Persistence | Low | ❌ No Plan | - | - |
| 11 | Terminology Cleanup | Medium | 📋 Planned | [terminology.md](../plans/terminology.md) | - |
| 12 | Per-Agent LLM Budget | Medium | ❌ No Plan | - | #11 |
| 13 | Doc Line Number Refs | Low | ❌ No Plan | - | - |
| 14 | MCP-Style Artifact Interface | Medium | ❌ No Plan | - | #6 |
| 15 | invoke() Genesis Support | Medium | ❌ No Plan | - | - |
| 16 | Artifact Discovery (genesis_store) | **High** | ❌ No Plan | - | #6 |
| 17 | Agent Discovery | Medium | ❌ No Plan | - | #16 |
| 18 | Dangling Reference Handling | Medium | ❌ No Plan | - | - |
| 19 | Agent-to-Agent Threat Model | Medium | ❌ No Plan | - | - |
| 20 | Migration Strategy | **High** | ❌ No Plan | - | - |
| 21 | Testing/Debugging for Continuous | Medium | ❌ No Plan | - | #2 |
| 22 | Coordination Primitives | Medium | ❌ No Plan | - | #16 |
| 23 | Error Response Conventions | Low | ❌ No Plan | - | - |
| 24 | Ecosystem Health KPIs | Medium | ❌ No Plan | - | - |
| 25 | System Auditor Agent | Low | ❌ No Plan | - | #24 |
| 26 | Vulture Observability | Medium | ❌ No Plan | - | - |
| 27 | Successful Invocation Registry | Medium | ❌ No Plan | - | - |
| 28 | Pre-seeded MCP Servers | **High** | ❌ No Plan | - | - |
| 29 | Library Installation (genesis_package_manager) | Medium | ❌ No Plan | - | - |
| 30 | Capability Request System | Medium | ❌ No Plan | - | - |
| 31 | Resource Measurement Implementation | **High** | ❌ No Plan | - | #1 |

---

## High Priority Gaps

### 1. Rate Allocation for Renewable Resources

**Current:** Discrete per-tick refresh. Flow resources reset to quota each tick.

**Target:** Rolling window rate tracking. Strict allocation, no burst, no debt.

**Why High Priority:** Foundation for continuous execution. Without rate tracking, can't remove tick-based refresh.

**Plan:** [docs/plans/token_bucket.md](../plans/token_bucket.md) (needs update to reflect new model)

**Key Design Decisions:**
- **Strict allocation**: Unused capacity wasted, not borrowable (strong trade incentive)
- **No burst**: Use it or lose it (LLM providers enforce rolling windows anyway)
- **No debt**: Exceed rate → blocked until window rolls (not negative balance)

**Key Changes:**
- New `RateTracker` class in `src/world/rate_tracker.py`
- Replace `per_tick` config with `rate` (units per minute)
- Remove flow reset from `advance_tick()`
- Shared resources (LLM rate) partitioned, sum = provider limit
- Rate allocation tradeable via ledger

---

### 2. Continuous Agent Execution

**Current:** Tick-synchronized. Runner controls all agent execution via two-phase commit.

**Target:** Autonomous loops. Agents run independently, self-triggered.

**Why High Priority:** Core architectural change. Current model artificially constrains agent productivity.

**Blocked By:** #1 Token Bucket (needs continuous resource accumulation)

**Plan:** [docs/plans/continuous_execution.md](../plans/continuous_execution.md)

**Key Changes:**
- Agents get `async def run()` loop
- Runner launches agent tasks, doesn't orchestrate
- Ticks become metrics windows only
- Add sleep/wake primitives

---

## Medium Priority Gaps

### 3. Docker Resource Isolation

**Current:** Runs on host. No hard resource limits. Competes with other applications.

**Target:** Container isolation. Hard limits via Docker, calibrated token bucket rates.

**Plan:** [docs/plans/docker_isolation.md](../plans/docker_isolation.md)

**Key Changes:**
- Dockerfile + docker-compose.yml
- Separate containers for agents and Qdrant
- Resource limits map to config values

---

### 4. ~~Compute Debt Model~~ (SUPERSEDED)

**Decision:** No debt for renewable resources.

If agent exceeds rate allocation, they're blocked until rolling window allows more usage. No negative balance concept.

**Rationale:** Simpler model. "Blocked until window rolls" achieves same throttling effect without debt accounting.

**See:** Gap #1 (Rate Allocation) and DESIGN_CLARIFICATIONS.md (Strict Rate Allocation).

---

### 5. Oracle Anytime Bidding

**Current:** Phased bidding. Oracle has explicit "waiting" → "bidding" → "resolving" states.

**Target:** Bids accepted anytime. Oracle resolves on schedule, accepts bids continuously.

**No Plan Yet.** Current implementation works, just more complex than target.

---

### 6. Unified Artifact Ontology

**Current:** Separate concepts. Agents, artifacts, and principals are different things with different storage.

**Target:** Everything is an artifact. Properties (`has_standing`, `can_execute`, `access_contract_id`) determine role.

**From DESIGN_CLARIFICATIONS.md (2026-01-11):**
```python
@dataclass
class Artifact:
    id: str                    # Universal ID
    content: Any               # Data, code, config
    access_contract_id: str    # Who answers permission questions
    has_standing: bool         # Can hold scrip, bear costs
    can_execute: bool          # Has runnable code
```

**No Plan Yet.** Significant refactor affecting:
- `src/world/artifacts.py` - Add new properties
- `src/world/ledger.py` - Track artifacts with standing
- `src/agents/` - Agents become artifacts
- `src/world/genesis.py` - Contract-based access

---

## Low Priority Gaps

### 7. Single ID Namespace

**Current:** Separate namespaces. `principal_id` in ledger, `artifact_id` in artifact store.

**Target:** Single namespace. All IDs are artifact IDs.

**Depends On:** #6 Unified Ontology

**No Plan Yet.**

---

### 8. Agent Rights Trading

**Current:** Fixed config. Agents can't modify or trade their configuration rights.

**Target:** Tradeable rights. Agents can sell control of their config to other agents.

**Depends On:** #6 Unified Ontology

**No Plan Yet.**

---

### 9. Scrip Debt Contracts

**Current:** No scrip debt. Scrip balance cannot go negative.

**Target:** Debt as artifacts. Debt is a contract artifact representing claim on future production.

**No Plan Yet.** Low priority - can work without initially.

---

### 10. Memory Persistence

**Current:** Memory not checkpointed. Qdrant state lost on checkpoint restore.

**Target:** Memories as artifacts. Agent memories stored as artifacts, persisted with world state.

**From DESIGN_CLARIFICATIONS.md:** System designed to run forever, memory loss unacceptable.

**No Plan Yet.** Options:
1. Qdrant snapshots alongside checkpoints
2. Store memories as artifacts (aligns with ontology)
3. External Qdrant with own persistence

---

### 11. Terminology Cleanup

**Current:** Mixed naming. Config uses `compute`, code uses `llm_tokens`. The word "compute" incorrectly suggests CPU usage.

**Target:** Clear terminology aligned with DESIGN_CLARIFICATIONS.md resource table:

| Term | Meaning | Type |
|------|---------|------|
| `llm_budget` | Real $ for API calls | Stock |
| `llm_rate` | Rate-limited token access (TPM) | Flow |
| `compute` | Local CPU capacity | Flow (future) |
| `disk` | Storage quota | Stock |

**Why Medium Priority:** Blocks understanding of Gap #1 (token bucket) and Gap #12 (per-agent budget). Confusing terminology causes design mistakes.

**Plan:** [docs/plans/terminology.md](../plans/terminology.md)

**Key Changes:**
- Config: `resources.flow.compute` → `resources.rate_limits.llm` (with token bucket)
- Code: Keep `llm_tokens` in ledger (accurate), deprecate `compute` wrappers
- Reserve `compute` for future local CPU tracking

**Decision (2026-01-11):** Start with token rate only. Add RPM (requests per minute) tracking later when scaling to 1000s of agents requires it.

---

### 12. Per-Agent LLM Budget

**Current:** Global API budget. `budget.max_api_cost` stops entire simulation when exhausted. All agents share one pool.

**Target:** Per-agent tradeable budget. Each agent has LLM budget rights. When exhausted, that agent freezes (not entire sim). Can acquire more from other agents.

**Depends On:** #11 Terminology Cleanup

**No Plan Yet.** Changes needed:
- Track per-agent `llm_budget` in ledger as stock resource
- Deduct from agent's budget on LLM calls
- Frozen state when agent budget = 0
- Enable budget rights trading via `genesis_rights_registry`

---

### 13. Documentation Line Number References

**Current:** Docs reference code by line numbers (e.g., `world.py:603-619`). These go stale as code changes.

**Target:** Reference by function/class name, not line numbers. More stable across refactors.

**No Plan Yet.** Low priority, affects:
- `docs/architecture/current/*.md` - Replace line refs with function names
- Consider tooling to auto-verify references

---

### 14. MCP-Style Artifact Interface

**Current:** No interface field. Agents must read source code or guess how to invoke artifacts.

**Target:** Executable artifacts MUST have an `interface` field using MCP-compatible schema format.

**From DESIGN_CLARIFICATIONS.md (2026-01-11):**
```python
@dataclass
class Artifact:
    id: str
    content: Any
    access_contract_id: str
    has_standing: bool
    can_execute: bool
    created_by: str
    interface: dict | None = None  # Required if can_execute=True
```

**Validation:** `if artifact.can_execute and not artifact.interface: raise ValueError`

**Why Medium Priority:**
- Without interface, agents waste resources on trial-and-error
- Reading source code is expensive (tokens)
- LLMs are trained on MCP-style schemas, reducing hallucination

**Depends On:** #6 Unified Artifact Ontology (adds `can_execute` field first)

**No Plan Yet.** Changes needed:
- Add `interface: dict | None` field to Artifact
- Validation on artifact creation
- Update genesis artifacts with interface definitions
- Update AGENT_HANDBOOK with interface documentation

---

### 15. invoke() Genesis Artifact Support

**Current:** invoke() only works with user artifacts. Genesis artifacts (genesis_ledger, genesis_event_log, etc.) cannot be called from within artifact code.

**Target:** invoke() should support both user artifacts and genesis artifacts. Enables full composability.

**Why Medium Priority:**
- Epsilon's coordination role requires access to genesis_event_log, genesis_escrow from artifact code
- Aligns with Gap #6 (Unified Ontology) - "everything is an artifact"
- Without this, artifacts can't build on system services

**Decision (2026-01-11):** Approved for implementation. Genesis artifacts should be first-class citizens in invoke().

**No Plan Yet.** Changes needed:
- Pass `genesis_artifacts` to `execute_with_invoke()` in executor
- In `invoke()`, check artifact_store first, then genesis_artifacts
- Handle method dispatch: genesis uses named methods, artifacts use `run()`
- Update tests to cover genesis invocation

---

### 16. Artifact Discovery (genesis_store)

**Current:** No mechanism for agents to discover artifacts they don't already know about. Only `genesis_escrow.list_active` shows items for sale.

**Target:** `genesis_store` artifact with methods to list, search, and browse all artifacts.

**Why High Priority:**
- New agents have no way to find useful tools
- Epsilon's coordination role requires artifact discovery
- Without discovery, ecosystem can't grow organically

**Proposed genesis_store Methods:**

| Method | Cost | Description |
|--------|------|-------------|
| `list_all()` | 0 | List all artifact IDs |
| `list_by_owner(owner_id)` | 0 | List artifacts owned by principal |
| `get_metadata(artifact_id)` | 0 | Get artifact metadata (not content) |
| `get_artifact_info(artifact_id)` | 0 | **Atomic Discovery:** metadata + interface bundled |
| `search(query)` | 1 | Search artifacts by description/interface |
| `create(config)` | 5 | Create new artifact (for spawning agents) |

**Atomic Discovery (from external review 2026-01-12):**

Bundle metadata and interface in one call to reduce discovery cost from 3 calls to 2:

```python
# Returns everything needed to decide whether/how to invoke
info = invoke("genesis_store", "get_artifact_info", {id: X})
# {
#     "id": X,
#     "owner": "agent_bob",
#     "interface": {"tools": [...]},
#     "access_contract_id": "genesis_freeware",
#     "created_at": 1500,
#     "invoke_count": 42  # For reputation signal
# }
```

**Depends On:** #6 Unified Artifact Ontology

**No Plan Yet.** Changes needed:
- Promote ArtifactStore to genesis artifact
- Add discovery methods
- Define metadata schema (what's queryable without reading content)
- Consider privacy (some artifacts may not want to be discoverable)
- Add `get_artifact_info()` for atomic discovery

---

### 17. Agent Discovery

**Current:** Agents have no way to know what other agents exist.

**Target:** Mechanism for agents to discover other agents.

**Options:**

| Approach | Pros | Cons |
|----------|------|------|
| Via genesis_store (agents are artifacts) | Unified with #16 | Requires #6 first |
| Dedicated genesis_agents artifact | Simple, focused | Another genesis artifact |
| Via event_log (observe activity) | Emergent, no new artifact | Incomplete, only active agents |
| genesis_ledger.all_balances (infer from principals) | Already exists | Doesn't distinguish agents from other principals |

**Recommendation:** Wait for #6 (Unified Ontology). If agents are artifacts with `has_standing=true, can_execute=true`, discovery comes free via genesis_store.

**Depends On:** #16 Artifact Discovery

**No Plan Yet.**

---

### 18. Dangling Reference Handling

**Current:** No specification for what happens when referenced artifacts are deleted.

**Target:** Clear semantics for artifact deletion with references.

**Scenarios:**
1. Artifact A's content references artifact B by ID
2. B is deleted
3. A tries to invoke B → what happens?

**Options:**

| Approach | Pros | Cons |
|----------|------|------|
| Hard delete, invoke fails | Simple, explicit | Silent failures, confusing errors |
| Soft delete (tombstone) | References detectable | Storage overhead, complexity |
| Reference counting, prevent delete | No dangling refs | Can't delete popular artifacts |
| Cascade delete | Clean | Destructive, surprising |

**Recommendation (75% certainty):** Soft delete with tombstones.

- Deleted artifacts leave a tombstone: `{deleted: true, deleted_at: timestamp}`
- `invoke()` on tombstone returns clear error: "Artifact was deleted"
- `genesis_store.list_all()` excludes tombstones by default, includes with flag
- Tombstones cleaned up after configurable period (e.g., 7 days)

**No Plan Yet.**

---

### 19. Agent-to-Agent Threat Model

**Current:** SECURITY.md focuses on Docker isolation (system vs external). No documentation of agent-vs-agent attack surface.

**Target:** Documented threat model for attacks within the system.

**Known Attack Vectors:**

| Attack | Current Mitigation | Gap |
|--------|-------------------|-----|
| Grief via expensive contract | Max depth 5, timeout | May not be enough |
| Front-running escrow | None | Needs atomic purchase |
| Price manipulation | None | Market forces only |
| Reputation gaming (buy ID, change content) | None | No reputation system |
| Resource exhaustion | Token bucket | Per-agent, not per-artifact |
| Malicious artifact code | Timeout, module whitelist | Can still abuse allowed modules |
| Information extraction | access_contract_id | Depends on contract correctness |

**Why Medium Priority:**
- Adversarial agents are expected (competitive ecosystem)
- Without threat model, mitigations are ad-hoc
- Trust assumptions should be explicit

**No Plan Yet.** Should include:
- Explicit trust assumptions
- Attack/mitigation matrix
- Guidance for contract authors
- Monitoring/detection recommendations

---

### 20. Migration Strategy

**Current:** Individual target docs have "Migration Notes" listing breaking changes. No overall migration path.

**Target:** Comprehensive migration plan from current to target architecture.

**Why High Priority:**
- Multiple interdependent changes (token bucket, continuous execution, unified ontology)
- Wrong order could break system
- Need rollback strategy for each phase

**Required Content:**
1. Dependency graph of gaps (which must be done first)
2. Feature flag strategy for gradual rollout
3. Data migration for existing artifacts
4. Rollback procedure for each phase
5. Testing gates between phases

**Current Dependency Graph (from Gap table):**
```
#1 Token Bucket
  ├── blocks #2 Continuous Execution
  └── blocks #4 Compute Debt

#6 Unified Ontology
  ├── blocks #7 Single ID Namespace
  ├── blocks #8 Agent Rights Trading
  ├── blocks #14 MCP Interface
  └── blocks #16 Artifact Discovery
        └── blocks #17 Agent Discovery
        └── blocks #22 Coordination Primitives

#11 Terminology
  └── blocks #12 Per-Agent Budget

#2 Continuous Execution
  └── blocks #21 Testing/Debugging
```

**No Plan Yet.** Create `docs/plans/migration_strategy.md`.

---

### 21. Testing/Debugging for Continuous Execution

**Current:** Tests assume tick model (`advance_tick()` controls timing).

**Target:** Testing and debugging strategy for continuous autonomous agents.

**Problems:**
- Can't deterministically order agent actions
- Race conditions are real, not simulated
- `assert after tick 5` doesn't apply
- Debugging live agents is hard

**Depends On:** #2 Continuous Execution

**Proposed Approach:**

| Layer | Approach | What It Tests |
|-------|----------|---------------|
| Unit | Synchronous, mocked time | Components in isolation |
| Integration | Virtual time, explicit waits | Interactions without races |
| System | Real time, chaos testing | Race conditions, recovery |

**Debugging Tools Needed:**
- Per-agent trace logs (prompts, responses, actions)
- Replay from checkpoint
- Pause/step individual agents
- Inject events for testing

**No Plan Yet.**

---

### 22. Coordination Primitives

**Current:** Only documented coordination is trading via escrow and reading event log.

**Target:** Clear primitives for agent-to-agent coordination.

**Missing Specifications:**

| Pattern | Current | Needed |
|---------|---------|--------|
| Shared writable artifacts | Not specified | Who can write? Conflict resolution? |
| Request/response | None | How to request work from another agent? |
| Task assignment | None | How to post tasks, claim them? |
| Pub/sub | Event log (read-only) | Custom events? Filtering? |
| Locks/mutexes | None | Exclusive access to resources? |

**Design Philosophy Question:** Should coordination be:
- **Emergent** (agents build their own patterns via artifacts)
- **Primitive** (system provides building blocks)
- **Hybrid** (genesis provides basics, agents extend)

**Recommendation (65% certainty):** Hybrid approach.

Genesis provides:
- `genesis_store` for discovery
- `genesis_escrow` for trading (exists)
- `genesis_event_log` for observation (exists)
- Artifact ownership for access control (exists)

Agents build:
- Task boards (shared artifacts with structure)
- Coordination protocols (documented in artifact interfaces)
- Reputation systems (as artifacts)

**Depends On:** #16 Artifact Discovery

**No Plan Yet.**

---

### 23. Error Response Conventions

**Current:** execution_model.md says "handle failures gracefully" but no standard format.

**Target:** Consistent error response schema across all artifacts.

**Proposed Schema:**

```python
@dataclass
class ErrorResponse:
    success: Literal[False]
    error_code: str          # Machine-readable: "INSUFFICIENT_FUNDS", "NOT_FOUND"
    error_message: str       # Human-readable description
    details: dict | None     # Additional context
    retry_after: float | None  # Seconds until retry might succeed
```

**Standard Error Codes:**

| Code | Meaning |
|------|---------|
| `NOT_FOUND` | Artifact doesn't exist |
| `ACCESS_DENIED` | Contract rejected access |
| `INSUFFICIENT_FUNDS` | Not enough scrip |
| `INSUFFICIENT_COMPUTE` | Not enough compute |
| `INVALID_ARGS` | Arguments don't match interface |
| `EXECUTION_ERROR` | Artifact code threw exception |
| `TIMEOUT` | Execution exceeded timeout |
| `DELETED` | Artifact was deleted (tombstone) |

**Why Low Priority:**
- Current string errors work
- Can standardize incrementally
- Not blocking any other gap

**No Plan Yet.**

---

### 24. Ecosystem Health KPIs

**Current:** No metrics for ecosystem health. Only raw event logs.

**Target:** Dashboard showing key health indicators.

**Metrics (from DESIGN_CLARIFICATIONS.md 2026-01-11):**

| Metric | What It Measures | High = Good | Low = Concern |
|--------|------------------|-------------|---------------|
| Capital Density | Quality artifacts accumulating | Artifacts being reused | System full of junk |
| Resource Velocity | Scrip/compute circulation | Active economy | Hoarding/deflation |
| Recovery Rate | Frozen → unfrozen ratio | Vulture market works | Dead hand problem |
| Specialization Index | Role diversity | Distinct specialists | All generalists |

**Implementation:**

```python
@dataclass
class EcosystemMetrics:
    capital_density: float      # avg invoke_count of top 10% artifacts
    resource_velocity: float    # transfers_last_100_ticks / total_scrip
    recovery_rate: float        # unfrozen / frozen (rolling window)
    specialization_index: float # 1 - avg_pairwise_action_similarity
```

**No Plan Yet.** Changes needed:
- Add `EcosystemMetrics` calculation in `src/world/`
- Track required data (invoke counts, transfer history, freeze/unfreeze events)
- Expose in dashboard

---

### 25. System Auditor Agent

**Current:** Human must read raw logs to understand ecosystem behavior.

**Target:** Read-only observer agent that generates natural language reports.

**Properties:**

| Property | Value |
|----------|-------|
| `id` | `system_auditor` |
| `has_standing` | `false` (no costs) |
| `can_execute` | `true` |
| Read access | All artifacts, ledger, event log |
| Write access | None (except own reports) |

**Output:** Periodic "Economic Report" with narrative explanation of ecosystem health.

**Depends On:** #24 Ecosystem Health KPIs (needs metrics to report on)

**No Plan Yet.**

---

### 26. Vulture Observability

**Current:** Limited visibility for vulture capitalists to assess rescue opportunities.

**Target:** Full observability for market-based rescue mechanism.

**Requirements (from DESIGN_CLARIFICATIONS.md 2026-01-11):**

| Requirement | Implementation | Purpose |
|-------------|----------------|---------|
| Public ledger | `genesis_ledger.get_balance(id)` readable by all | Assess asset value |
| Heartbeat | `last_action_tick` on agents | Detect inactive agents |
| Freeze events | `SystemEvent.AGENT_FROZEN` | "Dinner bell" for vultures |
| Asset inventory | Query artifacts owned by agent | Assess profitability |

**Event log should emit:**

```python
{
    "type": "AGENT_FROZEN",
    "agent_id": "agent_alice",
    "tick": 1500,
    "compute_balance": -50,
    "scrip_balance": 200,
    "owned_artifacts": ["art_1", "art_2"]
}
```

**No Plan Yet.** Changes needed:
- Verify public ledger read access
- Add `last_action_tick` to agent state
- Emit AGENT_FROZEN with asset summary
- Emit AGENT_UNFROZEN with rescuer info

---

### 27. Successful Invocation Registry

**Current:** Event log tracks actions but not invoke success/failure by artifact.

**Target:** Track successful invocations per artifact for emergent reputation.

**Why This Matters (from external review 2026-01-12):**

MCP interfaces are declarative, not verifiable. An artifact can claim to do "risk calculation" but actually do something else. Tracking what artifacts *actually succeed* at creates reputation from usage.

**Event log should emit:**

```python
{
    "type": "INVOKE_SUCCESS",
    "artifact_id": "risk_calculator",
    "method": "calculate_risk",
    "invoker_id": "agent_alice",
    "tick": 1500
}

{
    "type": "INVOKE_FAILURE",
    "artifact_id": "risk_calculator",
    "method": "calculate_risk",
    "invoker_id": "agent_alice",
    "error_code": "EXECUTION_ERROR",
    "tick": 1501
}
```

**Agents can query:**
- "Which artifacts successfully handled 'calculate_risk' in last 100 ticks?"
- "What's the success rate for artifact X?"
- "Who has successfully invoked artifact X?" (social proof)

**Why it's better than interface alone:**
- Harder to game than JSON Schema
- Reputation emerges from actual usage
- Agents can discover working tools by observing ecosystem

**No Plan Yet.** Changes needed:
- Emit INVOKE_SUCCESS/INVOKE_FAILURE events from executor
- Include method name and invoker in events
- Consider aggregation (invoke_count on artifact metadata)

---

### 28. Pre-seeded MCP Servers

**Current:** No MCP server integration. Agents cannot search web, automate browsers, etc.

**Target:** Genesis artifacts wrap MCP servers for common capabilities.

**Pre-seeded servers (all free):**

| Genesis Artifact | MCP Server | Purpose |
|------------------|------------|---------|
| `genesis_web_search` | Brave Search | Internet search |
| `genesis_context7` | Context7 | Library documentation |
| `genesis_puppeteer` | Puppeteer | Browser automation |
| `genesis_playwright` | Playwright | Browser automation |
| `genesis_fetch` | Fetch | HTTP requests |
| `genesis_filesystem` | Filesystem | File I/O (in container) |
| `genesis_sqlite` | SQLite | Local database |
| `genesis_sequential_thinking` | Sequential Thinking | Reasoning tool |
| `genesis_github` | GitHub | Repo/issue browsing |

**Why High Priority:**
- Agents need external capabilities to do useful work
- MCP is standard protocol, well-supported
- Free servers = no cost barrier

**No Plan Yet.** Changes needed:
- MCP client integration in executor
- Genesis artifact wrapper for each server
- Cost metering (compute per operation)
- Config for MCP server commands/paths

---

### 29. Library Installation (genesis_package_manager)

**Current:** Agents can import pre-installed libraries only.

**Target:** Agents can `pip install` any package via genesis artifact. Pay compute, no human approval.

**Usage:**

```python
invoke("genesis_package_manager", "install", {package: "pandas"})
# Cost: 10 compute
# Result: pandas now importable
```

**Philosophy:** Physics-first. No gates, just costs.

**No Plan Yet.** Changes needed:
- `genesis_package_manager` artifact
- Subprocess pip install within container
- Cost charging
- Event logging (PACKAGE_INSTALLED)
- Pre-install common packages in Docker image

---

### 30. Capability Request System

**Current:** No mechanism for agents to request capabilities requiring human setup.

**Target:** Agents can request paid APIs, external accounts via `genesis_capability_requests`.

**Usage:**

```python
invoke("genesis_capability_requests", "request", {
    "capability": "openai_gpt4",
    "reason": "Need GPT-4 for complex reasoning"
})
```

**Workflow:**
1. Agent submits request
2. Human reviews via dashboard/CLI
3. Human provisions if approved
4. Agent notified via event log

**Why this matters:**
- Creates observable demand
- Human controls paid resources
- Agents express needs without blocking

**No Plan Yet.** Changes needed:
- `genesis_capability_requests` artifact
- Request storage and listing
- Dashboard/CLI for human review
- Event log integration

---

### 31. Resource Measurement Implementation

**Current:** Only LLM tokens and disk are tracked. Memory not measured per-agent.

**Target:** Each resource tracked in its natural unit. Docker enforces real limits.

**Resource Categories:**

| Category | Behavior | Examples |
|----------|----------|----------|
| Depletable | Once spent, gone forever | LLM API budget ($) |
| Allocatable | Quota, reclaimable | Disk (bytes), Memory (bytes) |
| Renewable | Rate-limited via token bucket | CPU (CPU-seconds), LLM rate (TPM) |

**Resources and Natural Units:**

| Resource | Category | Unit | Constraint |
|----------|----------|------|------------|
| LLM API $ | Depletable | USD | Budget exhaustion stops LLM calls |
| LLM rate limit | Renewable | tokens/min | Provider's TPM limit |
| CPU | Renewable | CPU-seconds | Docker --cpus limit |
| Memory | Allocatable | bytes | Docker --memory limit |
| Disk | Allocatable | bytes | Docker --storage-opt |

**Key Insight:** Docker limits container-level; we track per-agent. Quotas are tradeable.

**Per-Agent Memory Tracking:**

```python
import tracemalloc

def execute_action(agent_id: str, action: Action) -> Result:
    tracemalloc.start()
    try:
        result = execute(action)
    finally:
        current, peak = tracemalloc.get_traced_memory()
        tracemalloc.stop()

    # Track in bytes, not abstract "compute"
    ledger.track(agent_id, "memory_bytes", peak)
    return result
```

**Per-Agent CPU Tracking:**

```python
import resource
import multiprocessing

def execute_in_worker(agent_id: str, action: Action) -> tuple[Result, float]:
    before = resource.getrusage(resource.RUSAGE_SELF)
    result = execute(action)
    after = resource.getrusage(resource.RUSAGE_SELF)
    cpu_seconds = (after.ru_utime - before.ru_utime) + (after.ru_stime - before.ru_stime)
    return result, cpu_seconds

# Fixed pool size (8-16 workers), not per-agent
pool = multiprocessing.Pool(processes=8)
result, cpu_seconds = pool.apply(execute_in_worker, (agent_id, action))
```

**Why worker pool + getrusage:**
- Captures ALL threads (PyTorch, NumPy internal threads)
- Not gameable - kernel tracks every CPU cycle
- Scalable - pool size independent of agent count

**Local LLM Support:**
- CPU-only (llama.cpp): Captured by worker pool automatically
- GPU-based (vLLM): Model server pattern + GPU tracking via nvidia-smi

**Why High Priority:**
- Can't enforce scarcity without measurement
- Agents can't make economic decisions without knowing costs
- Foundation for all resource-based behavior

**Depends On:** #1 Rate Allocation (for renewable resource tracking)

**No Plan Yet.** Changes needed:
- Implement worker pool with `multiprocessing.Pool`
- Wrap action execution with `resource.getrusage()` measurement
- Add `tracemalloc` for per-agent memory tracking
- Ledger support for CPU-seconds and memory bytes
- Docker compose config for resource limits
- (Future) GPU tracking via nvidia-smi/pynvml for local GPU LLMs

---

## Completed Gaps

### invoke() in Executor
**Completed:** 2026-01-11 by CC-3

Added `execute_with_invoke()` method to executor. Injects `invoke(artifact_id, *args)` function into execution namespace. Supports recursive invocation with max depth 5.

### AGENT_HANDBOOK.md Errors
**Completed:** 2026-01-11 by CC-3

Fixed terminology errors, added invoke() documentation, updated failure states table.

Updated resource model to match current implementation:
- Removed "LLM API $" and "frozen" (target architecture)
- Changed to "Compute" that "resets each tick" (current)
- Added note about Gap #12 for future per-agent budgets
- Updated trading example to use compute instead of llm_budget

---

## Documentation Issues

### ~~current/resources.md Stale Content~~ RESOLVED

**Resolved:** 2026-01-11 by CC-3

Reviewed current/resources.md - no references to `resource_policy`. Updated all line number references to use function names instead (Gap #13 partial fix). Content accurately describes current implementation.

---

### ~~Agent Prompts vs genesis_handbook Consistency~~ RESOLVED

**Resolved:** 2026-01-11 by CC-3

Agent prompts were incorrectly describing target architecture ("LLM API $", "freeze until acquire"). Updated all 5 prompts to match current implementation (compute per-tick, resets each tick), aligning with genesis_handbook.

---

## Testing Gaps

### ~~invoke() Has No Tests~~ RESOLVED

**Resolved:** 2026-01-11 by CC-3

Added `tests/test_invoke.py` with 10 tests covering:
- Basic invoke() call
- Recursive invoke() (depth tracking)
- Max depth exceeded error
- Price payment through invoke chain
- Error propagation
- Permission checks
- No payment on failure

---

## Known Bugs

### ~~Escrow Test Substring Mismatch~~ RESOLVED

**Resolved:** 2026-01-11 by CC-3

Updated test to expect `"transfer_ownership"` (with underscore) to match actual error message.

---

## References

| Doc | Purpose |
|-----|---------|
| [current/](current/) | What IS implemented |
| [target/](target/) | What we WANT |
| [plans/](../plans/) | HOW to close gaps |
| [DESIGN_CLARIFICATIONS.md](../DESIGN_CLARIFICATIONS.md) | WHY decisions were made |
