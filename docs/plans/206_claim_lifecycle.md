# Plan #206: Meta-Process Claim Lifecycle Fixes

**Status:** Complete
**Priority:** Critical
**Complexity:** Medium

## Problem

The meta-process has several gaps that cause stale claims, orphaned worktrees, and index sync issues:

### 1. No Claim Expiration
Claims persist forever in `.claude/active-work.yaml`. When a session crashes, compacts context, or gets killed, the claim stays orphaned with no automatic cleanup.

### 2. No Crash Recovery
The meta-process assumes `make finish` always runs. But if a session dies mid-work:
- Worktree remains
- Claim remains
- No PR exists
- Next session sees "claimed" and moves on

### 3. Worktrees in Multiple Locations
Worktrees created outside `/worktrees/` directory bypass tracking:
```
/home/brian/brian_projects/agent_ecology2/worktrees/          # expected
/home/brian/brian_projects/agent_ecology2_worktrees/          # external
/home/brian/brian_projects/worktrees/                         # another
```

### 4. Context Compaction Creates Orphans
When CC compacts context and starts "fresh", it loses memory of what it was working on. The old claim persists but no session owns it anymore.

### 5. Plan Index Shows Wrong Status
The plan index shows `❓` for plans that are actually Complete in their files. The auto-generation on commit isn't syncing correctly.

### 6. Duplicate/Inconsistent Claim Data
The `active-work.yaml` file has:
- Duplicate entries (same claim in both `claims` and `completed`)
- Inconsistent fields (`branch:` vs `cc_id:`)
- Legacy flags that aren't cleaned up

### 7. Ownership Blocks Cleanup Even When Owner Gone
When a PR is merged but the session is dead:
- `make worktree-remove` is blocked by ownership check
- `make finish` fails because PR already merged
- No way to detect "owner is gone" vs "owner is active"
- Manual intervention required to release claim first

### 8. Plan Completion Doesn't Verify Doc Cleanup
Plan #199 was marked complete but left stale references in:
- `src/agents/_handbook/planning.md`
- `src/agents/alpha_3/agent.yaml`
- `src/agents/_components/traits/buy_before_build.yaml`
- `src/dashboard/parser.py`

Plan completion should verify no stale references remain.

---

## Solution

### Phase 1: Claim Expiration (Auto-Release)

Add automatic claim release after configurable inactivity period.

**Implementation:**
```python
# In check_claims.py
def is_claim_stale(claim: dict, max_hours: int = 8) -> bool:
    """Check if claim is stale based on worktree last modification."""
    worktree_path = claim.get("worktree_path")
    if not worktree_path or not Path(worktree_path).exists():
        return True  # No worktree = definitely stale

    # Check worktree last modification time
    last_modified = get_worktree_last_modified(worktree_path)
    hours_since = (datetime.now() - last_modified).total_seconds() / 3600
    return hours_since > max_hours

def cleanup_stale_claims(max_hours: int = 8) -> list[str]:
    """Release claims that are stale (no activity for max_hours)."""
    released = []
    for claim in get_active_claims():
        if is_claim_stale(claim, max_hours):
            release_claim(claim["cc_id"])
            released.append(claim["cc_id"])
    return released
```

**Files:**
- `scripts/check_claims.py` - Add stale detection and cleanup
- `scripts/hooks/pre-command.sh` - Run stale cleanup on session start

### Phase 2: Session Startup Cleanup

On session start, automatically clean up orphaned state.

**Implementation:**
```bash
# In .claude/hooks/user-prompt-submit-hook.sh or pre-command.sh
# Run once per session (tracked via session ID file)

SESSION_FILE=".claude/current-session"
if [ ! -f "$SESSION_FILE" ] || [ "$(cat $SESSION_FILE)" != "$CLAUDE_SESSION_ID" ]; then
    echo "$CLAUDE_SESSION_ID" > "$SESSION_FILE"
    # First command in new session - cleanup
    python scripts/check_claims.py --cleanup-orphaned
fi
```

**Cleanup actions:**
1. Remove claims where worktree no longer exists
2. Remove claims older than 24h with no recent commits
3. Deduplicate claims/completed entries
4. Validate worktree paths exist

**Files:**
- `scripts/check_claims.py` - Add `--cleanup-orphaned` flag
- `.claude/hooks/user-prompt-submit-hook.sh` - Trigger on new session

### Phase 3: Worktree Location Enforcement

Block worktree creation outside the standard location.

**Implementation:**
```bash
# In .claude/hooks/block-worktree-remove.sh (rename to block-worktree-ops.sh)
EXPECTED_PREFIX="$REPO_ROOT/worktrees/"

if [[ "$WORKTREE_PATH" != "$EXPECTED_PREFIX"* ]]; then
    echo "BLOCKED: Worktrees must be created in $EXPECTED_PREFIX"
    echo "Got: $WORKTREE_PATH"
    exit 1
fi
```

