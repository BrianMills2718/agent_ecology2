# Handoff: PR Review Issues

**Created:** 2026-01-18T04:45:00Z
**From:** meta (main)
**Status:** Open

---

## Summary

Several PRs have CI failures that need attention from their owners. This handoff documents the issues so owners can fix them.

---

## PR #259 (plan-71-phase2) - Test Naming Issue

**Owner:** Whoever has worktree `plan-71-phase2` or similar
**Branch:** plan-71-phase2
**Issue:** CI `fast-checks` failing

**Problem:**
- Created: `tests/unit/test_template_injection.py`
- Expected: `tests/unit/test_template.py`

The `check_new_code_tests.py` script expects test files to match source files:
- `src/agents/template.py` → `tests/unit/test_template.py`

**Fix:** Rename `test_template_injection.py` to `test_template.py`

---

## PR #257 (plan-70-complete) - Missing Test

**Owner:** Whoever has worktree `plan-70-complete`
**Branch:** plan-70-complete
**Issue:** CI `plans` check failing

**Problem:**
Plan #70 documents `test_agent_modifies_workflow` in Required Tests but the test doesn't exist.

This test is REQUIRED - it maps to AC-6 (Agent self-modifies workflow) which is a Phase 1 acceptance criterion.

**Fix:** Either:
1. Implement `test_agent_modifies_workflow` in `tests/integration/test_agent_workflow.py`, OR
2. If the feature isn't implemented, remove from Required Tests (but this means Phase 1 is incomplete)

---

## PR #255 (plan-70-ownership-check) - Same Issue

**Owner:** Whoever has worktree `plan-70-ownership-check`
**Branch:** plan-70-ownership-check
**Issue:** Same as PR #257 - Plan #70 has missing test

**Note:** This PR and #257 both touch Plan #70. They may conflict. Coordinate.

---

## PR #258 (trivial-enforce-merge-hook) - Needs Rebase

**Owner:** Whoever has worktree `trivial-enforce-merge-hook`
**Branch:** trivial-enforce-merge-hook
**Issue:** Behind main, needs rebase

**Fix:**
```bash
cd worktrees/trivial-enforce-merge-hook
git fetch origin main && git rebase origin/main
git push --force-with-lease
```

---

## PRs #260, #261 - Pending CI

These PRs have `plans` check pending. May pass once CI completes.

---

## How to Claim This Work

If you own one of these branches:
1. Go to your worktree: `cd worktrees/<branch-name>`
2. Fix the issue described above
3. Push the fix
4. Delete this section from the handoff once resolved

---

## Meta-Process Notes

This handoff was created because:
1. CC instances can't modify each other's branches (ownership rule)
2. GitHub PR comments aren't automatically surfaced to CC instances
3. We need a file-based mechanism for cross-instance communication

---

## Pending Meta-Process Improvements

### 1. Add handoff display to meta_status.py

**Why blocked:** Can't edit `scripts/meta_status.py` from main (protect-main.sh hook working correctly)

**Proposed change:** Add `get_handoffs()` function that reads `.claude/handoffs/*.md` and displays open handoffs in the status output.

**To implement:** Create a trivial branch or include in next plan work:
```bash
make worktree BRANCH=trivial-handoff-display
# Add get_handoffs() to scripts/meta_status.py
# Add "## Handoffs" section to print_status()
```

### 2. Enforce test naming convention earlier

Currently `check_new_code_tests.py` catches naming issues in CI. Consider:
- Pre-commit hook that validates test file naming
- Better error message suggesting the correct name

### 3. Document handoff checking in Work Priorities

Added to CLAUDE.md - CC instances should check `.claude/handoffs/` on startup.
