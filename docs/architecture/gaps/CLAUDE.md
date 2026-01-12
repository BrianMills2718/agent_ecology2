# Gap Tracking System

**Single source of truth for all implementation gaps.**

Last verified: 2026-01-12

---

## Overview

| Metric | Count |
|--------|-------|
| Total gaps | 142 |
| Completed | 14 |
| In Progress | 0 |
| Remaining | 128 |

---

## How to Use This System

### For Implementers

1. **Find work** - Browse epics or workstreams below
2. **Claim task** - Update status to 🚧, add CC-ID
3. **Read gap detail** - Check workstream YAML for full spec
4. **Read/create plan** - Check `plans/` for implementation details
5. **Implement** - Follow TDD workflow below
6. **Mark complete** - Update status, update architecture docs

### Status Key

| Status | Meaning |
|--------|---------|
| ✅ Complete | Implemented, tests pass, docs updated |
| 🚧 In Progress | Being implemented (see CC-ID) |
| 📋 Ready | Has plan, ready to start |
| ⏸️ Blocked | Waiting on dependency |
| ❌ Needs Plan | Gap identified, needs design work |

### TDD Workflow

1. Read gap definition in workstream YAML
2. Write tests first (they should fail)
3. Implement until tests pass
4. Update `docs/architecture/current/`
5. Mark gap complete

---

## Phase Status

| Phase | Status | Gaps |
|-------|--------|------|
| Phase 1: Foundations | ✅ Complete | GAP-RES-001, GAP-GEN-001, GAP-EXEC-001, GAP-AGENT-001 |
| Phase 2: Integration | ✅ Complete | INT-001 through INT-004, CAP-001 through CAP-006 |
| Phase 3: Core Systems | ❌ Not Started | See epics below |
| Phase 4: Advanced | ❌ Not Started | See epics below |

---

## Dependency Graph

```
Epic 1: Rate Allocation (High) ✅
├── blocks Epic 2: Continuous Execution
└── blocks Epic 31: Resource Measurement

Epic 2: Continuous Execution (High)
└── blocks Epic 21: Testing for Continuous

Epic 6: Unified Ontology (Medium)
├── blocks Epic 7: Single ID Namespace
├── blocks Epic 8: Agent Rights Trading
├── blocks Epic 14: MCP Interface
└── blocks Epic 16: Artifact Discovery
      ├── blocks Epic 17: Agent Discovery
      └── blocks Epic 22: Coordination Primitives

Epic 11: Terminology (Medium)
└── blocks Epic 12: Per-Agent Budget

Epic 24: Ecosystem KPIs (Medium)
└── blocks Epic 25: System Auditor
```

---

## Completed Work History

| Gap/Task | Completed | By |
|----------|-----------|-----|
| Compute Debt Model | 2026-01-11 | Superseded by Epic 1 |
| invoke() in Executor | 2026-01-11 | CC-3 |
| AGENT_HANDBOOK Fixes | 2026-01-11 | CC-3 |
| GAP-RES-001 RateTracker | 2026-01-12 | Phase 1 |
| GAP-GEN-001 Contract System | 2026-01-12 | Phase 1 |
| GAP-EXEC-001 Autonomous Loops | 2026-01-12 | Phase 1 |
| GAP-AGENT-001 Unified Ontology Fields | 2026-01-12 | Phase 1 |
| Phase 2 Integration (10 tasks) | 2026-01-12 | Phase 2 |

---

## Deferred Items

From Phase 1/2 review. Address in future work:

| Item | Description | Location |
|------|-------------|----------|
| AgentProtocol asymmetry | `AgentProtocol.alive` is property but `AgentLoop.is_alive` is Callable | `src/simulation/agent_loop.py` |
| Architecture docs for new files | Add current/ docs for rate_tracker.py, agent_loop.py | `docs/architecture/current/` |

---

## Epics (31 High-Level Features)

Epics group related sub-gaps into user-facing features.

### Epic 1: Rate Allocation ✅
**Priority:** High | **Status:** Complete

Rate-limited resource allocation using rolling windows.

| Sub-gap | Name | Status |
|---------|------|--------|
| GAP-RES-001 | RateTracker class | ✅ |
| GAP-RES-018 | Remove tick-based reset | ✅ |
| GAP-RES-019 | Action blocking on exhaustion | ✅ |