**Files:**
- `.claude/hooks/block-worktree-remove.sh` - Add path validation

### Phase 4: Plan Index Reliability

Fix the plan index generation to correctly parse all status formats.

**Investigation needed:**
1. Check `scripts/generate_plan_index.py` for parsing bugs
2. Ensure all status formats are recognized:
   - `**Status:** Complete`
   - `**Status:** ✅ Complete`
   - `**Status:** 📋 Planned`
   - `**Status:** Done`
3. Add validation that warns when status can't be parsed

**Files:**
- `scripts/generate_plan_index.py` - Fix status parsing
- `scripts/sync_plan_status.py` - Add validation mode

### Phase 5: Smart Ownership Detection

Allow cleanup when owner is clearly gone (PR merged + session dead).

**Implementation:**
```python
def can_cleanup_worktree(worktree_path: str, claim: dict) -> tuple[bool, str]:
    """Determine if worktree can be safely cleaned up."""
    # Check if PR is merged
    branch = get_branch_for_worktree(worktree_path)
    pr_merged = is_branch_merged(branch)

    # Check if session is active (heartbeat file)
    session_active = is_session_active(claim.get("session_id"))

    if pr_merged and not session_active:
        return True, "PR merged and session inactive"

    if not worktree_has_uncommitted_changes(worktree_path):
        if pr_merged:
            return True, "PR merged, no uncommitted changes"

    return False, "Owner may still be active"
```

**Files:**
- `scripts/safe_worktree_remove.py` - Add smart ownership detection

### Phase 6: Plan Completion Verification

Verify no stale references remain when completing a plan.

**Implementation:**
```python
def verify_no_stale_references(plan_num: int, removed_items: list[str]) -> list[str]:
    """Check that removed items have no remaining references."""
    stale_refs = []
    for item in removed_items:
        # Search codebase for references
        refs = grep_codebase(item)
        if refs:
            stale_refs.append(f"{item} still referenced in: {refs}")
    return stale_refs
```

**Files:**
- `scripts/complete_plan.py` - Add stale reference check

### Phase 7: Clean Up Existing Mess

One-time cleanup of current state.

**Script:**
```python
# scripts/cleanup_claims_mess.py
def cleanup():
    # 1. Remove duplicate entries
    # 2. Remove claims where worktree doesn't exist
    # 3. Remove claims for merged branches
    # 4. Standardize field names (cc_id, not branch)
    # 5. Remove _legacy flags
    # 6. Regenerate plan index
    # 7. Clean up genesis_store references (Plan #199 leftovers)
```

---

## Files Affected

- scripts/check_claims.py (modify)
- scripts/generate_plan_index.py (modify)
- scripts/sync_plan_status.py (modify)
- scripts/safe_worktree_remove.py (modify)
- scripts/complete_plan.py (modify)
- scripts/cleanup_claims_mess.py (create)
- .claude/hooks/block-worktree-remove.sh (modify)
- .claude/hooks/session-startup-cleanup.sh (create)
- .claude/settings.json (modify)
- CLAUDE.md (modify)
- tests/scripts/test_claim_lifecycle.py (create)

---

## Acceptance Criteria

- [x] Stale claims (>8h no activity) are automatically released (PR #705)
- [x] Session startup cleans orphaned claims (PR #705)
- [x] Worktrees outside `/worktrees/` are blocked (PR #713)
- [x] Plan index correctly shows all statuses (no false `❓`) (PR #703)
- [x] Existing mess in `active-work.yaml` is cleaned up (PR #679)
- [x] Documentation updated with new cleanup commands (PR #705)

---

## Testing

### Manual Tests
1. Create claim, wait 8h (or mock time), verify auto-release
2. Create claim, delete worktree manually, verify cleanup detects
3. Try to create worktree in external location, verify blocked
4. Create plan with various status formats, verify index correct

### Automated Tests
- `tests/unit/test_claim_lifecycle.py` - Stale detection logic
- `tests/unit/test_plan_index.py` - Status parsing

---

## Notes

### Why This Matters
Without these fixes, the meta-process degrades over time:
- More stale claims accumulate
- CC instances can't find available work
- Plan index becomes unreliable
- Manual cleanup becomes necessary

### Design Decisions

1. **8 hour default expiration** - Long enough for lunch breaks and overnight, short enough to catch abandoned work.

2. **Worktree modification time, not claim time** - A claim could be old but still active if the worktree has recent changes.

3. **Session startup cleanup** - Catches orphans before they cause problems.

4. **Non-destructive by default** - Cleanup commands show what they would do before acting.
