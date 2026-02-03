# Plan #275: Alpha Prime Prompt Observability

**Status:** Complete
**Owner:** Claude Code
**Created:** 2026-02-03
**Completed:** 2026-02-03

## Problem

Alpha Prime BabyAGI loop wasn't creating artifacts or submitting to tasks. Investigation revealed the LLM didn't have access to:
1. Query results (mint_tasks) - only saved task_result description, not actual data
2. Action history - initialized empty but never shown to LLM
3. Artifact creation tracking - insights.artifacts_created never populated

## Solution

Update the BabyAGI loop to:
1. Store `last_mint_tasks_query` in state after query_kernel(mint_tasks)
2. Include available tasks and action history in the LLM prompt
3. Track artifacts_created in insights when write_artifact succeeds

## Files Changed

- `src/world/world.py`:
  - Add `available_tasks` and `action_history` to prompt context
  - Track `artifacts_created` in insights on successful artifact creation
  - (Prior: Store `last_mint_tasks_query` in state, track `action_history`)

## Testing

- All agent loop tests pass (61 tests)
- Syntax verification passes
- Manual testing: `make run DURATION=60 AGENTS=1` with v4_solo
