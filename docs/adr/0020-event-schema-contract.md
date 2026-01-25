# ADR-0020: Event Schema Contract

**Status:** Accepted
**Date:** 2026-01-21
**Accepted:** 2026-01-25

## Context

The dashboard and backend have grown independently with no formal contract for event data. This creates multiple problems:

1. **Terminology confusion** - Dashboard shows "Compute" but backend tracks `llm_tokens` and `llm_budget` separately. "Tick" terminology persists despite continuous execution model.

2. **Missing data** - Backend tracks disk usage and rate limits in ResourceManager but never emits events when these change. Dashboard shows 0% disk because no events exist.

3. **Unclear data flow** - Dashboard parses JSONL hoping for fields that may or may not exist. No schema validation, no clear contract.

4. **Architectural debt** - Dashboard parser.py is 1752 lines doing parsing, state tracking, and metric computation. No separation of concerns.

The root cause: no defined contract between event producer (backend) and event consumer (dashboard).

## Decision

### 1. Define Canonical Event Types

All events have a common envelope:

```python
{
    "timestamp": str,       # ISO 8601 UTC
    "event_type": str,      # One of defined types below
    "sequence": int,        # Monotonic event counter (replaces 'tick' for ordering)
    ...event_specific_fields
}
```

**Note:** The `tick` field is retained for backwards compatibility but deprecated. Use `sequence` for event ordering. The term "tick" in code and UI should be replaced with "event" or "sequence" where appropriate.

### 2. Resource Events (New)

Emit explicit events when resources change:

```python
# When tokens consumed (LLM call)
{
    "event_type": "resource_consumed",
    "sequence": 42,
    "principal_id": "agent_alpha",
    "resource": "llm_tokens",        # Renewable (rate-limited)
    "amount": 1500,
    "balance_after": 8500,
    "quota": 10000,
    "rate_window_remaining": 6500    # For renewable resources
}

# When disk allocated (artifact written)
{
    "event_type": "resource_allocated",
    "sequence": 43,
    "principal_id": "agent_alpha",
    "resource": "disk",              # Allocatable (quota-based)
    "amount": 2048,
    "used_after": 5120,
    "quota": 10000
}

# When budget spent (depletable)
{
    "event_type": "resource_spent",
    "sequence": 44,
    "principal_id": "agent_alpha",
    "resource": "llm_budget",        # Depletable (never recovers)
    "amount": 0.05,
    "balance_after": 0.95
}
```

### 3. Resource Types (from Plan #95)

| Type | Behavior | Examples | Dashboard Display |
|------|----------|----------|-------------------|
| DEPLETABLE | Once spent, gone | `llm_budget` ($) | "Budget: $X.XX remaining" |
| ALLOCATABLE | Quota-based, reclaimable | `disk` (bytes) | "Disk: X% (Y/Z bytes)" |
| RENEWABLE | Rate-limited, refills over time | `llm_tokens` | "Tokens: X/s available" |

### 4. Action Events (Existing, Clarified)

Action events include resource context:

```python
{
    "event_type": "action",
    "sequence": 45,
    "principal_id": "agent_alpha",
    "action_type": "invoke",
    "target": "genesis_ledger",
    "success": true,
    "duration_ms": 150,
    "resources": {
        "llm_tokens_used": 500,
        "disk_delta": 0
    }
}
```

### 5. Agent State Events

Emit when agent state changes materially:

```python
{
    "event_type": "agent_state",
    "sequence": 46,
    "agent_id": "agent_alpha",
    "status": "active",           # active | frozen | terminated
    "scrip": 150.5,
    "resources": {
        "llm_tokens": {"used": 1500, "quota": 10000, "rate_remaining": 6500},
        "llm_budget": {"used": 0.05, "initial": 1.0},
        "disk": {"used": 5120, "quota": 10000}
    },
    "frozen_reason": null         # If frozen, why
}
```

### 6. Dashboard Must Not Infer

The dashboard should display what events explicitly state, not infer from absence:

- **Good:** Show disk usage from `resource_allocated` events
- **Bad:** Assume disk is 0 because no events mention it

If data is missing, show "N/A" or "No data", not "0%".

### 7. Terminology Migration

| Old Term | New Term | Reason |
|----------|----------|--------|
| tick | sequence/event | Continuous execution, not turn-based |
| compute | llm_tokens | Clarity about what's measured |
| Compute % | Token Usage | Dashboard column header |

## Consequences

### Positive

- Clear contract enables independent evolution of backend and dashboard
- Dashboard can validate events against schema
- Missing data visible as "no data" not wrong data
- Resource tracking complete (disk, rate limits now visible)
- Terminology confusion eliminated

### Negative

- Backend must emit more events (resource changes)
- Dashboard refactor required to consume new events
- Breaking change for any external tools parsing run.jsonl

### Neutral

- Event volume increases (more granular resource events)
- Old events still parseable (backwards compatible envelope)

## Implementation

1. **Plan #149:** Dashboard architecture refactor - clean separation of parser/state/metrics
2. **Plan #151:** Backend event emission - emit resource events on every change
3. **Migration:** Dashboard supports both old and new event formats during transition

## Related

- Plan #95: Unified Resource System (ResourceManager)
- ADR-0014: Continuous Execution Primary
- ADR-0008: Token Bucket Rate Limiting
