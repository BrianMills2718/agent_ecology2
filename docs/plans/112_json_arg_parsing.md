# Gap 112: Auto-Parse JSON String Arguments

**Status:** 📋 Planned
**Priority:** **High**
**Blocked By:** -
**Blocks:** -

---

## Gap

**Current:** When agents invoke artifacts with dict/object arguments, the LLM generates JSON strings in the args list (e.g., `["register", "{\"id\": \"foo\"}"]`). The executor passes these strings directly to the artifact's `run()` method, causing `AttributeError: 'str' object has no attribute 'get'` when the artifact tries to use them as dicts.

**Target:** The executor should auto-detect JSON strings in args and parse them to Python objects before passing to artifacts. This allows agents to naturally express structured data while artifacts receive proper Python types.

**Why High:** This causes repeated failures that agents can diagnose but cannot fix. In simulations, agents like delta_3 hit error limits (8 errors → pause) because they understand "I'm passing a JSON string instead of a dictionary" but the LLM keeps generating strings. This blocks productive artifact interaction.

---

## References Reviewed

- `logs/run_20260119_145007/events.jsonl` - delta_3 repeatedly fails with `'str' object has no attribute 'get'`
- `src/world/executor.py` - Where artifact invocation happens
- `src/world/actions.py` - InvokeArtifactAction definition
- `src/agents/schema.py` - Action schema shown to LLM

---

## Files Affected

- src/world/executor.py (modify)
- tests/unit/test_executor.py (modify)
- src/agents/schema.py (modify)

---

## Plan

### Changes Required

| File | Change |
|------|--------|
| `src/world/executor.py` | Add `_parse_json_args()` helper that attempts JSON parse on string args |
| `tests/unit/test_executor.py` | Test JSON string args are parsed to dicts |

### Implementation

In `executor.py`, before invoking an artifact's `run()` method:

```python
def _parse_json_args(args: list[Any]) -> list[Any]:
    """Parse JSON strings in args to Python objects.

    LLMs often generate JSON strings for dict arguments.
    This auto-converts them to proper Python types.
    """
    import json
    parsed = []
    for arg in args:
        if isinstance(arg, str):
            # Try to parse as JSON
            try:
                parsed.append(json.loads(arg))
            except (json.JSONDecodeError, ValueError):
                # Not valid JSON, keep as string
                parsed.append(arg)
        else:
            parsed.append(arg)
    return parsed
```

Call this before `artifact.run(*args)`:
```python
parsed_args = _parse_json_args(args)
result = artifact.run(*parsed_args)
```

### Edge Cases

1. **Valid JSON strings that should stay strings** - A string like `"hello"` is valid JSON but should remain a string. Solution: Only parse if result is dict or list.
2. **Nested JSON** - Handled automatically by `json.loads()`
3. **Numbers as strings** - `"123"` parses to `123`. This is probably desired behavior.

---

## Required Tests

### New Tests (TDD)

| Test File | Test Function | What It Verifies |
|-----------|---------------|------------------|
| `tests/unit/test_executor.py` | `test_json_string_arg_parsed_to_dict` | `'{"a": 1}'` becomes `{"a": 1}` |
| `tests/unit/test_executor.py` | `test_json_string_list_parsed` | `'[1, 2, 3]'` becomes `[1, 2, 3]` |
| `tests/unit/test_executor.py` | `test_plain_string_unchanged` | `'hello'` stays `'hello'` |
| `tests/unit/test_executor.py` | `test_mixed_args_parsed` | `['register', '{"id": "x"}']` → `['register', {"id": "x"}]` |

### Existing Tests (Must Pass)

| Test Pattern | Why |
|--------------|-----|
| `tests/unit/test_executor.py` | Executor behavior preserved |
| `tests/integration/test_runner.py` | E2E invocation still works |

---

## E2E Verification

| Scenario | Steps | Expected Outcome |
|----------|-------|------------------|
| Agent invokes with JSON string args | 1. Run simulation 2. Agent creates artifact expecting dict 3. Agent invokes with JSON string arg | Invocation succeeds, no type errors |

```bash
# Run E2E verification
pytest tests/e2e/test_real_e2e.py -v --run-external
```

---

## Verification

### Tests & Quality
- [ ] All required tests pass: `python scripts/check_plan_tests.py --plan 112`
- [ ] Full test suite passes: `pytest tests/`
- [ ] Type check passes: `python -m mypy src/ --ignore-missing-imports`
- [ ] **E2E verification passes:** `pytest tests/e2e/test_real_e2e.py -v --run-external`

### Documentation
- [ ] Doc-coupling check passes: `python scripts/check_doc_coupling.py`

### Completion Ceremony
- [ ] Plan file status → `✅ Complete`
- [ ] `plans/CLAUDE.md` index → `✅ Complete`
- [ ] Claim released from Active Work table (root CLAUDE.md)
- [ ] Branch merged or PR created

---

## Notes

**Alternative approaches considered:**

1. **Fix in action schema** - Tell LLM to use Python dict syntax. Problem: LLMs naturally produce JSON, fighting this is hard.
2. **Fix in agent code** - Parse before sending. Problem: Adds complexity to every agent.
3. **Fix in executor** (chosen) - Central fix, handles all cases, backwards compatible.

**Risk:** Could accidentally parse strings that should stay strings. Mitigation: Only convert if result is dict/list, not primitives.
