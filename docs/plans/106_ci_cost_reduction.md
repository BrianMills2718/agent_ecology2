# Plan #106: CI Cost Reduction

**Status:** 🚧 In Progress

**Priority:** High
**Blocked By:** None
**Blocks:** None

---

## Problem

GitHub Actions is costing ~$60/month due to:

1. **Duplicate pytest runs**: The `plans` job runs full pytest via `check_plan_tests.py --all` (~9 min) even when the `test` job already ran it (~2 min)
2. **Separate test/mypy jobs**: Each job has ~30-60s setup overhead
3. **Plans job always runs**: Even for docs-only changes where no plan tests exist

Current cost per full PR: ~$0.10 (12 minutes × $0.008/min)
At 600 runs/month = $60

---

## Solution

### Phase 1: Eliminate Duplicate pytest (Biggest Win)

The `plans` job runs `check_plan_tests.py --all --strict` which re-runs pytest for every plan's required tests. This is redundant when the `test` job already ran full pytest.

**Options:**
1. **Skip plan tests if test job passed** - Add conditional: only run plan tests if `test` job was skipped
2. **Remove pytest from plans job entirely** - The `test` job already covers it
3. **Make check_plan_tests.py smarter** - Check if tests already passed in this CI run

**Recommendation:** Option 2 - Remove pytest from plans job. The regular `test` job runs all tests; plan test requirements are enforced by the test file naming convention (`tests/unit/test_*.py` for plans).

Savings: ~9 minutes per run = ~$0.07/run = **~75% cost reduction**

### Phase 2: Merge test + mypy Jobs

Combine into single `quality` job:
- Saves one runner startup (~30s)
- Uses same cached dependencies

```yaml
quality:
  needs: changes
  if: needs.changes.outputs.code == 'true'
  runs-on: ubuntu-latest
  steps:
    - uses: actions/checkout@v4
    - uses: actions/setup-python@v5
    - uses: actions/cache@v4
    - run: pip install -e . && pip install -r requirements.txt mypy
    - run: pytest tests/ -v --tb=short
    - run: mypy --strict ...
```

Savings: ~30-60s per run

### Phase 3: Skip plans Job for Docs-Only

Add conditional to plans job:
```yaml
plans:
  needs: changes
  if: needs.changes.outputs.code == 'true' || needs.changes.outputs.docs == 'true'
```

Actually, keep it running but skip the expensive pytest part (Phase 1 handles this).

### Phase 4 (Optional): Self-Hosted Runner

For zero recurring cost:
- Run CI on local machine or cheap VPS
- One-time setup, then free forever

---

## Implementation

### Changes to `.github/workflows/ci.yml`

1. Remove `check_plan_tests.py --all` from plans job (or make it `--skip-pytest`)
2. Merge `test` and `mypy` into single `quality` job
3. Update branch protection to require new job names

### Changes to `scripts/check_plan_tests.py`

Add `--skip-pytest` flag that only validates plan test requirements exist without running them.

---

## Files Affected

- `.github/workflows/ci.yml` (modify)
- `docs/architecture/current/ci.md` (modify)

---

## Required Tests

- `tests/unit/test_check_plan_tests.py` - Test --skip-pytest flag

---

## Acceptance Criteria

1. Plans job no longer runs full pytest (~9 min saved)
2. Test and mypy combined into single job (~30s saved)
3. CI still catches all the same issues
4. Total CI time reduced from ~12 min to ~3 min for code changes
5. Cost reduced by ~75% (from ~$0.10 to ~$0.025 per run)

---

## Metrics

Before:
- Full PR CI time: ~12 minutes
- Cost per run: ~$0.10

After:
- Full PR CI time: ~3 minutes
- Cost per run: ~$0.025

Monthly savings at 600 runs: $60 → $15

---

## Risk Assessment

**Low risk** - All checks still run, just more efficiently:
- pytest runs once instead of twice
- mypy runs in same job as pytest
- Plan status checks still enforce requirements

---

## Notes

The duplicate pytest in plans job appears to be unintentional - `check_plan_tests.py --all` runs pytest for every plan that declares required tests, but the standalone `test` job already runs all tests. The plan tests script was likely intended for local TDD workflow, not CI.
