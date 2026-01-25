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
| 102 | [Complete Tick Removal (Cosmetic Cleanup)](102_complete_tick_removal.md) | **High** | ✅ Complete | - |
| 103 | [Meta-Process Doc Separation](103_meta_doc_separation.md) | Medium | ✅ Complete | Meta-process maintainability |
| 104 | [Meta-Process Hooks Separation](104_meta_hooks_separation.md) | Low | ✅ Deferred | Meta-process maintainability |
| 105 | [Meta-Process Scripts Separation](105_meta_scripts_separation.md) | Low | ✅ Deferred | Meta-process maintainability |
| 106 | [CI Cost Reduction](106_ci_cost_reduction.md) | **High** | ✅ Complete | Reduce GitHub Actions costs |
| 107 | [Temporal Network Visualization](107_temporal_network_viz.md) | **High** | ✅ Complete | Dashboard artifact network view |
| 108 | [Agent Config Display](108_agent_config_display.md) | **High** | ✅ Complete | - |
| 109 | [CI Plan Tests Optimization](109_ci_plan_tests_optimization.md) | **High** | ✅ Complete | - |
| 110 | [Dashboard Overhaul for Autonomous Mode & Emergence Observability](110_dashboard_overhaul.md) | **High** | ✅ Complete | - |
| 111 | [Genesis Deprivilege Audit](111_genesis_deprivilege_audit.md) | **High** | ✅ Complete | Ensure genesis uses kernel interfaces |
| 112 | [JSON Arg Parsing](112_json_arg_parsing.md) | **High** | ✅ Complete | Auto-parse JSON strings in invoke args |
| 113 | [Contractable Model Access](113_contractable_model_access.md) | **High** | ✅ Complete | LLM model access as tradeable resource |
| 114 | [Interface Discovery](114_interface_discovery.md) | **High** | ✅ Complete | Cross-agent collaboration |
| 115 | [Worktree Ownership Enforcement](115_worktree_ownership_enforcement.md) | **High** | ✅ Complete | Multi-CC worktree safety |
| 116 | [Enforce Finish From Main](116_enforce_finish_from_main.md) | Medium | ✅ Complete | Meta-process integrity |
| 117 | [Remove Duplicate Action Logging](117_remove_duplicate_logging.md) | **High** | ✅ Complete | - |
| 118 | [Computed Plan Status from Git History](118_computed_plan_status.md) | Medium | 📋 Planned | - |
| 119 | [Documentation Consistency Fixes](119_doc_consistency.md) | **High** | ✅ Complete | - |
| 120 | [Document Executable Interface Requirement](120_executable_interface_docs.md) | **High** | ✅ Complete | - |
| 121 | [Unclosed File Handle Fix](121_unclosed_file_handle.md) | **High** | ✅ Complete | - |
| 122 | [Model Registry Config Fix](122_model_registry_config.md) | **High** | ✅ Complete | - |
| 123 | [Safe Expression Evaluator](123_safe_expression_evaluator.md) | **Critical** | ✅ Complete | Replace eval() with safe evaluator |
| 124 | [Config Documentation Sync](124_config_doc_sync.md) | **High** | ✅ Complete | Sync config files with docs |
| 125 | [Massive Function Refactor](125_massive_function_refactor.md) | **High** | ✅ Complete | - |
| 126 | [Test Mock Justification Audit](126_test_mock_justification.md) | **High** | ✅ Complete | - |
| 127 | [Block Direct merge_pr.py Calls](127_merge_script_hook_gap.md) | **High** | ✅ Complete | - |
| 128 | [Fix Gemini Schema for Interface Field](128_gemini_schema_interface_fix.md) | **High** | ✅ Complete | - |
| 129 | [Error Observability](129_error_observability.md) | **High** | ✅ Complete | - |
| 130 | [Automatic Post-Merge Cleanup](130_post_merge_cleanup.md) | **High** | ✅ Complete | - |
| 131 | [Edit Artifact Action](131_edit_artifact_action.md) | **High** | ✅ Complete | - |
| 133 | [Dashboard Autonomous Mode Fixes](133_dashboard_autonomous_fixes.md) | **High** | ✅ Complete | - |
| 134 | [Per-Session Identity and Mandatory Claiming](134_session_identity_coordination.md) | **High** | ✅ Complete | - |
| 135 | [Run Analysis Metrics Script](135_analyze_run_metrics.md) | **High** | ✅ Complete | - |
| 136 | [Lifecycle Robustness](136_lifecycle_robustness.md) | **High** | ✅ Complete | - |
| 137 | [Agent IRR Improvements](137_agent_irr_improvements.md) | **High** | ✅ Complete | - |
| 138 | [Provider-Level Union Schema Transformation](138_provider_union_schema_transform.md) | Medium | 📋 Planned | - |
| 139 | [Dashboard Bug Fixes and Improvements](139_dashboard_phase2_phase3.md) | **High** | ✅ Complete | - |
| 140 | [Kernel Permission Fixes](140_kernel_permission_fixes.md) | Medium | 📋 Planned | - |
| 141 | [Fix merge hook gap for `make -C` pattern](141_merge_hook_gap.md) | **High** | ✅ Complete | - |
| 142 | [Dashboard Improvements - KPI Trends, Pagination, WebSocket](142_dashboard_improvements.md) | **High** | ✅ Complete | - |
| 143 | [Reflex System (System 1 Fast Path)](143_reflex_system.md) | **High** | ✅ Complete | - |
| 144 | [Workflows as Tradeable Artifacts](144_workflows_as_artifacts.md) | Medium | ❓  | - |
| 145 | [Supervisor Auto-Restart](145_supervisor_auto_restart.md) | **High** | ✅ Complete | - |
| 146 | [Unified Artifact Intelligence](146_unified_artifact_intelligence.md) | Medium | 📋 Planned | - |
| 147 | [Dashboard Features - Latency, Search, Comparison](147_dashboard_features.md) | Medium | 📋 Planned | - |
| 148 | [ADR-0019 Implementation Audit](148_adr019_implementation_audit.md) | **High** | ✅ Complete | - |
| 149 | [Dashboard Architecture Refactor](149_dashboard_architecture.md) | Medium | 📋 Planned | - |
| 150 | [Prompt Component Library](150_prompt_component_library.md) | Medium | 📋 Planned | - |
| 151 | [Backend Event Emission](151_backend_event_emission.md) | **High** | ✅ Complete | - |
| 155 | [V4 Architecture - Deferred Considerations](155_v4_architecture_deferred.md) | Medium | ❓  | - |
| 156 | [V4 Agent Immediate Fixes](156_v4_agent_immediate_fixes.md) | **High** | ✅ Complete | - |
| 157 | [Agent Goal Clarity and Time Awareness](157_agent_goal_clarity.md) | **High** | ✅ Complete | - |
| 160 | [Phase 1 - Cognitive Self-Modification](160_phase1_cognitive_self_modification.md) | Medium | 🚧 In Progress | - |
| 161 | [Agent Error Learning](161_agent_error_learning.md) | Medium | 🚧 In Progress | - |
| 162 | [Contract Artifact Lookup](162_contract_artifact_lookup.md) | Medium | 📋 Planned | - |
| 163 | [Checkpoint Completeness](163_checkpoint_completeness.md) | **High** | ✅ Complete | - |
| 164 | [Tick Terminology Purge](164_tick_terminology_purge.md) | **High** | ✅ Complete | - |
| 165 | [Genesis Contracts as Artifacts](165_genesis_contracts_as_artifacts.md) | **High** | ✅ Complete | - |
| 166 | [Resource Rights Model](166_resource_rights_model.md) | Medium | 📋 Planned | - |
| 167 | [Debt Contract Time-Based Redesign](167_debt_contract_time_based.md) | **High** | ✅ Complete | - |
| 168 | [Artifact Metadata Field](168_artifact_metadata.md) | **High** | ✅ Complete | - |
| 169 | [Kernel Event Triggers](169_kernel_event_triggers.md) | **High** | ✅ Complete | - |
| 170 | [Artifact Dependency Tracking](170_artifact_dependency_tracking.md) | **High** | ✅ Complete | - |
| 172 | [Dashboard v2 Visualization Panels](172_dashboard_v2_visualization_panels.md) | **High** | ✅ Complete | - |
| 173 | [Dashboard Emergence Alerts](173_dashboard_emergence_alerts.md) | **High** | ✅ Complete | - |
| 174 | [Dashboard Tab-Based Layout Refactor](174_dashboard_tab_refactor.md) | **High** | ✅ Complete | - |
| 175 | [Emergence Metrics Cleanup](175_emergence_metrics_cleanup.md) | **High** | ✅ Complete | - |
| 176 | [Atomic Worktree-Claim Enforcement](176_atomic_worktree_claims.md) | **High** | ✅ Complete | Meta-process enforcement |
| 177 | [Dashboard Bug Fixes](177_dashboard_bugfixes.md) | **High** | ✅ Complete | - |
| 178 | [Configurable Enforcement Strictness](178_enforcement_strictness_config.md) | Medium | 🚧 In Progress | - |
| 179 | [Dashboard Bugfixes - Coordination Density & Tick Language](179_dashboard_bugfixes.md) | Medium | 📋 Planned | - |
| 180 | [Complete Trigger Integration](180_trigger_integration.md) | **High** | ✅ Complete | - |
| 181 | [Split Large Core Files](181_split_large_files.md) | Medium | 📋 Planned | - |
| 182 | [Metadata Indexing for Artifact Discovery](182_metadata_indexing.md) | **High** | ✅ Complete | - |
| 183 | [Genesis Voting Artifact](183_genesis_voting.md) | **High** | ✅ Complete | - |
| 184 | [Query Kernel Action](184_query_kernel_action.md) | **High** | ✅ Complete | - |
| 185 | [Time-Based Scheduling](185_time_based_scheduling.md) | Medium | ✅ Complete | - |
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
