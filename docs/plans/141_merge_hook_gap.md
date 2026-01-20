# Plan #141: Fix merge hook gap for `make -C` pattern

**Status:** in_progress
**Priority:** high
**Complexity:** trivial

## Problem

The `enforce-make-merge.sh` hook correctly blocks `make merge` from inside a worktree, but fails to catch `make -C /path/to/main merge PR=N`.

### Root cause

Line 154 of the hook uses this pattern:
```bash
if echo "$COMMAND" | grep -qE '(^|&&|\|\||;)\s*make\s+merge(\s|$)'; then
```

This matches `make merge` but NOT `make -C /path merge` because the `-C /path` appears between `make` and `merge`.

### How we discovered this

During PR #481 merge, the hook blocked:
1. `make finish` from worktree - BLOCKED (correct)
2. `gh pr merge` - BLOCKED (correct)
3. `make -C /main merge PR=481` - NOT BLOCKED (gap!)

The merge succeeded but the worktree was deleted while the shell CWD was inside it, breaking all subsequent bash commands.

## Solution

Update the regex pattern to also match `make` with `-C` flag before `merge`:

```bash
# Before (line 154):
if echo "$COMMAND" | grep -qE '(^|&&|\|\||;)\s*make\s+merge(\s|$)'; then

# After:
if echo "$COMMAND" | grep -qE '(^|&&|\|\||;)\s*make\s+(-C\s+\S+\s+)?merge(\s|$)'; then
```

The `(-C\s+\S+\s+)?` captures an optional `-C /some/path ` between make and merge.

## Implementation

1. Edit `.claude/hooks/enforce-make-merge.sh` line 154
2. Update the regex to include the optional `-C` flag pattern
3. Test manually

## Files to change

- `.claude/hooks/enforce-make-merge.sh` (1 line change)

## Required Tests

None - this is a hook script, manual verification is sufficient.

## Acceptance Criteria

- [ ] `make -C /main merge PR=N` from worktree is blocked
- [ ] `make merge PR=N` from worktree is still blocked
- [ ] `make merge PR=N` from main still works
