# Plan #189: Meta-Process Robustness Overhaul

**Status:** 📋 Planned
**Priority:** **Critical**
**Blocked By:** None
**Blocks:** All future meta-process reliability

---

## Gap

**Current:** Meta-process has multiple failure modes:
- Plan index drift (two files need manual sync)
- Stale claims (manual release, often forgotten)
- Orphaned worktrees (cleanup can fail partway)
- CWD invalidation (worktrees deleted while in use)
- Content mismatches (status doesn't match content)

**Target:** Self-maintaining meta-process where:
- Single source of truth (no sync needed)
- Automatic cleanup (no manual steps)
- Fail-safe defaults (block when uncertain)
- Observable state (always know what's happening)

**Why Critical:** User has tried to fix meta-process issues "100 times" - patches don't stick because root causes aren't addressed.

---

## References Reviewed

- `CLAUDE.md` - Current meta-process documentation
- `hooks/pre-commit` - Current validation (plan #186 added index check)
- `scripts/check_claims.py` - Manual claim management
- `scripts/sync_plan_status.py` - Manual sync required
- `scripts/finish_pr.py` - Multi-step cleanup that can fail
- `.claude/active-work.yaml` - Manual claims file

---

## Files Affected

- `scripts/generate_plan_index.py` (create) - Generate index from plan files
- `hooks/pre-commit` (modify) - Add content validation, auto-generate index
- `scripts/check_claims.py` (modify) - Switch to branch-based claims
- `scripts/finish_pr.py` (modify) - Make atomic with validation
- `scripts/safe_worktree_remove.py` (modify) - Add process locking
- `CLAUDE.md` (modify) - Document new workflow
- `docs/plans/CLAUDE.md` (modify) - Will be auto-generated
- `.claude/active-work.yaml` (delete) - No longer needed

---

## Plan

### Design Principles

1. **Single Source of Truth** - Never maintain two files that need sync
2. **Computed > Stored** - Generate state from reality, don't store separately
3. **Atomic Operations** - All-or-nothing, no partial states
4. **Fail-Safe** - When uncertain, block and ask rather than proceed
5. **Observable** - Every state change is logged and visible

### Phase 1: Computed Index (Eliminate Sync)

**Problem:** `docs/plans/CLAUDE.md` index must manually match plan files.

**Solution:** Generate index from plan files on every commit.

```python
# scripts/generate_plan_index.py
def generate_index():
    """Generate CLAUDE.md index from plan files."""
    plans = []
    for f in sorted(Path("docs/plans").glob("[0-9]*_*.md")):
        meta = parse_plan_file(f)
        plans.append({
            "number": meta["number"],
            "name": meta["name"],
            "file": f.name,
            "priority": meta["priority"],
            "status": meta["status"],
            "blocks": meta["blocks"]
        })

    return render_template("docs/plans/CLAUDE.md.template", plans=plans)
```

**Pre-commit hook:**
```bash
# Generate index and stage it
python scripts/generate_plan_index.py > docs/plans/CLAUDE.md
git add docs/plans/CLAUDE.md
```

**Result:** Index is always correct by construction. No manual sync. No drift.

### Phase 2: Content Validation (Enforce Consistency)

**Problem:** Plan status doesn't match content (e.g., "Planned" but no ## Plan).

**Solution:** Pre-commit validates content matches status.

```python
# In hooks/pre-commit
def validate_plan_content(plan_file):
    meta = parse_plan_file(plan_file)

    if meta["status"] == "Planned":
        assert "## Plan" in content, f"{plan_file}: Planned but no ## Plan section"

    if meta["status"] == "Complete":
        assert "Verification Evidence" in content, f"{plan_file}: Complete but no evidence"

    # Validate [Plan #N] references
    for ref in find_plan_refs(content):
        assert plan_exists(ref), f"{plan_file}: References non-existent Plan #{ref}"
```

**Result:** Can't commit invalid content. Consistency enforced at source.

### Phase 3: Branch-Based Claims (Eliminate Stale Claims)

**Problem:** Manual claims in `.claude/active-work.yaml` become stale.

**Solution:** Branch existence IS the claim. No separate tracking.

**Rules:**
- If `plan-N-*` or `feature-*` branch exists → work is claimed
- If branch has commits in last 48h → actively worked
- If branch merged/deleted → claim automatically released
- Worktree existence → work is active right now

**Implementation:**
```python
# scripts/check_claims.py (rewritten)
def get_active_claims():
    """Get claims from git branches, not YAML file."""
    claims = []
    for branch in get_remote_branches():
        if match := re.match(r"plan-(\d+)-", branch):
            plan_num = int(match.group(1))
            last_commit = get_last_commit_time(branch)
            worktree = get_worktree_for_branch(branch)

            claims.append({
                "branch": branch,
                "plan": plan_num,
                "last_activity": last_commit,
                "has_worktree": worktree is not None,
                "stale": is_stale(last_commit, worktree)
            })
    return claims

def is_stale(last_commit, worktree):
    """Stale = no commits in 48h AND no active worktree."""
    if worktree and worktree_has_recent_activity(worktree):
        return False
    return (now() - last_commit) > timedelta(hours=48)
```

**Delete:** `.claude/active-work.yaml` - no longer needed

**Result:** Claims can't become stale. Branch merged = claim gone.

### Phase 4: Worktree Locking (Prevent CWD Invalidation)

**Problem:** Deleting worktree while CC is using it breaks their shell.

**Solution:** Check for processes using worktree before deletion.

```python
# scripts/safe_worktree_remove.py
def remove_worktree(path):
    # Check if any process has this as CWD
    for proc in psutil.process_iter(['pid', 'cwd']):
        try:
            if proc.info['cwd'] and path in proc.info['cwd']:
                raise BlockedError(
                    f"BLOCKED: Process {proc.pid} is using this worktree\n"
                    f"Wait for them to finish or ask them to move."
                )
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            pass

    # Also check for CC session markers
    marker = Path(path) / ".claude" / "session-marker"
    if marker.exists():
        age = now() - marker.stat().st_mtime
        if age < timedelta(minutes=30):
            raise BlockedError(
                f"BLOCKED: Active CC session in this worktree (last activity {age} ago)"
            )

    # Safe to remove
    git_worktree_remove(path)
```

**Result:** Can't delete worktree that's in use. No more CWD invalidation.

### Phase 5: Atomic Finish (Eliminate Partial Failures)

**Problem:** `make finish` has multiple steps that can fail independently.

**Solution:** Validate everything first, then execute with rollback.

```python
# scripts/finish_pr.py (rewritten)
def finish(branch, pr):
    # === VALIDATION PHASE (can fail safely) ===
    errors = []

    # Must be in main
    if not in_main_worktree():
        errors.append("Must run from main, not worktree")

    # PR must be mergeable
    if not pr_is_mergeable(pr):
        errors.append(f"PR #{pr} is not mergeable")

    # Worktree must be clean (or not exist)
    worktree = get_worktree_for_branch(branch)
    if worktree and has_uncommitted_changes(worktree):
        errors.append(f"Worktree has uncommitted changes: {worktree}")

    # Worktree must not be in use
    if worktree and worktree_in_use(worktree):
        errors.append(f"Worktree is in use by another process")

    if errors:
        print("BLOCKED: Cannot finish PR")
        for e in errors:
            print(f"  - {e}")
        return 1

    # === EXECUTION PHASE (atomic) ===
    # Only one operation that can't be undone: merge
    merge_pr(pr)  # This also deletes remote branch

    # === CLEANUP PHASE (best effort, logged) ===
    if worktree:
        try:
            remove_worktree(worktree)
            print(f"✓ Removed worktree: {worktree}")
        except Exception as e:
            print(f"⚠ Worktree cleanup failed: {e}")
            print(f"  Run manually: make worktree-remove BRANCH={branch}")

    print(f"✓ PR #{pr} merged successfully")
    return 0
```

**Result:** Either PR merges cleanly or nothing happens. No partial states.

### Phase 6: CLAUDE.md Updates

Update documentation to explain:

1. **Why worktrees exist** - Isolation prevents corruption, not just organization
2. **Why claims exist** - Coordination, not bureaucracy (will be automatic)
3. **What happens if you bypass** - Concrete consequences
4. **How to recover** - Step-by-step for each failure mode

Add new section:

```markdown
## Meta-Process Guarantees

When you follow the meta-process:
- Your work won't be lost (worktree isolation)
- Your work won't conflict (branch-based claims)
- Your commits won't break the build (pre-commit validation)
- Your PRs will merge cleanly (atomic finish)

When you bypass the meta-process:
- You may lose work (main has no isolation)
- You may conflict with others (no claim = no coordination)
- You may break the build (no validation)
- You may create inconsistent state (partial operations)
```

---

## Required Tests

### Unit Tests

| Test | Verifies |
|------|----------|
| `test_generate_index_matches_files` | Index generation is accurate |
| `test_content_validation_blocks_invalid` | Pre-commit catches mismatches |
| `test_branch_claims_detect_stale` | Stale detection works |
| `test_worktree_locking_blocks_in_use` | Can't delete in-use worktree |
| `test_finish_validates_before_merge` | Validation runs first |
| `test_finish_atomic_on_failure` | Failure doesn't leave partial state |

### Integration Tests

| Test | Verifies |
|------|----------|
| `test_full_workflow_happy_path` | Complete cycle works |
| `test_full_workflow_with_failures` | Failures handled gracefully |

---

## E2E Verification

| Scenario | Steps | Expected |
|----------|-------|----------|
| Index auto-generated | Create plan file, commit | Index updated automatically |
| Content validation | Change status without content, commit | BLOCKED |
| Branch claim | Create branch, check claims | Branch shows as claimed |
| Stale detection | Old branch, no worktree | Marked as stale |
| Worktree locking | Try to delete in-use worktree | BLOCKED |
| Atomic finish | Run finish with validation error | Nothing changes |

---

## Verification

### Tests & Quality
- [ ] All unit tests pass
- [ ] Integration tests pass
- [ ] Full E2E workflow verified
- [ ] Type check passes

### Documentation
- [ ] CLAUDE.md updated with new workflow
- [ ] Recovery procedures documented
- [ ] Consequences of bypass documented

### Migration
- [ ] Existing claims migrated to branch-based
- [ ] Old `.claude/active-work.yaml` removed
- [ ] All existing plans pass content validation (or fixed)

---

## Notes

### Why This Fixes It For Real

Previous fixes were patches because they added validation without removing the manual steps that cause drift. This plan:

1. **Removes manual sync** - Index is computed, not maintained
2. **Removes manual claims** - Branch existence is the claim
3. **Removes partial failures** - Atomic operations only
4. **Prevents accidents** - Locking prevents in-use deletion

### Migration Path

1. Fix all existing content mismatches first
2. Deploy computed index (backward compatible)
3. Deploy content validation (may require fixes)
4. Deploy branch-based claims (migration script)
5. Deploy atomic finish (backward compatible)
6. Deploy worktree locking (backward compatible)
7. Delete old `.claude/active-work.yaml`

### Risks

- Branch-based claims may not work for very long-running work (>48h)
  - Mitigation: Activity detection includes worktree file changes
- psutil dependency for process detection
  - Mitigation: Graceful fallback if not available
