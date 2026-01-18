# Plan 85: Inter-CC Messaging System

**Status:** ✅ Complete

**Verified:** 2026-01-18T16:22:15Z
**Verification Evidence:**
```yaml
completed_by: scripts/complete_plan.py
timestamp: 2026-01-18T16:22:15Z
tests:
  unit: 1633 passed, 9 skipped, 3 warnings in 43.29s
  e2e_smoke: PASSED (6.25s)
  e2e_real: skipped (--skip-real-e2e)
  doc_coupling: passed
commit: 9448d2a
```
**Priority:** Medium
**Blocked By:** None
**Blocks:** None

---

## Gap

**Current:** CC instances collaborate via:
- Text in conversation (human copy-pastes)
- PRs against each other's branches (heavyweight)
- No direct async communication channel

When instance A wants to send suggestions/questions to instance B, there's no structured way to do so without human mediation.

**Target:** Async message queue allowing any CC instance to send messages to any other. Messages persist until read. Recipients check inbox on startup or periodically.

**Why Medium:** Improves multi-CC collaboration efficiency. Not blocking any features, but reduces friction for cross-instance work like the plan-83 review situation.

---

## References Reviewed

- `.claude/sessions.yaml` - Existing port→name mapping (partial implementation)
- `.claude/hooks/refresh-session-marker.sh` - Session activity tracking pattern
- `CLAUDE.md:185-199` - Session identity documentation
- `docs/meta/18_claim-system.md` - Current coordination patterns
- `docs/meta/19_worktree-enforcement.md` - Isolation philosophy
- `scripts/check_claims.py` - Pattern for CC coordination scripts

---

## Files Affected

### Scripts (create)
- `scripts/send_message.py` - Send formatted message to another instance
- `scripts/check_messages.py` - Check inbox, list/read/archive messages

### Hooks (create)
- `.claude/hooks/check-inbox-notify.sh` - Notify on session start if unread messages

### Config (create)
- `.claude/messages/inbox/.gitkeep` - Inbox directory structure
- `.claude/messages/archive/.gitkeep` - Archived messages

### Docs (modify)
- `CLAUDE.md` - Add messaging section to Multi-Claude Coordination
- `docs/meta/18_claim-system.md` - Reference messaging as collaboration option

---

## Plan

### Message Directory Structure

```
.claude/
  sessions.yaml              # Port → name mapping (existing)
  messages/
    inbox/
      <session-or-worktree>/  # One inbox per identity
        001_<timestamp>_from-<sender>_<type>.md
    archive/
      <session-or-worktree>/  # Read/processed messages
    .gitkeep
```

### Message Format

```markdown
---
id: msg-20260118-143000-meta-abc123
from: meta
to: plan-83-remove-ticks
timestamp: 2026-01-18T14:30:00Z
type: suggestion | question | handoff | info | review-request
subject: Plan 83 improvements
status: unread
---

## Content

[Markdown content here]

## Requested Action

- [ ] Review and integrate suggested changes
- [ ] Reply with questions if unclear
```

### Message Types

| Type | Purpose | Expected Response |
|------|---------|-------------------|
| `suggestion` | Code/doc improvements | Integrate or decline |
| `question` | Clarification needed | Reply with answer |
| `handoff` | Transferring ownership | Acknowledge receipt |
| `info` | FYI, no action needed | Acknowledge |
| `review-request` | Please review my work | Approve/comment |

### Blocking Enforcement

**All messages block edits until acknowledged.** This ensures coordination messages are never missed.

```
On any Edit/Write in a worktree:
1. Determine recipient identity (worktree name or session name)
2. Check .claude/messages/inbox/{identity}/ for unread messages
3. If ANY unread messages exist:
   → BLOCK with error:
   "📬 You have N unread message(s). Acknowledge before editing:
    python scripts/check_messages.py --ack"
4. If inbox empty or all acknowledged:
   → Allow edit
```

**Rationale:** If another instance took the time to send a message, it's important. Passive notification risks messages being ignored. Blocking ensures coordination actually happens.

### Identity Resolution

Sender/recipient identity determined by:
1. **Worktree name** - If in `/worktrees/plan-83-foo/`, identity is `plan-83-foo`
2. **Port mapping** - Look up `$CLAUDE_CODE_SSE_PORT` in `.claude/sessions.yaml`
3. **Fallback** - `main` or `unknown`

---

## Required Tests

### New Tests (TDD)

| Test File | Test Function | What It Verifies |
|-----------|---------------|------------------|
| `tests/unit/test_messaging.py` | `test_send_message_creates_file` | Message file created in recipient inbox |
| `tests/unit/test_messaging.py` | `test_message_format_valid` | Message has required frontmatter fields |
| `tests/unit/test_messaging.py` | `test_check_messages_lists_inbox` | Lists messages in inbox |
| `tests/unit/test_messaging.py` | `test_archive_moves_message` | Archive moves from inbox to archive dir |
| `tests/unit/test_messaging.py` | `test_sender_identity_from_worktree` | Detects sender from worktree path |
| `tests/unit/test_messaging.py` | `test_sender_identity_from_port` | Detects sender from port mapping |

### Existing Tests (Must Pass)

| Test Pattern | Why |
|--------------|-----|
| `tests/` | No regressions |

---

## E2E Verification

| Scenario | Steps | Expected Outcome |
|----------|-------|------------------|
| Cross-instance message | 1. Instance A sends to B 2. B checks inbox 3. B reads 4. B archives | Message flows correctly |

```bash
# Manual E2E test
python scripts/send_message.py --to test-inbox --type info --subject "Test" --content "Hello"
python scripts/check_messages.py --inbox test-inbox --list
```

---

## Verification

### Tests & Quality
- [ ] All required tests pass: `python scripts/check_plan_tests.py --plan 85`
- [ ] Full test suite passes: `pytest tests/`
- [ ] Type check passes: `python -m mypy scripts/send_message.py scripts/check_messages.py`

### Documentation
- [ ] CLAUDE.md updated with messaging section
- [ ] `docs/meta/18_claim-system.md` references messaging

### Completion Ceremony
- [ ] Plan file status → `✅ Complete`
- [ ] `plans/CLAUDE.md` index → `✅ Complete`
- [ ] Claim released
- [ ] Branch merged or PR created

---

## Notes

### Design Decisions

1. **File-based, not service-based** - No daemon. Messages are files. Git-trackable.
2. **Recipient-named inboxes** - Each identity has own inbox. Simple routing.
3. **No delivery confirmation** - Async, fire-and-forget.
4. **Archive, don't delete** - Preserves audit trail.
5. **Hook notifies, doesn't block** - Informational only.

### Future Enhancements

- Reply threading (in-reply-to field)
- Priority levels
- Expiration (auto-archive after N days)
- Broadcast to all instances
