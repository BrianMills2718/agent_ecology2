# Plan 71: Ownership Check in Meta-Process

**Status:** ✅ Complete
**CC-ID:** plan-71-ownership-check

## Problem

CC instances repeatedly suggest fixing/taking over other instances' work (blocked PRs, failing CI, orphaned worktrees) instead of respecting ownership boundaries. This violates the meta-process principle that "ownership stays with the claimant."

Root cause: No explicit ownership check in the reasoning process before recommending actions.

## Solution

Multi-part fix to make ownership visible and enforce checking:

1. **CLAUDE.md Priority 0** - Add explicit ownership check before all other priorities
2. **meta_status.py enhancement** - Show owner for each PR/worktree, flag "NOT YOURS"
3. **/proceed skill update** - Add ownership verification step
4. **docs/meta pattern** - Document ownership respect as a meta-pattern

## Files Affected

- CLAUDE.md (modify) - Add Priority 0
- scripts/meta_status.py (modify) - Add owner column
- .claude/commands/proceed.md (modify) - Add ownership check
- docs/meta/26_ownership-respect.md (create) - New pattern doc

## Required Tests

- `tests/unit/test_meta_status.py::TestGetCurrentBranch::test_returns_branch_name`
- `tests/unit/test_meta_status.py::TestGetCurrentBranch::test_handles_git_failure`
- `tests/unit/test_meta_status.py::TestGetMyIdentity::test_returns_identity_dict`
- `tests/unit/test_meta_status.py::TestGetMyIdentity::test_is_main_true_on_main_branch`
- `tests/unit/test_meta_status.py::TestGetMyIdentity::test_is_main_false_on_feature_branch`
- `tests/unit/test_meta_status.py::TestGetMyIdentity::test_finds_matching_claim`

## Acceptance Criteria

- [x] CLAUDE.md has Priority 0: Check ownership
- [x] meta_status.py shows PR owner and flags non-owned PRs
- [x] /proceed skill includes ownership verification
- [x] docs/meta has ownership respect pattern documented

---

## Verification

**Verified:** 2026-01-18T07:00:00Z (retroactive - PR already merged)
**PR:** #255
**Merged:** 2026-01-18T05:12:55Z

**CI Evidence:**
- All checks passed (SUCCESS)
- 6 unit tests in test_meta_status.py pass
- docs/meta/26_ownership-respect.md created
