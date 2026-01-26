# Plan #226: Agent Learning & Strategic Behavior Fixes

**Status:** In Progress
**Priority:** Critical
**Blocks:** Effective agent learning, strategic planning, reduced noop rates

---

## Problem Statement

Investigation revealed 7 critical issues preventing effective agent learning and strategic behavior:

| # | Issue | Severity | Impact |
|---|-------|----------|--------|
| 1 | Semantic search not invoked during RAG | Critical | Memory infrastructure unused |
| 2 | Working memory never refreshed | Critical | Goals invisible across steps |
| 3 | Context variables frozen at step 1 | Critical | Stale data in all prompts |
| 4 | Action instructions in non-executable steps | High | 50% noop rate (beta_3) |
| 5 | No deduplication in memory storage | Medium | Wasted scrip, noisy memories |
| 6 | Behaviors are prompts, not enforcement | High | Agents ignore loop warnings |
| 7 | Delta_3 missing health check gate | High | No automated pivot on failure |

---

## Implementation

### Phase 1: Critical Issues (1-3) - DONE

1. **Working memory refresh method** - `agent.py:refresh_working_memory()`
2. **Working memory in workflow context** - Added to `_build_workflow_context()`
3. **Context refresh after LLM steps** - Updated `workflow.py`
4. **Semantic search logging** - Added to `_search_longterm_memory_artifact()`

### Phase 2: High Priority (4, 6, 7) - PARTIAL

1. **Fixed reflection steps** - Removed action instructions from beta_3/delta_3 `learn_from_outcome`
2. **Added GenesisLoopDetector** - New artifact for automated loop detection
3. **Registered in factory** - Loop detector available as `genesis_loop_detector`

### Phase 3: Medium Priority (5) - TODO

1. Memory deduplication in genesis_memory

---

## Files Modified

| File | Change |
|------|--------|
| `src/agents/agent.py` | Add `refresh_working_memory()`, update `_build_workflow_context()`, add logging |
| `src/agents/workflow.py` | Call refresh after LLM steps, update context |
| `src/agents/beta_3/agent.yaml` | Fix learn_from_outcome step |
| `src/agents/delta_3/agent.yaml` | Fix learn_from_outcome step |
| `src/world/genesis/decision_artifacts.py` | Add GenesisLoopDetector class |
| `src/world/genesis/factory.py` | Register genesis_loop_detector |

---

## Verification

1. `make test-quick` passes
2. Run simulation and check for:
   - "Refreshed working memory" in logs
   - "Semantic search for" in logs
   - Reduced noop rates

---

## Acceptance Criteria

- [x] Working memory values persist across workflow steps
- [x] Semantic search logging added
- [x] GenesisLoopDetector artifact created
- [x] Reflection steps simplified (no conflicting action instructions)
- [ ] beta_3 noop rate < 30% (was 50%)
- [ ] delta_3 noop rate < 20% (was 32%)
- [x] `make test-quick` passes
