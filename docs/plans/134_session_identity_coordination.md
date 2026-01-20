# Plan #134: Per-Session Identity and Mandatory Claiming

**Status:** 🚧 In Progress
**Priority:** High
**Blocked By:** None
**Blocks:** Multi-CC coordination reliability

---

## Gap

**Current:** Multiple Claude Code instances running in the same checkout cannot reliably coordinate because:

1. **Identity is branch name**: All instances in `main` share identity "main"
2. **Claims opt-in**: Unclaimed plans can be edited by multiple instances simultaneously
3. **No ownership verification**: Any instance can release any claim via `--id` flag
4. **Staleness is coarse**: 24-hour session markers can't detect "abandoned 5 minutes ago"

**Target:** Each Claude Code session has a unique identity that:
- Survives the session lifetime
- Distinguishes concurrent sessions in same directory
- Enables ownership verification on claim operations
- Supports automatic staleness detection (minutes, not hours)

**Why High:** This is the root cause of coordination failures. ~20 previous plans addressed symptoms but not the fundamental identity problem.

---

## References Reviewed

- `scripts/check_claims.py:751-805` - `release_claim()` has no ownership verification
- `scripts/check_claims.py:908` - Uses branch name as cc_id
- `.claude/hooks/protect-main.sh:108-135` - Allows unclaimed plan edits
- `docs/plans/52_worktree_session_tracking.md` - Session marker approach
- `docs/plans/87_meta_process_coordination_improvements.md` - Plan file exceptions
- `docs/plans/115_worktree_ownership_enforcement.md` - Ownership on removal only

---

## Files Affected

- `.claude/hooks/session-start.sh` (create) - Generate session ID on Claude Code start
- `scripts/check_claims.py` (modify) - Add session ID parameter, ownership verification
- `.claude/hooks/protect-main.sh` (modify) - Auto-claim unclaimed plans, verify session
- `scripts/session_heartbeat.py` (create) - Update session marker with heartbeat
- `CLAUDE.md` (modify) - Document session-based coordination

---

## Design

### Session Identity

Each Claude Code session gets a unique ID:

```bash
# In session-start.sh hook (runs on Claude Code startup)
export CLAUDE_SESSION_ID="${CLAUDE_SESSION_ID:-$(uuidgen)}"
echo "$CLAUDE_SESSION_ID" > .claude/sessions/$(hostname)-$$.session
```

Session file contains:
```yaml
session_id: "a1b2c3d4-..."
hostname: "brian-laptop"
pid: 12345
started_at: "2026-01-20T19:30:00Z"
last_activity: "2026-01-20T19:45:00Z"
working_on: "Plan #131"
```

### Mandatory Claiming

Modified `protect-main.sh`:

```bash
# When editing docs/plans/NN_*.md:
# 1. If unclaimed AND no other session working on it -> auto-claim for this session
# 2. If claimed by THIS session -> allow
# 3. If claimed by DIFFERENT session -> block
# 4. If claimed but session is stale (>30 min no heartbeat) -> allow takeover
```

### Ownership Verification

Modified `check_claims.py`:

```python
def release_claim(data, cc_id, session_id=None, ...):
    """Release a claim with session verification."""
    claim = find_claim(data, cc_id)

    if claim and session_id:
        claim_session = claim.get("session_id")
        if claim_session and claim_session != session_id:
            print(f"Error: Claim owned by session {claim_session}, not {session_id}")
            print("You can only release claims you own.")
            return False

    # ... existing release logic
```

### Heartbeat Mechanism

Each Edit/Write tool call updates session marker:

```python
# In hook or wrapper
def update_heartbeat():
    session_file = f".claude/sessions/{hostname}-{pid}.session"
    data = yaml.load(session_file)
    data["last_activity"] = datetime.now().isoformat()
    yaml.dump(data, session_file)
```

Staleness threshold: 30 minutes (configurable).

### Staleness Recovery

