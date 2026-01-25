# Plan #209: Trigger-Hook Integration

**Status:** 📋 Deferred
**Priority:** Low
**Depends On:** Plan #208 (Workflow Hooks), Plan #169/180 (Triggers)

## Problem

Plan #208 (Workflow Hooks) and Plan #169/180 (Triggers) are intentionally decoupled:
- Hooks are step-based timing (before/after workflow steps)
- Triggers are event-based (when kernel events occur)

Currently, to use trigger results in hooks, agents must create a bridging artifact:

```yaml
# Agent creates a "trigger inbox" artifact
hooks:
  pre_decision:
    - artifact_id: my_trigger_inbox
      method: get_pending_events
      inject_as: triggered_events
```

If this bridging pattern becomes common, we should add sugar to simplify it.

## Proposed Solution (When Needed)

Add direct trigger reference in hooks:

```yaml
hooks:
  pre_decision:
    - from_triggers: ["my_market_watcher", "my_alert_trigger"]
      inject_as: triggered_events
      # Automatically reads pending events from these triggers
      # Clears them after injection (or configurable)
```

### Semantics

| Field | Meaning |
|-------|---------|
| `from_triggers` | List of trigger artifact IDs to read from |
| `inject_as` | Context key for collected events |
| `clear_after` | Whether to clear pending events after reading (default: true) |
| `since_last_step` | Only events since agent's last step (default: true) |

### Implementation Notes

- Would require hooks to know about trigger registry
- Need to handle timing: what counts as "since last step"?
- Need to handle ownership: can only read your own triggers

## Why Deferred

1. **Decoupled systems are simpler** - Fewer interactions, easier to reason about
2. **Bridging artifact works** - Agents can already achieve this, just with extra step
3. **Wait for signal** - If agents frequently create trigger inbox artifacts, that's signal to add sugar
4. **Avoid premature abstraction** - Don't add complexity until proven needed

## Signal to Implement

Implement this plan when:
- Multiple agents independently create "trigger inbox" patterns
- The bridging artifact pattern appears in genesis agents
- Users/developers request this integration

## References

- Plan #208: Workflow Hooks (base system)
- Plan #169: Kernel Event Triggers
- Plan #180: Complete Trigger Integration
