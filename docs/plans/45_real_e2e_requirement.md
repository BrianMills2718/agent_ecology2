# Plan #45: Require Real E2E Tests Before Completion

**Status:** 🚧 In Progress
**Priority:** High
**Type:** Quality Gate / Meta-process
**Created:** 2026-01-14

**Related Plans:**
- Plan #44: Meta-Process Enforcement (broader enforcement improvements)
- Plan #41: Enforcement Gaps (meta-process gaps)

## Summary

Require real E2E tests (actual LLM calls, not mocked) to pass before a plan can be marked complete. Currently `complete_plan.py` only runs smoke tests with mocked LLM, which provides weaker verification.

## Problem Statement

The current verification in `complete_plan.py` runs:
1. Unit tests (`pytest tests/ --ignore=tests/e2e/`)
2. E2E smoke tests (`pytest tests/e2e/test_smoke.py`) - **mocked LLM**
3. Doc-coupling check

Smoke tests use a mocked LLM, meaning they verify:
- Code doesn't crash
- Integration points work
- Configuration is valid

But they **don't verify**:
- Real LLM produces valid actions
- Prompt engineering works correctly
- Full end-to-end behavior under real conditions

This creates risk of "big bang" failures when code reaches production.

## Current Test Hierarchy

| Test Type | What It Tests | LLM | Speed | Cost |
|-----------|---------------|-----|-------|------|
| Unit | Single components | None | Fast | Free |
| Integration | Component interaction | None | Fast | Free |
| E2E Smoke | Full simulation | Mocked | Fast | Free |
| **E2E Real** | Full simulation | **Real** | Slow | ~$0.01-0.05 |

Only E2E Real tests verify the actual LLM integration works.

## Solution

### 1. Add Real E2E Step to `complete_plan.py`

Update `complete_plan.py` to run real E2E tests as step [2/4] (before doc-coupling):

```python
def run_real_e2e_tests(project_root: Path, verbose: bool = True) -> tuple[bool, str]:
    """Run real E2E tests (actual LLM calls).

    Returns (success, summary).
    """
    real_e2e = project_root / "tests" / "e2e" / "test_real_e2e.py"

    if not real_e2e.exists():
        if verbose:
            print("\n[3/4] Real E2E tests... SKIPPED (test_real_e2e.py not found)")
        return True, "skipped (no real e2e test)"

    if verbose:
        print("\n[3/4] Running real E2E tests (actual LLM, costs ~$0.01-0.05)...")

    result = subprocess.run(
        ["pytest", "tests/e2e/test_real_e2e.py", "-v", "--tb=short", "--run-external"],
        cwd=project_root,
        capture_output=True,
        text=True,
    )

    # ... extract timing and summary ...
    return result.returncode == 0, summary
```

### 2. Update Verification Evidence

Add real E2E result to the verification evidence block:

```yaml
tests:
  unit: 45 passed in 12.34s
  e2e_smoke: PASSED (2.1s)
  e2e_real: PASSED (8.5s, cost: $0.02)  # NEW
  doc_coupling: passed
```

### 3. Add Skip Flag for Special Cases

Add `--skip-real-e2e` flag for documentation-only plans (like `--skip-e2e`):

```bash
# For plans that don't affect simulation behavior
python scripts/complete_plan.py --plan 45 --skip-real-e2e
```

### 4. CI Integration

Update CI workflow to run real E2E on merge to main:

```yaml
# .github/workflows/ci.yml
release-check:
  if: github.ref == 'refs/heads/main'
  runs-on: ubuntu-latest
  steps:
    - name: Real E2E tests
      run: pytest tests/e2e/test_real_e2e.py -v --run-external
      env:
        ANTHROPIC_API_KEY: ${{ secrets.ANTHROPIC_API_KEY }}
```

## Cost Analysis

| Per-plan completion | Cost |
|--------------------|------|
| Unit + smoke (current) | $0.00 |
| + Real E2E (proposed) | ~$0.01-0.05 |

For a project with ~50 plans, this adds ~$0.50-2.50 total cost for full verification.

**Tradeoff:** Slightly higher cost for significantly higher confidence that features actually work with real LLM.

## Implementation Steps

### Phase 1: Core Implementation
1. Add `run_real_e2e_tests()` function to `complete_plan.py`
2. Update verification step numbering (1/3 -> 1/4, etc.)
3. Update verification evidence format
4. Add `--skip-real-e2e` flag
5. Update docstring and help text

### Phase 2: Plan-Specific E2E
1. Ensure each plan has feature-specific tests in `tests/plans/plan_NN/`
2. Run plan-specific tests as part of completion (already exists via `check_plan_tests.py`)

### Phase 3: CI Integration
1. Add real E2E step to release workflow
2. Configure API keys as secrets
3. Add cost tracking/alerts

## Required Tests

### Unit Tests
- `test_run_real_e2e_tests_success`: Verify function runs and parses output
- `test_run_real_e2e_tests_skip_missing`: Verify graceful skip if file missing
- `test_skip_real_e2e_flag`: Verify flag skips real E2E

### Integration Tests
- `test_complete_plan_with_real_e2e`: Full completion flow with real E2E step

### E2E Tests
- The existing `test_real_e2e.py` tests serve as the verification target

## Acceptance Criteria

- [ ] `complete_plan.py` runs real E2E tests by default
- [ ] Real E2E results recorded in verification evidence
- [ ] `--skip-real-e2e` flag available for documentation-only plans
- [ ] Plans cannot be completed if real E2E tests fail
- [ ] Documentation updated with new verification step

## Open Questions

1. **Cost limits:** Should there be a max cost per plan completion? (e.g., abort if >$0.10)
2. **API key requirement:** What happens if ANTHROPIC_API_KEY not set? (fail or skip with warning?)
3. **Parallel execution:** Can real E2E tests run in parallel with other verification?

## References

- `scripts/complete_plan.py` - Current implementation
- `tests/e2e/test_smoke.py` - Mocked E2E tests
- `tests/e2e/test_real_e2e.py` - Real E2E tests
- `docs/meta/verification-enforcement.md` - Verification pattern
- `tests/CLAUDE.md` - Test hierarchy documentation
