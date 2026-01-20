# Plan 127: Block Direct merge_pr.py Calls

**Status:** 📋 Planned

**Priority:** Medium
**Blocked By:** None
**Blocks:** None

---

## Gap

**Current:** The `enforce-make-merge.sh` hook blocks direct calls to `finish_pr.py` and `safe_worktree_remove.py`, but does NOT block direct calls to `merge_pr.py`. This allows CC instances to bypass the worktree-in-CWD protection by calling `merge_pr.py` directly.

**Target:** Hook blocks ALL direct script calls that could delete worktrees.

**Why:** When `merge_pr.py` is called from inside a worktree, the Python `os.chdir()` only changes the Python process CWD, not the parent shell's CWD. When the worktree is deleted, the shell's CWD becomes invalid, breaking all subsequent bash commands.

---

## Root Cause Analysis

1. Hook gave clear guidance: "DO THIS (two separate commands): cd /main && make finish"
2. Previous CC session ignored guidance and called `python scripts/merge_pr.py 424` directly
3. Hook didn't block this because `merge_pr.py` wasn't in the blocked list
4. `merge_pr.py` has `os.chdir(project_root)` which changes Python's CWD but not the shell's
5. Worktree was deleted, shell CWD became invalid

---

## Changes Required

### 1. .claude/hooks/enforce-make-merge.sh

Add blocking for `merge_pr.py` direct calls (after the `finish_pr.py` block around line 71):

```bash
# Block direct calls to merge_pr.py (must use make merge or make finish)
# This ensures proper workflow and avoids CWD issues
if echo "$COMMAND" | grep -qE '(^|&&|;|\|)\s*python[3]?\s+scripts/merge_pr\.py'; then
    PR_NUM=$(echo "$COMMAND" | grep -oE '[0-9]+' | head -1 || echo "N")

    echo "BLOCKED: Direct script call is not allowed" >&2
    echo "" >&2
    echo "Running 'python scripts/merge_pr.py' directly may:" >&2
    echo "  - Use a stale copy from your worktree instead of main" >&2
    echo "  - Cause CWD issues if your shell is in a worktree being deleted" >&2
    echo "" >&2
    echo "Use the proper command instead:" >&2
    echo "  make merge PR=$PR_NUM" >&2
    echo "Or for full workflow:" >&2
    echo "  make finish BRANCH=<branch> PR=$PR_NUM" >&2
    exit 2
fi
```

---

## Files Affected

- `.claude/hooks/enforce-make-merge.sh` (modify - add merge_pr.py to blocked scripts)
- `docs/plans/127_merge_script_hook_gap.md` (create - this plan file)

---

## Verification

- [ ] `make finish` from worktree still shows guidance
- [ ] `python scripts/merge_pr.py N` from anywhere is blocked with clear message
- [ ] `make merge PR=N` still works from main
- [ ] `make finish BRANCH=x PR=N` still works from main

---

## Notes

- This is a single hook modification
- No code changes, just defense-in-depth for the meta-process
- The hook already has the pattern for blocking scripts (finish_pr.py, safe_worktree_remove.py)
- Just need to add merge_pr.py to the same pattern
