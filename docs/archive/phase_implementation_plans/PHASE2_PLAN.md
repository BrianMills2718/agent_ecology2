# Phase 2: Integration Plan

**Created:** 2026-01-12
**Status:** Ready to Execute
**Prerequisite:** Phase 1 Complete ✓

---

## Executive Summary

Phase 1 created **standalone modules** (RateTracker, Contracts, AgentLoop, Artifact extensions).
Phase 2 **integrates these modules** into the existing system and adds capabilities that build on them.

**Key Insight:** Several Phase 2 gaps are already partially complete from Phase 1 work.

---

## What Phase 1 Built (Standalone, Not Integrated)

| Module | Location | Status |
|--------|----------|--------|
| RateTracker | `src/world/rate_tracker.py` | Exists, not used by Ledger |
| Contracts | `src/world/contracts.py`, `genesis_contracts.py` | Exists, not used by Executor |
| AgentLoop | `src/simulation/agent_loop.py` | Exists, not used by Runner |
| Artifact Extensions | `src/world/artifacts.py` | Fields exist, Agent not refactored |

---

## Phase 2 Priority Order

### Priority 1: INTEGRATION (Blocking)

These must be done first - they wire Phase 1 modules into the system.

| ID | Task | Complexity | Files | Parallelizable |
|----|------|------------|-------|----------------|
| **INT-001** | Integrate RateTracker into Ledger | M | `ledger.py` | No |
| **INT-002** | Integrate Contracts into Executor | L | `executor.py` | Yes (with INT-001) |
| **INT-003** | Integrate AgentLoop into Runner | L | `runner.py` | Yes (after INT-001) |
| **INT-004** | Refactor Agent to use Artifact backing | M | `agent.py`, `loader.py` | Yes (after INT-002) |

### Priority 2: Core Capabilities (After Integration)

These add new capabilities that depend on integration being complete.

| ID | Gap ID | Task | Complexity | Stream |
|----|--------|------|------------|--------|
| **CAP-001** | GAP-RES-018 | Remove tick-based resource reset | S | Resources |
| **CAP-002** | GAP-EXEC-008 | Add async locks to Ledger | M | Execution |
| **CAP-003** | GAP-ART-008 | Remove owner bypass from Executor | M | Access Control |
| **CAP-004** | GAP-AGENT-006 | Memory as separate artifact | M | Agents |
| **CAP-005** | GAP-RES-019 | Action blocking vs skip on exhaustion | S | Resources |
| **CAP-006** | GAP-GEN-004 | Contract execution environment | L | Access Control |

### Priority 3: Extended Capabilities (Parallel)

Can be done in parallel after Priority 2.

| Stream A: Execution | Stream B: Access Control | Stream C: Resources |
|---------------------|--------------------------|---------------------|
| GAP-AGENT-009: Event bus | GAP-GEN-005: Contract cost model | GAP-RES-002: CPU tracking |
| GAP-EXEC-014: Race resolution | GAP-ART-003: Permission caching | GAP-RES-003: Memory tracking |
| GAP-EXEC-017: Process isolation | GAP-GEN-006: Depth limits | GAP-RES-010: Resource transfer |

---

## Detailed Task Breakdown

### INT-001: Integrate RateTracker into Ledger

**Goal:** Replace tick-based resource refresh with rolling window rate limiting.

**Files:** `src/world/ledger.py`, `src/world/world.py`

**Tasks:**
1. Add `rate_tracker: RateTracker` field to Ledger
2. Initialize RateTracker from config in Ledger.__init__()
3. Replace `reset_compute()` with RateTracker capacity checks
4. Add `check_resource_capacity(agent_id, resource)` method
5. Add `consume_resource(agent_id, resource, amount)` method
6. Update tests to use new methods
7. Keep `reset_compute()` for backward compatibility (deprecated)

**Acceptance Criteria:**
- [ ] Ledger uses RateTracker for renewable resources
- [ ] `check_resource_capacity()` returns bool
- [ ] `consume_resource()` deducts from rolling window
- [ ] Old tick-based reset still works (feature flag)

---

### INT-002: Integrate Contracts into Executor

**Goal:** Use contract system for permission checks instead of inline policy.

**Files:** `src/world/executor.py`

**Tasks:**
1. Import contracts module
2. Add `_get_contract(contract_id)` helper method
3. Modify `_check_permission()` to use contract.check_permission()
4. Handle missing contracts (fall back to freeware)
5. Add `use_contracts` feature flag (default: True)
6. Keep legacy policy check path (for migration)
7. Update tests

**Acceptance Criteria:**
- [ ] Executor calls contract.check_permission() for access checks
- [ ] Genesis contracts work correctly
- [ ] Legacy policy dict still works when use_contracts=False
- [ ] Permission denial includes contract's reason

---

### INT-003: Integrate AgentLoop into Runner

**Goal:** Enable autonomous agent execution alongside tick-based mode.

**Files:** `src/simulation/runner.py`, `src/world/world.py`

**Tasks:**
1. Import AgentLoopManager
2. Add `loop_manager` field to World
3. Add `use_autonomous_loops` feature flag check in Runner
4. Create agent loops in Runner.run() when flag enabled
5. Start all loops instead of tick-based execution
6. Handle graceful shutdown of loops
7. Keep tick-based mode as default

