# Plan 70: Ownership Check in Meta-Process

**Status:** 🚧 In Progress
**CC-ID:** plan-70-ownership-check

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

No new tests required - this is documentation and display changes only.

## Acceptance Criteria

- [ ] CLAUDE.md has Priority 0: Check ownership
- [ ] meta_status.py shows PR owner and flags non-owned PRs
- [ ] /proceed skill includes ownership verification
- [ ] docs/meta has ownership respect pattern documented
