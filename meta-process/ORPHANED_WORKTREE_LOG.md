# Orphaned Worktree Incident Log

This log tracks every occurrence of orphaned worktrees — worktrees that persist after
their associated work is complete (PR merged, branch deleted, or work abandoned).
The purpose is to stop running in circles — we keep "fixing" these without fixing them.

## Known Failure Classes

### Class A: PR Merged, Worktree Not Deleted

**Symptom:** Worktree exists in `worktrees/` but the PR was merged and branch deleted.
`cleanup_orphaned_worktrees.py` reports it as orphaned.

**Expected behavior:** `make finish BRANCH=X PR=N` should:
1. Merge the PR
2. Delete the remote branch
3. Delete the local worktree
4. Release the claim

**Root cause candidates:**
- `finish_pr.py` failed partway through
- Worktree has uncommitted changes (cleanup skipped)
- `make finish` wasn't used (manual `gh pr merge`)

### Class B: Uncommitted Changes Blocking Cleanup

**Symptom:** `cleanup_orphaned_worktrees.py --auto` reports "SKIPPED (uncommitted changes)".
The worktree can't be auto-cleaned because it has modified files.

**Root cause candidates:**
- Work was done but never committed
- `.claim.yaml` was modified (local file, not tracked)
- Generated files left behind

### Class C: Stale Claims Without Worktrees

**Symptom:** `check_claims.py --list` shows claims, but worktrees don't exist.

**Root cause candidates:**
- Worktree manually deleted without releasing claim
- `git worktree remove` used directly instead of `make worktree-remove`

### Class D: Claims Exist for Merged Work

**Symptom:** Claims exist for branches that were already merged.

**Root cause candidates:**
- `finish_pr.py` released claim before merge failed
- Claim release succeeded but worktree deletion failed

## Defenses In Place

| Defense | Location | What it does |
|---------|----------|--------------|
| `finish_pr.py` | `scripts/finish_pr.py` | Merges PR + deletes worktree + releases claim |
| `cleanup_orphaned_worktrees.py` | `scripts/` | Finds and optionally cleans orphaned worktrees |
| `cleanup_claims_mess.py` | `scripts/` | One-time cleanup of stale/duplicate claims |
| `check_claims.py --cleanup-orphaned` | `scripts/` | Removes claims with missing worktrees |
| `check_claims.py --cleanup-stale` | `scripts/` | Removes inactive claims (>8h default) |
| `health_check.py` | `scripts/` | Reports orphaned worktrees and claims |
| `block-worktree-remove.sh` | `.claude/hooks/` | Blocks direct `git worktree add/remove` |
| `enforce-make-merge.sh` | `.claude/hooks/` | Blocks direct `gh pr merge` |

## What Would Actually Fix This

### For Class A (PR merged, worktree not deleted):
1. **Audit `finish_pr.py`** — Is it atomic? If merge succeeds but cleanup fails,
   what state are we left in?
2. **Add cleanup to session startup** — If orphaned worktrees exist, prompt to clean

### For Class B (uncommitted changes blocking cleanup):
1. **`.claim.yaml` should be gitignored** — It's a local coordination file, not code
2. **`--force` cleanup option** — For known-safe cleanup of local-only files

### For Class C (stale claims without worktrees):
1. **`check_claims.py --cleanup-orphaned`** should handle this — verify it works

### For Class D (claims for merged work):
1. **Verify `finish_pr.py` order of operations** — Should be:
   1. Merge PR
   2. Verify merge succeeded
   3. Delete worktree
   4. Release claim (only after worktree gone)

## Incident Log

### Incident #1 - 2026-02-01

**Session:** General review
**Class:** A + B (PR merged, uncommitted changes blocking cleanup)
**Worktrees found:**
- `plan-248-script-testing` — PR #917 merged, has uncommitted `.claim.yaml` + `docs/plans/248_script_testing.md`
- `explore-v4-architecture` — Branch deleted, has uncommitted `.claim.yaml` + untracked generated files

