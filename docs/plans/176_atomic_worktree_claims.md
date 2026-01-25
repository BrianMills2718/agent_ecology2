# Plan 176: Atomic Worktree-Claim Enforcement

**Status:** ✅ Complete

**Verified:** 2026-01-25T03:55:30Z
**Verification Evidence:**
```yaml
completed_by: scripts/complete_plan.py
timestamp: 2026-01-25T03:55:30Z
tests:
  unit: 2198 passed, 10 skipped, 3 warnings in 53.89s
  e2e_smoke: skipped (--skip-e2e)
  e2e_real: skipped (--skip-real-e2e)
  doc_coupling: passed
commit: 6ad445c
```
**Priority:** High
**Blocked By:** None
**Blocks:** None

---

## Gap

**Current:** Claims and worktrees are loosely coupled advisory systems. They are stored separately (`.claude/active-work.yaml` vs `worktrees/<branch>/`) and can exist independently. This creates multiple failure modes:

1. **Claims on main allowed** - `check_claims.py` warns but allows claiming on `main`
2. **Worktrees without claims** - `make worktree-quick` and direct `git worktree add` bypass claiming
3. **Claims without worktrees** - If worktree creation fails mid-script, claim exists orphaned
4. **Stale claims from external merges** - Merging via GitHub UI leaves claim active, worktree orphaned
5. **Force-released claims** - `finish_pr.py` uses `--force` bypassing ownership verification

**Target:** Worktree existence IS the claim. No separate claim tracking. Impossible states become impossible:
- Worktree exists = claim is active (metadata stored IN worktree)
- Worktree gone = claim gone (no orphan possible)
- No central `active-work.yaml` for claims (becomes derived view only)

**Why High:** These enforcement gaps cause:
- Stale claims requiring manual cleanup
- Orphaned worktrees consuming disk
- Confusion about who owns what work
- Risk of parallel work conflicts

---

## References Reviewed

- `scripts/check_claims.py` - Current claim management, session identity logic
- `scripts/create_worktree.sh` - Worktree creation with claiming (lines 127-134)
- `scripts/finish_pr.py` - PR lifecycle with `--force` release (line 113)
- `Makefile:77-83` - `worktree` and `worktree-quick` targets
- `.claude/active-work.yaml` - Current claim storage format
- `docs/plans/52_worktree_session_tracking.md` - Session marker concept
- `docs/plans/98_robust_worktree_lifecycle.md` - Prior worktree improvements
- `docs/plans/115_worktree_ownership_enforcement.md` - Ownership enforcement

---

## Files Affected

- `scripts/check_claims.py` (modify) - Read claims from worktrees, not YAML
- `scripts/create_worktree.sh` (modify) - Store claim in worktree, not YAML
- `scripts/finish_pr.py` (modify) - Remove worktree = release claim (already true)
- `scripts/safe_worktree_remove.py` (modify) - Removing worktree releases claim
- `scripts/parse_plan.py` (modify) - Fix backtick handling in Files Affected parsing
- `Makefile` (modify) - Remove `worktree-quick`, block `claim` on main
- `hooks/pre-commit` (modify) - Add worktree creation enforcement
- `.claude/active-work.yaml` (modify) - Becomes derived view or removed
- `tests/test_claims.py` (create) - Test atomic enforcement

---

## Plan

### Design: Worktree as Single Source of Truth

```
Before (two loosely-coupled systems):
  .claude/active-work.yaml  ←→  worktrees/<branch>/
        (claims)                    (worktrees)

After (single atomic system):
  worktrees/<branch>/.claim.yaml  =  THE claim
       (worktree IS the claim)
```

### Claim File Format

Each worktree contains `.claim.yaml`:
```yaml
# worktrees/plan-176-atomic-claims/.claim.yaml
plan: 176
task: "Implement atomic worktree-claim enforcement"
session_id: "uuid-here"
claimed_at: "2026-01-25T03:00:00Z"
feature: null  # optional
```

### Changes Required

| File | Change |
|------|--------|
| `scripts/check_claims.py` | Read claims by scanning `worktrees/*/.claim.yaml` |
| `scripts/create_worktree.sh` | Write `.claim.yaml` in worktree instead of updating YAML |
| `scripts/finish_pr.py` | Remove `--force` from release call (worktree removal IS release) |
| `Makefile` | Remove `worktree-quick` target; block `claim` without worktree |
| `hooks/commit-msg` | Add check: non-main branch must have worktree with claim |
| `.claude/active-work.yaml` | Keep for `completed` history only, remove `claims` section |

