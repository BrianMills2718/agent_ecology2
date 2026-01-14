# Plan #46: PR Review Coordination

**Status:** ✅ Complete

**Verified:** 2026-01-14T09:21:11Z
**Verification Evidence:**
```yaml
completed_by: scripts/complete_plan.py
timestamp: 2026-01-14T09:21:11Z
tests:
  unit: 1277 passed, 1 skipped in 16.66s
  e2e_smoke: PASSED (2.21s)
  doc_coupling: passed
commit: 336ba35
```
**Priority:** High
**Type:** Meta-process
**Created:** 2026-01-14

**Related Plans:**
- Plan #41: Meta-Process Enforcement Gaps
- Plan #44: Meta-Process Enforcement Improvements

## Summary

Add coordination mechanism for PR reviews to prevent duplicate review work when multiple CC instances are active. Currently, reviews have no coordination - multiple instances could review the same PR simultaneously while others are ignored.

## Problem Statement

With 7+ CC instances working in parallel:
- Implementation work is coordinated via claims
- PR reviews have NO coordination mechanism
- Multiple instances may review the same PR (wasted effort)
- Some PRs may be ignored while others get duplicate reviews
- No visibility into who is reviewing what

**Evidence:** Meta-status shows 6 open PRs but no way to know which are being reviewed.

## Current State

| Activity | Coordination | Visibility |
|----------|-------------|------------|
| Implementation | Claims + worktrees | Active Work table |
| PR Creation | Worktree ownership | PR list |
| **PR Review** | **None** | **None** |
| Merging | PR ownership | PR state |

## Plan

## Proposed Solution

### Option A: Lightweight Review Tracking (Recommended)

Add review status to the "Awaiting Review" table in CLAUDE.md:

```markdown
**Awaiting Review:**
| PR | Title | Reviewer | Started | Status |
|----|-------|----------|---------|--------|
| #120 | [Plan #41] Status validation | plan-46-review | 08:45 | In Review |
| #122 | [Plan #42] Kernel quotas | - | - | Awaiting |
| #124 | [Plan #43] Reasoning | - | - | Awaiting |
```

**Protocol:**
1. Before reviewing, check table for "Awaiting" PRs
2. Update table: add your CC-ID and "In Review" status
3. After review, update status to "Reviewed" or "Changes Requested"
4. After merge, remove row

**Pros:** Lightweight, visible, no new tooling
**Cons:** Manual, relies on discipline

### Option B: Review Claims

Extend claim system to support review claims:

```bash
python scripts/check_claims.py --claim-review --pr 120
```

**Pros:** Enforced, automated
**Cons:** More tooling, overhead for quick reviews

### Option C: Automated Review Assignment

Add `meta_status.py` feature to suggest review assignments:

```
## Suggested Reviews
Based on expertise and availability:
- #120 (Plan #41): Suggest CC-plan-42 (worked on related #41)
- #122 (Plan #42): Suggest any available instance
```

**Pros:** Smart assignment, load balancing
**Cons:** Complex, may over-engineer

## Recommendation

**Start with Option A** (lightweight tracking):
1. Simple table update
2. No new tooling required
3. Can evolve to Option B/C if needed

Add CI check (optional) to warn if:
- PR has been "In Review" for >1 hour without completion
- Multiple PRs show same reviewer (bottleneck)

## Implementation Steps

### Phase 1: Documentation + Protocol
1. Update CLAUDE.md with review coordination protocol
2. Add "Reviewer" and "Started" columns to Awaiting Review table
3. Document the review workflow

### Phase 2: Tooling (Optional)
1. Add `--list-reviews` to `meta_status.py`
2. Add `--start-review PR` to update table automatically
3. Add CI warning for stale reviews

### Phase 3: Enforcement (Optional)
1. Add review claims to claim system
2. CI check for unclaimed reviews before merge

## Acceptance Criteria

- [ ] CLAUDE.md documents review coordination protocol
- [ ] Awaiting Review table includes Reviewer column
- [ ] `meta_status.py` shows review status in output
- [ ] Protocol tested with multiple instances

## Open Questions

1. **Should reviews be exclusive?** Or can multiple instances review same PR?
   - Suggestion: First reviewer is primary, others can add comments

2. **How long before review "expires"?** If reviewer goes idle?
   - Suggestion: 1 hour timeout, then PR returns to "Awaiting"

3. **Should we track review expertise?** Match reviewers to PR topics?
   - Suggestion: Defer to Phase 3, keep it simple first

## References

- `CLAUDE.md` - Current Awaiting Review table
- `scripts/meta_status.py` - Coordination status tool
- `scripts/check_claims.py` - Existing claim system
