# Gap 50: Test Structure Refactor for AI Navigability

**Status:** 🚧 In Progress
**Priority:** Medium
**Type:** Enabler (no feature E2E required)
**Blocked By:** None
**Blocks:** None

---

## Gap

**Current:**
- Tests organized in `tests/plans/` and `tests/features/` directories
- Feature association implicit through directory structure
- Plan-based directories create lifecycle mismatch (plans are temporary, tests are permanent)
- AI coding assistants must infer feature relationships from directory paths

**Target:**
- Pure type-based directory structure (`tests/unit/`, `tests/integration/`, `tests/e2e/`)
- Explicit markers for feature/plan associations: `@pytest.mark.feature("X")`, `@pytest.mark.plans([N])`
- Acceptance tests in `tests/integration/test_*_acceptance.py` files
- Feature specs (`features/*.yaml`) as authoritative source for test-feature mappings
- `--feature NAME` pytest option to run all tests for a feature

**Why Medium:**
Improves AI coding assistant navigability which is critical for the metaprocess template goal. The current organization creates cognitive overhead and potential confusion.

---

## Plan

### Changes Required

| File | Change |
|------|--------|
| `tests/conftest.py` | Add `feature` marker registration, `--feature` CLI option |
| `tests/integration/test_*_acceptance.py` | Create acceptance test files with `@pytest.mark.feature()` markers |
| `features/*.yaml` | Update test paths to point to new acceptance test locations |
| `tests/features/` | Remove directory (move tests to integration/) |
| `tests/plans/` | Remove directory (tests should use markers, not directories) |
| `tests/CLAUDE.md` | Document marker-based organization |
| `docs/meta/03_testing-strategy.md` | Update to reflect new structure |

### Steps

1. Add `@pytest.mark.feature("X")` marker registration to conftest.py
2. Add `--feature NAME` option to pytest for filtering by feature
3. Create acceptance test files in `tests/integration/` for each feature
4. Move any existing tests from `tests/features/` to appropriate type-based directories
5. Update feature specs to reference new test paths
6. Remove `tests/features/` and `tests/plans/` directories
7. Update documentation (tests/CLAUDE.md, docs/meta/03_testing-strategy.md)
8. Verify all tests pass and markers work correctly

---

## Required Tests

### New Tests (TDD)

This is an Enabler plan - validation is via verification that the structure works:

| Test File | Test Function | What It Verifies |
|-----------|---------------|------------------|
| `tests/integration/test_escrow_acceptance.py` | `TestEscrowFeature::test_ac_1_*` | Escrow feature acceptance criteria |
| `tests/integration/test_ledger_acceptance.py` | `TestLedgerFeature::test_ac_*` | Ledger feature acceptance criteria |
| N/A | `pytest --feature escrow` | Feature marker filtering works |
| N/A | `pytest -m "feature"` | Marker-based selection works |

### Existing Tests (Must Pass)

All existing tests must still pass:

| Test Pattern | Why |
|--------------|-----|
| `pytest tests/` | Full test suite unchanged |
| `python -m mypy src/` | Type checking still passes |

---

## E2E Verification

**Type:** Enabler - No feature E2E required

Verification is that the test infrastructure works correctly:

```bash
# Verify markers work
pytest --feature escrow tests/ --collect-only

# Verify all tests pass
pytest tests/ -v
```

---

## Verification

### Tests & Quality
- [ ] All required tests pass: `pytest tests/`
- [ ] Feature marker filtering works: `pytest --feature escrow tests/`
- [ ] Type check passes: `python -m mypy src/ --ignore-missing-imports`

### Documentation
- [ ] `tests/CLAUDE.md` updated with marker conventions
- [ ] `docs/meta/03_testing-strategy.md` updated with new structure
- [ ] Feature specs updated with new test paths

### Completion Ceremony
- [ ] Plan file status → `✅ Complete`
- [ ] `plans/CLAUDE.md` index → `✅ Complete`
- [ ] Claim released from Active Work table (root CLAUDE.md)
- [ ] Branch merged or PR created

---

## Notes

**AI Navigability Rationale:**
- Explicit metadata (markers) is superior to implicit semantics (directory structure) for LLMs
- Markers are queryable via grep/pytest and support multi-dimensional associations
- Feature specs remain the authoritative source; markers provide machine-readable links
- Type-based directories (unit/integration/e2e) are universally understood

**Origin:** Plan #50 based on analysis that AI coding assistants benefit from explicit, queryable metadata over directory-based organization.
