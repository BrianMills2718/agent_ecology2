# Plan 240: Cross-CC Review Enforcement

**Status:** 📋 Deferred
**Priority:** Medium
**Blocked By:** -
**Blocks:** -

---

## Gap

**Current:** CC instances self-merge PRs when CI passes. Plan #68 established
review checklists but no enforcement. Plan #85 built inter-CC messaging
infrastructure (send/receive/acknowledge messages, session identity, inbox hooks)
but it was never wired into the merge flow. GitHub's review system can't be used
because all CC instances share a single GitHub account.

**Target:** A meta-process-enforced review gate where:
1. PRs require review by a CC instance other than the author before merge
2. Review is tracked outside GitHub (since all CCs share one account)
3. The existing messaging system (Plan #85) is used for review communication
4. `make finish` / `make merge` checks for a review artifact before allowing merge

**Why Medium:** Self-merge works fine for solo development. This becomes important
when multiple CC instances are actively working in parallel and code quality
benefits from cross-review. Deferred until multi-CC workflows are common enough
to justify the coordination overhead.

---

## Existing Infrastructure (Plan #85)

These scripts and hooks already exist and are functional (tested):

| Component | Location | Status |
|-----------|----------|--------|
| `scripts/send_message.py` | Send messages between CCs | Working, tested |
| `scripts/check_messages.py` | List/read/ack messages | Working, tested |
| `scripts/session_manager.py` | CC identity resolution | Working, tested |
| `.claude/hooks/check-inbox.sh` | Block edits on unread messages | Working, disabled |
| `.claude/hooks/notify-inbox-startup.sh` | Warn on session start | Working, disabled |
| `meta-process.yaml` | `block_on_unread_messages: false` | Config exists |
| `.claude/meta-config.yaml` | `inter_cc_messaging: false` | Config exists |
| `tests/scripts/test_messaging.py` | 15 unit tests | All passing |

## What's Missing

The existing messaging infrastructure handles message transport. What's missing
is the review orchestration layer:

### 1. Review Gate in Merge Flow
- `scripts/finish_pr.py` and `scripts/merge_pr.py` need a check:
  "Has this PR been reviewed by a non-author CC instance?"
- Review evidence could be a file (e.g., `.reviews/PR-N.yaml`) or a message artifact
- Gate should be configurable (enabled/disabled via meta-process.yaml)

### 2. Review Assignment
- How does a CC know it should review a PR?
- Options: round-robin, opportunistic (check `gh pr list`), explicit assignment
- Could extend the claim system: "review claims" alongside "implementation claims"

### 3. Review Artifact Format
- What constitutes a valid review? A message? A file? A specific message type?
- Must be non-forgeable (author can't review their own PR)
- Must reference the specific PR and commit SHA

### 4. CC Discovery
- Reviewer needs to know author's identity to send feedback
- `session_manager.py` handles this but relies on worktree names and port mappings
- May need a more robust discovery mechanism

### 5. Workflow Integration
- When a CC finishes a PR, it should signal "ready for review"
- Reviewer CC should discover this via `meta_status.py` or similar
- After review, author gets feedback via messaging, addresses it, pushes
- Reviewer confirms, produces review artifact
- Author (or reviewer) merges

---

## Open Questions

### Before Planning

1. [ ] **Question:** Should review be mandatory for all PRs or only plan-based PRs?
   - **Status:** ❓ OPEN
   - **Why it matters:** [Trivial] PRs may not warrant review overhead

2. [ ] **Question:** What prevents a CC from forging a review artifact for its own PR?
   - **Status:** ❓ OPEN
   - **Why it matters:** Without separate GitHub accounts, there's no cryptographic identity

3. [ ] **Question:** How should review assignment work when only one CC is active?
   - **Status:** ❓ OPEN
   - **Why it matters:** Can't block merge indefinitely waiting for a reviewer that doesn't exist

4. [ ] **Question:** Should the review gate be blocking (prevent merge) or advisory (warn but allow)?
   - **Status:** ❓ OPEN
   - **Why it matters:** Blocking creates deadlock risk; advisory may be ignored

---

## Notes

- Plan #46 (PR Review Coordination) and Plan #68 (PR Review Enforcement) are
  predecessors — both complete but neither achieved actual enforcement
- The messaging system (Plan #85) is the transport layer; this plan is the
  orchestration layer
- Key design tension: enforcement vs. practicality when CCs share one identity
- Consider whether this should integrate with the simulation's own contract
  system (dogfooding the artifact/contract primitives for meta-process)
