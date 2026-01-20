# Plan #117: Remove Duplicate Action Logging

**Status:** 📋 Planned
**Priority:** Medium
**Blocked By:** None
**Blocks:** None

---

## Gap

**Current:** Actions are logged TWICE with different formats:
1. **OLD format** (runner.py:1068-1080) - flat structure: `{agent_id, action_type, success, message}`
2. **NEW format** (world.py:745-750) - nested: `{intent: {..., reasoning}, result: {...}, scrip_after}`

This creates duplicate events in events.jsonl (286 old + 286 new for same 286 actions).

**Target:** Single action event per action with consistent nested structure from world.py.

**Why Medium:** Reduces log noise and dashboard parsing confusion. Clean-up of technical debt.

---

## References Reviewed

- `src/simulation/runner.py:1068-1080` - old-format logging that duplicates
- `src/world/world.py:745-750` - new-format `_log_action()` method (superior format)
- `src/world/actions.py:256-259` - reasoning parsing in Intent
- `src/world/actions.py:41` - `intent.to_dict()` includes reasoning
- `config/schema.yaml` - `logging.truncation.result_data` (default 1000)

---

## Files Affected

- `src/simulation/runner.py` (modify)

---

## Plan

### Changes Required
| File | Change |
|------|--------|
| `src/simulation/runner.py` | Delete lines 1068-1080 (duplicate logging) |

### Steps
1. Remove the redundant old-format logging from runner.py (13 lines)

The world.py logging is superior because:
- Nested intent/result structure for clear separation
- Includes `reasoning` field (Plan #49 already captures this)
- Includes `scrip_after` for economic tracking
- Includes truncated `data` in results
- Already has configurable truncation via `logging.truncation.result_data`

---

## Required Tests

### Existing Tests (Must Pass)

These tests must still pass after changes:

| Test Pattern | Why |
|--------------|-----|
| `tests/integration/test_runner.py` | Runner integration unchanged |
| `tests/integration/test_action_logging.py` | Action logging still works |

---

## E2E Verification

| Scenario | Steps | Expected Outcome |
|----------|-------|------------------|
| Action logging works | 1. Run simulation: `python run.py --ticks 5 --dashboard` 2. Check `logs/latest/events.jsonl` | Each action appears ONCE (not twice) with nested `intent` and `result` structure |

---

## Verification

### Tests & Quality
- [ ] All required tests pass: `python scripts/check_plan_tests.py --plan 117`
- [ ] Full test suite passes: `pytest tests/`
- [ ] Type check passes: `python -m mypy src/ --ignore-missing-imports`

### Documentation
- [ ] No doc updates needed (internal logging change)

---

## Notes

**Note on Empty Reasoning:** If `intent.reasoning` is empty in logs, that's because the LLM didn't output a detailed `thought_process` or `action_rationale`. This is separate from the logging duplication issue. The infrastructure to capture reasoning exists (Plan #49); whether agents populate it depends on their prompts and the cognitive mode.