---

### Epic 2: Continuous Execution 🚧
**Priority:** High | **Status:** Partial (module done, integration pending)

Transform from tick-synchronized to continuous autonomous loops.

| Sub-gap | Name | Status |
|---------|------|--------|
| GAP-EXEC-001 | Autonomous agent loops | ✅ |
| GAP-EXEC-002 | Agent sleep system | ❌ |
| GAP-EXEC-003 | Rate limiting integration | ✅ |
| GAP-EXEC-017 | Worker process isolation | ❌ |

**Note:** AgentLoop module exists but tick-based runner still active. Full transformation requires removing ticks.

---

### Epic 3: Docker Isolation 📋
**Priority:** Medium | **Status:** Ready

Container-based process isolation for agents.

| Sub-gap | Name | Status |
|---------|------|--------|
| GAP-INFRA-001 | Docker containerization | ❌ |
| GAP-INFRA-002 | Resource limits via cgroups | ❌ |
| GAP-INFRA-003 | Network isolation | ❌ |

---

### Epic 5: Oracle Anytime Bidding ❌
**Priority:** Medium | **Status:** Needs Plan

Accept bids anytime, resolve on time-based schedule.

| Sub-gap | Name | Status |
|---------|------|--------|
| GAP-GEN-020 | Anytime bidding | ❌ |
| GAP-GEN-021 | Time-based resolution | ❌ |

---

### Epic 6: Unified Ontology 🚧
**Priority:** Medium | **Status:** Partial (fields done, storage pending)

Everything is an artifact with properties.

| Sub-gap | Name | Status |
|---------|------|--------|
| GAP-AGENT-001 | has_standing, can_execute fields | ✅ |
| GAP-AGENT-002 | Agent stored as artifact | ❌ |
| GAP-AGENT-006 | Memory as tradeable artifact | ✅ |
| GAP-ART-001 | access_contract_id field | ✅ |

**Note:** Artifact fields added. Agents not yet stored as artifacts.

---

### Epic 7: Single ID Namespace ⏸️
**Priority:** Low | **Status:** Blocked by Epic 6

Unified namespace for all entity types.

| Sub-gap | Name | Status |
|---------|------|--------|
| GAP-AGENT-003 | Unified ID generation | ❌ |
| GAP-ART-002 | ID collision prevention | ❌ |

---

### Epic 8: Agent Rights Trading ⏸️
**Priority:** Low | **Status:** Blocked by Epic 6

Trade agent ownership and capabilities.

| Sub-gap | Name | Status |
|---------|------|--------|
| GAP-AGENT-004 | Agent ownership transfer | ❌ |
| GAP-AGENT-005 | Capability delegation | ❌ |

---

### Epic 9: Scrip Debt Contracts ❌
**Priority:** Low | **Status:** Needs Plan

Contract-based debt and lending.

| Sub-gap | Name | Status |
|---------|------|--------|
| GAP-GEN-022 | Debt contract type | ❌ |
| GAP-GEN-023 | Interest calculation | ❌ |

---

### Epic 10: Memory Persistence ❌
**Priority:** Low | **Status:** Needs Plan

Persistent agent memory across sessions.

| Sub-gap | Name | Status |
|---------|------|--------|
| GAP-AGENT-007 | Memory serialization | ❌ |
| GAP-AGENT-008 | Memory restoration | ❌ |

---

### Epic 11: Terminology Cleanup 📋
**Priority:** Medium | **Status:** Ready

Consistent naming across codebase.

| Sub-gap | Name | Status |
|---------|------|--------|
| GAP-INFRA-015 | Rename flow→compute | ❌ |
| GAP-INFRA-016 | Rename stock→budget | ❌ |
| GAP-INFRA-017 | Update all references | ❌ |

---

### Epic 12: Per-Agent LLM Budget ⏸️
**Priority:** Medium | **Status:** Blocked by Epic 11

Individual API budget per agent.

| Sub-gap | Name | Status |
|---------|------|--------|
| GAP-RES-009 | Per-agent budget tracking | ❌ |
| GAP-RES-010 | Budget transfer | ❌ |

---

