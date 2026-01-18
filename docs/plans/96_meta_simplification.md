# Plan 96: Meta-Process Simplification

**Status:** 🚧 In Progress
**Priority:** High
**Blocked By:** None
**Blocks:** None

---

## Gap

**Current:** Multiple friction points in the meta-process:

1. **Three-step completion**: Completing a plan requires 3 commands:
   - `python scripts/check_plan_tests.py --plan N` (verify tests)
   - `python scripts/complete_plan.py --plan N` (update status)
   - `python scripts/check_claims.py --release` (release claim)

2. **Multiple claiming paths**: Work can be claimed via:
   - `make worktree` (interactive, creates claim + worktree)
   - `make worktree-quick` (requires pre-claim)
   - `python scripts/check_claims.py --claim` (manual, no worktree)

3. **Manual rebase before PR**: Easy to forget `make pr-ready`, causing stale branches

4. **Plan number collisions**: No atomic reservation, leading to #92 collision

**Problems caused:**
- Lost work from uncommitted changes during conflict resolution
- 9+ open PRs with merge conflicts
- Plan number collision (#92 used twice)
- Confusion about which command to use

**Target:** Simplified workflow:
- One command to complete work: `make complete PLAN=N`
- One path to start work: `make worktree` only
- Auto-rebase on PR creation
- Atomic plan number reservation

---

## References Reviewed

- `docs/meta/15_plan-workflow.md` - Current plan workflow
- `docs/meta/18_claim-system.md` - Claim system documentation
- `docs/meta/20_rebase-workflow.md` - Rebase workflow
- `scripts/complete_plan.py` - Current completion script
- `scripts/check_claims.py` - Current claim script
- `Makefile` - Current make targets
- `CLAUDE.md` - Coordination protocol

---

## Files Affected

- Makefile (modify)
- scripts/complete_plan.py (modify)
- scripts/check_claims.py (modify)
- docs/meta/15_plan-workflow.md (modify)
- CLAUDE.md (modify)

---

## Plan

### Phase 1: One-Command Completion

Modify `complete_plan.py` to do everything:

```python
# New behavior of: python scripts/complete_plan.py --plan N
1. Run tests (existing)
2. Record verification evidence (existing)
3. Update plan status to Complete (existing)
4. Sync plan index (NEW - calls sync_plan_status.py)
5. Release claim if active (NEW - calls check_claims.py --release)
6. Show summary: "Plan #N complete. Claim released. Ready for PR."
```

Add Makefile target:
```makefile
complete:
	@test -n "$(PLAN)" || (echo "Usage: make complete PLAN=N" && exit 1)
	python scripts/complete_plan.py --plan $(PLAN)
```

### Phase 2: Single Claiming Path

Deprecate direct `check_claims.py --claim` usage:
1. Update `check_claims.py --claim` to warn: "Use 'make worktree' instead"
2. Keep `--claim` working for backwards compatibility
3. Update CLAUDE.md to only document `make worktree`

### Phase 3: Auto-Rebase on PR Push

Modify `make pr-ready` or create `make pr`:
```makefile
pr:
	git fetch origin main
	git rebase origin/main
	git push --force-with-lease
	@echo "Branch rebased and pushed. Create PR with: gh pr create"
```

### Phase 4: Atomic Plan Number Reservation

Add to `check_claims.py`:
```bash
python scripts/check_claims.py --reserve-plan
# Output: "Reserved plan number: 97"
# Creates placeholder in docs/plans/97_reserved.md
```

---

## Required Tests

### Manual Verification

| Scenario | Steps | Expected |
|----------|-------|----------|
| One-command complete | `make complete PLAN=96` | Tests run, status updated, claim released |
| Claim warning | `python scripts/check_claims.py --claim` | Warning shown, still works |
| Auto-rebase | `make pr` | Rebases onto main, pushes |

---

## Verification

- [ ] `make complete PLAN=N` works end-to-end
- [ ] Claim auto-released after completion
- [ ] Plan index synced after completion
- [ ] Documentation updated

---

## Notes

### Why This Matters

The current multi-step process led to:
1. Lost work when switching branches with uncommitted changes
2. Stale PRs that sat for hours/days
3. Plan number collision (#92)
4. Confusion about workflow

### Incremental Rollout

Phase 1 (one-command complete) is highest value, lowest risk.
Phases 2-4 can be done incrementally.

### Backwards Compatibility

All existing commands continue to work. New commands are additions, not replacements.
