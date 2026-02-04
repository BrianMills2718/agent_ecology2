# Plan #280: Workflow Single Step per Iteration

## Status: COMPLETE

## Problem

Agents with workflow configurations appeared stuck because the workflow engine ran ALL steps in a single call, overwriting intermediate actions. Example:

1. Step "question" produces action → stored in `last_action`
2. Step "investigate" produces action → overwrites `last_action`
3. Step "analyze" produces action → overwrites `last_action`
4. Step "reflect" produces action → overwrites `last_action`
5. Only "reflect" action returned

This meant agents would only ever produce "reflect" step actions (like `write_artifact` to working_memory), never executing the earlier steps' actions.

## Solution

Add `break` after the first LLM step that produces an action. This ensures each `propose_action_async()` call executes exactly one meaningful workflow step.

## Changes

### `src/agents/workflow.py`

Added ~3 lines in `run_workflow()`:

```python
# Plan #280: Stop after first LLM step that produces an action
# This ensures each iteration executes one meaningful step
if last_action is not None:
    break
```

## Verification

- All 61 workflow tests pass
- All 7 agent tests pass
- Run simulation and observe agents cycling through different workflow steps

## Impact

Agents will now:
- Execute one step per turn instead of all steps
- Produce diverse actions (question, investigate, analyze, reflect) based on workflow state
- Progress through state machine states meaningfully
