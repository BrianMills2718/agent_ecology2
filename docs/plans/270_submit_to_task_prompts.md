# Plan 270: Improve submit_to_task Action Prompts

**Status:** 🚧 In Progress

**Priority:** High
**Blocked By:** Plan #269
**Blocks:** -

---

## Gap

**Current:** Agents are aware of `submit_to_task` action but not outputting valid action JSON. They query `mint_tasks`, create correct artifacts, but then fail to produce the action.

**Target:** Agents successfully complete mint tasks by submitting their artifacts.

**Why High:** Task-based mint is the primary mechanism for objective, verifiable agent work rewards.

---

## Fix

1. Add explicit CORRECT/WRONG examples to `submit_to_task` schema (like `submit_to_mint` has)
2. Add `mint_tasks` and `mint_task` to the query types documentation
3. Emphasize that `submit_to_task` is a DIRECT ACTION TYPE

---

## Files Changed

- `src/agents/schema.py` - Enhanced action documentation

---

## Verification

Run simulation and observe agents successfully completing tasks.
