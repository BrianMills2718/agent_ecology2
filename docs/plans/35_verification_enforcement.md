# Gap 35: Verification Enforcement

**Status:** ✅ Complete

**Verified:** 2026-01-12T09:45:11Z
**Verification Evidence:**
```yaml
completed_by: scripts/complete_plan.py
timestamp: 2026-01-12T09:45:11Z
tests:
  unit: 868 passed, 1 warning in 21.57s
  e2e_smoke: PASSED (4.86s)
  doc_coupling: passed
commit: 8667d0f
```
**Priority:** **High**
**Blocked By:** None
**Blocks:** All future plans (meta-process)

---

## Gap

**Current:**
- Plans have optional `## Verification` sections
- Nothing enforces running tests before marking complete
- No evidence that tests were run
- CC instances can mark plans "complete" without verification

**Target:**
- Mandatory verification before plan completion
- Script-enforced test runs with recorded evidence
- E2E smoke test required for all plans

**Why High Priority:**
Without enforcement, we accumulate technical debt through untested "complete" work. Big-bang integration failures compound insurmountably.

---

## Plan

### Phase 1: Infrastructure

| File | Change |
|------|--------|
| `scripts/complete_plan.py` | Plan completion enforcement script |
| `tests/e2e/__init__.py` | E2E test directory |
| `tests/e2e/test_smoke.py` | Basic E2E smoke test |
| `tests/e2e/conftest.py` | E2E fixtures (mocked LLM) |

### Phase 2: Documentation

| File | Change |
|------|--------|
| `docs/meta/verification-enforcement.md` | Meta pattern documentation |
| `docs/meta/README.md` | Add to pattern index |
| `CLAUDE.md` | Add mandatory verification requirement |

---

## Required Tests

### New Tests (TDD)

| Test File | Test Function | What It Verifies |
|-----------|---------------|------------------|
| `tests/e2e/test_smoke.py` | `test_simulation_starts` | Runner can be instantiated |
| `tests/e2e/test_smoke.py` | `test_tick_mode_completes` | Basic tick simulation works |
| `tests/e2e/test_smoke.py` | `test_tick_mode_creates_artifacts` | Genesis artifacts created |
| `tests/e2e/test_smoke.py` | `test_tick_mode_tracks_balances` | Balances tracked |
| `tests/e2e/test_smoke.py` | `test_autonomous_mode_starts` | Autonomous mode can start |
| `tests/e2e/test_smoke.py` | `test_autonomous_mode_runs_briefly` | Autonomous runs without crash |
| `tests/e2e/test_smoke.py` | `test_world_state_summary` | State summary works |
| `tests/e2e/test_smoke.py` | `test_no_unhandled_exceptions` | No crashes |

### Existing Tests (Must Pass)

| Test Pattern | Why |
|--------------|-----|
| `tests/test_runner.py` | Runner still works |
| `tests/test_agent_loop.py` | Autonomous loops work |

---

## Verification

### E2E Smoke Test (Required)
```bash
pytest tests/e2e/test_smoke.py -v  # Must pass
```

### Regression Check
```bash
pytest tests/ -v  # All tests must pass
```

### Completion Command
```bash
# REQUIRED - do not manually update status
python scripts/complete_plan.py --plan 35
```

---

## Notes

This is a meta-plan that establishes the verification pattern for all future plans. Once complete, all subsequent plan completions must use `scripts/complete_plan.py`.

See also: `docs/meta/verification-enforcement.md` for the reusable pattern.
