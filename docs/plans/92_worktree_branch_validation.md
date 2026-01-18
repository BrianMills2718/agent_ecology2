# Plan #92: Worktree/Branch Mismatch Detection

**Status:** ✅ Complete
**Priority:** High (Meta-process integrity)
**Complexity:** Low
**Blocked by:** None

## Files Affected

- scripts/meta_status.py (modify)
- CLAUDE.md (modify)
- tests/scripts/__init__.py (create)
- tests/scripts/test_meta_status.py (create)

## Problem Statement

When a worktree directory is reused for a different plan (by switching branches inside), the orphan detection in `meta_status.py` can give false positives or miss actual issues because:

1. The claim `cc_id` may reference the worktree directory name
2. The orphan detection compares against the branch name
3. These can be different when branches are switched inside existing worktrees

**Example that caused the issue:**
- Worktree directory: `worktrees/plan-86-ooda-logging`
- Branch inside: `plan-88-ooda-fresh`
- Claim cc_id: `plan-86-ooda-logging`
- Result: Orphan detection checked branch name against claims, found no match, reported orphan

## Solution

### 1. Improve `meta_status.py` orphan detection

- Extract both worktree directory name AND branch name
- Check claims against BOTH (directory pattern AND branch)
- Report specific mismatch warnings when directory != branch pattern
- Add "Directory/Branch Mismatch" as a distinct issue type

### 2. Add worktree branch validation hook

- Create a post-checkout hook (or enhance existing hooks)
- Warn when branch name doesn't match worktree directory pattern
- Pattern: worktree `plan-NN-foo` should have branch `plan-NN-*`

### 3. Update `check_claims.py`

- Add validation that worktree directory pattern matches branch
- Warn during claim operations if mismatch detected

## Required Tests

- `tests/scripts/test_meta_status.py::TestWorktreeBranchMismatchDetection::test_detects_mismatch_when_dir_and_branch_have_different_plans`
- `tests/scripts/test_meta_status.py::TestOrphanDetectionUsesBothDirAndBranch::test_not_orphaned_when_claim_matches_dir_name`
- `tests/scripts/test_meta_status.py::TestOrphanDetectionUsesBothDirAndBranch::test_not_orphaned_when_claim_matches_branch`
- `tests/scripts/test_meta_status.py::TestOrphanDetectionUsesBothDirAndBranch::test_orphaned_when_no_matching_claim`

## Implementation Checklist

- [ ] Update `meta_status.py` `get_worktrees()` to return directory name
- [ ] Update `meta_status.py` `identify_issues()` to detect mismatches
- [ ] Add hook to warn on branch checkout in worktrees
- [ ] Update `check_claims.py` to validate consistency
- [ ] Add tests for new detection logic
- [ ] Update CLAUDE.md with guidance on worktree reuse (don't do it)

## Acceptance Criteria

1. `meta_status.py` reports when worktree directory doesn't match branch pattern
2. Branch switching in worktrees produces a warning
3. No false positive orphan reports when cc_id matches directory (not branch)