### Epic 14: MCP-Style Artifact Interface ⏸️
**Priority:** Medium | **Status:** Blocked by Epic 6

Standard interface schema for artifacts.

| Sub-gap | Name | Status |
|---------|------|--------|
| GAP-ART-003 | Schema definition format | ❌ |
| GAP-ART-004 | Schema validation | ❌ |

---

### Epic 16: Artifact Discovery ⏸️
**Priority:** High | **Status:** Blocked by Epic 6

genesis_store with list/search/browse.

| Sub-gap | Name | Status |
|---------|------|--------|
| GAP-GEN-024 | genesis_store artifact | ❌ |
| GAP-GEN-025 | List/search methods | ❌ |

---

### Epic 17: Agent Discovery ⏸️
**Priority:** Medium | **Status:** Blocked by Epic 16

Discover other agents in the system.

| Sub-gap | Name | Status |
|---------|------|--------|
| GAP-AGENT-010 | Agent listing | ❌ |
| GAP-AGENT-011 | Agent capability query | ❌ |

---

### Epic 19: Agent-to-Agent Threat Model ❌
**Priority:** Medium | **Status:** Needs Plan

Security model for agent interactions.

| Sub-gap | Name | Status |
|---------|------|--------|
| GAP-INFRA-008 | Threat model document | ❌ |
| GAP-INFRA-009 | Security test suite | ❌ |

---

### Epic 20: Migration Strategy ❌
**Priority:** High | **Status:** Needs Plan

Graceful upgrade path for breaking changes.

| Sub-gap | Name | Status |
|---------|------|--------|
| GAP-INFRA-010 | Version tracking | ❌ |
| GAP-INFRA-011 | Migration scripts | ❌ |

---

### Epic 21: Testing for Continuous ⏸️
**Priority:** Medium | **Status:** Blocked by Epic 2

Test infrastructure for continuous execution.

| Sub-gap | Name | Status |
|---------|------|--------|
| GAP-EXEC-018 | Async test fixtures | ❌ |
| GAP-EXEC-019 | Race condition tests | ❌ |

---

### Epic 22: Coordination Primitives ⏸️
**Priority:** Medium | **Status:** Blocked by Epic 16

Agent coordination mechanisms.

| Sub-gap | Name | Status |
|---------|------|--------|
| GAP-AGENT-012 | Broadcast messages | ❌ |
| GAP-AGENT-013 | Request/response pattern | ❌ |

---

### Epic 24: Ecosystem Health KPIs ❌
**Priority:** Medium | **Status:** Needs Plan

Metrics for ecosystem health.

| Sub-gap | Name | Status |
|---------|------|--------|
| GAP-INFRA-012 | KPI definitions | ❌ |
| GAP-INFRA-013 | Dashboard integration | ❌ |

---

### Epic 25: System Auditor Agent ⏸️
**Priority:** Low | **Status:** Blocked by Epic 24

Agent that monitors ecosystem health.

| Sub-gap | Name | Status |
|---------|------|--------|
| GAP-AGENT-014 | Auditor agent implementation | ❌ |

---

### Epic 28: Pre-seeded MCP Servers ❌
**Priority:** High | **Status:** Needs Plan

Genesis artifacts wrapping MCP servers.

| Sub-gap | Name | Status |
|---------|------|--------|
| GAP-GEN-026 | MCP protocol adapter | ❌ |
| GAP-GEN-027 | Standard MCP servers | ❌ |

---

### Epic 29: Library Installation ❌
**Priority:** Medium | **Status:** Needs Plan

Agent-installable Python packages.

| Sub-gap | Name | Status |
|---------|------|--------|
| GAP-INFRA-014 | Package sandbox | ❌ |
| GAP-RES-011 | Disk quota for packages | ❌ |

---

### Epic 30: Capability Request System ❌
**Priority:** Medium | **Status:** Needs Plan

Agents request capabilities from genesis.

| Sub-gap | Name | Status |
|---------|------|--------|
| GAP-GEN-028 | Capability request artifact | ❌ |
| GAP-GEN-029 | Request approval flow | ❌ |

---

### Epic 31: Resource Measurement ⏸️
**Priority:** High | **Status:** Blocked by Epic 1

Accurate measurement of all resource types.

