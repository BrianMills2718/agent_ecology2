# Plan 69: Auto-cleanup Worktrees After PR Merge

**Status:** ✅ Complete

**Verified:** 2026-01-18T02:57:07Z
**Verification Evidence:**
```yaml
completed_by: scripts/complete_plan.py
timestamp: 2026-01-18T02:57:07Z
tests:
  unit: 1527 passed, 9 skipped, 4 warnings in 34.66s
  e2e_smoke: PASSED (1.69s)
  e2e_real: PASSED (64.64s)
  doc_coupling: passed
commit: 348979a
```
**Feature:** shared
**CC-ID:** -
**Branch:** plan-69-worktree-cleanup

## Problem

When PRs are merged via `make merge PR=N`, the remote branch is deleted (via `--delete-branch`), but the local worktree remains. This creates "orphaned" worktrees that clutter the workspace and confuse `meta_status.py`.

Current state: Worktrees accumulate after PR merges, requiring periodic manual cleanup.

## Solution

Modify `scripts/merge_pr.py` to automatically clean up the local worktree after successful merge:

1. Get the PR's head branch name before merge
2. After successful merge, check if a local worktree exists for that branch
3. If yes, clean it up using `make worktree-remove BRANCH=xxx`
4. Handle errors gracefully (warn but don't fail merge)

## Files Affected

- scripts/merge_pr.py (modify)
- tests/unit/test_merge_pr.py (create)

## Required Tests

| Test File | Test Function | What It Verifies |
|-----------|---------------|------------------|
| `tests/unit/test_merge_pr.py` | `test_finds_matching_branch` | Parses porcelain output correctly |
| `tests/unit/test_merge_pr.py` | `test_returns_none_for_no_match` | Returns None when branch not found |
| `tests/unit/test_merge_pr.py` | `test_handles_detached_head_worktrees` | Skips detached HEAD entries |
| `tests/unit/test_merge_pr.py` | `test_handles_git_command_failure` | Returns None on git failure |
| `tests/unit/test_merge_pr.py` | `test_handles_empty_output` | Returns None for empty output |

## Acceptance Criteria

- [ ] `make merge PR=N` auto-cleans up local worktree for merged branch
- [ ] Cleanup failures warn but don't fail the merge
- [ ] Worktrees for other branches are not affected