**Analysis:**
Both worktrees have `.claim.yaml` modified (local coordination file) which blocks auto-cleanup.
The `explore-v4-architecture` also has untracked files (`repomix.v4-architecture.json`,
`v4-architecture-prompt.md`) from exploratory work.

**Investigation findings:**

1. **`plan-248-script-testing`** — No longer exists. Appears to have been cleaned up.
   PR #917 was followed by more work (PRs #933), then worktree was deleted.

2. **`explore-v4-architecture`** — Still exists with:
   - Modified `.claim.yaml` (local coordination file)
   - Untracked `repomix.v4-architecture.json` (generated ~81K token context file)
   - Untracked `v4-architecture-prompt.md` (exploration prompt for V4 architecture)
   - No remote branch (never pushed)
   - No PR (exploratory work, never formalized)
   - Claim exists for Plan #155 (deferred)

**Root cause:** This is legitimate abandoned exploratory work, not a bug. The worktree
was created for exploratory research on Plan #155, the work was done but never committed
or pushed because it was exploration, not implementation. The claim was created but
never released because the work was neither completed nor formally abandoned.

**Pattern identified:** Exploratory worktrees (research, spikes, investigations) don't
fit the normal claim→PR→merge→cleanup lifecycle. They get stuck in limbo.

**Resolution:**
1. Save valuable content to docs/research/ or external archive before cleanup
2. Release the claim: `python scripts/check_claims.py --release --id explore-v4-architecture`
3. Force-clean the worktree: `python scripts/cleanup_orphaned_worktrees.py --force`

**Follow-up:**
1. Consider adding an "exploratory" claim type that auto-expires
2. Document the pattern: exploratory worktrees should be explicitly abandoned when done
3. Add `.claim.yaml` to `.gitignore` — it's a local file that shouldn't block cleanup

### Incident #2 - 2026-02-01

**Session:** General review session
**Class:** NEW — Uncommitted changes in main (cross-reference: MP-018)
**Files found:** 16 files modified in main:
- `src/simulation/runner.py` — 138 lines changed (genesis removal)
- `src/world/action_executor.py` — 190 lines changed (genesis removal)
- `src/world/artifacts.py` — 5 lines removed
- `src/world/world.py` — 84 lines changed
- 12 test files with `pytest.skip` markers added

**Analysis:**
This is the SAME pattern as MP-018 recurrence #2. Genesis removal work is leaking into main.
The `protect-main.sh` hook should block these edits, but they're appearing anyway.

**Key question:** Where are these changes coming from?
- Not from this session (I didn't edit these files)
- The worktree `explore-v4-architecture` exists and may be involved
- Possibly from a merge/rebase operation that brought in uncommitted changes

**Resolution:** Cleaned up with `git checkout src/ tests/`

**Follow-up:**
1. Need to investigate the explore-v4-architecture worktree
2. Check if the worktree's state is bleeding into main somehow
3. This is the 3rd occurrence of genesis-related changes leaking into main

---

## Template for New Incidents

```markdown
### Incident #N - YYYY-MM-DD

**Session:** What was being worked on
**Class:** A, B, C, or D
**Worktrees found:** List of orphaned worktrees
**Analysis:** Root cause investigation findings
**Questions to investigate:** Specific things to check
**Resolution:** How it was fixed
**Follow-up:** Any systemic fixes added
```

---

## Investigation Checklist

When orphaned worktrees are found, investigate:

1. **How was the PR merged?**
   - `make finish BRANCH=X PR=N` (correct)
   - `gh pr merge N` directly (bypasses cleanup)
   - Manual merge on GitHub (bypasses everything)

2. **What's in the worktree?**
   - `git -C worktrees/X status`
   - Are changes committed? Staged? Untracked?

3. **What's the claim state?**
   - `python scripts/check_claims.py --list`
   - Is there a claim for this worktree?

4. **What's the branch state?**
   - `git branch -r | grep X` — Does remote branch exist?
   - `gh pr list --state merged | grep X` — Was PR merged?

5. **Check `finish_pr.py` execution:**
   - Was it run? Check session transcript
   - Did it complete? Check for partial execution
