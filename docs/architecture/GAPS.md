# Architecture Gaps

Prioritized gaps between current implementation and target architecture.

**Last verified:** 2026-01-11

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
| 1 | Token Bucket | **High** | 📋 Planned | [token_bucket.md](../plans/token_bucket.md) | #2, #4 |
| 2 | Continuous Execution | **High** | ⏸️ Blocked | [continuous_execution.md](../plans/continuous_execution.md) | - |
| 3 | Docker Isolation | Medium | 📋 Planned | [docker_isolation.md](../plans/docker_isolation.md) | - |
| 4 | Compute Debt Model | Medium | ❌ No Plan | - | - |
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

---

## High Priority Gaps

### 1. Token Bucket for Flow Resources

**Current:** Discrete per-tick refresh. Flow resources reset to quota each tick.

**Target:** Rolling window accumulation. Continuous accumulation up to capacity, debt allowed.

**Why High Priority:** Foundation for continuous execution. Without token bucket, can't remove tick-based refresh.

**Plan:** [docs/plans/token_bucket.md](../plans/token_bucket.md)

**Key Changes:**
- New `TokenBucket` class in `src/world/token_bucket.py`
- Replace `per_tick` config with `rate` + `capacity`
- Remove flow reset from `advance_tick()`
- Allow negative balances (debt)

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

### 4. Compute Debt Model

**Current:** No debt allowed. Actions fail if insufficient resources.

**Target:** Debt allowed for compute. Negative balance = can't act until accumulated out.

**Depends On:** #1 Token Bucket

**No Plan Yet.** Partially covered by token bucket plan (debt is built into TokenBucket class).

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
| `search(query)` | 1 | Search artifacts by description/interface |
| `create(config)` | 5 | Create new artifact (for spawning agents) |

**Depends On:** #6 Unified Artifact Ontology

**No Plan Yet.** Changes needed:
- Promote ArtifactStore to genesis artifact
- Add discovery methods
- Define metadata schema (what's queryable without reading content)
- Consider privacy (some artifacts may not want to be discoverable)

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
