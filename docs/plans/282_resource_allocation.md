# Plan #282: Ensure Resource Scarcity System is Fully Operational

## Status: In Progress

## Problem

Plan #281 fixed cost tracking (api_cost now populated), but `llm_budget_after: null` indicated agents weren't receiving llm_budget allocation from `resources.stock.llm_budget`.

## Root Cause Found

The code at `World.__init__()` looked for `budget.per_agent_budget` (deprecated config path) instead of reading from `resources.stock.llm_budget`. The `compute_per_agent_quota()` function correctly computed quotas from `resources.stock`, but the result was never used for agent initialization.

## Solution

Modified `World.__init__()` to:
1. Read `llm_budget_total` directly from passed config dict (not global config)
2. Compute `llm_budget_quota = total / num_agents`
3. Use this as default for agent initialization

## Files Changed

- `src/world/world.py` - Fix quota computation to use passed config dict
- `tests/integration/test_per_agent_budget.py` - Update tests to use `resources.stock.llm_budget` config
- `docs/architecture/current/execution_model.md` - Updated Last verified date
- `src/simulation/runner.py` - Add `llm_budget_after` to thinking events, add missing `deduct_llm_cost` call

## Acceptance Criteria

- [x] Agents receive llm_budget from `resources.stock.llm_budget.total / num_agents`
- [x] Per-principal override via "llm_budget" field still works
- [x] Tests pass with new config structure
- [x] `llm_budget_after` shows non-null values in thinking events
- [x] Budget decreases after each LLM call (deduct_llm_cost call added)

## Priority

Medium - Initial allocation now works. Deduction/enforcement were already in place, just needed budget to be allocated.
