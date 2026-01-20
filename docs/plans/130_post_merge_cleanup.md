# Plan #130: Automatic Post-Merge Cleanup

**Status:** 📋 Planned
**Priority:** Medium
**Blocked By:** None
**Blocks:** Meta-process reliability

---

## Problem

When PRs are merged without using `make finish`, worktrees and claims become orphaned:

1. **Direct GitHub merges** - Web UI, mobile app, or API merges bypass local hooks
2. **`make merge` without `make finish`** - Merges PR but doesn't clean up worktree
3. **Non-standard worktree locations** - Worktrees outside `./worktrees/` aren't found

This leads to:
- Accumulating orphaned worktrees consuming disk space
- Stale claims blocking plan numbers
- Confusion about what work is actually in progress

## Current State

The `enforce-make-merge.sh` hook prevents Claude Code from bypassing the workflow, but:
- Only runs when CC executes bash commands
- Doesn't prevent humans or other tools from direct merges
- No server-side enforcement

## Proposed Solution

### Option A: GitHub Action (Recommended)

Add a GitHub Action that runs on PR merge:

```yaml
# .github/workflows/post-merge-cleanup.yml
name: Post-Merge Cleanup

on:
  pull_request:
    types: [closed]

jobs:
  cleanup:
    if: github.event.pull_request.merged == true
    runs-on: ubuntu-latest
    steps:
      - name: Log merge for tracking
        run: |
          echo "PR #${{ github.event.pull_request.number }} merged"
          echo "Branch: ${{ github.event.pull_request.head.ref }}"
          # Could notify a webhook or update a tracking file
```

**Limitations:** Can't directly clean up local worktrees from CI.

### Option B: Periodic Local Cleanup Script

Add a script that finds and reports orphaned worktrees:

```bash
# scripts/cleanup_orphaned_worktrees.py
# Finds worktrees whose branches no longer exist on remote
# Reports them for manual cleanup or auto-cleans with --force
```

Run periodically or at session start.

### Option C: Enhanced `make status`

Modify `meta_status.py` to:
1. Detect orphaned worktrees (branch deleted from remote)
2. Suggest cleanup commands
3. Optionally auto-clean with confirmation

## Files Affected

- scripts/cleanup_orphaned_worktrees.py (create)
- Makefile (modify)
- scripts/meta_status.py (modify)
- scripts/CLAUDE.md (modify)

## Files to Create/Modify

| File | Change |
|------|--------|
| `scripts/cleanup_orphaned_worktrees.py` | New script to find/clean orphaned worktrees |
| `Makefile` | Add `make clean-worktrees` target |
| `scripts/meta_status.py` | Add orphan detection to status report |
| `.github/workflows/post-merge-cleanup.yml` | Optional: CI notification |

## Implementation Steps

1. Create `cleanup_orphaned_worktrees.py`:
   - List all worktrees
   - Check if branch exists on remote
   - Check if associated PR is merged
   - Report orphans with cleanup commands

2. Add Makefile target:
   ```makefile
   clean-worktrees:
       python scripts/cleanup_orphaned_worktrees.py --auto
   ```

3. Enhance meta_status.py:
   - Already detects some issues (worktree mismatch)
   - Add: "Orphaned worktree: branch merged, worktree remains"
   - Suggest: `make clean-worktrees`

4. Optional: Add session-start hook to check for orphans

## Verification

- [ ] `cleanup_orphaned_worktrees.py` correctly identifies orphans
- [ ] Script handles non-standard worktree locations
- [ ] `make clean-worktrees` safely removes orphaned worktrees
- [ ] `meta_status.py` reports orphans in "Needs Attention" section
- [ ] No false positives (active work incorrectly flagged)

## Notes

- Must handle worktrees in different locations (./worktrees/, ../worktrees/, etc.)
- Should check for uncommitted changes before cleanup
- Claims should be auto-released when associated worktree is cleaned
- Consider adding to session startup checks
