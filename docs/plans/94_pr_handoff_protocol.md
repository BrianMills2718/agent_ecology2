# Plan 94: PR Handoff Protocol

**Status:** 📋 Planned
**Priority:** Medium
**Blocked By:** None
**Blocks:** None

---

## Gap

**Current:** The meta-process requires the PR creator to also merge their own PR:
- Owner claims work
- Owner implements and creates PR
- Reviewer reviews but cannot merge
- Owner must return to merge
- Owner releases claim

**Problem:** This creates bottlenecks:
1. Reviewer does work but can't complete the cycle
2. PRs sit waiting for owner to return
3. Two round-trips required for simple merges
4. If owner is busy/unavailable, work stalls

**Target:** Handoff at PR creation, not at merge:
- Owner claims work
- Owner implements and creates PR
- Owner releases claim (PR is the handoff artifact)
- Any reviewer can claim, review, and merge
- Reviewer releases claim after merge

**Why Medium:** Process improvement that reduces friction and enables parallelization. Not blocking any features but improves velocity.

---

## References Reviewed

- `CLAUDE.md:Multi-Claude Coordination` - Current ownership rules
- `CLAUDE.md:Review vs. Ownership` - "Only the claiming instance can merge"
- `docs/meta/pr-coordination.md` - PR workflow details
- `scripts/check_claims.py` - Claim management implementation

---

## Files Affected

- `CLAUDE.md` (modify) - Update coordination protocol
- `docs/meta/pr-coordination.md` (modify) - Update merge workflow
- `scripts/check_claims.py` (modify) - Add `--handoff` flag for PR-ready release

---

## Plan

### Protocol Change

**Old rule:**
> Only the claiming instance can merge their own PR

**New rule:**
> Owner releases claim when PR is created. PR becomes the handoff artifact. Any instance can claim, review, and merge.

### Workflow Comparison

| Step | Old Process | New Process |
|------|-------------|-------------|
| 1 | Owner claims | Owner claims |
| 2 | Owner implements | Owner implements |
| 3 | Owner creates PR | Owner creates PR |
| 4 | Owner waits | **Owner releases claim** |
| 5 | Reviewer reviews | Reviewer claims (optional) |
| 6 | Reviewer waits | Reviewer reviews |
| 7 | Owner merges | **Reviewer merges** |
| 8 | Owner releases | Reviewer releases |

### Documentation Changes

Update `CLAUDE.md` "Review vs. Ownership" section:

```markdown
### Review vs. Ownership

**Claim covers implementation, not merge.** Once a PR is created:
- The PR itself is the handoff artifact (contains all context)
- Owner should release claim
- Any instance can review and merge
- Reviewer optionally claims to prevent duplicate work

| Phase | Who Can Do It |
|-------|---------------|
| Implementation (claimed) | Only the claiming instance |
| PR creation | Only the claiming instance |
| Review | Any instance |
| Merge (after PR created) | Any instance |
| Claim release | Owner (at PR creation) or Merger (after merge) |
```

### Optional: `--handoff` Flag

Add convenience flag to `check_claims.py`:

```bash
# Current: manual release
python scripts/check_claims.py --release

# New: release with handoff message
python scripts/check_claims.py --handoff --pr 284
# Outputs: "Released claim. PR #284 ready for review/merge by any instance."
```

### Changes Required

| File | Change |
|------|--------|
| `CLAUDE.md` | Update "Review vs. Ownership" section |
| `CLAUDE.md` | Update "Coordination Protocol" workflow |
| `docs/meta/pr-coordination.md` | Update merge workflow documentation |
| `scripts/check_claims.py` | (Optional) Add `--handoff` flag |

### Steps

1. Update `CLAUDE.md` coordination protocol
2. Update `docs/meta/pr-coordination.md`
3. (Optional) Add `--handoff` flag to claims script
4. Test by having one instance create PR, another merge

---

## Required Tests

### Manual Verification

| Scenario | Steps | Expected Outcome |
|----------|-------|------------------|
| Handoff merge | 1. Instance A creates PR, releases claim 2. Instance B reviews and merges | B can merge without issues |
| No double-claim | 1. A releases claim 2. B claims for review 3. C tries to claim | C sees B's claim, doesn't duplicate |

### Script Tests (if --handoff implemented)

| Test File | Test Function | What It Verifies |
|-----------|---------------|------------------|
| `tests/unit/test_claims.py` | `test_handoff_flag_releases_with_message` | --handoff releases and logs PR |

---

## Verification

### Documentation
- [ ] `CLAUDE.md` updated with new protocol
- [ ] `docs/meta/pr-coordination.md` updated
- [ ] Protocol is clear and unambiguous

### Validation
- [ ] At least one PR successfully handed off and merged by different instance
- [ ] No confusion about who can merge

### Completion Ceremony
- [ ] Plan file status -> `Complete`
- [ ] `plans/CLAUDE.md` index -> `Complete`
- [ ] Claim released

---

## Notes

### Why This Works

1. **PR is the artifact** - Once created, the PR contains all context (description, code, tests, CI status). No hidden knowledge remains with owner.

2. **Low-risk merge** - After CI passes, merging is mechanical. No judgment calls that require original context.

3. **Enables parallelization** - Multiple instances can work without waiting for each other.

4. **Reduces bottlenecks** - No single instance becomes a blocker.

### Edge Cases

**What if owner wants to make changes after PR?**
- Owner can re-claim if no one else has
- Or coordinate with current claimant
- PR comments work for async coordination

**What if reviewer finds issues?**
- Request changes via PR review
- Anyone can pick up the fixes (owner or new claimant)

**What about complex PRs that need owner context?**
- PR description should capture context
- If truly complex, owner can note "please coordinate before merging"
- Exception, not the rule

### Alternatives Considered

1. **Keep current protocol** - Rejected. Creates unnecessary bottlenecks.

2. **Auto-release on PR creation** - Considered. Might be too aggressive; explicit release is clearer.

3. **Anyone can merge any time** - Rejected. Some coordination (optional claim) prevents duplicate reviews.
