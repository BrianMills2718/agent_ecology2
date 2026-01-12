# Implementation Plans

Master index of all gaps and their implementation plans.

**Last verified:** 2026-01-12

---

## How to Use

1. **Find a gap** - Browse the summary table below
2. **Read the plan** - Click through to the detailed plan file
3. **Implement** - Follow the steps in the plan
4. **Update status** - Mark complete in the plan file AND this index
5. **Update current/** - Document the new reality in `docs/architecture/current/`

### Status Key

| Status | Meaning |
|--------|---------|
| 📋 Planned | Has implementation plan, ready to start |
| 🚧 In Progress | Being implemented (see CLAUDE.md for CC-ID) |
| ⏸️ Blocked | Waiting on dependency |
| ❌ Needs Plan | Gap identified, needs design work |
| ✅ Complete | Implemented, docs updated |

---

## Gap Summary

| # | Gap | Priority | Status | Blocks |
|---|-----|----------|--------|--------|
| 1 | [Rate Allocation](01_rate_allocation.md) | **High** | 📋 Planned | #2, #31 |
| 2 | [Continuous Execution](02_continuous_execution.md) | **High** | ⏸️ Blocked | #21 |
| 3 | [Docker Isolation](03_docker_isolation.md) | Medium | 📋 Planned | - |
| 4 | ~~Compute Debt Model~~ | - | ✅ Superseded | - |
| 5 | [Oracle Anytime Bidding](05_oracle_anytime.md) | Medium | ❌ Needs Plan | - |
| 6 | [Unified Artifact Ontology](06_unified_ontology.md) | Medium | ❌ Needs Plan | #7,#8,#14,#16 |
| 7 | [Single ID Namespace](07_single_id_namespace.md) | Low | ⏸️ Blocked | - |
| 8 | [Agent Rights Trading](08_agent_rights.md) | Low | ⏸️ Blocked | - |
| 9 | [Scrip Debt Contracts](09_scrip_debt.md) | Low | ❌ Needs Plan | - |
| 10 | [Memory Persistence](10_memory_persistence.md) | Low | ❌ Needs Plan | - |
| 11 | [Terminology Cleanup](11_terminology.md) | Medium | 📋 Planned | #12 |
| 12 | [Per-Agent LLM Budget](12_per_agent_budget.md) | Medium | ⏸️ Blocked | - |
| 13 | [Doc Line Number Refs](13_doc_line_refs.md) | Low | ❌ Needs Plan | - |
| 14 | [MCP-Style Artifact Interface](14_mcp_interface.md) | Medium | ⏸️ Blocked | - |
| 15 | [invoke() Genesis Support](15_invoke_genesis.md) | Medium | ❌ Needs Plan | - |
| 16 | [Artifact Discovery](16_artifact_discovery.md) | **High** | ⏸️ Blocked | #17,#22 |
| 17 | [Agent Discovery](17_agent_discovery.md) | Medium | ⏸️ Blocked | - |
| 18 | [Dangling Reference Handling](18_dangling_refs.md) | Medium | ❌ Needs Plan | - |
| 19 | [Agent-to-Agent Threat Model](19_threat_model.md) | Medium | ❌ Needs Plan | - |
| 20 | [Migration Strategy](20_migration_strategy.md) | **High** | ❌ Needs Plan | - |
| 21 | [Testing for Continuous](21_continuous_testing.md) | Medium | ⏸️ Blocked | - |
| 22 | [Coordination Primitives](22_coordination.md) | Medium | ⏸️ Blocked | - |
| 23 | [Error Response Conventions](23_error_conventions.md) | Low | ❌ Needs Plan | - |
| 24 | [Ecosystem Health KPIs](24_health_kpis.md) | Medium | ❌ Needs Plan | #25 |
| 25 | [System Auditor Agent](25_system_auditor.md) | Low | ⏸️ Blocked | - |
| 26 | [Vulture Observability](26_vulture_observability.md) | Medium | ❌ Needs Plan | - |
| 27 | [Invocation Registry](27_invocation_registry.md) | Medium | ❌ Needs Plan | - |
| 28 | [Pre-seeded MCP Servers](28_mcp_servers.md) | **High** | ❌ Needs Plan | - |
| 29 | [Library Installation](29_package_manager.md) | Medium | ❌ Needs Plan | - |
| 30 | [Capability Request System](30_capability_requests.md) | Medium | ❌ Needs Plan | - |
| 31 | [Resource Measurement](31_resource_measurement.md) | **High** | ⏸️ Blocked | - |

---

## Dependency Graph

```
#1 Rate Allocation (High)
├── blocks #2 Continuous Execution
└── blocks #31 Resource Measurement

#2 Continuous Execution (High)
└── blocks #21 Testing/Debugging

#6 Unified Ontology (Medium)
├── blocks #7 Single ID Namespace
├── blocks #8 Agent Rights Trading
├── blocks #14 MCP Interface
└── blocks #16 Artifact Discovery
      ├── blocks #17 Agent Discovery
      └── blocks #22 Coordination Primitives

#11 Terminology (Medium)
└── blocks #12 Per-Agent Budget

#24 Ecosystem KPIs (Medium)
└── blocks #25 System Auditor
```

---

## Implementation Phases

### Phase 1: Foundation (Current Focus)
1. **#1 Rate Allocation** - Token bucket for flow resources
2. **#11 Terminology** - Clean up naming confusion
3. **#3 Docker Isolation** - Real resource limits

### Phase 2: Continuous Execution
4. **#2 Continuous Execution** - Remove tick dependency
5. **#21 Testing for Continuous** - New testing strategy
6. **#31 Resource Measurement** - Track all resources

### Phase 3: Unified Ontology
7. **#6 Unified Ontology** - Everything is an artifact
8. **#16 Artifact Discovery** - genesis_store
9. **#14 MCP Interface** - Artifact schemas

### Phase 4: Advanced Features
10. **#28 MCP Servers** - External capabilities
11. **#12 Per-Agent Budget** - Individual LLM budgets
12. **#22 Coordination** - Agent collaboration

---

## Completed Gaps

| # | Gap | Completed | By |
|---|-----|-----------|-----|
| 4 | Compute Debt Model | 2026-01-11 | Superseded by #1 |
| - | invoke() in Executor | 2026-01-11 | CC-3 |
| - | AGENT_HANDBOOK Fixes | 2026-01-11 | CC-3 |

---

## Plan Template

When creating a new plan file:

```markdown
# Gap N: [Name]

**Status:** ❌ Needs Plan
**Priority:** High | Medium | Low
**Blocked By:** #X, #Y
**Blocks:** #A, #B

---

## Gap

**Current:** What exists now

**Target:** What we want

**Why [Priority]:** Why this priority level

---

## Plan

### Changes Required
| File | Change |
|------|--------|
| ... | ... |

### Steps
1. Step one
2. Step two

---

## Verification
- [ ] Tests pass
- [ ] Docs updated
- [ ] [Specific criteria]

---

## Notes
[Design decisions, alternatives considered, etc.]
```

---

## References

| Doc | Purpose |
|-----|---------|
| `docs/architecture/current/` | What IS implemented |
| `docs/architecture/target/` | What we WANT |
| `docs/DESIGN_CLARIFICATIONS.md` | WHY decisions were made |
| `docs/GLOSSARY.md` | Canonical terminology |
