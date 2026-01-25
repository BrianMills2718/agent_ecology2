# Plan #169: Kernel Event Triggers

**Status:** Planned
**Priority:** Medium
**Complexity:** Medium

## Problem

The kernel is purely request-response. Agents cannot register for notifications when events occur - they must poll. This is inefficient and creates latency for time-sensitive coordination.

## Solution

Add event trigger capability allowing agents to register: "when event matching X occurs, invoke my artifact Y."

### Design Decisions (from architecture review)

1. **Filter language:** Field matching with basic operators
   - Simple: `{event_type: "artifact_created"}`
   - Operators: `$in`, `$eq`, `$ne`, `$exists`
   - **Deferred:** Full predicate expressions, agent-defined code

2. **Invocation:** Queued (not synchronous)
   - Prevents trigger loops (A triggers B triggers A)
   - Matches async nature of the system
   - **Deferred:** Synchronous option, depth-limited chains

3. **Storage:** Trigger artifacts
   - Consistent with "everything is artifact"
   - Discoverable, tradeable, manageable
   - **Deferred:** Kernel registry for performance

### Phase 1: Trigger Artifact Type

```python
# Trigger artifact structure
{
    "type": "trigger",
    "content": {
        "filter": {
            "event_type": "artifact_created",
            "metadata.category": {"$in": ["oracle", "tool"]}
        },
        "callback_artifact": "my_handler",
        "callback_method": "on_event",
        "enabled": True
    },
    "created_by": "alice"  # Only alice can create triggers for her artifacts
}
```

### Phase 2: Trigger Registration

Kernel tracks active triggers:

```python
class World:
    _active_triggers: list[TriggerSpec]  # Cached from trigger artifacts

    def _refresh_triggers(self):
        """Scan trigger artifacts, update cache."""
        triggers = self.artifacts.get_by_type("trigger")
        self._active_triggers = [parse_trigger(t) for t in triggers if t.content.get("enabled")]
```

### Phase 3: Event Matching

When event is logged, check triggers:

```python
def _log_event(self, event: dict):
    self.logger.log(event)

    # Check triggers
    for trigger in self._active_triggers:
        if self._matches_filter(event, trigger.filter):
            self._queue_trigger_invocation(trigger, event)
```

### Phase 4: Queued Invocation

Process trigger invocations:

```python
class World:
    _pending_trigger_invocations: list[PendingInvocation]

    def process_pending_triggers(self):
        """Process queued trigger invocations (called by runner)."""
        for invocation in self._pending_trigger_invocations:
            self._execute_invoke(invocation.to_intent())
        self._pending_trigger_invocations.clear()
```

### Phase 5: Spam Prevention

Only callback artifact owner can create triggers:

```python
def _validate_trigger(self, trigger_artifact: Artifact) -> bool:
    callback_id = trigger_artifact.content.get("callback_artifact")
    callback = self.artifacts.get(callback_id)

    # Trigger creator must own the callback
    if callback.created_by != trigger_artifact.created_by:
        return False  # Spam prevention

    return True
```

## Filter Operators (Phase 1)

| Operator | Example | Meaning |
|----------|---------|---------|
| (none) | `{"type": "x"}` | Equals |
| `$eq` | `{"type": {"$eq": "x"}}` | Equals (explicit) |
| `$ne` | `{"type": {"$ne": "x"}}` | Not equals |
| `$in` | `{"type": {"$in": ["a","b"]}}` | In list |
| `$exists` | `{"metadata.foo": {"$exists": true}}` | Field exists |

## Future Enhancements (Deferred)

- Full predicate expressions (`$and`, `$or`, `$not`)
- Agent-defined matcher functions
- Synchronous invocation option
- Kernel registry cache for high-volume events
- Trigger rate limiting
- Trigger priority/ordering

## Testing

- [ ] Create trigger artifact
- [ ] Event matching works
- [ ] Callback invoked after matching event
- [ ] Spam prevention (can't trigger others' artifacts)
- [ ] Disabled triggers don't fire
- [ ] Trigger loops don't crash (queued invocation)

## Files to Modify

| File | Change |
|------|--------|
| `src/world/world.py` | Trigger registry, matching, invocation queue |
| `src/world/artifacts.py` | Trigger artifact type |
| `src/world/logger.py` | Hook for trigger checking |
| `tests/integration/test_triggers.py` | Trigger tests |

## Dependencies

- Plan #168: Artifact Metadata (optional but helpful for filtering)
