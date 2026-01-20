# Plan #115: Worktree Ownership Enforcement

**Status:** ✅ Complete
**Priority:** High
**Blocked by:** None

---

## Problem

When multiple Claude Code instances work in parallel, cleaning up merged worktrees can break other instances' shells. The issue:

1. CC-A works in worktree/plan-X, creates PR, PR gets merged
2. Remote branch is deleted, meta_status shows "merged worktree - safe to cleanup"
3. CC-B sees this and runs cleanup
4. CC-A's shell breaks because its CWD was deleted

The session marker system exists but we've been bypassing it with `--force`.

---

## Solution

Add ownership checks to prevent cleaning up worktrees you don't own:

1. **meta_status.py** - Show WHO owns each merged worktree and whether it's YOURS
2. **safe_worktree_remove.py** - Block removal if claim owner differs from current CC
3. **CLAUDE.md** - Document the rule explicitly

---

## Files Affected

- scripts/meta_status.py (modify - add ownership display for merged worktrees)
- scripts/safe_worktree_remove.py (modify - add ownership check blocking)
- CLAUDE.md (modify - add "Never clean up worktrees you don't own" rule)
- tests/unit/test_safe_worktree_remove.py (modify - add ownership check tests)

---

## Required Tests

### Existing Tests (Must Pass)
- tests/unit/test_safe_worktree_remove.py

### New Tests
| Test File | Test Function | What It Verifies |
|-----------|---------------|------------------|
| tests/unit/test_safe_worktree_remove.py | test_blocks_removal_if_different_owner | Removal blocked when claim owner differs |
| tests/unit/test_safe_worktree_remove.py | test_allows_removal_if_same_owner | Removal allowed when claim owner matches |

---

## Acceptance Criteria

1. meta_status shows "Owner: X (✓ YOURS)" or "Owner: X (NOT YOURS)" for merged worktrees
2. safe_worktree_remove.py blocks removal if cc_id doesn't match, even without --force
3. Error message explains ownership and suggests alternative actions
