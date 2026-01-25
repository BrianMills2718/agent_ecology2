# Plan #185: Time-Based Scheduling

**Status:** Planned
**Priority:** Medium
**Complexity:** Medium-High
**Blocks:** Time-based contracts, scheduled tasks

## Problem

The kernel has no mechanism for scheduling future execution. All triggers are event-driven and fire immediately. This prevents:

1. **Delayed execution** - "Invoke this method in 100 ticks"
2. **Time-based contracts** - Payment plans, vesting schedules
3. **Scheduled tasks** - Periodic maintenance, cleanup
4. **Deadlines** - "If no response by tick N, cancel"

### Current Behavior

```python
# Triggers fire immediately on matching events
class TriggerRegistry:
    def fire(self, event_type, event_data):
        for trigger in self.active_triggers:
            if self._matches(trigger, event_type, event_data):
                # Fires NOW, no delay option
                self._queue_invocation(trigger)
```

No `fire_at_tick` or `scheduled_for` field exists.

## Solution

Add tick-indexed scheduling to the trigger system.

### Option A: Scheduled Triggers (Recommended)

Extend TriggerSpec with optional scheduling:

```python
@dataclass
class TriggerSpec:
    id: str
    event_type: str
    filter: dict
    callback_artifact_id: str
    callback_method: str
    # NEW: Optional scheduling
    fire_at_tick: int | None = None  # Fire at specific tick
    fire_after_ticks: int | None = None  # Fire N ticks from registration
```

### Option B: Separate Scheduler

Create a dedicated scheduler alongside triggers:

```python
class KernelScheduler:
    def __init__(self):
        self.scheduled: dict[int, list[ScheduledAction]] = defaultdict(list)

    def schedule(self, at_tick: int, action: ScheduledAction):
        self.scheduled[at_tick].append(action)

    def tick(self, current_tick: int):
        for action in self.scheduled.pop(current_tick, []):
            self._execute(action)
```

### Implementation (Option A)

1. **Extend TriggerSpec** with `fire_at_tick` field
2. **Add scheduled queue** in TriggerRegistry:
   ```python
   self.scheduled_triggers: dict[int, list[TriggerSpec]] = defaultdict(list)
   ```
3. **Kernel loop integration** in World.step():
   ```python
   def step(self):
       # ... existing logic ...

       # Fire scheduled triggers
       scheduled = self.trigger_registry.get_scheduled(self.tick_number)
       for trigger in scheduled:
           self._execute_trigger(trigger)
   ```
4. **KernelActions method**:
   ```python
   def schedule_trigger(self, trigger_spec: TriggerSpec, at_tick: int):
       """Schedule a trigger to fire at a specific tick."""
       trigger_spec.fire_at_tick = at_tick
       self.trigger_registry.schedule(trigger_spec)
   ```

### Agent Interface

```python
# Schedule a callback for tick 1000
kernel_actions.register_trigger({
    "event_type": "scheduled",  # Special type
    "fire_at_tick": 1000,
    "callback_artifact_id": "my_agent",
    "callback_method": "handle_deadline"
})

# Or schedule relative to now
kernel_actions.register_trigger({
    "event_type": "scheduled",
    "fire_after_ticks": 100,  # 100 ticks from now
    "callback_artifact_id": "my_agent",
    "callback_method": "periodic_check"
})
```

## Testing

1. Schedule trigger for future tick, verify it fires at correct time
2. Schedule multiple triggers for same tick, verify all fire
3. Cancel scheduled trigger before it fires
4. Verify scheduled triggers survive checkpoint/restore
5. Verify `fire_after_ticks` calculates correctly from current tick

## Acceptance Criteria

1. Triggers can be scheduled for specific future ticks
2. Scheduled triggers fire in the correct tick
3. Agents can cancel scheduled triggers
4. Scheduled triggers persist through checkpoint/restore
5. `kernel_actions.register_trigger()` supports `fire_at_tick` parameter

## Dependencies

- Plan #180 (Trigger Integration) should complete first
- This extends the trigger system, not replaces it

## Future Enhancements

- Recurring schedules ("every N ticks")
- Cron-like expressions
- Priority ordering within same tick
- Resource cost for scheduling (prevent spam)
