# Plan #121: Unclosed File Handle Fix

**Status:** ✅ Complete

**Verified:** 2026-01-20T13:15:39Z
**Verification Evidence:**
```yaml
completed_by: scripts/complete_plan.py
timestamp: 2026-01-20T13:15:39Z
tests:
  unit: 1892 passed, 10 skipped, 3 warnings, 1 rerun in 63.68s (0:01:03)
  e2e_smoke: skipped (--skip-e2e)
  e2e_real: skipped (--skip-real-e2e)
  doc_coupling: passed
commit: e1fd626
```
**Priority:** **Critical**
**Blocked By:** None
**Blocks:** None

---

## Gap

**Current:** `src/simulation/runner.py:803` uses `sum(1 for _ in open(log_path))` which leaks file descriptors. The `open()` call in a generator expression is never closed.

**Target:** Use context manager to properly close file handles.

**Why Critical:** File descriptor exhaustion will cause simulation failures after repeated runs. This is a resource leak that accumulates over time.

---

## References Reviewed

- `src/simulation/runner.py:803` - The problematic line
- Python documentation on context managers and file handling

---

## Files Affected

- `src/simulation/runner.py` (modify)

---

## Plan

### Changes Required
| File | Change |
|------|--------|
| `src/simulation/runner.py` | Replace bare `open()` with context manager |

### Steps
1. Find the line with `sum(1 for _ in open(log_path))`
2. Replace with proper context manager:
   ```python
   with open(log_path) as f:
       event_count = sum(1 for _ in f)
   ```

---

## Required Tests

### New Tests (TDD)

| Test File | Test Function | What It Verifies |
|-----------|---------------|------------------|
| N/A | N/A | Trivial fix - existing tests cover functionality |

### Existing Tests (Must Pass)

| Test Pattern | Why |
|--------------|-----|
| `tests/unit/test_runner.py` | Runner functionality unchanged |
| `tests/integration/test_runner.py` | Integration behavior unchanged |

---

## E2E Verification

Not required for this trivial fix - no behavioral change, just resource management improvement.

---

## Verification

### Tests & Quality
- [ ] All existing tests pass: `pytest tests/`
- [ ] Type check passes: `python -m mypy src/ --ignore-missing-imports`

### Documentation
- [ ] No doc changes needed (internal fix)

### Completion Ceremony
- [ ] Plan file status → `✅ Complete`
- [ ] `plans/CLAUDE.md` index → `✅ Complete`

---

## Notes
This is a straightforward resource leak fix. The generator expression with `open()` works but never closes the file handle, relying on garbage collection which is non-deterministic.
