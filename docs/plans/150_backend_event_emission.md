# Plan #150: Backend Event Emission

**Status:** 📋 Planned
**Priority:** High
**Blocked By:** ADR-0020 (Event Schema Contract)
**Blocks:** -

---

## Gap

**Current:** Backend tracks resources but doesn't emit events when they change:
- `ResourceManager` tracks llm_budget, llm_tokens, disk - but no events on change
- `RateTracker` manages rate limiting - no visibility to dashboard
- Dashboard shows 0% disk because no `resource_allocated` events exist
- Action events don't include resource consumption details

**Target:** Emit comprehensive resource events per ADR-0020:
- `resource_consumed` on token usage
- `resource_allocated` on disk usage
- `resource_spent` on budget depletion
- `agent_state` on material state changes
- Action events include resource delta

**Why High:** Dashboard needs this data to display accurate resource status. Currently disk is always 0% because events don't exist.

---

## References Reviewed

- `src/world/resource_manager.py` - ResourceManager tracks balances/quotas/rates
- `src/world/logger.py` - EventLogger.log() for writing events
- `src/world/world.py:770-785` - _log_action() current implementation
- `src/world/world.py:820-837` - Disk quota check (has data but doesn't log)
- `docs/adr/0020-event-schema-contract.md` - Event schema contract

---

## Files Affected

**Modify:**
- `src/world/resource_manager.py` - Add event emission hooks
- `src/world/world.py` - Emit resource events on state changes
- `src/world/logger.py` - Add resource event helper methods
- `tests/unit/test_resource_manager.py` - Test event emission
- `tests/unit/test_world.py` - Test resource events in actions

**Create:**
- `tests/unit/test_resource_events.py` - Dedicated resource event tests

---

## Plan

### Phase 1: Logger Extensions

| Step | Description |
|------|-------------|
| 1.1 | Add `log_resource_consumed()` helper to EventLogger |
| 1.2 | Add `log_resource_allocated()` helper to EventLogger |
| 1.3 | Add `log_resource_spent()` helper to EventLogger |
| 1.4 | Add `log_agent_state()` helper to EventLogger |

### Phase 2: ResourceManager Event Emission

| Step | Description |
|------|-------------|
| 2.1 | Inject logger into ResourceManager |
| 2.2 | Emit `resource_consumed` on `consume_rate()` |
| 2.3 | Emit `resource_allocated` on `allocate()` |
| 2.4 | Emit `resource_spent` on `spend()` |

### Phase 3: World Event Emission

| Step | Description |
|------|-------------|
| 3.1 | Update `_log_action()` to include resource delta |
| 3.2 | Emit `agent_state` after material state changes |
| 3.3 | Emit disk allocation events on artifact write |

### Phase 4: Deprecate "tick" in events

| Step | Description |
|------|-------------|
| 4.1 | Add `sequence` field to events (monotonic counter) |
| 4.2 | Keep `tick` for backwards compatibility but document deprecation |

---

## Required Tests

### New Tests (TDD)

| Test File | Test Function | What It Verifies |
|-----------|---------------|------------------|
| `tests/unit/test_resource_events.py` | `test_token_consumption_logged` | Token usage emits resource_consumed event |
| `tests/unit/test_resource_events.py` | `test_disk_allocation_logged` | Disk allocation emits resource_allocated event |
| `tests/unit/test_resource_events.py` | `test_budget_spend_logged` | Budget spend emits resource_spent event |
| `tests/unit/test_resource_events.py` | `test_action_includes_resource_delta` | Action events include resources used |
| `tests/unit/test_resource_events.py` | `test_agent_state_on_material_change` | Material changes emit agent_state event |
| `tests/unit/test_resource_events.py` | `test_sequence_field_present` | All events have sequence field |

### Existing Tests (Must Pass)

| Test Pattern | Why |
|--------------|-----|
| `tests/unit/test_resource_manager.py` | ResourceManager functionality unchanged |
| `tests/unit/test_world.py` | World action processing unchanged |
| `tests/integration/test_simulation*.py` | Full simulation still works |

---

## E2E Verification

| Scenario | Steps | Expected Outcome |
|----------|-------|------------------|
| Disk usage tracked | 1. Run simulation 2. Agent writes artifact 3. Check run.jsonl | `resource_allocated` event present with correct bytes |
| Token usage tracked | 1. Run simulation 2. Agent makes LLM call 3. Check run.jsonl | `resource_consumed` event present with token count |

```bash
# Verify events in log
grep "resource_allocated\|resource_consumed\|resource_spent" logs/latest/events.jsonl
```

---

## Verification

### Tests & Quality
- [ ] All required tests pass: `python scripts/check_plan_tests.py --plan 150`
- [ ] Full test suite passes: `pytest tests/`
- [ ] Type check passes: `python -m mypy src/world/ --ignore-missing-imports`

### Documentation
- [ ] `docs/architecture/current/resources.md` updated
- [ ] Doc-coupling check passes

### Completion Ceremony
- [ ] Plan file status → `✅ Complete`
- [ ] `plans/CLAUDE.md` index updated
- [ ] Claim released
- [ ] PR merged

---

## Notes

### Event Volume Consideration

This will increase event volume. For a simulation with N agents making M actions:
- Before: ~M action events
- After: ~M action events + ~M resource events

Mitigation: Resource events are small (50-100 bytes each). Log rotation and the summary.jsonl handle volume.

### Backwards Compatibility

- `tick` field retained but deprecated
- New `sequence` field added
- Dashboard should handle both during transition

### Resource Event Structure (ADR-0020)

```python
# Token consumption
{
    "event_type": "resource_consumed",
    "timestamp": "2026-01-21T12:00:00Z",
    "sequence": 42,
    "principal_id": "agent_alpha",
    "resource": "llm_tokens",
    "amount": 1500,
    "balance_after": 8500,
    "quota": 10000,
    "rate_window_remaining": 6500
}

# Disk allocation
{
    "event_type": "resource_allocated",
    "timestamp": "2026-01-21T12:00:01Z",
    "sequence": 43,
    "principal_id": "agent_alpha",
    "resource": "disk",
    "amount": 2048,
    "used_after": 5120,
    "quota": 10000
}
```
