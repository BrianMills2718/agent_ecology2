# Plan #180: Complete Trigger Integration

**Status:** Planned
**Priority:** High
**Complexity:** Medium
**Blocks:** Real-time coordination patterns

## Problem

Plan #169 (Kernel Event Triggers) created `TriggerRegistry` with filter matching logic, but the integration with World.py and the simulation runner was never completed.

**Current state:**
- `TriggerRegistry` class exists in `src/world/triggers.py`
- Filter matching logic works (unit tests pass)
- World.py does NOT import or use TriggerRegistry
- Runner does NOT call `process_pending_triggers()`
- Triggers do NOT actually fire

**Impact:**
- Agents must poll for changes (inefficient)
- Real-time coordination patterns have unnecessary friction
- Pub-sub pattern doesn't work as designed

## Solution

Complete the integration described in Plan #169 Phases 2-4:

### Phase 1: World Integration

```python
# src/world/world.py
from .triggers import TriggerRegistry

class World:
    def __init__(self, ...):
        ...
        self.trigger_registry = TriggerRegistry(self.artifacts)

    def _log_event(self, event: dict):
        """Log event and check triggers."""
        self.logger.log(event)
        self.trigger_registry.queue_matching_invocations(event)
```

### Phase 2: Event Hook

Ensure all state-changing operations call trigger check:
- `write_artifact()` → emit event → check triggers
- `transfer_scrip()` → emit event → check triggers
- etc.

### Phase 3: Runner Integration

```python
# src/simulation/runner.py or agent_loop.py
def process_loop_iteration():
    # ... agent action ...

    # Process pending trigger invocations
    pending = world.trigger_registry.get_pending_invocations()
    for invocation in pending:
        world.execute_invoke(...)
    world.trigger_registry.clear_pending_invocations()
```

### Phase 4: Refresh on Artifact Changes

When trigger artifacts are created/updated/deleted, refresh the registry:

```python
def _on_trigger_artifact_change(self, artifact_id: str):
    if artifact.type == "trigger":
        self.trigger_registry.refresh()
```

## Testing

### Unit Tests
- Trigger fires on matching event
- Trigger doesn't fire on non-matching event
- Callback is invoked with event data
- Spam prevention (can't trigger others' artifacts)

### Integration Tests
- Agent A writes artifact, Agent B's trigger fires
- Trigger chain doesn't infinite loop
- Disabled triggers don't fire

## Acceptance Criteria

1. Triggers actually fire when matching events occur
2. Callbacks are invoked asynchronously (queued, not synchronous)
3. Spam prevention works (only own artifacts)
4. Performance acceptable (trigger check < 10ms)

## References

- Plan #169: Kernel Event Triggers (original design)
- `src/world/triggers.py`: Existing implementation
- `tests/unit/test_event_triggers.py`: Existing tests
