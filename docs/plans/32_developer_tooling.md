# Gap 32: Developer Tooling

**Status:** ✅ Complete
**Priority:** High
**Blocked By:** -
**Blocks:** -

---

## Gap

**Current:** Developer tooling is fragmented and lacks enforcement mechanisms.

**Target:** Comprehensive tooling that enforces project standards:
- Git hooks for commit message format and doc-coupling
- Mock test policy enforcement
- Plan file overlap detection
- Tracked hooks directory (new clones configure path, not reinstall)

**Why High:** Good tooling prevents common issues before they reach CI.

---

## Plan

### Changes Required

| File | Action |
|------|--------|
| `hooks/commit-msg` | CREATE - Enforce plan references in commits |
| `hooks/pre-commit` | CREATE - Doc-coupling and mypy checks |
| `scripts/check_mock_tests.py` | CREATE - Mock test policy enforcement |
| `scripts/check_plan_overlap.py` | CREATE - Detect file overlaps between plans |
| `scripts/setup_hooks.sh` | UPDATE - Use tracked hooks directory |
| `pyproject.toml` | UPDATE - Add external test marker |
| `tests/conftest.py` | UPDATE - Add --run-external support |
| `.github/workflows/ci.yml` | UPDATE - Add mock-tests job |

### Steps

1. Create `hooks/` directory with tracked hooks
2. Create commit-msg hook for plan reference enforcement
3. Create pre-commit hook for doc-coupling/mypy
4. Create check_mock_tests.py for mock policy
5. Create check_plan_overlap.py for overlap detection
6. Update setup_hooks.sh to use `git config core.hooksPath hooks`
7. Add external marker to pyproject.toml
8. Add --run-external support to conftest.py
9. Add mock-tests CI job

---

## Required Tests

### New Tests (TDD)

| Test File | Test Function | What It Verifies |
|-----------|---------------|------------------|
| `tests/test_tooling.py` | `test_check_mock_tests_finds_violations` | Mock policy detection works |
| `tests/test_tooling.py` | `test_check_plan_overlap_detects_conflicts` | Overlap detection works |

### Existing Tests (Must Pass)

| Test Pattern | Why |
|--------------|-----|
| `tests/` | All existing tests unchanged |

---

## Verification

### Tests & Quality
- [ ] All required tests pass
- [ ] Full test suite passes: `pytest tests/`
- [ ] Type check passes: `python -m mypy src/ --ignore-missing-imports`

### Documentation
- [ ] `scripts/CLAUDE.md` updated with new scripts
- [ ] Hooks documented

### Completion Ceremony
- [ ] Plan file status -> `✅ Complete`
- [ ] `plans/CLAUDE.md` index -> `✅ Complete`
- [ ] Branch merged or PR created

---

## Notes

### Mock Test Policy
- Real tests are REQUIRED (marked `@pytest.mark.external`)
- Mock tests are OPTIONAL (named with `_mocked` suffix)
- Every `_mocked` test must have a corresponding real test
- CI enforces via `check_mock_tests.py --strict`

### Hooks Approach
- Hooks are tracked in `hooks/` directory
- `setup_hooks.sh` runs `git config core.hooksPath hooks`
- New clones configure path, don't need to reinstall hooks

### Commit Message Format
- Required: `[Plan #N] Description` or `[Unplanned] Description`
- `[Unplanned]` shows warning, doesn't block
- Merge/fixup/squash commits exempt
