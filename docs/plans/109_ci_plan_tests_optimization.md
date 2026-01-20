# Plan #109: CI Plan Tests Optimization

**Status:** ✅ Complete
**Priority:** High
**Blocked By:** None

## Problem

The `plans` CI job runs `check_plan_tests.py --all --strict` which executes tests for ALL "In Progress" AND "Complete" plans. With ~90 complete plans containing ~350 tests, this takes 5+ minutes and often hangs or times out.

This is redundant because:
1. Complete plan tests are already part of the main test suite
2. The `test` CI job runs `pytest tests/` which executes all tests
3. Only "In Progress" plans need TDD enforcement (tests must exist AND pass)

Additionally, Plan #102 (tick removal) broke E2E tests by removing tick mode but not updating test fixtures to use duration-based execution. The E2E tests call `run_sync()` without a duration, which in autonomous-only mode runs forever.

## Solution

1. Modify `check_plan_tests.py --all` to:
   - **In Progress plans**: Run tests (enforce TDD)
   - **Complete plans**: Only verify tests exist (don't execute)

2. Fix E2E test fixtures to work with autonomous-only mode:
   - Add `duration` parameter to `run_sync()` for test compatibility
   - Update `e2e_config` fixture to not rely on removed `max_ticks`
   - Update smoke tests to pass short durations

This maintains safety while reducing CI time from 5+ minutes to ~30 seconds.

## Why This Is Safe

1. Complete plan tests are covered by `pytest tests/` in the `test` job
2. If a Complete plan's tests start failing, the `test` job catches it
3. In Progress plans still get full TDD enforcement
4. No test coverage is lost - just moved to the right place

## Files Affected

- scripts/check_plan_tests.py (modify) - Already implemented, optimize for In Progress only
- src/simulation/runner.py (modify) - Add duration param to run_sync
- tests/e2e/conftest.py (modify) - Remove max_ticks, use duration-based config
- tests/e2e/test_smoke.py (modify) - Update tests to use duration parameter

## Required Tests

### Existing Tests
| Test | Purpose |
|------|---------|
| `tests/e2e/test_smoke.py` | E2E smoke tests (must pass after fixture fix) |

## Acceptance Criteria

- [ ] AC-1: `check_plan_tests.py --all` completes in <60 seconds
- [ ] AC-2: In Progress plans still have tests executed
- [ ] AC-3: Complete plans only have test existence verified
- [ ] AC-4: All E2E smoke tests pass

## Implementation Notes

Change in `check_plan_tests.py` around line 505:
```python
# Before: active_statuses = ["In Progress", "Complete", "🚧", "✅"]
# After: Only run tests for In Progress plans
active_statuses = ["In Progress", "🚧"]
```

For Complete plans, we still want to verify tests exist (documentation check), just not run them.
