# Plan 250: Meta-Process Enforcement Gaps

**Status:** 📋 Planned
**Priority:** High
**Blocked By:** None
**Blocks:** None

---

## Gap

**Current:** Multiple meta-process enforcement gaps allow violations to slip through:

1. **Hook bypass evidence:** Historical sessions edited main directly despite `protect-main.sh` being registered. Cause unclear but hooks can silently fail.

2. **No dirty-main detection:** Sessions start without warning if main has uncommitted `src/`/`tests/` changes.

3. **Claims without worktrees:** Claims can be created/exist without associated worktrees, causing orphaned claims.

4. **Plan status not in CI:** `sync_plan_status.py --check` validates plan file/index/content consistency but isn't enforced in CI.

5. **Silent hook failures:** When hooks fail (timeout, crash, config issue), there's no logging or alerting.

**Target:** Close all enforcement gaps so violations are prevented or immediately visible.

**Evidence:**
- `tests/conftest.py` uncommitted in main (edit bypassed hook on 2026-01-21)
- Stale claim `trivial-cwd-incident-6` exists without worktree
- 6 plans have status/content mismatches caught by `sync_plan_status.py`

---

## References Reviewed

- `.claude/hooks/protect-main.sh` - Current hook implementation
- `.claude/settings.json` - Hook registration
- `meta-process/ISSUES.md` - MP-018 investigation notes
- `scripts/health_check.py` - Current health check (warns but doesn't block)
- `scripts/sync_plan_status.py` - Plan status validation

---

## Plan

### Phase 1: Add Startup Dirty-Main Warning

Add hook to warn at session start if main has uncommitted `src/` or `tests/` changes.

**Files:**
- `.claude/hooks/session-startup-cleanup.sh` - Add dirty check
- Or new hook: `.claude/hooks/warn-dirty-main.sh`

**Behavior:**
- On first Read/Glob in session, check `git status --short src/ tests/`
- If files modified, emit warning (not blocking - could be intentional work)
- Suggest `git checkout` or `git stash` commands

### Phase 2: Require Worktree for Claims

Modify claim system so claims require a worktree path.

**Files:**
- `scripts/check_claims.py` - Require worktree path in `--claim`
- `scripts/create_worktree.sh` - Already does this correctly
- `.claude/active-work.yaml` schema - Add `worktree_path` as required

**Behavior:**
- `--claim` without worktree path fails with helpful error
- Orphaned claim detection becomes simpler (worktree missing = orphaned)

### Phase 3: Add Plan Status to CI

Add plan status validation to CI pipeline.

**Files:**
- `.github/workflows/ci.yml` - Add `python scripts/sync_plan_status.py --check`

**Behavior:**
- PR blocked if plan status/content mismatches exist
- Authors must fix with `--fix-content` before merge

### Phase 4: Add Hook Execution Logging

Add optional debug logging to hooks for troubleshooting.

**Files:**
- `.claude/hooks/hook-debug.sh` - Shared logging utility
- Modify hooks to source it and log on entry/exit
- `meta-process.yaml` - Add `hooks.debug: true/false` config

**Behavior:**
- When `hooks.debug: true`, hooks log to `.claude/hook-debug.log`
- Helps diagnose silent failures

### Phase 5: Fix Existing Deferred Plan Mismatches

Fix the 6 plans with status "Planned" that lack `## Plan` sections.

**Files:**
- `docs/plans/138_provider_union_schema_transform.md`
- `docs/plans/155_v4_architecture_deferred.md`
- `docs/plans/162_contract_artifact_lookup.md`
- `docs/plans/207_executor_refactor.md`
- `docs/plans/209_trigger_hook_integration.md`
- `docs/plans/240_cross_cc_review_enforcement.md`

**Change:**
- Change status from "Planned" to "Deferred" (accurate for items without `## Plan`)
- Or add minimal `## Plan` sections if they should be Planned

---

## Open Questions

1. **Should dirty-main warning block or just warn?** Blocking could break legitimate workflows (e.g., manual testing). Recommend: warn only, with clear remediation.

2. **What if someone needs a claim before creating worktree?** Current flow is `make worktree` which claims + creates atomically. The claim-then-worktree pattern shouldn't be supported.

3. **Should hook debug logging be on by default?** Adds overhead but aids diagnosis. Recommend: off by default, enable when debugging.

---

## Required Tests

### New Tests

| Test File | Test Function | What It Verifies |
|-----------|---------------|------------------|
| `tests/test_check_claims.py` | `test_claim_requires_worktree_path` | `--claim` without worktree fails |
| `tests/test_check_claims.py` | `test_orphaned_claim_detection` | Missing worktree detected |

### Existing Tests (Must Pass)

| Test Pattern | Why |
|--------------|-----|
| `tests/unit/test_*` | No regressions |
| `scripts/check_claims.py --list` | Claim listing works |

---

## Acceptance Criteria

1. [ ] Session startup warns if main has uncommitted `src/`/`tests/` changes
2. [ ] Claims require worktree path (no orphaned claims created)
3. [ ] CI fails on plan status/content mismatches
4. [ ] Hook debug logging available for troubleshooting
5. [ ] No plan status mismatches in repo

---

## Notes

- Phase 1-3 are enforcement
- Phase 4 is observability
- Phase 5 is cleanup

Prioritize prevention (Phases 1-3) over cleanup (Phase 5).
