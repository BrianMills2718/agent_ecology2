# Gap 98: Robust Worktree Lifecycle

**Status:** 🚧 In Progress
**Priority:** High
**Blocked By:** None
**Blocks:** None

---

## Gap

**Current:** CC instances experience bash crashes when worktrees are deleted while their shell CWD is in the worktree. This happens because:
1. `merge_pr.py` changes its own subprocess CWD but cannot change CC's shell CWD
2. When worktree is deleted, CC's bash fails on any subsequent command
3. Orphaned worktrees and claims accumulate

**Target:** Single `make finish` command that:
1. MUST run from main (refuses to run from worktree)
2. Merges PR, releases claim, deletes worktree, pulls main
3. CC uses `cd /main && make finish BRANCH=X PR=N` in one bash command

---

## References Reviewed

- `scripts/merge_pr.py` - Current merge logic
- `CLAUDE.md` - Workflow documentation
- `docs/meta/15_plan-workflow.md` - Plan workflow pattern
- `scripts/meta_status.py` - Status dashboard
- `.claude/hooks/check-file-scope.sh` - File scope enforcement

---

## Files Affected

- scripts/finish_pr.py (create)
- Makefile (modify)
- scripts/meta_status.py (modify)
- CLAUDE.md (modify)
- docs/meta/15_plan-workflow.md (modify)
- tests/scripts/test_finish_pr.py (create)
- tests/scripts/test_meta_status.py (modify)
- docs/plans/CLAUDE.md (modify)

---

## Plan

### Steps

1. Create `scripts/finish_pr.py` - CWD check + full lifecycle
2. Add `make finish` target to Makefile
3. Add orphan detection to `meta_status.py` (detached HEAD or missing remote branch)
4. Update CLAUDE.md with 4-step workflow
5. Update docs/meta/15_plan-workflow.md
6. Test and verify

---

## Required Tests

### New Tests (TDD)

| Test File | Test Function | What It Verifies |
|-----------|---------------|------------------|
| `tests/test_finish_pr.py` | `test_worktree_detection` | Detects worktree vs main repo |
| `tests/test_finish_pr.py` | `test_refuses_from_worktree` | Blocks execution from worktree |

### Existing Tests (Must Pass)

| Test Pattern | Why |
|--------------|-----|
| `tests/test_meta_status.py` | Meta status still works |

---

## Verification

- [ ] `make finish` refuses to run from worktree
- [ ] `make finish` completes full lifecycle from main
- [ ] meta_status.py detects orphaned worktrees
- [ ] CLAUDE.md documents 4-step workflow

---

## Notes

Root cause: CC's shell CWD cannot be changed by a subprocess. The solution forces CC to explicitly `cd` to main before running cleanup, keeping both in one bash command so the shell CWD is valid after cleanup.
