# Gap 20: Migration Strategy

**Status:** 📋 Planned
**Priority:** High
**Blocked By:** None
**Blocks:** None

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

### Phase 2: Integration (CURRENT)

**Goal:** Wire new infrastructure into simulation runner

| Gap | Status | Description |
|-----|--------|-------------|
| #2 Continuous Execution | ⏸️ In Progress | AgentLoop, remove tick dependency |
| #21 Testing for Continuous | ⏸️ Blocked by #2 | New testing patterns |

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

### Phase 3: Unified Ontology

**Goal:** Everything is an artifact with consistent interface

| Gap | Status | Description |
|-----|--------|-------------|
| #6 Unified Ontology | ❌ In Progress | Common artifact fields |
| #14 MCP Interface | ⏸️ Blocked by #6 | Artifact schemas |
| #16 Artifact Discovery | ⏸️ Blocked by #6 | genesis_store interface |
| #7 Single ID Namespace | ⏸️ Blocked by #6 | Unify agent/artifact IDs |

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
| #5 Contracts | ✅ Complete | Basic contract system |
| #8 Agent Rights Trading | ⏸️ Blocked by #6 | Tradeable capabilities |

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

### Phase 5: Real Resource Limits

**Goal:** Docker containers with actual resource limits

| Gap | Status | Description |
|-----|--------|-------------|
| #3 Docker Isolation | ✅ Complete | Container infrastructure |
| #12 Per-Agent Budget | ⏸️ Blocked by #11 | Individual LLM budgets |

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

### Phase 6: Advanced Features

**Goal:** Full target architecture

| Gap | Status | Description |
|-----|--------|-------------|
| #28 MCP Servers | ❌ Needs Plan | External tool access |
| #22 Coordination | ⏸️ Blocked | Agent collaboration |
| #17 Agent Discovery | ⏸️ Blocked | Find other agents |

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

Based on dependency graph:

```
Phase 1 (✅) → Phase 2 (current)
                    ↓
              Phase 3 → Phase 4
                    ↓
              Phase 5 → Phase 6
```

**Critical path:** Phase 2 (Continuous Execution) unblocks most other work.

---

## Notes

- This plan tracks high-level phases; individual gaps have detailed plans
- Update this document as phases complete
- Feature flags enable safe experimentation
- Prioritize Phase 2 to unblock downstream work