If a session is stale (no heartbeat for 30 minutes):
1. Its claims become "orphaned"
2. Other sessions can take over orphaned claims
3. Takeover logged for observability

---

## Plan

### Phase 1: Session Identity Infrastructure

1. Create `.claude/hooks/session-start.sh` to generate session ID
2. Create `.claude/sessions/` directory for session files
3. Add `session_id` field to claims in `check_claims.py`
4. Update `add_claim()` to record session ID

### Phase 2: Ownership Verification

1. Modify `release_claim()` to verify session ID
2. Add `--session` parameter to check_claims.py CLI
3. Block release if session mismatch (unless --force)

### Phase 3: Mandatory Claiming

1. Modify `protect-main.sh` to auto-claim unclaimed plans
2. Pass session ID to auto-claim
3. Block if different session has claim

### Phase 4: Heartbeat + Staleness

1. Create `scripts/session_heartbeat.py`
2. Hook Edit/Write to call heartbeat
3. Add staleness check to claim verification
4. Implement orphan takeover logic

---

## Required Tests

### New Tests (TDD)

| Test File | Test Function | What It Verifies |
|-----------|---------------|------------------|
| `tests/unit/test_session_identity.py` | `test_session_id_generated` | Session ID created on startup |
| `tests/unit/test_session_identity.py` | `test_claim_records_session` | Claims include session_id |
| `tests/unit/test_session_identity.py` | `test_release_blocked_wrong_session` | Can't release others' claims |
| `tests/unit/test_session_identity.py` | `test_release_allowed_same_session` | Can release own claims |
| `tests/unit/test_session_identity.py` | `test_heartbeat_updates_timestamp` | Activity updates last_activity |
| `tests/unit/test_session_identity.py` | `test_stale_session_detection` | Sessions stale after 30 min |
| `tests/unit/test_session_identity.py` | `test_orphan_takeover` | Can take over stale session's claims |

### Existing Tests (Must Pass)

| Test Pattern | Why |
|--------------|-----|
| `tests/unit/test_safe_worktree_remove.py` | Ownership logic unchanged |
| `tests/unit/test_actions.py` | Core functionality unchanged |

---

## Verification

### Tests & Quality
- [ ] All required tests pass: `python scripts/check_plan_tests.py --plan 134`
- [ ] Full test suite passes: `pytest tests/`
- [ ] Type check passes: `python -m mypy src/ --ignore-missing-imports`

### Manual Verification
- [ ] Two terminals in same directory can't edit same plan
- [ ] Releasing claim from different session blocked
- [ ] Stale session's claims can be taken over
- [ ] Heartbeat updates on every Edit/Write

### Documentation
- [ ] CLAUDE.md updated with session coordination docs
- [ ] Doc-coupling check passes: `python scripts/check_doc_coupling.py`

### Completion Ceremony
- [ ] Plan file status -> `Complete`
- [ ] `plans/CLAUDE.md` index -> `Complete`
- [ ] Branch merged

---

## Notes

### Why Previous Attempts Failed

| Approach | Problem |
|----------|---------|
| Branch name identity | Multiple instances share "main" |
| Worktree isolation | User workflow has multiple terminals in same dir |
| Session markers (24h) | Too coarse, can't detect recent abandonment |
| Ownership on removal | Only protects deletion, not concurrent editing |

### Design Decisions

1. **30-minute staleness**: Long enough for human breaks, short enough for practical takeover
2. **Auto-claim on edit**: Reduces friction vs. mandatory explicit claiming
3. **Session files not in git**: Local coordination artifact, not shared state
4. **PID in session file name**: Quick lookup, handles process restart

### Alternatives Considered

1. **Lock files with flock()**: Cross-platform issues, doesn't work with hooks
2. **SQLite database**: Overkill for simple coordination
3. **Git-based locking**: Too slow, merge conflicts

### Open Questions

1. Should session ID persist across terminal restart? (Currently: no)
2. Should stale takeover require explicit confirmation? (Recommend: no for automation)
3. What happens to claims when session file is manually deleted? (Become orphaned)
