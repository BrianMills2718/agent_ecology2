# Plan #48: CI Optimization

**Status:** ✅ Complete

**Verified:** 2026-01-15T09:43:03Z
**Verification Evidence:**
```yaml
completed_by: scripts/complete_plan.py
timestamp: 2026-01-15T09:43:03Z
tests:
  unit: 1426 passed, 7 skipped, 5 warnings in 21.71s
  e2e_smoke: PASSED (2.46s)
  e2e_real: PASSED (33.12s)
  doc_coupling: passed
commit: ea9d2d7
```

**Priority:** Medium
**Blocked By:** None
**Blocks:** None

---

## Problem

CI takes too long due to:
1. 14 parallel jobs competing for limited GitHub Actions runners
2. No dependency caching - each job installs deps fresh (~30s overhead)
3. No conditional execution - all checks run even when irrelevant files changed
4. Runner queuing on free tier can add minutes of wait time

Current CI time: Often 3-5+ minutes (mostly waiting for runners)
Target: <2 minutes for typical PRs

---

## Solution

### Phase 1: Add Dependency Caching

Add `actions/cache` for pip dependencies. Saves ~30s per job.

```yaml
- uses: actions/cache@v4
  with:
    path: ~/.cache/pip
    key: ${{ runner.os }}-pip-${{ hashFiles('requirements.txt') }}
    restore-keys: |
      ${{ runner.os }}-pip-
```

### Phase 2: Consolidate Jobs

Reduce from 14 jobs to 5, maintaining same checks:

| New Job | Contains | Rationale |
|---------|----------|-----------|
| `test` | pytest, mypy | Core quality gates |
| `docs` | doc-coupling, governance-sync | Doc-related checks |
| `plans` | plan-status-sync, plan-blockers, plan-tests, plan-required | Plan-related checks |
| `code-quality` | mock-usage, new-code-tests, feature-coverage | Code quality checks |
| `meta` | claim-verification, locked-sections, validate-specs | Meta-process checks |

Benefits:
- 5 runners instead of 14 = less queuing
- Shared setup per group = less overhead
- Same robustness - all checks still run

### Phase 3: Conditional Execution

Only run checks when relevant files change:

```yaml
docs:
  if: |
    contains(github.event.pull_request.changed_files, 'docs/') ||
    contains(github.event.pull_request.changed_files, 'scripts/doc_coupling')
```

| Job | Trigger Files |
|-----|---------------|
| `test` | `src/**`, `tests/**`, `requirements.txt` |
| `docs` | `docs/**`, `scripts/doc_coupling.py`, `scripts/governance.yaml` |
| `plans` | `docs/plans/**`, `scripts/*plan*` |
| `code-quality` | `src/**`, `tests/**` |
| `meta` | `.claude/**`, `features/**`, `scripts/check_claims.py` |

### Phase 4 (Optional): GitHub Paid Tier

If still slow after optimizations:
- **GitHub Team** ($4/user/month): More concurrent runners
- **GitHub Enterprise**: Even more capacity
- **Self-hosted runners**: Maximum control, but maintenance burden

---

## Required Tests

### Validation (no automated tests needed)
- [ ] CI passes on a test PR after Phase 1
- [ ] CI passes on a test PR after Phase 2
- [ ] Conditional execution correctly skips irrelevant jobs (Phase 3)
- [ ] Total CI time reduced (measure before/after)

---

## Acceptance Criteria

1. Dependency caching enabled
2. Jobs consolidated from 14 to ~5
3. Conditional execution for non-critical checks
4. CI time reduced by 50%+ for typical PRs
5. All existing checks still run (no robustness loss)

---

## Files to Modify

| File | Changes |
|------|---------|
| `.github/workflows/ci.yml` | Add caching, consolidate jobs, add conditionals |

---

## Metrics

Measure before/after:
- Time from PR push to CI complete
- Time spent in "queued" state
- Number of runner-minutes consumed

---

## Notes

This is pure infrastructure optimization - no changes to what gets checked, just how efficiently we check it.
