<!-- AUTO-GENERATED FILE - DO NOT EDIT MANUALLY -->
<!-- This file is auto-synced by post-merge CI via sync_plan_status.py -->
<!-- To update: Edit individual plan files, then merge to main -->

# Implementation Plans

Master index of all gaps and their implementation plans.

**Last synced:** Auto-updated after each merge to main

---

## Quick Start

1. **Find a gap** - Browse table below
2. **Read the plan** - `NN_name.md` for details
3. **Implement** - TDD: write tests first
4. **Complete** - `python scripts/complete_plan.py --plan N`

> **🚨 NEVER manually edit status to Complete.** Always use `complete_plan.py`.
> Manual edits cause index/file mismatches that break CI. The script updates
> both the plan file AND this index automatically.

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
| 8 | [Agent Rights Trading](08_agent_rights.md) | Low | ✅ Post-V1 | - |
| 9 | [Scrip Debt Contracts](09_scrip_debt.md) | Low | ✅ Complete | - |
| 10 | [Memory Persistence](10_memory_persistence.md) | Low | ✅ Complete | - |
| 11 | [Terminology Cleanup](11_terminology.md) | Medium | ✅ Complete | #12 |
| 12 | [Per-Agent LLM Budget](12_per_agent_budget.md) | Medium | ✅ Complete | - |
| 13 | [Doc Line Number Refs](13_doc_line_refs.md) | Low | 📋 Post-V1 | - |
| 14 | [Artifact Interface Schema](14_mcp_interface.md) | Medium | ✅ Complete | - |
| 15 | [invoke() Genesis Support](15_invoke_genesis.md) | Medium | ✅ Complete | - |
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
| 30 | [LLM Budget Trading](30_capability_requests.md) | Medium | ✅ Complete | - |
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
| 48 | [CI Optimization](48_ci_optimization.md) | Medium | ✅ Post-V1 | - |
| 49 | [Reasoning in Narrow Waist](49_reasoning_narrow_waist.md) | **High** | ✅ Complete | LLM-native monitoring |
| 50 | [Test Structure Refactor](50_test_structure_refactor.md) | Medium | ✅ Complete | AI navigability |
| 51 | [V1 Acceptance Criteria](51_v1_acceptance.md) | **High** | ✅ Complete | V1 release |
| 52 | [Worktree Session Tracking](52_worktree_session_tracking.md) | Medium | ✅ Complete | - |
| 53 | [Scalable Resource Architecture](53_scalable_resource_architecture.md) | **High** | ✅ Complete | #31 |
| 54 | [Interface Reserved Terms](54_interface_reserved_terms.md) | Medium | ✅ Complete | #14 |
| 56 | [Per-Run Logging](56_per_run_logging.md) | Medium | ✅ Complete | - |
| 57 | [Agent Resource Management](57_agent_improvements.md) | **High** | ✅ Complete | - |
| 58 | [Dashboard Autonomous Mode](58_dashboard_autonomous.md) | Medium | ✅ Complete | #57 |
| 59 | [Agent Intelligence Patterns](59_agent_intelligence.md) | **High** | ✅ Complete | plan-59-agent-intelligence |
| 60 | [Tractable Logs](60_tractable_logs.md) | Medium | ✅ Complete | plan-60-tractable-logs |
| 61 | [Dashboard Entity Detail](61_dashboard_entity_detail.md) | Medium | ✅ Complete | - |
| 62 | [Config Magic Numbers](62_config_magic_numbers.md) | Medium | ✅ Complete | - |
| 63 | [Artifact Dependencies](63_artifact_dependencies.md) | **High** | ✅ Complete | Dashboard capital structure |
| 64 | [Dependency Graph Visualization](64_dependency_graph_viz.md) | Medium | ✅ Complete | #63 |
| 65 | [Continuous Execution Primary](65_continuous_execution_primary.md) | **High** | ✅ Complete | Agent workflows |
| 66 | [Genesis Split](66_genesis_split.md) | Medium | ✅ Complete | - |
| 68 | [PR Review Enforcement](68_pr_review_enforcement.md) | **High** | ✅ Complete | Quality assurance |
| 69 | [Worktree Auto-Cleanup](69_worktree_auto_cleanup.md) | Medium | ✅ Complete | Cleaner workflow |
| 70 | [Agent Workflow Phase 1](70_agent_workflow_phase1.md) | **High** | ✅ Complete | Agent intelligence |
| 71 | [Ownership Check](71_ownership_check.md) | **High** | ✅ Complete | Meta-process integrity |
| 72 | [Plan Number Enforcement](72_plan_number_enforcement.md) | **High** | ✅ Complete | Meta-process integrity |
| 73 | [Output Messaging Fix](73_output_messaging_fix.md) | **High** | ✅ Complete | - |
| 74 | [Meta-Process Doc Fixes](74_meta_process_doc_fixes.md) | Medium | ✅ Complete | - |
| 75 | [Autonomous Mint Resolution](75_autonomous_mint_resolution.md) | **Critical** | ✅ Complete | Emergent behavior |
| 76 | [Simulation Metrics](76_simulation_metrics.md) | Medium | ✅ Complete | - |
| 77 | [Genesis Coordinator](77_genesis_coordinator.md) | **High** | ✅ Complete | Cross-agent coordination |
| 78 | [Emergence Monitoring](78_emergence_monitoring.md) | **High** | ✅ Complete | Strategic thinking detection |
| 79 | [Time-Based Auctions](79_time_based_auctions.md) | Medium | ✅ Complete | Autonomous mode purity |
| 80 | [Log Optimization](80_log_optimization.md) | Medium | ✅ Complete | - |
| 81 | [Handbook Audit](81_handbook_audit.md) | Medium | ✅ Complete | Agent capability |
| 82 | [VSM-Aligned Improved Agents](82_vsm_aligned_agents.md) | Medium | ✅ Complete | - |
| 83 | [Remove Tick-Based Execution](83_remove_tick_based_execution.md) | **High** | ✅ Complete | - |
| 84 | [Float/Decimal Consistency](84_float_decimal_consistency.md) | Low | ✅ Deferred | - |
| 85 | [Inter-CC Messaging](85_inter_cc_messaging.md) | Medium | ✅ Complete | Multi-CC collaboration |
| 86 | [Interface Validation](86_interface_validation.md) | Medium | ✅ Complete | #14 |
| 87 | [Meta-Process Coordination](87_meta_process_coordination_improvements.md) | Medium | ✅ Complete | Hook improvements |
| 88 | [OODA Cognitive Logging](88_ooda_cognitive_logging.md) | **High** | ✅ Complete | Agent observability |
| 89 | [Plan Enforcement Hooks](89_plan_enforcement_hooks.md) | **High** | ✅ Complete | - |
| 90 | [Cognitive Schema Configurability](90_cognitive_schema_configurability.md) | Low | ❌ Post-V1 | #88 |
| 91 | [Acceptance Gate Cleanup](91_acceptance_gate_cleanup.md) | **High** | ✅ Complete | Meta-process clarity |
| 92 | [Worktree/Branch Mismatch Detection](92_worktree_branch_validation.md) | **High** | ✅ Complete | Meta-process integrity |
| 93 | [Agent Resource Visibility](93_agent_resource_visibility.md) | Medium | ✅ Complete | #95 |
| 94 | [PR Handoff Protocol](94_pr_handoff_protocol.md) | Medium | ✅ Complete | Coordination efficiency |
| 95 | [Unified Resource System](95_unified_resource_system.md) | **Critical** | ✅ Complete | Core economic mechanics |
| 97 | [SQLite Concurrency Fix](97_sqlite_concurrency.md) | **High** | ✅ Complete | Concurrent state access |
| 98 | [Robust Worktree Lifecycle](98_robust_worktree_lifecycle.md) | **High** | ✅ Complete | Meta-process reliability |
| 99 | [SQLite Isolation Fix](99_sqlite_isolation_fix.md) | **High** | ✅ Complete | Proper read/write concurrency |
| 100 | [Contract System Overhaul](100_contract_system_overhaul.md) | **High** | ✅ Complete | Custom contracts, advanced access control |
| 103 | [Meta-Process Doc Separation](103_meta_doc_separation.md) | Medium | ✅ Complete | Meta-process maintainability |
| 104 | [Meta-Process Hooks Separation](104_meta_hooks_separation.md) | Low | ✅ Deferred | Meta-process maintainability |
| 105 | [Meta-Process Scripts Separation](105_meta_scripts_separation.md) | Low | ✅ Deferred | Meta-process maintainability |
| 106 | [CI Cost Reduction](106_ci_cost_reduction.md) | **High** | ✅ Complete | Reduce GitHub Actions costs |
| 107 | [Temporal Network Visualization](107_temporal_network_viz.md) | **High** | ✅ Complete | Dashboard artifact network view |
| 111 | [Genesis Deprivilege Audit](111_genesis_deprivilege_audit.md) | **High** | ✅ Complete | Ensure genesis uses kernel interfaces |
| 112 | [JSON Arg Parsing](112_json_arg_parsing.md) | **High** | ✅ Complete | Auto-parse JSON strings in invoke args |
| 113 | [Contractable Model Access](113_contractable_model_access.md) | **High** | ✅ Complete | LLM model access as tradeable resource |
| 114 | [Interface Discovery](114_interface_discovery.md) | **High** | ✅ Complete | Cross-agent collaboration |
| 115 | [Worktree Ownership Enforcement](115_worktree_ownership_enforcement.md) | **High** | ✅ Complete | Multi-CC worktree safety |
| 116 | [Enforce Finish From Main](116_enforce_finish_from_main.md) | Medium | ✅ Complete | Meta-process integrity |
| 123 | [Safe Expression Evaluator](123_safe_expression_evaluator.md) | **Critical** | ✅ Complete | Replace eval() with safe evaluator |
| 124 | [Config Documentation Sync](124_config_doc_sync.md) | **High** | ✅ Complete | Sync config files with docs |
| 176 | [Atomic Worktree-Claim Enforcement](176_atomic_worktree_claims.md) | **High** | ✅ Complete | Meta-process enforcement |
| 186 | [Git-Level Meta-Process Resilience](186_meta_resilience.md) | **Critical** | ✅ Complete | Meta-process reliability |

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
