# Plan #109: CI Plan Tests Optimization

**Status:** In Progress
**Priority:** High
**Blocked By:** None

## Problem

The `plans` CI job runs `check_plan_tests.py --all --strict` which executes tests for ALL "In Progress" AND "Complete" plans. With ~90 complete plans containing ~350 tests, this takes 5+ minutes and often hangs or times out.

This is redundant because:
1. Complete plan tests are already part of the main test suite
2. The `test` CI job runs `pytest tests/` which executes all tests
3. Only "In Progress" plans need TDD enforcement (tests must exist AND pass)

## Solution

Modify `check_plan_tests.py --all` to:
- **In Progress plans**: Run tests (enforce TDD)
- **Complete plans**: Only verify tests exist (don't execute)

This maintains safety while reducing CI time from 5+ minutes to ~30 seconds.

## Why This Is Safe

1. Complete plan tests are covered by `pytest tests/` in the `test` job
2. If a Complete plan's tests start failing, the `test` job catches it
3. In Progress plans still get full TDD enforcement
4. No test coverage is lost - just moved to the right place

## Files Affected

- scripts/check_plan_tests.py (modify)

## Required Tests

### Existing Tests
| Test | Purpose |
|------|---------|
| `tests/unit/test_check_plan_tests.py` | Verify script behavior |

## Acceptance Criteria

- [ ] AC-1: `check_plan_tests.py --all` completes in <60 seconds
- [ ] AC-2: In Progress plans still have tests executed
- [ ] AC-3: Complete plans only have test existence verified
- [ ] AC-4: CI passes with the change

## Implementation Notes

Change in `check_plan_tests.py` around line 505:
```python
# Before: active_statuses = ["In Progress", "Complete", "🚧", "✅"]
# After: Only run tests for In Progress plans
active_statuses = ["In Progress", "🚧"]
```

For Complete plans, we still want to verify tests exist (documentation check), just not run them.
