# Plan #281: Fix Workflow Usage Tracking for Resource Accounting

## Status: COMPLETE

## Problem

The resource scarcity system (llm_budget tracking) was broken because:

1. **Workflow didn't return usage** - `run_workflow()` didn't include LLM usage data in its return
2. **Agent had silent fallback** - `workflow_result.get("usage", {zeros})` silently fell back to zeros
3. **Result**: `api_cost` always 0.0, no budget ever deducted, scarcity system disabled

This violated the "Fail Loud" principle - a silent fallback hid a critical bug.

## Solution

1. **Workflow captures usage** - `_execute_llm_step()` now captures `llm_provider.last_usage` and fails if missing
2. **Workflow returns usage** - `run_workflow()` includes usage in return dict
3. **Agent fails loud** - Agent raises `RuntimeError` if workflow returns action without usage

## Changes

### `src/agents/workflow.py`
- Added `last_usage` tracking in `run_workflow()`
- `_execute_llm_step()` captures and returns `llm_provider.last_usage`
- Raises `RuntimeError` if usage missing (fail loud)
- Returns `usage` in workflow result

### `src/agents/agent.py`
- Removed silent fallback `workflow_result.get("usage", {zeros})`
- Now raises `RuntimeError` if workflow returns action without usage
- Added comments explaining when zeros are legitimate (no LLM step ran)

## Verification

- All 68 workflow and agent tests pass
- Run simulation and verify `api_cost > 0` and `llm_budget_after` populated

## Impact

The resource scarcity system now works:
- LLM costs are tracked per agent
- `llm_budget` is deducted after each thinking call
- Agents with exhausted budget are skipped
- Resource metrics visible in logs and dashboard
