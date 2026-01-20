# Plan #116: Enforce make finish from Main

**Status:** 📋 Planned
**Priority:** Medium
**Blocked By:** None
**Blocks:** Meta-process integrity

---

## Problem Statement

The current `enforce-make-merge.sh` hook blocks direct `gh pr merge` commands, but doesn't enforce:

1. **Running from main directory** - `make merge` can be run from worktrees, which causes issues
2. **Using `make finish` over `make merge`** - `make merge` only merges the PR; `make finish` does the complete workflow:
   - Merge PR
   - Release claim
   - Delete worktree
   - Pull latest main

When CC instances run `make merge` from inside a worktree, or forget to use `make finish`, it leaves:
- Orphan worktrees
- Stale claims
- Inconsistent state

---

## Solution

Enhance the hook to:

1. **Detect if CWD is inside a worktree** and block merge operations
2. **Recommend `make finish`** for the complete workflow
3. **Allow `make merge` from main** as a fallback (for edge cases)

### Hook Logic

```bash
# 1. Check if running from worktree
if [[ "$PWD" == */worktrees/* ]]; then
    echo "BLOCKED: Cannot merge from inside a worktree" >&2
    echo "Run from main: cd /path/to/main && make finish BRANCH=X PR=N" >&2
    exit 2
fi

# 2. Suggest make finish over make merge
if [[ "$COMMAND" =~ make[[:space:]]+merge ]]; then
    echo "SUGGESTION: Consider using 'make finish' instead" >&2
    echo "  make finish BRANCH=X PR=N" >&2
    echo "This handles: merge + release claim + delete worktree" >&2
    # Allow but warn (exit 0)
fi
```

---

## Files to Create/Modify

### Modified Files

| File | Changes |
|------|---------|
| `.claude/hooks/enforce-make-merge.sh` | Add worktree detection and finish recommendation |

---

## Implementation Details

### Worktree Detection

Check if `$PWD` contains `/worktrees/`:

```bash
if [[ "$PWD" == */worktrees/* ]]; then
    # Block - we're inside a worktree
fi
```

### Extract Branch from Worktree Path

If blocking from worktree, help the user by extracting the branch name:

```bash
BRANCH=$(basename "$PWD")
echo "Run from main: make finish BRANCH=$BRANCH PR=N"
```

---

## Required Tests

```yaml
tests:
  manual:
    - test_hook_blocks_merge_from_worktree:
        description: Verify hook blocks make merge from inside worktree
        steps:
          - cd worktrees/some-branch
          - Run make merge PR=123
          - Should be blocked with helpful message

    - test_hook_allows_merge_from_main:
        description: Verify hook allows make merge from main
        steps:
          - cd /path/to/main
          - Run make merge PR=123
          - Should succeed (with suggestion to use finish)
```

---

## Acceptance Criteria

1. **Blocks from worktree**: `make merge` from inside `worktrees/*` is blocked
2. **Helpful message**: Error includes the correct `make finish` command to run
3. **Works from main**: `make merge` from main directory still works
4. **Suggests finish**: When merge is allowed, suggests `make finish` as better option

---

## References

- Existing hook: `.claude/hooks/enforce-make-merge.sh`
- Meta-process docs: `CLAUDE.md` workflow section
- Related: Plan #98 (Robust Worktree Lifecycle)