| Sub-gap | Name | Status |
|---------|------|--------|
| GAP-RES-012 | CPU time measurement | ❌ |
| GAP-RES-013 | Memory measurement | ❌ |
| GAP-RES-014 | Disk I/O measurement | ❌ |

---

## Workstream Files

Detailed gap definitions organized by component:

| File | Component | Gap Count |
|------|-----------|-----------|
| [ws1_execution_model.yaml](ws1_execution_model.yaml) | Execution Model | 23 |
| [ws2_agents.yaml](ws2_agents.yaml) | Agents | 22 |
| [ws3_resources.yaml](ws3_resources.yaml) | Resources | 30 |
| [ws4_genesis.yaml](ws4_genesis.yaml) | Genesis Artifacts | 27 |
| [ws5_artifacts.yaml](ws5_artifacts.yaml) | Artifacts & Executor | 22 |
| [ws6_infrastructure.yaml](ws6_infrastructure.yaml) | Infrastructure | 18 |

---

## Implementation Plans

Detailed implementation plans for complex gaps:

| Plan | Status | Gaps Covered |
|------|--------|--------------|
| [phase1_gap_res_001_rate_tracker.md](plans/phase1_gap_res_001_rate_tracker.md) | ✅ Complete | GAP-RES-001 |
| [phase1_gap_gen_001_contract_system.md](plans/phase1_gap_gen_001_contract_system.md) | ✅ Complete | GAP-GEN-001 |
| [phase1_gap_exec_001_autonomous_loops.md](plans/phase1_gap_exec_001_autonomous_loops.md) | ✅ Complete | GAP-EXEC-001 |
| [phase1_gap_agent_001_unified_ontology.md](plans/phase1_gap_agent_001_unified_ontology.md) | ✅ Complete | GAP-AGENT-001 |
| [PHASE2_PLAN.md](plans/PHASE2_PLAN.md) | ✅ Complete | INT-001 to INT-004, CAP-001 to CAP-006 |
| [epic03_docker_isolation.md](plans/epic03_docker_isolation.md) | 📋 Ready | GAP-INFRA-001 to 003 |
| [epic11_terminology_cleanup.md](plans/epic11_terminology_cleanup.md) | 📋 Ready | GAP-INFRA-015 to 017 |

---

## CC Coordination

### Active Work

| CC-ID | Epic/Gap | Started | Notes |
|-------|----------|---------|-------|
| (none) | - | - | - |

### Coordination Rules

1. **One task at a time** - Finish or abandon before claiming another
2. **Update this file first** - Claim before starting work
3. **Tests + mypy must pass** - Before marking complete
4. **Review required** - Another CC verifies before final completion

### Review Checklist

- [ ] `pytest tests/` passes
- [ ] `python -m mypy src/ --ignore-missing-imports` passes
- [ ] Code matches gap definition
- [ ] No new silent fallbacks
- [ ] `docs/architecture/current/` updated

---

## Plan Template

When creating a new implementation plan in `plans/`:

```markdown
# Epic N: [Name] / GAP-XXX-NNN: [Name]

**Status:** ❌ Needs Plan
**Priority:** High | Medium | Low
**Epic:** N (if sub-gap)
**Sub-gaps:** GAP-XXX-NNN, GAP-XXX-NNN (if epic)

---

## Gap

**Current:** What exists now

**Target:** What we want

---

## Implementation Steps

### Step 1: ...
### Step 2: ...

---

## Files Affected

| File | Change |
|------|--------|
| ... | ... |

---

## Test Cases

| Test | Description | Expected |
|------|-------------|----------|
| ... | ... | ... |

---

## Acceptance Criteria

- [ ] Criterion 1
- [ ] Criterion 2
- [ ] Tests pass
- [ ] Docs updated
```

---

## References

| Doc | Purpose |
|-----|---------|
| [GAPS_SUMMARY.yaml](GAPS_SUMMARY.yaml) | Overview and metrics |
| [IMPLEMENTATION_PLAN.md](IMPLEMENTATION_PLAN.md) | Phased implementation strategy |
| `docs/architecture/current/` | What IS implemented |
| `docs/architecture/target/` | What we WANT |
| `docs/GLOSSARY.md` | Canonical terminology |
