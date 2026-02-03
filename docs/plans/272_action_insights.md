# Plan #272: Structured Action Insights for Loop Breaking

**Status:** Complete
**Priority:** High
**Theme:** Agent Cognition

---

## Problem Statement

Agents get stuck in loops trying closed tasks. Example from logs:
```
Event 54: submit_to_task(alpha_prime_adder, add_numbers) → FAILED: Task 'add_numbers' is no longer open
Event 55: query_kernel(mint_tasks) → SUCCESS (shows add_numbers still in list)
Event 56: submit_to_task(alpha_prime_adder, add_numbers) → FAILED: Task 'add_numbers' is no longer open
... repeats forever
```

The agent sees the failure message in `last_action_result` but doesn't have structured tracking to remember "add_numbers is closed, try something else."

---

## Solution

Add `ActionInsights` - auto-extracted structured learnings from action results:
- `tried_tasks: set[str]` - Tasks attempted
- `closed_tasks: set[str]` - Tasks confirmed closed
- `completed_tasks: set[str]` - Tasks successfully completed

Inject into prompt as natural language:
```
## TASK STATUS (from your attempts)
CLOSED tasks (don't retry): add_numbers
COMPLETED tasks: multiply_numbers
```

---

## Implementation

### Changes to `src/agents/agent.py`

1. Added `self._action_insights` dict in `__init__`
2. Added `_extract_action_insights()` method - parses action results for task closure patterns
3. Added `_format_action_insights()` method - formats insights for prompt injection
4. Updated `set_last_result()` to call `_extract_action_insights()`
5. Updated `_build_workflow_context()` to include `action_insights` variable
6. Updated `export_state()` and `restore_state()` for checkpoint persistence

### Changes to `src/agents/v4_solo/agent.yaml`

1. Upgraded model from `gemini/gemini-2.0-flash` to `gemini/gemini-2.5-flash` (thinking capability)
2. Added `{action_insights}` section to workflow prompt

---

## Verification

```python
agent.set_last_result('submit_to_task', False, "Task 'add_numbers' is no longer open", {'task_id': 'add_numbers'})
assert "add_numbers" in agent._action_insights["closed_tasks"]
assert "CLOSED tasks (don't retry): add_numbers" in agent._format_action_insights()
```

---

## Future Extensions (Option C)

This is Option A (quick fix). Future work could implement full 3-tier memory:
- Tier 1: Sliding window (last N actions) + auto-compaction
- Tier 2: Structured JSON (task tracking, lessons)
- Tier 3: Semantic search via Qdrant/mem0 (cross-session learning)
