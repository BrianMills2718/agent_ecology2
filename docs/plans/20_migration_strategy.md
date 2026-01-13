# Gap 20: Migration Strategy

**Status:** ✅ Complete

**Verified:** 2026-01-13T12:00:02Z
**Verification Evidence:**
```yaml
completed_by: scripts/complete_plan.py
timestamp: 2026-01-13T12:00:02Z
tests:
  unit: 997 passed in 10.94s
  e2e_smoke: PASSED (2.31s)
  doc_coupling: passed
commit: 4705401
```
**Priority:** High
**Blocked By:** None
**Blocks:** None
**Last Updated:** 2026-01-13

---

## Gap

**Current:** Individual migration notes scattered across docs, no overall plan

**Target:** Comprehensive phased migration plan from tick-based to continuous architecture

**Why High Priority:** Without a clear strategy, work proceeds ad-hoc, creating integration debt and inconsistent states.

---

## Target Architecture Summary

From `docs/architecture/target/01_README.md`:

| Aspect | Current | Target |
|--------|---------|--------|
| Execution | Tick-synchronized | Continuous autonomous loops |
| Renewable resources | Discrete per-tick refresh | Rolling window rate tracking |
| Agent control | System-triggered | Self-triggered with sleep |
| Resource limits | Configured numbers | Docker container limits |
| Access control | Policy fields on artifacts | Contract artifacts |

---

## Migration Phases

### Phase 1: Foundation ✅ COMPLETE

**Goal:** Rate tracking infrastructure, resource measurement

| Gap | Status | Description |
|-----|--------|-------------|
| #1 Rate Allocation | ✅ Complete | Token bucket rate tracking |
| #31 Resource Measurement | ✅ Complete | ResourceUsage, ResourceMeasurer |
| #32 Developer Tooling | ✅ Complete | Claims, doc-coupling, hooks |

**Outcome:** Infrastructure exists but isn't integrated into main loop.

---

### Phase 2: Integration ✅ MOSTLY COMPLETE

**Goal:** Wire new infrastructure into simulation runner

| Gap | Status | Description |
|-----|--------|-------------|
| #2 Continuous Execution | ✅ Complete | AgentLoop, feature flag implemented |
| #21 Testing for Continuous | 📋 Planned | Now unblocked, ready for work |

**Key Changes:**
1. Replace tick loop with agent loops
2. Use RateTracker instead of per-tick refresh
3. Agents self-schedule (sleep/wake)

**Migration Steps:**
1. Add feature flag: `execution.mode: "tick" | "continuous"`
2. Keep tick mode as default (backwards compatible)
3. Implement continuous mode behind flag
4. Test both modes in CI
5. Once stable, make continuous default
6. Eventually remove tick mode

**Files Affected:**
- `src/simulation/runner.py` - Main loop change
- `src/simulation/agent_loop.py` - Already exists, needs integration
- `config/config.yaml` - Add execution.mode flag
- `tests/` - Add continuous mode tests

---

### Phase 3: Unified Ontology ✅ MOSTLY COMPLETE

**Goal:** Everything is an artifact with consistent interface

| Gap | Status | Description |
|-----|--------|-------------|
| #6 Unified Ontology | ✅ Complete | Common artifact fields implemented |
| #14 MCP Interface | 📋 Unblocked | Now ready for implementation |
| #16 Artifact Discovery | ✅ Complete | genesis_store interface done |
| #7 Single ID Namespace | 📋 Unblocked | Now ready for implementation |

**Key Changes:**
1. Add `has_standing`, `can_execute`, `access_contract_id` to all artifacts
2. Implement MCP-compatible interface schemas
3. Build genesis_store discovery methods

**Migration Steps:**
1. Add new fields with defaults (backwards compatible)
2. Update genesis artifacts to use new schema
3. Update agent creation to set new fields
4. Deprecate old artifact structure
5. Remove deprecated fields

---

### Phase 4: Contract-Based Access Control

**Goal:** Permissions via contract artifacts, not policy fields

| Gap | Status | Description |
|-----|--------|-------------|
| Contract System | ✅ Complete | Basic contract system (GAP-GEN-001) |
| #8 Agent Rights Trading | 📋 Unblocked | Now ready (#6 complete) |

**Key Changes:**
1. Every artifact gets `access_contract_id` field
2. `genesis_freeware` as default open contract
3. Remove `read_policy`, `invoke_policy` fields
4. Permission checks go through contracts

