# Plan 49: Reasoning in Narrow Waist

**Status:** ✅ Complete

**Verified:** 2026-01-14T16:19:13Z
**Verification Evidence:**
```yaml
completed_by: scripts/complete_plan.py
timestamp: 2026-01-14T16:19:13Z
tests:
  unit: 1347 passed, 7 skipped in 16.33s
  e2e_smoke: PASSED (2.11s)
  e2e_real: PASSED (4.16s)
  doc_coupling: passed
commit: b72bed0
```
**Priority:** High
**Blocked By:** None
**Blocks:** LLM-native monitoring, semantic analysis

---

## Gap

**Current:** Agent reasoning (`thought_process`) is captured as a **side channel**, logged separately from actions. The narrow waist (`ActionIntent`) has no reasoning field - it only sees `{action_type, principal_id, artifact_id, ...}`.

```python
# Current flow - reasoning is a side channel
class ActionResponse(BaseModel):
    thought_process: str  # <- Captured here (LLM output)
    action: Action        # <- Only this goes to narrow waist

# ActionIntent has NO reasoning
@dataclass
class ActionIntent:
    action_type: ActionType
    principal_id: str
    # No reasoning field - kernel never sees "why"
```

Events are scattered:
- `thinking` event: Contains `thought_process`, logged before action execution
- `action` event: Contains action details, but no reasoning

This was an **implementation accident**, not a design choice. The side channel exists because `ActionResponse` (LLM schema) and `ActionIntent` (kernel interface) evolved separately.

**Target:** Every action through the narrow waist requires a `reasoning` field. Action and reasoning are logged together as a single event.

```python
@dataclass
class ActionIntent:
    action_type: ActionType
    principal_id: str
    reasoning: str  # NEW: Required explanation for this action

# Single unified event
logger.log("action", {
    "action_type": "invoke_artifact",
    "artifact_id": "genesis_escrow",
    "reasoning": "Listing my tool for sale because market prices are high...",
    ...
})
```

**Why High Priority:**

1. **Core observability principle** - LLM agents have legible reasoning; we should capture it in the kernel
2. **Enables LLM-native monitoring** - Can analyze reasoning quality, extract strategies, detect anomalies
3. **Removes accidental complexity** - Side channel was implementation accident
4. **Single source of truth** - Action + reasoning in one event, not scattered
5. **Aligns with philosophy** - "Observe, don't prevent" requires observing the *why*, not just *what*

---

## Design Decisions

| Decision | Choice | Rationale |
|----------|--------|-----------|
| Field name | `reasoning` | Clearer than `thought_process`; implies justification |
| Format | Free text (`str`) | Don't constrain agent expression; add structure later via LLM analysis |
| Required | Yes, always | Every action must be justified; empty string allowed but rare |
| Logged with action | Yes | Single event contains both what and why |
| Remove thinking event | Yes (Phase 2) | Superseded by unified action event |

### Why Not Structured Reasoning?

Decided against for now:
- **Constrains agent expression** - May reduce emergent creativity
- **Adds LLM output complexity** - More tokens, higher cost
- **Free text is analyzable** - LLM-as-judge can extract structure post-hoc
- **Can add later** - If analysis needs it, add structured fields incrementally

---

## Plan

### Changes Required

| File | Change |
|------|--------|
| `src/world/actions.py` | Add `reasoning: str` to `ActionIntent` and all subclasses |
| `src/world/actions.py` | Update `parse_intent_from_json()` to extract reasoning |
| `src/world/actions.py` | Update `to_dict()` methods to include reasoning |
| `src/agents/models.py` | Keep `thought_process` for LLM schema, map to `reasoning` |
| `src/simulation/runner.py` | Pass reasoning when creating ActionIntent |
| `src/simulation/runner.py` | Remove separate "thinking" event (Phase 2) |
| `src/dashboard/parser.py` | Read reasoning from action events |

### Steps

**Phase 1: Add field, keep backwards compatibility**

1. **Add reasoning to ActionIntent** (`src/world/actions.py`)
   - Add `reasoning: str = ""` to base class
   - Update all subclasses: NoopIntent, ReadArtifactIntent, WriteArtifactIntent, InvokeArtifactIntent

2. **Update `parse_intent_from_json()`**
   - Extract `reasoning` field from JSON
   - Default to empty string if not provided

3. **Update runner** (`src/simulation/runner.py`)
   - Pass `thought_process` as `reasoning` to ActionIntent
   - Include reasoning in "action" event

4. **Update dashboard parser**
   - Read reasoning from action events

**Phase 2: Remove thinking events (separate PR)**

5. Remove "thinking" event logging
6. Update dashboard to not expect thinking events

---

## Required Tests

### New Tests (TDD)

| Test File | Test Function | What It Verifies |
|-----------|---------------|------------------|
| `tests/unit/test_actions.py` | `test_action_intent_has_reasoning_field` | ActionIntent has reasoning attribute |
| `tests/unit/test_actions.py` | `test_noop_intent_accepts_reasoning` | NoopIntent accepts reasoning |
| `tests/unit/test_actions.py` | `test_read_intent_accepts_reasoning` | ReadArtifactIntent accepts reasoning |
| `tests/unit/test_actions.py` | `test_write_intent_accepts_reasoning` | WriteArtifactIntent accepts reasoning |
| `tests/unit/test_actions.py` | `test_invoke_intent_accepts_reasoning` | InvokeArtifactIntent accepts reasoning |
| `tests/unit/test_actions.py` | `test_parse_intent_extracts_reasoning` | JSON parsing extracts reasoning |
| `tests/unit/test_actions.py` | `test_parse_intent_default_reasoning` | Missing reasoning defaults to "" |
| `tests/unit/test_actions.py` | `test_intent_to_dict_includes_reasoning` | to_dict() includes reasoning |
| `tests/integration/test_action_logging.py` | `test_action_event_includes_reasoning` | Logged events have reasoning |

### Existing Tests (Must Pass)

| Test Pattern | Why |
|--------------|-----|
| `tests/unit/test_actions.py` | Action parsing still works |
| `tests/unit/test_async_agent.py` | Agent response handling unchanged |
| `tests/integration/test_runner.py` | E2E simulation works |

---

## E2E Verification

```bash
# Run simulation
python run.py --ticks 3 --agents 1

# Verify reasoning in log
grep '"reasoning"' run.jsonl | head -3

# Expected: action events have reasoning field
```

---

## Verification

### Tests & Quality
- [ ] All required tests pass: `python scripts/check_plan_tests.py --plan 43`
- [ ] Full test suite passes: `pytest tests/`
- [ ] Type check passes: `python -m mypy src/ --ignore-missing-imports`

### Documentation
- [ ] `docs/architecture/current/execution_model.md` updated
- [ ] Doc-coupling check passes

### Completion
- [ ] Plan status -> Complete
- [ ] `plans/CLAUDE.md` index updated
- [ ] Claim released
- [ ] PR merged

---

## Future Work (Enabled by This Plan)

Once reasoning is in the narrow waist:

1. **LLM-as-judge** - Score reasoning quality per action
2. **Strategy extraction** - Cluster agents by reasoning patterns
3. **Goal coherence** - Do actions match stated goals?
4. **Anomaly detection** - Flag reasoning that doesn't match behavior
5. **Semantic search** - Find actions about "escrow" or "trading"

---

## Notes

### Empty Reasoning

Allow empty string for now:
```python
reasoning: str = ""  # Valid, but should be rare
```

If agents abuse this, add validation later.
