# Gap 52: Worktree Session Tracking

**Status:** ✅ Complete

**Verified:** 2026-01-15T01:40:31Z
**Verification Evidence:**
```yaml
completed_by: scripts/complete_plan.py
timestamp: 2026-01-15T01:40:31Z
tests:
  unit: 1359 passed, 7 skipped, 5 warnings in 17.56s
  e2e_smoke: PASSED (1.98s)
  e2e_real: PASSED (31.21s)
  doc_coupling: passed
commit: 35988c9
```
**Priority:** Medium
**Blocked By:** None
**Blocks:** None

---

## Gap

**Current:** Worktrees can be deleted while Claude sessions are actively using them, causing shell CWD breakage.

**Target:** Session-aware worktree management that prevents deletion of worktrees with active sessions.

---

## Problem Analysis

### What Happened
1. Claude session working in worktree `plan-29-library-install`
2. Changes committed and pushed, PR merged
3. Worktree deleted (appeared "safe" - no uncommitted changes)
4. Session's shell broke because CWD no longer existed

### Why Current Meta-Process Didn't Prevent This
- `make worktree-remove` checks for uncommitted changes only
- No tracking of which sessions are actively using which worktrees
- Once changes are committed, worktree appears "safe" to delete
- PR #169 (CWD fix) only helps scripts that can cd elsewhere, not running sessions

---

## Design Options

### Option A: Session Registration in active-work.yaml

Track session-to-worktree mapping:

```yaml
claims:
  plan-29-library-install:
    plan: 29
    task: "..."
    session_cwd: "/home/brian/agent_ecology/worktrees/plan-29-library-install"
```

`make worktree-remove` checks if any claim has matching `session_cwd`.

**Pros:** Simple, uses existing infrastructure
**Cons:** Relies on claim not being released before worktree cleanup

### Option B: Separate Session Tracking

New file `.claude/active-sessions.yaml`:

```yaml
sessions:
  - id: "f092742d-..."
    worktree: "plan-29-library-install"
    started: "2026-01-15T00:00:00"
```

Sessions register on start, unregister on clean exit.

**Pros:** Independent of claim lifecycle
**Cons:** Sessions may crash without cleanup (stale entries)

### Option C: Work From Main, Worktrees for Git Only

Sessions always run from main repo root. Worktrees used only for git operations (commits, branches), not as CWD.

**Pros:** CWD never becomes invalid
**Cons:** Major workflow change, loses isolation benefits

### Recommendation: Option A (Enhanced Claims)

Simplest approach - enhance existing claim to include worktree path. Worktree removal blocked while claim exists with that path.

---

## Plan

### Phase 1: Enhanced Claim Tracking

1. Add `worktree_path` field to claims in `active-work.yaml`
2. Update `make worktree` to record path in claim
3. Update `make worktree-remove` to check for claims using that worktree

### Phase 2: Removal Protection

1. `make worktree-remove` fails if claim exists with matching worktree
2. Clear error message: "Worktree in use by claim X - release claim first"
3. Add `--force` flag to override (with warning)

### Phase 3: Cleanup on Release

1. `make release` optionally offers to remove worktree
2. Or separate `make release-and-cleanup` command

---

## Required Tests

- `tests/unit/test_worktree_session.py::TestWorktreeRemovalBlocking::test_worktree_remove_blocked_with_active_claim`
- `tests/unit/test_worktree_session.py::TestWorktreeRemovalBlocking::test_worktree_remove_allowed_after_release`
- `tests/unit/test_worktree_session.py::TestWorktreeRemovalBlocking::test_force_flag_bypasses_claim_check`

---

## Verification

- [ ] Claims track worktree path
- [ ] Worktree removal blocked while claim active
- [ ] Clear error message on blocked removal
- [ ] Force flag works for emergency cleanup
- [ ] Tests pass