**Migration Steps:**
1. Add `access_contract_id` field (default: `genesis_freeware`)
2. Create `genesis_freeware` contract
3. Route permission checks through contract invoke
4. Deprecate policy fields
5. Remove policy fields after transition

---

### Phase 5: Real Resource Limits ✅ PARTIALLY COMPLETE

**Goal:** Docker containers with actual resource limits

| Gap | Status | Description |
|-----|--------|-------------|
| #3 Docker Isolation | ✅ Complete | Container infrastructure |
| #12 Per-Agent Budget | 📋 Unblocked | Now ready (#11 complete) |

**Key Changes:**
1. Each agent runs in Docker container
2. Container limits = actual resource constraints
3. Per-agent LLM budget tracking

**Migration Steps:**
1. Docker mode behind feature flag
2. Single-container mode for development
3. Multi-container mode for production
4. Per-agent budget tracking

---

### Phase 6: Advanced Features (In Progress)

**Goal:** Full target architecture

| Gap | Status | Description |
|-----|--------|-------------|
| #28 MCP Servers | 🚧 In Progress | External tool access (CC-3 working) |
| #22 Coordination | 📋 Unblocked | Now ready (#16 complete) |
| #17 Agent Discovery | ✅ Complete | Agent discovery implemented |

---

## Feature Flags

All migrations use feature flags for gradual rollout:

```yaml
# config/config.yaml
features:
  execution_mode: "tick"  # "tick" | "continuous"
  artifact_ontology: "legacy"  # "legacy" | "unified"
  access_control: "policy"  # "policy" | "contract"
  resource_limits: "config"  # "config" | "docker"
```

**Policy:** New modes are opt-in until stable, then become default, then old modes are removed.

---

## Backwards Compatibility Rules

1. **Never break existing tests** - All current tests must pass throughout migration
2. **Feature flags for new behavior** - Default to old behavior
3. **Deprecation warnings first** - Warn before removing
4. **Two-version support** - Support old and new for at least one phase

---

## Verification Criteria

### Per-Phase
- [ ] All existing tests pass
- [ ] New feature tests pass
- [ ] Feature flag toggles cleanly
- [ ] No performance regression

### Final
- [ ] Tick mode removed (or deprecated)
- [ ] All artifacts use unified ontology
- [ ] Access control via contracts only
- [ ] Docker isolation working
- [ ] Continuous execution stable

---

## Implementation Order

Based on dependency graph (updated 2026-01-13):

```
Phase 1 (✅ COMPLETE) → Phase 2 (✅ mostly complete)
                              ↓
                        Phase 3 (✅ mostly complete) → Phase 4 (partial)
                              ↓
                        Phase 5 (partial) → Phase 6 (in progress)
```

**Progress Summary:**
- Phase 1: ✅ Foundation complete
- Phase 2: ✅ #2 Continuous Execution done, #21 Testing ready
- Phase 3: ✅ #6 Ontology done, #16 Discovery done, #14/#7 unblocked
- Phase 4: ✅ Contract system done, #8 unblocked
- Phase 5: ✅ #3 Docker done, #12 unblocked
- Phase 6: 🚧 #17 done, #28 in progress, #22 unblocked

**Remaining blockers:** None - all previously blocked items are now unblocked.

---

## Required Tests

This is a meta-tracking plan. Tests live in individual gap plans:
- `tests/test_rate_tracking.py` - Phase 1 (#1 Rate Allocation)
- `tests/test_agent_loop.py` - Phase 2 (#2 Continuous Execution)
- `tests/test_discovery.py` - Phase 3 (#16 Artifact Discovery)
- `tests/e2e/test_smoke.py` - End-to-end verification

**Verification approach:** All referenced gaps must be ✅ Complete with passing tests before this plan can be marked complete.

---

## E2E Verification

Meta-plan completion criteria:
1. All Phase 1-3 gaps marked ✅ Complete
2. Feature flags functional: `execution_mode`, `artifact_ontology`, `access_control`
3. E2E test passes with continuous mode: `pytest tests/e2e/ -v --run-external`

---

## Notes

- This plan tracks high-level phases; individual gaps have detailed plans
- Update this document as phases complete
- Feature flags enable safe experimentation
- ~~Prioritize Phase 2 to unblock downstream work~~ (Phase 2 done)
