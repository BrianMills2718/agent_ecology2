# Plan #319: Emit Thinking Events from `_syscall_llm`

**Status:** ✅ Complete

**PR:** #1123

## Problem

Agent cognition is unobservable. The `reasoning` field in LLM responses goes into `action_history` (capped at 15 entries), never reaching the event log, dashboard, or analysis scripts. The entire downstream infrastructure (dashboard `_handle_thinking()`, `analyze_run.py`, `analyze_logs.py`, `collect_metrics.py`) already consumes `thinking`/`thinking_failed` events but receives no data.

Root cause: `_syscall_llm` in `executor.py` never calls `world.logger.log()`.

## Solution

Add `world.logger.log()` calls to `_syscall_llm` after each LLM call:

- **Success:** `thinking` event with `principal_id`, `model`, `input_tokens`, `output_tokens`, `api_cost`, `llm_budget_after`, `reasoning` (capped at 2000 chars)
- **Budget exhaustion:** `thinking_failed` event with `principal_id`, `model`, `api_cost=0.0`, `reason`
- **LLM exception:** `thinking_failed` event with `principal_id`, `model`, `api_cost=0.0`, `reason` (capped at 500 chars)

## Files Changed

| File | Change |
|------|--------|
| `src/world/executor.py` | 3 `world.logger.log()` calls in `_syscall_llm` |
| `docs/architecture/current/artifacts_executor.md` | Note thinking event emission |
| `tests/unit/test_executor.py` | 4 tests for thinking event emission |

## What This Lights Up

Dashboard `/api/thinking`, agent detail ThinkingEvents, LLM token charts, API cost tracking, `analyze_run.py` thought capture rate, `analyze_logs.py` reasoning snippets, `collect_metrics.py` per-agent token/cost.
