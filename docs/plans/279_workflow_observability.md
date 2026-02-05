# Plan #279: Workflow Observability

**Status:** ✅ Complete

## Problem

Agents using workflow state machines have no logging of:
1. Which state they're in
2. State transitions (successes only logged on failure)
3. Which workflow step executed
4. Workflow context in thinking events

This makes debugging agent behavior nearly impossible. The discourse_analyst agent appears stuck but we can't see why.

## Solution

Add observability events for workflow execution:

1. **`workflow_state_changed`** - Emitted when state machine transitions
2. **`workflow_step_executed`** - Emitted when a workflow step completes
3. **Add workflow context to `thinking` events** - current_state, current_step

## Implementation

### 1. workflow.py - Add event callback and logging

Add optional `event_callback` to WorkflowRunner that's called for state transitions and step execution.

```python
def __init__(
    self,
    llm_provider: Callable | None = None,
    world: Any = None,
    event_callback: Callable[[str, dict], None] | None = None,  # Plan #279
):
    self.event_callback = event_callback
```

Emit events after state transitions (line ~640):
```python
if state_machine.transition_to(step.transition_to, context):
    # Plan #279: Log state transition
    if self.event_callback:
        self.event_callback("workflow_state_changed", {
            "agent_id": context.get("agent_id"),
            "from_state": old_state,
            "to_state": step.transition_to,
            "step_name": step.name,
        })
```

Emit events after step execution:
```python
# Plan #279: Log step execution
if self.event_callback:
    self.event_callback("workflow_step_executed", {
        "agent_id": context.get("agent_id"),
        "step_name": step.name,
        "step_type": step.step_type.value,
        "success": result.get("success", False),
        "current_state": context.get("_current_state"),
    })
```

### 2. workflow.py - Return workflow context in result

Add current_state and executed_steps to workflow result:

```python
return {
    "success": True,
    "action": action,
    "reasoning": reasoning,
    "workflow_state": context.get("_current_state"),  # Plan #279
    "workflow_step": last_executed_step,  # Plan #279
}
```

### 3. agent.py - Pass event callback to WorkflowRunner

```python
runner = WorkflowRunner(
    llm_provider=self.llm,
    world=self._world,
    event_callback=self._workflow_event_callback,  # Plan #279
)
```

Store world reference for logging:
```python
def _workflow_event_callback(self, event_type: str, data: dict) -> None:
    """Callback for workflow events (Plan #279)."""
    if self._world and hasattr(self._world, 'logger'):
        self._world.logger.log(event_type, {
            "event_number": self._world.event_number,
            **data,
        })
```

### 4. runner.py - Add workflow context to thinking events

```python
thinking_data: dict[str, Any] = {
    # ... existing fields ...
    "workflow_state": result.get("workflow_state"),  # Plan #279
    "workflow_step": result.get("workflow_step"),  # Plan #279
}
```

## Files Changed

| File | Change |
|------|--------|
| `src/agents/workflow.py` | Add event_callback, emit state/step events |
| `src/agents/agent.py` | Pass event callback, add callback method |
| `src/simulation/runner.py` | Add workflow context to thinking events |
| `docs/architecture/current/agents.md` | Document new events |

## Testing

1. Run discourse_analyst simulation
2. Verify `workflow_state_changed` events appear in logs
3. Verify `workflow_step_executed` events appear in logs
4. Verify `thinking` events include `workflow_state` and `workflow_step`

## Acceptance

- [ ] State transitions are logged with from/to states
- [ ] Step executions are logged with step name and result
- [ ] Thinking events include workflow context
- [ ] Can debug why discourse_analyst is stuck
