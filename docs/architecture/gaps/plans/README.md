# Phase 1 Implementation Plans

Detailed implementation plans for the 4 foundational gaps.

## Overview

| Gap ID | Name | Status | Dependencies |
|--------|------|--------|--------------|
| GAP-RES-001 | RateTracker Class | **COMPLETE** | None |
| GAP-GEN-001 | Contract System | **COMPLETE** | None |
| GAP-EXEC-001 | Autonomous Loops | **COMPLETE** | GAP-RES-001 |
| GAP-AGENT-001 | Unified Ontology | **COMPLETE** | GAP-GEN-001 |

**Phase 1 Status:** ALL COMPLETE (2026-01-12)

## Dependency Graph

```
GAP-RES-001 (RateTracker) ──────► GAP-EXEC-001 (Autonomous Loops)
                                          │
                                          ▼
                                    Phase 2 Stream A

GAP-GEN-001 (Contract System) ──► GAP-AGENT-001 (Unified Ontology)
                                          │
                                          ▼
                                    Phase 2 Stream B
```

## Plan Files

- [phase1_gap_res_001_rate_tracker.md](./phase1_gap_res_001_rate_tracker.md) - Rolling window rate limiting
- [phase1_gap_gen_001_contract_system.md](./phase1_gap_gen_001_contract_system.md) - Contract-based access control
- [phase1_gap_exec_001_autonomous_loops.md](./phase1_gap_exec_001_autonomous_loops.md) - Continuous agent execution
- [phase1_gap_agent_001_unified_ontology.md](./phase1_gap_agent_001_unified_ontology.md) - Agents as artifacts

## Implementation Notes

1. **Wave 1**: GAP-RES-001 and GAP-GEN-001 can be implemented in parallel
2. **Wave 2**: GAP-EXEC-001 and GAP-AGENT-001 start after Wave 1 completes
3. All implementations include feature flags for gradual rollout
4. Each gap requires tests before marking complete

---

# Phase 2: Integration

See [PHASE2_PLAN.md](./PHASE2_PLAN.md) for the full plan.

## Phase 2 Overview

Phase 1 created standalone modules. Phase 2 **integrates them** into the system.

| Task ID | Name | Status | Depends On |
|---------|------|--------|------------|
| INT-001 | RateTracker → Ledger | **COMPLETE** | None |
| INT-002 | Contracts → Executor | **COMPLETE** | INT-001 |
| INT-003 | AgentLoop → Runner | **COMPLETE** | INT-001 |
| CAP-001 | Remove tick-based reset | **COMPLETE** | INT-001 |
| INT-004 | Agent → Artifact | **COMPLETE** | INT-002 |
| CAP-002 | Async locks in Ledger | **COMPLETE** | INT-003 |
| CAP-003 | Remove owner bypass | **COMPLETE** | INT-002 |
| CAP-004 | Memory as artifact | **COMPLETE** | INT-004 |
| CAP-005 | Action blocking on exhaustion | **COMPLETE** | CAP-001 |
| CAP-006 | Contract execution environment | **COMPLETE** | INT-002 |

**Phase 2 Status:** ALL COMPLETE (2026-01-12)

## Phase 2 Parallelization

```
Wave 1: INT-001 (blocking)
Wave 2: INT-002 + INT-003 + CAP-001 (parallel)
Wave 3: INT-004 + CAP-002 (parallel)
Wave 4: CAP-003 + CAP-004 + CAP-005 + CAP-006 (parallel)
```

## Detailed Task Plans

- [phase2_int_001_rate_tracker_integration.md](./phase2_int_001_rate_tracker_integration.md)
- [phase2_int_002_contracts_executor.md](./phase2_int_002_contracts_executor.md)
- [phase2_int_003_agent_loop_runner.md](./phase2_int_003_agent_loop_runner.md)
