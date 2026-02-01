# Plan 246: Pre-Merge Plan Completion Enforcement

**Status:** 🚧 In Progress
**Priority:** Medium
**Blocked By:** -
**Blocks:** -

---

## Gap

**Current:** `finish_pr.py` merges the PR first (irreversible), then marks the plan complete as best-effort cleanup in Phase 3. If `complete_plan.py` fails after merge, the plan stays "In Progress" indefinitely. Plans #231 and #242 slipped through this gap.

**Target:** Plan completion happens BEFORE merge. The plan status update is committed to the branch and included in the PR itself. If completion fails, the merge is aborted.

**Why Medium:** The gap causes manual cleanup work and stale plan statuses. The fix is narrow (one file) and the workaround is manual `complete_plan.py` runs.

---

## Design

Move plan completion from Phase 3 (post-merge best-effort) to between Phase 1 (validation) and Phase 2 (execution) in `finish_pr()`. The worktree still exists at that point, so we can run `complete_plan.py` in the worktree, commit, and push before the merge.

### New function: `ensure_plan_complete()`

1. Check if plan already shows Complete status — skip if so (idempotent)
2. Run `complete_plan.py --status-only` with `cwd=worktree_path`
3. Stage and commit changed plan files in the worktree
4. Push to the branch
5. If any step fails, return error → caller aborts before merge

### Edge cases

- No worktree: fall back to post-merge completion with warning
- `SKIP_COMPLETE=1`: skip entirely (explicit opt-out)
- Non-plan branch: no plan number, skip entirely
- Plan already Complete: idempotent, skip

---

## Files Affected

- `scripts/finish_pr.py` (modify) — add `ensure_plan_complete()`, restructure `finish_pr()` flow

---

## Plan

| Step | Change |
|------|--------|
| 1 | Add `ensure_plan_complete()` function |
| 2 | Insert pre-merge completion call between Phase 1 and Phase 2 |
| 3 | Remove plan completion from Phase 3 |
| 4 | Handle no-worktree fallback |
| 5 | Update dry-run output to reflect new flow |

---

## Verification

- [ ] `make finish` on a plan branch completes the plan before merging
- [ ] Plan file shows Complete status in the merged PR
- [ ] `SKIP_COMPLETE=1` still works as escape hatch
- [ ] Non-plan branches work unchanged
- [ ] Already-complete plans don't re-commit
- [ ] Missing worktree falls back gracefully