**Acceptance Criteria:**
- [ ] `use_autonomous_loops: true` enables autonomous execution
- [ ] Agents run independent loops
- [ ] Graceful shutdown stops all loops
- [ ] Tick-based mode unchanged when flag is false

---

### INT-004: Refactor Agent to Use Artifact Backing

**Goal:** Agents become runtime wrappers around artifact storage.

**Files:** `src/agents/agent.py`, `src/agents/loader.py`

**Tasks:**
1. Add `artifact: Artifact` field to Agent class
2. Add `Agent.from_artifact(artifact)` class method
3. Modify AgentLoader to create agent artifacts
4. Agent properties (agent_id, config) delegate to artifact
5. Memory stored in separate memory artifact
6. Update tests

**Acceptance Criteria:**
- [ ] Agent wraps an Artifact with is_agent=True
- [ ] Agent.from_artifact() creates runtime from artifact
- [ ] AgentLoader creates artifacts in store
- [ ] Memory artifact linked via memory_artifact_id

---

### CAP-001: Remove Tick-Based Resource Reset

**Goal:** Renewable resources use rolling windows only.

**Files:** `src/world/ledger.py`, `src/simulation/runner.py`

**Tasks:**
1. Remove `reset_compute()` calls from runner
2. Remove `advance_tick()` resource reset logic
3. Resources flow continuously via RateTracker
4. Update config to remove tick-based settings

**Depends on:** INT-001

---

### CAP-002: Add Async Locks to Ledger

**Goal:** Thread-safe ledger operations for concurrent agents.

**Files:** `src/world/ledger.py`

**Tasks:**
1. Add `asyncio.Lock()` for balance operations
2. Wrap transfer_scrip() in async lock
3. Wrap deduct operations in async lock
4. Ensure atomicity of balance changes

**Depends on:** INT-001, INT-003

---

### CAP-003: Remove Owner Bypass from Executor

**Goal:** Contracts become SOLE authority for permissions.

**Files:** `src/world/executor.py`

**Tasks:**
1. Remove `if caller == owner: return True` checks
2. All permission decisions go through contracts
3. Update tests to reflect new behavior
4. Document security implications

**Depends on:** INT-002

---

## Parallelization Strategy

```
                    INT-001 (RateTracker → Ledger)
                              │
              ┌───────────────┼───────────────┐
              ▼               ▼               ▼
        INT-002         INT-003         CAP-001
    (Contracts →     (AgentLoop →     (Remove tick
      Executor)        Runner)          reset)
              │               │
              ▼               ▼
        INT-004         CAP-002
    (Agent →         (Async locks)
     Artifact)              │
              │               │
              ▼               ▼
        CAP-003         CAP-005
    (Remove owner    (Block vs skip)
      bypass)
```

**Wave 1:** INT-001 (blocking - everyone depends on this)
**Wave 2:** INT-002, INT-003, CAP-001 (parallel)
**Wave 3:** INT-004, CAP-002 (parallel)
**Wave 4:** CAP-003, CAP-004, CAP-005, CAP-006 (parallel)
**Wave 5:** Priority 3 streams (highly parallel)

---

## Subagent Dispatch Plan

### Wave 1 (Sequential - Blocking)
```
Subagent: INT-001-rate-tracker-integration
Files: ledger.py, world.py
Est. complexity: M
```

### Wave 2 (3 Parallel)
```
Subagent A: INT-002-contracts-executor
Files: executor.py

Subagent B: INT-003-agent-loop-runner
Files: runner.py, world.py

Subagent C: CAP-001-remove-tick-reset
Files: ledger.py, runner.py
```

### Wave 3 (2 Parallel)
```
Subagent A: INT-004-agent-artifact-refactor
Files: agent.py, loader.py

Subagent B: CAP-002-async-locks
Files: ledger.py
```

### Wave 4 (4 Parallel)
```
Subagent A: CAP-003-remove-owner-bypass
Subagent B: CAP-004-memory-artifact
Subagent C: CAP-005-action-blocking
Subagent D: CAP-006-contract-environment
```

---

## Test Strategy

Each integration task must:
1. Keep existing tests passing (backward compatibility)
2. Add new tests for integrated behavior
3. Add feature flag tests (both modes work)

Run after each wave:
```bash
pytest tests/ -v
python -m mypy src/ --ignore-missing-imports
```

---

## Risk Mitigation

| Risk | Mitigation |
|------|------------|
| Breaking existing behavior | Feature flags default to old behavior |
| Integration conflicts | Wave 1 must complete before Wave 2 |
| Test failures | Run full suite after each task |
| Performance regression | Benchmark before/after integration |

---

## Gaps Already Complete (From Phase 1)

These gaps from the original Phase 2 plan are already done:

| Gap ID | Description | Phase 1 Work |
|--------|-------------|--------------|
| GAP-GEN-003 | Genesis contracts | Created in `genesis_contracts.py` |
| GAP-ART-001 | access_contract_id field | Added to Artifact |
| GAP-ART-002 | has_standing, can_execute | Added to Artifact |
| GAP-EXEC-002 | Agent sleep system | AgentLoop has sleep/wake |
| GAP-ART-006 | Create genesis contracts | Done in Phase 1 |
| GAP-ART-010 | check_permission interface | Done in contracts.py |
| GAP-GEN-002 | check_permission standard | Done in contracts.py |

---

## Next Action

**Start with INT-001** (RateTracker → Ledger integration) as it blocks all other work.

Then dispatch Wave 2 subagents in parallel once INT-001 completes.
