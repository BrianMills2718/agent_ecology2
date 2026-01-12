# Gap Closure Implementation Plan

**Created:** 2026-01-12
**Total Gaps:** 142
**Estimated Phases:** 4

---

## Executive Summary

This plan organizes 142 identified gaps into a phased implementation approach. The goal is to maximize parallelization while respecting dependencies.

---

## Phase Overview

| Phase | Name | Gaps | Focus | Parallelizable |
|-------|------|------|-------|----------------|
| 1 | Foundations | 4 | Core architectural changes | Limited |
| 2 | Core Systems | 12 | Build on foundations | 3 streams |
| 3 | Integration | 40 | Connect systems | 3 streams |
| 4 | Polish | 86 | Remaining gaps | Highly parallel |

---

## Phase 1: Foundations (BLOCKING)

These 4 gaps are foundational. Most other work depends on them.

### GAP-EXEC-001: Autonomous Agent Loops
**Complexity:** XL | **Risk:** High | **Files:** runner.py, agent.py, world.py

Transform from tick-synchronized to continuous autonomous execution.

**Tasks:**
1. Add `agent.alive` flag to Agent class
2. Create `async def agent_loop(agent)` function
3. Remove tick-based triggering from SimulationRunner
4. Implement resource-gated loop continuation
5. Update tests for new execution model

**Acceptance Criteria:**
- [ ] Agents run independently without tick synchronization
- [ ] Agents can start/stop independently
- [ ] Resource exhaustion pauses agent (doesn't crash)

---

### GAP-AGENT-001: Unified Ontology (Agents as Artifacts)
**Complexity:** XL | **Risk:** Medium | **Files:** agent.py, artifacts.py, world.py

Agents become artifacts with `has_standing=true` and `can_execute=true`.

**Tasks:**
1. Add `has_standing` field to Artifact
2. Add `can_execute` field to Artifact
3. Create agent artifacts during initialization
4. Update agent loading to read from artifacts
5. Enable agent trading via artifact transfer

**Acceptance Criteria:**
- [ ] Agents are stored as artifacts
- [ ] Agent ownership can be transferred
- [ ] has_standing/can_execute fields work correctly

---

### GAP-GEN-001: Contract-Based Access Control
**Complexity:** XL | **Risk:** High | **Files:** artifacts.py, genesis.py, executor.py

Replace inline policy dicts with contract references.

**Tasks:**
1. Add `access_contract_id` field to Artifact
2. Define `check_permission(caller, action, target)` interface
3. Implement permission check flow via contract invocation
4. Create migration path from policy dict to contract
5. Update all access checks to use contracts

**Acceptance Criteria:**
- [ ] Artifacts reference contracts for permissions
- [ ] check_permission interface is standard
- [ ] Old policy dicts still work (migration period)

---

### GAP-RES-001: RateTracker Class
**Complexity:** L | **Risk:** Medium | **Files:** ledger.py, rate_tracker.py (new)

Implement rolling window rate limiting instead of tick-based refresh.

**Tasks:**
1. Create RateTracker class with sliding window
2. Implement `has_capacity(agent_id, resource)` method
3. Implement `consume(agent_id, resource, amount)` method
4. Implement `wait_for_capacity()` async method
5. Replace tick-based refresh with rate tracker

**Acceptance Criteria:**
- [ ] Rate limits use rolling windows
- [ ] Agents can check capacity before acting
- [ ] Agents can wait for capacity

---

## Phase 2: Core Systems

After Phase 1 completes, these can be worked in 3 parallel streams.

### Stream A: Execution (8 gaps)
- GAP-EXEC-002: Agent sleep system
- GAP-EXEC-003: Rate limiting with capacity checking
- GAP-EXEC-008: Async locks on Ledger
- GAP-AGENT-002: Autonomous execution loop integration
- GAP-AGENT-006: Memory as separate artifact
- GAP-AGENT-009: Event bus for wake triggers
- GAP-EXEC-014: Artifact-based race resolution
- GAP-EXEC-017: Worker process isolation

### Stream B: Access Control (8 gaps)
- GAP-GEN-003: Genesis contracts (freeware, self_owned, private, public)
- GAP-ART-001: access_contract_id field
- GAP-ART-006: Create genesis contracts
- GAP-ART-010: check_permission interface
- GAP-GEN-002: check_permission interface standard
- GAP-GEN-004: Contract execution environment
- GAP-GEN-005: Contract cost model
- GAP-ART-012: Expand contract namespace

### Stream C: Resources (8 gaps)
- GAP-RES-002: CPU resource tracking
- GAP-RES-003: Memory resource tracking
- GAP-RES-008: ProcessPoolExecutor
- GAP-RES-018: Remove tick-based reset
- GAP-RES-019: Action blocking vs skip
- GAP-RES-010: Generic resource transfer
- GAP-RES-011: estimate_cost() interface
- GAP-RES-020: Invocation cost model

---

## Phase 3: Integration

Connect the systems built in Phase 2.

### Cross-Cutting Concerns
- Remove owner bypass (GAP-ART-008) - requires contract system
- Custom contracts (GAP-GEN-034) - requires contract execution
- Tradeable quotas (GAP-RES-*) - requires rate tracker
- Docker isolation (GAP-INFRA-001) - enables resource measurement

### Oracle Updates
- Anytime bidding (GAP-GEN-020)
- Time-based resolution (GAP-GEN-021)
- Multiple winners (GAP-GEN-022)

### Infrastructure
- PostgreSQL for ledger (GAP-INFRA-006)
- Redis event bus (GAP-INFRA-007)
- Git-backed artifacts (GAP-INFRA-012)

---

## Phase 4: Polish

Remaining 86 gaps - mostly S/M complexity.
Can be highly parallelized across many subagents.

---

## Dependency Graph

```
Phase 1 (Sequential/Limited Parallel)
├── GAP-EXEC-001 (autonomous loops)
├── GAP-AGENT-001 (agents as artifacts)
├── GAP-GEN-001 (contract system)
└── GAP-RES-001 (rate tracker)
         │
         ▼
Phase 2 (3 Parallel Streams)
├── Stream A: Execution ────────┐
├── Stream B: Access Control ───┼── Can run in parallel
└── Stream C: Resources ────────┘
         │
         ▼
Phase 3 (Integration)
├── Cross-cutting concerns
├── Oracle updates
└── Infrastructure
         │
         ▼
Phase 4 (Highly Parallel)
└── 86 remaining gaps
```

---

## Implementation Strategy

### For Phase 1
- Work sequentially or with careful coordination
- Each gap gets a dedicated subagent
- Frequent sync points to manage dependencies

### For Phase 2+
- 3 parallel workstreams
- Each stream gets a dedicated subagent team
- Streams sync at phase boundaries

### Testing Strategy
- Each gap must include tests
- Integration tests at phase boundaries
- Full regression before Phase 4

---

## Risk Mitigation

| Risk | Mitigation |
|------|------------|
| Phase 1 takes too long | Timebox to essential changes only |
| Breaking changes | Feature flags for gradual rollout |
| Test coverage gaps | Require tests with each gap |
| Integration failures | Phase boundary testing |

---

## Next Steps

1. Create detailed task breakdowns for Phase 1 gaps
2. Dispatch subagents for Phase 1 implementation
3. Run tests after each gap completion
4. Proceed to Phase 2 when Phase 1 passes all tests
