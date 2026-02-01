# Gap 242: Makefile Workflow Simplification

**Status:** 📋 Planned
**Priority:** Low
**Blocked By:** None
**Blocks:** None

---

## Gap

**Current:** The Makefile has ~40 targets covering the full meta-process workflow plus cleanup, recovery, CI config, and gap management. Many cleanup targets (clean-claims, clean-merged, clean-branches, clean-worktrees) exist because automated hooks don't yet cover all maintenance. Recovery targets (health, health-fix, recover, recover-auto) are rarely used. The gap management targets (gaps, gaps-sync, gaps-check) overlap with plan scripts.

**Target:** A leaner Makefile where:
1. Cleanup targets are unnecessary because session-startup-cleanup.sh handles them automatically
2. Recovery is folded into health checks or startup hooks
3. Gap management uses scripts directly (not make wrappers)
4. The core workflow (worktree → check → finish) is the primary interface

## Analysis

### Targets by Category (post-trivial-cleanup)

**Core workflow (keep):** status, worktree, test, check, pr-ready, pr, finish (~7)
**Useful variants (keep):** test-quick, check-quick, mypy, lint, lint-suggest, worktree-list, worktree-remove, worktree-remove-force (~8)
**Simulation (keep):** run, dash, dash-run, kill, analyze (~5)
**Claims (keep for now):** claim, release, claims (~3)
**CI config (keep):** ci-status, ci-require, ci-optional (~3)
**PR info (keep):** pr-list, pr-view (~2)
**Setup (keep):** install, install-hooks, help (~3)

**Candidates for automation/removal (deferred):**
- clean-claims, clean-merged → automate in session-startup-cleanup.sh
- clean-branches, clean-branches-delete → automate or run periodically
- clean-worktrees, clean-worktrees-auto → automate in session-startup-cleanup.sh
- health, health-fix → fold into startup hook or `make check`
- recover, recover-auto → fold into health-fix
- gaps, gaps-sync, gaps-check → use scripts directly
- rebase → redundant with pr-ready (which also rebases)
- clean → rarely needed manually

### Dependencies

- session-startup-cleanup.sh must reliably handle all automated cleanup before targets can be removed
- Hooks reference specific make target names - need audit
- CLAUDE.md documents all targets - needs update with each removal

## Implementation Plan

1. Extend session-startup-cleanup.sh to cover: stale branches, orphaned worktrees
2. Remove cleanup targets that are fully automated
3. Consolidate recovery into health checks
4. Remove gap management make targets (scripts work directly)
5. Remove `rebase` (subset of `pr-ready`)
6. Update CLAUDE.md and pattern docs

## Acceptance Criteria

- [ ] Makefile has <30 targets
- [ ] All removed cleanup is handled by automation
- [ ] No broken references in CLAUDE.md or patterns
- [ ] `make help` shows a clean, focused command list
