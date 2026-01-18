# Plan 70: Agent Workflow Phase 1

**Status:** ✅ Complete
**Priority:** High
**Blocked By:** None
**Blocks:** Agent intelligence improvements

---

## Gap

**Current:** Agents have fixed execution model - single `propose_action()` call per iteration with monolithic prompt construction. No configurable workflow steps, no separation of concerns.

**Target:** Agents define configurable workflows with code and LLM steps. Workflows are ordered lists of steps that execute sequentially. Agents can modify their workflows at runtime.

**Why High:** Agent paralysis (0 writes in 10 ticks) partly due to inflexible execution. Research shows effective agents need observation, planning, AND reflection - requires multi-step workflows.

---

## References

- ADR-0013: Configurable Agent Workflows (Accepted)
- Feature spec: `acceptance_gates/agent_workflow.yaml`
- Simulation observation: `docs/simulation_learnings/2026-01-16_agent_paralysis.md`

---

## Files Affected

- src/agents/workflow.py (create)
- src/agents/agent.py (modify)
- src/agents/alpha/agent.yaml (modify)
- src/agents/beta/agent.yaml (modify)
- src/agents/gamma/agent.yaml (modify)
- src/agents/delta/agent.yaml (modify)
- src/agents/epsilon/agent.yaml (modify)
- tests/unit/test_workflow.py (create)
- tests/integration/test_agent_workflow.py (create)
- scripts/check_plan_tests.py (modify)
- docs/architecture/current/agents.md (modify)

---

## Plan

### Phase 1: Workflow Engine

Create `src/agents/workflow.py` with:
- `WorkflowStep` dataclass (step name, type, config)
- `WorkflowConfig` dataclass (list of steps, error handling)
- `WorkflowRunner` class that executes steps sequentially
- Code step execution (eval Python expressions)
- LLM step execution (read prompt artifact, call LLM)
- Error handling (retry, skip, fail based on config)

### Phase 2: Agent Integration

Modify `src/agents/agent.py`:
- Add `workflow` property loaded from artifact config
- Add `run_workflow()` method that replaces monolithic `propose_action()`
- Keep `propose_action()` for backward compatibility
- Workflow steps access agent context (self, world_state, etc.)

### Phase 3: Agent Configs

Update genesis agents with workflow configs:
- Create `src/agents/alpha/prompts/think.md`
- Create `src/agents/alpha/prompts/act.md`
- Add workflow section to `agent.yaml`
- Repeat for beta, gamma, delta, epsilon

### Phase 4: Tests

Write tests per acceptance criteria in feature spec.

---

## Required Tests

### Unit Tests (`tests/unit/test_workflow.py`)

| Test | Description |
|------|-------------|
| `test_code_step_executes` | Code step runs Python expression |
| `test_code_step_sets_context` | Code step can modify context dict |
| `test_llm_step_reads_artifact` | LLM step reads prompt from artifact |
| `test_llm_step_calls_llm` | LLM step invokes LLM provider |
| `test_run_if_condition_true` | Step runs when condition is true |
| `test_run_if_condition_false` | Step skips when condition is false |
| `test_error_retry` | Step retries on failure when configured |
| `test_error_skip` | Step skips on failure when configured |
| `test_error_fail` | Workflow fails on step failure when configured |
| `test_empty_workflow` | Empty workflow completes without error |

### Integration Tests (`tests/integration/test_agent_workflow.py`)

| Test | Description |
|------|-------------|
| `test_agent_runs_workflow` | Agent executes full workflow |
| `test_agent_workflow_produces_action` | Workflow produces valid action |
| `test_agent_modifies_workflow` | Agent can update workflow config |
| `test_workflow_error_returned` | Errors returned to agent |

---

## Verification

### Tests & Quality
- [x] All unit tests pass (18 tests in test_workflow.py)
- [x] All integration tests pass (test_agent_workflow.py)
- [x] `pytest tests/` passes
- [x] `python -m mypy src/ --ignore-missing-imports` passes

### Documentation
- [x] `docs/architecture/current/agents.md` updated
- [x] ADR-0013 status is Accepted

### Completion Ceremony
- [x] Plan file status -> `Complete`
- [x] `plans/CLAUDE.md` index updated
- [x] Claim released
- [x] PR created/merged

**Verified:** 2026-01-18T07:00:00Z (retroactive - PR already merged)
**PR:** #253
**Merged:** 2026-01-18T03:28:17Z

**CI Evidence:**
- All checks passed (SUCCESS)
- Phase 1 implementation: workflow.py, test_workflow.py, test_agent_workflow.py

---

## Notes

### Design Decisions

1. **Workflow stored in agent artifact content** - JSON config under `workflow` key
2. **Prompt artifacts per agent** - Each agent has its own prompts in `src/agents/{name}/prompts/`
3. **Sequential execution only** - Phase 1 is simple; parallel steps deferred
4. **Context dict passed through steps** - Steps can read/write shared context

### Risks

- Workflow complexity could confuse agents (mitigate: start with simple 2-step workflows)
- Prompt artifact management overhead (mitigate: genesis agents pre-configured)
