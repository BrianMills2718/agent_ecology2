# Plan 290: Fix Workflow Noop Break Issue

## Status: In Progress

## Problem

Plan #280 introduced logic to break the workflow after the first LLM step that produces an action. This ensures each iteration executes one meaningful step.

However, the current implementation breaks on ANY action, including `noop`. This causes agents with reflection steps (like beta_3's `learn_from_outcome`) to get stuck in loops:

1. `learn_from_outcome` runs (reflection step, produces noop or write_artifact)
2. Plan #280 breaks immediately after this step
3. The workflow never reaches the actual planning steps (`strategic_planning`, etc.)
4. Next iteration, same thing happens - agent is stuck

**Observed behavior from logs:**
- beta_3 shows 24 thinking events all at `workflow_state=strategic, workflow_step=learn_from_outcome`
- No state transitions, no action executions
- Agent never progresses past the reflection step

## Solution

Modify the Plan #280 break condition to exclude `noop` actions. A noop explicitly means "do nothing" and shouldn't count as a meaningful action that stops the workflow.

**Change in `src/agents/workflow.py`:**

```python
# Before (breaks on any action):
if last_action is not None:
    break

# After (breaks only on meaningful actions):
if last_action is not None and last_action.get("action_type") != "noop":
    break
```

## Files Changed

- `src/agents/workflow.py` - Add noop check to break condition (~1 line change)

## Testing

1. Run simulation with beta_3 agent
2. Verify workflow progresses past `learn_from_outcome` to `strategic_planning`
3. Verify beta_3 executes actual actions (not stuck in reflection loop)

## Verification

```bash
make run DURATION=60 AGENTS=1
# Check logs for beta_3 state transitions
```
