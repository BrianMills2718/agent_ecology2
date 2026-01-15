# Implementation Plans

Master index of all gaps and their implementation plans.

**Last verified:** 2026-01-15 (Plan #43 all phases complete)

---

## Quick Start

1. **Find a gap** - Browse table below
2. **Read the plan** - `NN_name.md` for details
3. **Implement** - TDD: write tests first
4. **Complete** - `python scripts/complete_plan.py --plan N`

### Status Key

| Status | Meaning |
|--------|---------|
| 📋 Planned | Ready to implement |
| ✅ Complete | Implemented and verified |
| ❌ Needs Plan | Needs design work |

---

## Gap Summary

| # | Gap | Priority | Status | Blocks |
|---|-----|----------|--------|--------|
| 1 | [Rate Allocation](01_rate_allocation.md) | **High** | ✅ Complete | #2, #31 |
| 2 | [Continuous Execution](02_continuous_execution.md) | **High** | ✅ Complete | #21 |
| 3 | [Docker Isolation](03_docker_isolation.md) | Medium | ✅ Complete | - |
| 4 | ~~Compute Debt Model~~ | - | ✅ Superseded | - |
| 5 | [Oracle Anytime Bidding](05_oracle_anytime.md) | Medium | ✅ Complete | - |
| 6 | [Unified Artifact Ontology](06_unified_ontology.md) | Medium | ✅ Complete | #7,#8,#14,#16 |
| 7 | [Single ID Namespace](07_single_id_namespace.md) | Low | ✅ Complete | - |
| 8 | [Agent Rights Trading](08_agent_rights.md) | Low | ✅ Complete | - |
| 9 | [Scrip Debt Contracts](09_scrip_debt.md) | Low | 📋 Post-V1 | - |
| 10 | [Memory Persistence](10_memory_persistence.md) | Low | 📋 Post-V1 | - |
| 11 | [Terminology Cleanup](11_terminology.md) | Medium | ✅ Complete | #12 |
| 12 | [Per-Agent LLM Budget](12_per_agent_budget.md) | Medium | ✅ Complete | - |
| 13 | [Doc Line Number Refs](13_doc_line_refs.md) | Low | 📋 Post-V1 | - |
| 14 | [Artifact Interface Schema](14_mcp_interface.md) | Medium | ✅ Complete | - |
| 15 | [invoke() Genesis Support](15_invoke_genesis.md) | Medium | 📋 Post-V1 | - |
| 16 | [Artifact Discovery](16_artifact_discovery.md) | **High** | ✅ Complete | #17,#22 |
| 17 | [Agent Discovery](17_agent_discovery.md) | Medium | ✅ Complete | - |
| 18 | [Dangling Reference Handling](18_dangling_refs.md) | Medium | ✅ Complete | - |
| 19 | [Agent-to-Agent Threat Model](19_threat_model.md) | Medium | ✅ Complete | - |
| 20 | [Migration Strategy](20_migration_strategy.md) | **High** | ✅ Complete | - |
| 21 | [Testing for Continuous](21_continuous_testing.md) | Medium | ✅ Complete | - |
| 22 | [Coordination Primitives](22_coordination.md) | Medium | ✅ Complete | - |
| 23 | [Error Response Conventions](23_error_conventions.md) | Low | ✅ Complete | - |
| 24 | [Ecosystem Health KPIs](24_health_kpis.md) | Medium | ✅ Complete | #25 |
| 25 | [System Auditor Agent](25_system_auditor.md) | Low | ✅ Complete | - |
| 26 | [Vulture Observability](26_vulture_observability.md) | Medium | ✅ Complete | - |
| 27 | [Invocation Registry](27_invocation_registry.md) | Medium | ✅ Complete | - |
| 28 | [Pre-seeded MCP Servers](28_mcp_servers.md) | **High** | ✅ Complete | - |
| 29 | [Library Installation](29_package_manager.md) | Medium | ✅ Complete | - |
| 30 | [LLM Budget Trading](30_capability_requests.md) | Medium | 📋 Post-V1 | - |
| 31 | [Resource Measurement](31_resource_measurement.md) | **High** | ✅ Complete | - |
| 32 | [Developer Tooling](32_developer_tooling.md) | **High** | ✅ Complete | - |
| 33 | [ADR Governance](33_adr_governance.md) | **High** | ✅ Complete | - |
| 34 | [Oracle to Mint Rename](34_oracle_mint_rename.md) | Medium | ✅ Complete | - |
| 35 | [Verification Enforcement](35_verification_enforcement.md) | **High** | ✅ Complete | - |
| 36 | [Re-verify Complete Plans](36_reverify_complete_plans.md) | **High** | ✅ Complete | - |
| 37 | [Mandatory Planning + Human Review](37_mandatory_planning_human_review.md) | **High** | ✅ Complete | - |
| 38 | [Meta-Process Simplification](38_meta_process_simplification.md) | **High** | ✅ Complete | - |
| 39 | [Genesis Unprivilege](39_genesis_unprivilege.md) | **High** | ✅ Complete | - |
| 40 | [ActionResult Error Integration](40_actionresult_errors.md) | **High** | ✅ Complete | - |
| 41 | [Meta-Process Enforcement Gaps](41_enforcement_gaps.md) | **Critical** | ✅ Complete | - |
| 42 | [Kernel Quota Primitives](42_kernel_quota_primitives.md) | **High** | ✅ Complete | #1 |
| 43 | [Comprehensive Meta-Enforcement](43_meta_enforcement.md) | **Critical** | ✅ Complete | - |
| 44 | [Genesis Full Unprivilege](44_genesis_full_unprivilege.md) | **High** | ✅ Complete | #42 |
| 45 | [Real E2E Test Requirement](45_real_e2e_requirement.md) | **High** | ✅ Complete | - |
| 46 | [PR Review Coordination](46_review_coordination.md) | **High** | ✅ Complete | - |
| 48 | [CI Optimization](48_ci_optimization.md) | Medium | 📋 Post-V1 | - |
| 49 | [Reasoning in Narrow Waist](49_reasoning_narrow_waist.md) | **High** | ✅ Complete | LLM-native monitoring |
| 50 | [Test Structure Refactor](50_test_structure_refactor.md) | Medium | ✅ Complete | AI navigability |
| 51 | [V1 Acceptance Criteria](51_v1_acceptance.md) | **High** | ✅ Complete | V1 release |
| 52 | [Worktree Session Tracking](52_worktree_session_tracking.md) | Medium | ✅ Complete | - |

---

## TDD Workflow

```bash
# Check what tests to write
python scripts/check_plan_tests.py --plan N --tdd

# Run tests for a plan
python scripts/check_plan_tests.py --plan N

# Complete (runs E2E, records evidence)
python scripts/complete_plan.py --plan N
```

---

## Coordination

Active work claims in root `CLAUDE.md`. Before starting:
```bash
python scripts/check_claims.py --list
make worktree BRANCH=plan-NN-description
```

---

## References

| Doc | Purpose |
|-----|---------|
| `docs/architecture/current/` | What IS implemented |
| `docs/architecture/target/` | What we WANT |
| `docs/architecture/gaps/` | 142-gap detailed analysis |
| `TEMPLATE.md` | New plan file template |
