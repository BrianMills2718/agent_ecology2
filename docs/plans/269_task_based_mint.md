# Plan 269: Task-Based Mint System

**Status:** ✅ Complete

**Verified:** 2026-02-02T20:19:27Z
**Verification Evidence:**
```yaml
completed_by: scripts/complete_plan.py
timestamp: 2026-02-02T20:19:27Z
tests:
  unit: skipped (--status-only, CI-validated)
  e2e_smoke: skipped (--status-only, CI-validated)
  e2e_real: skipped (--status-only, CI-validated)
  doc_coupling: skipped (--status-only, CI-validated)
commit: 56803bb
```

**Priority:** High
**Blocked By:** -
**Blocks:** -

---

## Gap

**Current:** Mint uses LLM-based quality scoring which is subjective and gameable. Agents submit artifacts to auctions and an LLM judge scores them.

**Target:** Objective, verifiable task-based minting. Tasks have public tests (agents can see/run) and hidden tests (kernel runs secretly to prevent gaming).

**Why High:** Enables predictable, fair incentive mechanism for agent work. Hidden tests prevent gaming while public tests enable debugging.

---

## Design

```
+-------------------------------------------------------------+
|                     MINT TASK                               |
+-------------------------------------------------------------+
| task_id: "sort_algorithm"                                   |
| description: "Create a sorting function"                    |
| reward: 50 scrip                                            |
|                                                             |
| PUBLIC TESTS (agents can see):                              |
|   - run([3,1,2]) == [1,2,3]                                |
|   - run([]) == []                                          |
|                                                             |
| HIDDEN TESTS (kernel runs secretly):                        |
|   - run([5,5,5]) == [5,5,5]  # duplicates                  |
|   - performance check                                       |
+-------------------------------------------------------------+
```

**Flow:**
1. Agent queries `query_kernel(query_type="mint_tasks")` -> sees available tasks
2. Agent reads task details including public tests
3. Agent builds artifact with `run()` function
4. Agent submits `submit_to_task(artifact_id, task_id)`
5. Kernel runs public tests -> agent sees detailed results
6. Kernel runs hidden tests -> pass/fail only (no details)
7. All pass -> reward distributed, task closed

---

## Implementation

### New Files
- `src/world/mint_tasks.py` - MintTaskManager, MintTask, TaskTest dataclasses

### Modified Files
- `src/config_schema.py` - TaskTestConfig, SeedTaskConfig, MintTasksConfig
- `src/world/actions.py` - SubmitToTaskIntent action
- `src/world/action_executor.py` - submit_to_task handler
- `src/world/kernel_queries.py` - mint_tasks, mint_task query types
- `src/world/world.py` - MintTaskManager initialization
- `src/agents/schema.py` - submit_to_task action documentation
- `config/config.yaml` - seed_tasks configuration

---

## Test Plan

- Run simulation with task-based mint enabled
- Verify agents can query available tasks
- Verify agents can submit solutions and earn rewards
- Verify hidden tests don't leak details

---

## References

- ADR-0019: Contract-Based Access Control
- Plan #254: Kernel actions (transfer, mint)
- Plan #259: submit_to_mint action type
