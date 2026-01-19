# Gap 74: Meta-Process Doc Fixes

**Status:** ✅ Complete

**Verified:** 2026-01-19
**Verification Evidence:**
```yaml
completed_by: manual verification
pr: "#319"
commit: a7b8179
changes:
  - Removed sync_to_claude_md() function from scripts/check_claims.py
  - Removed --sync argument
  - Updated docs/meta/18_claim-system.md
```

**Priority:** Medium
**Blocked By:** -
**Blocks:** -

---

## Gap

**Current:** The claim system was changed to store claims in `.claude/active-work.yaml` (local, not git-tracked), but dead code and stale docs still reference a non-existent `CLAUDE.md` markdown table.

- `sync_to_claude_md()` function in `scripts/check_claims.py` attempts to write to a markdown table that doesn't exist
- Running `--sync` outputs: "Warning: Could not find Active Work table in CLAUDE.md"
- `docs/meta/18_claim-system.md` says CLAUDE.md has a "Human-readable Active Work table" but it doesn't

**Target:** Remove dead code and update documentation to reflect the current reality.

**Why Medium:** Not blocking any work, but creates confusion and noise in claim operations.

---

## References Reviewed

- `scripts/check_claims.py:811-854` - dead `sync_to_claude_md()` function
- `scripts/check_claims.py:1068,1078,1082-1083` - calls to dead function
- `scripts/check_claims.py:35-36` - docstring mentions `--sync`
- `docs/meta/18_claim-system.md:148-154` - stale file table
- `CLAUDE.md:319-326` - correct "Active Work" section (no table)

---

## Files Affected

- `scripts/check_claims.py` (modify) - remove dead code
- `docs/meta/18_claim-system.md` (modify) - update stale reference

---

## Plan

### Changes Required

| File | Change |
|------|--------|
| `scripts/check_claims.py` | Remove `sync_to_claude_md()` function (lines 811-854) |
| `scripts/check_claims.py` | Remove `--sync` argument (lines 902-905) |
| `scripts/check_claims.py` | Remove docstring mention of `--sync` (lines 35-36) |
| `scripts/check_claims.py` | Remove `args.sync` handling (lines 1082-1083) |
| `scripts/check_claims.py` | Remove `sync_to_claude_md()` calls after claim/release (lines 1068, 1078) |
| `docs/meta/18_claim-system.md` | Update line 151 - remove "Human-readable Active Work table" |

### Steps

1. Remove the dead `sync_to_claude_md()` function
2. Remove the `--sync` argument from argparse
3. Remove the docstring mention of `--sync`
4. Remove the `args.sync` handling block
5. Remove the two calls to `sync_to_claude_md()` in claim/release handlers
6. Update `docs/meta/18_claim-system.md` to reflect current reality
7. Run tests to verify nothing breaks

---

## Required Tests

### New Tests (TDD)

No new tests needed - this is removing dead code.

### Existing Tests (Must Pass)

| Test Pattern | Why |
|--------------|-----|
| `tests/scripts/test_check_claims.py` | Verify claim functionality still works |

---

## E2E Verification

| Scenario | Steps | Expected Outcome |
|----------|-------|------------------|
| Claim without --sync error | `python scripts/check_claims.py --claim --plan 74 --task "test"` | No "Could not find Active Work table" warning |
| --sync argument removed | `python scripts/check_claims.py --sync` | Error: unrecognized argument |

---

## Verification

### Tests & Quality
- [ ] All required tests pass: `python scripts/check_plan_tests.py --plan 74`
- [ ] Full test suite passes: `pytest tests/`
- [ ] Type check passes: `python -m mypy src/ --ignore-missing-imports`

### Documentation
- [ ] `docs/meta/18_claim-system.md` updated
- [ ] Doc-coupling check passes: `python scripts/check_doc_coupling.py`

### Completion Ceremony
- [ ] Plan file status -> `Complete`
- [ ] `plans/CLAUDE.md` index -> `Complete`
- [ ] Claim released
- [ ] PR merged

---

## Notes

The claim system was simplified to use only `.claude/active-work.yaml` for machine-to-machine coordination. The markdown table in CLAUDE.md was removed to avoid git conflicts when multiple PRs merge.
