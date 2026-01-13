# Gap 26: Vulture Observability

**Status:** 📋 Planned
**Priority:** Medium
**Blocked By:** None
**Blocks:** None

---

## Gap

**Current:** Limited visibility for vulture capitalists to assess rescue opportunities

**Target:** Full observability for market-based rescue mechanism

---

## Problem Statement

The "Vulture Capitalist" pattern enables market-based rescue of frozen agents. Agents with excess resources can "rescue" frozen agents by transferring resources to them, hoping for reciprocation or asset seizure.

For this to work, vultures need data to assess risk and opportunity:
- Which agents are frozen?
- What assets do they own?
- Are they worth rescuing?

Currently:
- `frozen_agent_count` KPI exists but no events for individual frozen agents
- `last_action_tick` exists for activity tracking
- No AGENT_FROZEN or AGENT_UNFROZEN events in event log
- No easy way to query artifacts owned by an agent

---

## Plan

### Phase 1: Freeze/Unfreeze Events

Add events to the event log when agents freeze or unfreeze.

**Event: AGENT_FROZEN**
```python
{
    "event_type": "agent_frozen",
    "tick": 1500,
    "agent_id": "agent_alice",
    "reason": "compute_exhausted",  # or "rate_limited", "manual"
    "scrip_balance": 200,
    "compute_remaining": 0,
    "owned_artifacts": ["art_1", "art_2"],
    "last_action_tick": 1480
}
```

**Event: AGENT_UNFROZEN**
```python
{
    "event_type": "agent_unfrozen",
    "tick": 1600,
    "agent_id": "agent_alice",
    "unfrozen_by": "vulture_bob",  # or "self" if natural recovery
    "resources_transferred": {
        "compute": 100,
        "scrip": 0
    }
}
```

### Phase 2: Asset Inventory API

Add methods to query artifacts owned by an agent:

```python
# In GenesisStore or World
def get_artifacts_by_owner(owner_id: str) -> list[str]:
    """Return artifact IDs owned by the given principal."""
    ...
```

Expose via dashboard API:
```python
@app.get("/api/agents/{agent_id}/artifacts")
async def get_agent_artifacts(agent_id: str) -> list[dict]:
    """Get artifacts owned by agent."""
    ...
```

### Phase 3: Public Ledger Verification

Verify that `genesis_ledger.get_balance(id)` is callable by any principal without access restrictions. This enables vultures to assess agent wealth.

### Changes Required

| File | Change |
|------|--------|
| `src/world/world.py` | Emit AGENT_FROZEN/AGENT_UNFROZEN events |
| `src/world/logger.py` | Add event types if needed |
| `src/world/artifacts.py` | Add `get_artifacts_by_owner()` method |
| `src/dashboard/server.py` | Add `/api/agents/{id}/artifacts` endpoint |
| `src/dashboard/parser.py` | Parse new event types |
| `src/dashboard/models.py` | Add models for freeze events |
| `docs/architecture/current/supporting_systems.md` | Document new events |

### Implementation Steps

1. **Add freeze detection in World.tick()** - Detect when agent transitions to frozen
2. **Emit AGENT_FROZEN event** - With asset summary
3. **Add unfreeze detection** - Detect when agent becomes unfrozen
4. **Emit AGENT_UNFROZEN event** - With rescuer info if applicable
5. **Add `get_artifacts_by_owner()`** - Query method for asset inventory
6. **Add dashboard endpoint** - API for artifact inventory
7. **Update parser** - Parse new event types
8. **Verify public ledger** - Confirm no access restrictions

---

## Required Tests

### Unit Tests
- `tests/unit/test_freeze_events.py::test_agent_frozen_event_emitted` - Event on compute exhaustion
- `tests/unit/test_freeze_events.py::test_agent_unfrozen_event_emitted` - Event on resource transfer
- `tests/unit/test_freeze_events.py::test_frozen_event_includes_assets` - Asset inventory in event
- `tests/unit/test_freeze_events.py::test_unfrozen_event_includes_rescuer` - Rescuer ID tracked

### Integration Tests
- `tests/integration/test_vulture_observability.py::test_freeze_event_in_log` - Event appears in run.jsonl
- `tests/integration/test_vulture_observability.py::test_artifacts_by_owner_api` - API returns owned artifacts
- `tests/integration/test_vulture_observability.py::test_public_ledger_access` - Balance readable by all

---

## E2E Verification

Run simulation with agent freezing:

```bash
python run.py --ticks 50 --agents 3 --config config/test_freeze.yaml
# Agents should run out of compute and freeze
# Check run.jsonl for agent_frozen events
grep "agent_frozen" run.jsonl | jq .
```

Expected: AGENT_FROZEN events with asset summaries when agents exhaust compute.

---

## Out of Scope

- **Vulture rescue contracts** - Not implementing actual rescue logic
- **Reputation system** - Not tracking vulture success rates
- **Automatic rescue** - No system-level rescue mechanism
- **Asset seizure** - Not implementing forced asset transfer

These are emergent patterns, not system features.

---

## Verification

- [ ] Tests pass
- [ ] Docs updated
- [ ] Implementation matches target

---

## Notes

This plan provides **observability only**, not mechanism. The vulture capitalist pattern should emerge from agent behavior, not be prescribed by the system.

Key design decision: We emit events and provide queries, but don't build any rescue logic. Agents decide what to do with the information.

Reference: docs/DESIGN_CLARIFICATIONS.md "Vulture Observability Requirements (DECIDED 2026-01-11)"