### Steps

1. **Create claim file format** - Define `.claim.yaml` schema
   - Same fields as current claim: `cc_id`, `task`, `plan`, `feature`, `session_id`, `claimed_at`
   - Add `worktree_path` for self-reference

2. **Update `check_claims.py --list`** - Scan worktrees for claims
   - `load_claims()` reads from `worktrees/*/.claim.yaml`
   - Backwards compat: also read `.claude/active-work.yaml` during migration
   - Remove YAML write path for claims (completed stays)

3. **Update `create_worktree.sh`** - Write claim to worktree
   - After `git worktree add`, write `.claim.yaml` in worktree
   - Remove call to `check_claims.py --claim`
   - Fail if worktree creation fails (no orphan claim possible)

4. **Block claiming on main** - Error, not warning
   - In `check_claims.py --claim`, error if branch is `main`
   - "Cannot claim on main. Use: make worktree"

5. **Remove `worktree-quick`** - No bypass path
   - Delete `worktree-quick` target from Makefile
   - All worktree creation goes through `make worktree`

6. **Add git hook for direct worktree creation** - Prevent bypass
   - `hooks/post-checkout` or pre-push hook
   - If in worktree without `.claim.yaml`, warn/block

7. **Update `finish_pr.py`** - Worktree removal IS release
   - Remove `--force` from release call
   - When worktree is deleted, claim file goes with it
   - No need for separate release step

8. **Migrate existing claims** - One-time migration
   - Script to read `.claude/active-work.yaml` claims
   - Write `.claim.yaml` to corresponding worktrees
   - Clear `claims` section from YAML

9. **Update CLAUDE.md** - Document new model
   - "Worktree = Claim" mental model
   - No separate claiming step needed

---

## Required Tests

### New Tests (TDD)

| Test File | Test Function | What It Verifies |
|-----------|---------------|------------------|
| `tests/test_claims.py` | `test_claim_stored_in_worktree` | `.claim.yaml` created in worktree |
| `tests/test_claims.py` | `test_list_claims_reads_worktrees` | `--list` scans worktree dirs |
| `tests/test_claims.py` | `test_claim_on_main_errors` | `--claim` on main returns error |
| `tests/test_claims.py` | `test_worktree_removal_releases_claim` | Deleting worktree removes claim |
| `tests/test_claims.py` | `test_no_orphan_claims_possible` | Cannot have claim without worktree |

### Existing Tests (Must Pass)

| Test Pattern | Why |
|--------------|-----|
| `tests/test_*.py` | Full suite regression |

---

## E2E Verification

| Scenario | Steps | Expected Outcome |
|----------|-------|------------------|
| Create worktree | `make worktree`, provide plan/task | Worktree has `.claim.yaml`, `--list` shows it |
| Finish PR | `make finish BRANCH=X PR=N` | Worktree deleted, claim gone from `--list` |
| Try claim on main | `python scripts/check_claims.py --claim --task "test"` | Error: "Cannot claim on main" |
| Direct worktree add | `git worktree add worktrees/test -b test` | Warning/block on next commit |

---

## Verification

### Tests & Quality
- [ ] All required tests pass: `python scripts/check_plan_tests.py --plan 176`
- [ ] Full test suite passes: `pytest tests/`
- [ ] Type check passes: `python -m mypy src/ --ignore-missing-imports`

### Documentation
- [ ] CLAUDE.md updated with new model
- [ ] `scripts/CLAUDE.md` updated

### Completion Ceremony
- [ ] Plan file status -> `Complete`
- [ ] `plans/CLAUDE.md` index -> `Complete`
- [ ] Branch merged or PR created

---

## Notes

### Why Not Just Add More Enforcement Hooks?

The user explicitly said: "i want to solve the problems not clean them up or add patches."

Adding hooks to detect orphans is a patch. Making orphans impossible is a fix.

### Backwards Compatibility

During migration:
1. `check_claims.py --list` reads BOTH old YAML and new worktree claims
2. One-time migration script moves claims to worktrees
3. After migration, YAML `claims` section is removed

### Session Identity Preserved

The `.claim.yaml` file stores `session_id` exactly as before. Ownership verification still works - just reads from worktree file instead of central YAML.

### completed History

The `completed` section of `active-work.yaml` is kept. It's a log, not active state, so orphaning isn't a concern.

### Edge Cases

1. **Worktree on detached HEAD** - Claim uses commit hash as `cc_id`
2. **Multiple worktrees same plan** - Error on second worktree creation
3. **Worktree for branch that already has remote PR** - Allow (continuing work)
