# Gap N: [Name]

**Status:** ❌ Needs Plan
**Priority:** High | Medium | Low
**Blocked By:** #X, #Y
**Blocks:** #A, #B

---

## Gap

**Current:** What exists now

**Target:** What we want

**Why [Priority]:** Why this priority level

---

## Plan

### Changes Required
| File | Change |
|------|--------|
| ... | ... |

### Steps
1. Step one
2. Step two

---

## Required Tests

### New Tests (TDD)

Create these tests FIRST, before implementing:

| Test File | Test Function | What It Verifies |
|-----------|---------------|------------------|
| `tests/test_feature.py` | `test_happy_path` | Basic functionality works |
| `tests/test_feature.py` | `test_edge_case` | Handles edge case |

### Existing Tests (Must Pass)

These tests must still pass after changes:

| Test Pattern | Why |
|--------------|-----|
| `tests/test_related.py` | Integration unchanged |
| `tests/test_other.py::test_specific` | Specific behavior preserved |

---

## Verification

### Tests & Quality
- [ ] All required tests pass: `python scripts/check_plan_tests.py --plan N`
- [ ] Full test suite passes: `pytest tests/`
- [ ] Type check passes: `python -m mypy src/ --ignore-missing-imports`

### Documentation
- [ ] `docs/architecture/current/` updated
- [ ] Doc-coupling check passes: `python scripts/check_doc_coupling.py`
- [ ] [Plan-specific criteria]

### Completion Ceremony
- [ ] Plan file status → `✅ Complete`
- [ ] `plans/CLAUDE.md` index → `✅ Complete`
- [ ] Claim released from Active Work table (root CLAUDE.md)
- [ ] Branch merged or PR created

---

## Notes
[Design decisions, alternatives considered, etc.]
