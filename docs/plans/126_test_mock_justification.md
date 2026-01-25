# Plan #126: Test Mock Justification Audit

**Status:** ✅ Complete

**Verified:** 2026-01-25T04:45:00Z
**Verification Evidence:**
```yaml
completed_by: Manual verification (PR #599 merged)
timestamp: 2026-01-25T04:45:00Z
commit: 05a66f6 (merged from PR #599)
notes: |
  - Fixed check_mock_usage.py to scan subdirectories (was only scanning top-level tests/)
  - Script now finds 480 mocks across 42 files
  - All mock patterns justified with # mock-ok: comments
  - `python scripts/check_mock_usage.py --strict` passes
```

**Priority:** **Medium**
**Blocked By:** None
**Blocks:** None

---

## Gap

**Current:** 280 mock usages across 37 test files, but only 73 have `# mock-ok:` justification comments (26%). This means 207 mocks (~74%) lack explicit reasoning for why mocking is necessary.

**Problem files:**
- `tests/unit/test_memory.py` - 8 mocks, only 1 justified
- `tests/unit/test_agent_loop.py` - Heavy AsyncMock use for callbacks
- `tests/integration/test_runner.py` - Multiple `@patch` without justification
- `tests/unit/test_agent_cognitive_schema.py` - AsyncMock for LLM, only 2 justified

**Target:** All mocks have `# mock-ok: <reason>` justification explaining why mocking is necessary (vs testing with real implementation).

**Why Medium:** Technical debt affecting test quality and maintainability, but doesn't cause immediate failures.

---

## References Reviewed

- `tests/unit/test_memory.py` - Mock pattern example
- `tests/unit/test_ledger.py` - Good example (no mocks)
- Project convention: `# mock-ok: <reason>` required
- `scripts/check_mock_usage.py` - Existing enforcement script

---

## Files Affected

- `tests/unit/test_memory.py` (modify)
- `tests/unit/test_agent_loop.py` (modify)
- `tests/integration/test_runner.py` (modify)
- `tests/unit/test_agent_cognitive_schema.py` (modify)
- ~33 other test files with unjustified mocks (modify)

---

## Plan

### Approach

For each unjustified mock, determine if:
1. **Mock is necessary** → Add `# mock-ok: <reason>`
2. **Mock can be removed** → Replace with real implementation
3. **Test is testing implementation** → Consider rewriting to test behavior

### Justification Categories

```python
# mock-ok: external-service - LLM API call
# mock-ok: filesystem - Avoids disk I/O in unit tests
# mock-ok: time - Deterministic timing
# mock-ok: network - HTTP/WebSocket calls
# mock-ok: expensive - Operation too slow for unit tests
# mock-ok: side-effect - Prevents unwanted state changes
```

### Steps

1. Run `python scripts/check_mock_usage.py --verbose` to get full list
2. For each file with unjustified mocks:
   - Review each mock usage
   - Add justification comment OR remove unnecessary mock
3. Run `python scripts/check_mock_usage.py --strict` to verify

### Priority Files (most mocks, most critical):
1. `tests/unit/test_agent_loop.py`
2. `tests/unit/test_memory.py`
3. `tests/integration/test_runner.py`
4. `tests/unit/test_agent_cognitive_schema.py`
5. `tests/e2e/conftest.py`

---

## Required Tests

### New Tests (TDD)

None - this is a documentation/audit task.

### Existing Tests (Must Pass)

| Test Pattern | Why |
|--------------|-----|
| `pytest tests/` | All tests must still pass |
| `python scripts/check_mock_usage.py --strict` | Mock audit passes |

---

## E2E Verification

Not needed - no behavioral changes.

---

## Verification

### Tests & Quality
- [ ] All tests pass: `pytest tests/`
- [ ] Mock audit passes: `python scripts/check_mock_usage.py --strict`

### Documentation
- [ ] Each mock has clear justification

### Completion Ceremony
- [ ] Plan file status → `✅ Complete`
- [ ] `plans/CLAUDE.md` index → `✅ Complete`

---

## Notes
This is a cleanup task that improves code quality and makes the testing philosophy explicit. Some mocks may be discovered to be unnecessary and can be removed entirely.

The `# mock-ok:` convention helps future developers understand:
1. That the mock was intentional (not lazy)
2. Why it was necessary
3. What would be needed to remove it
