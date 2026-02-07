# Plan 253: Feature → Gate Terminology Cleanup

**Status:** ✅ Complete

**Verified:** 2026-02-01T16:02:27Z
**Verification Evidence:**
```yaml
completed_by: scripts/complete_plan.py
timestamp: 2026-02-01T16:02:27Z
tests:
  unit: skipped (--status-only, CI-validated)
  e2e_smoke: skipped (--status-only, CI-validated)
  e2e_real: skipped (--status-only, CI-validated)
  doc_coupling: skipped (--status-only, CI-validated)
commit: c3c91dc
```
**Priority:** Medium
**Blocked By:** None
**Blocks:** None

---

## Gap

**Current:** META-ADR-0001 mandates "acceptance gate" terminology, but multiple scripts and patterns still use "feature":

**Scripts using `--feature`:**
- `scripts/check_claims.py` - `--feature` flag for claiming
- `scripts/check_feature_coverage.py` - entire script named around "feature"
- `scripts/check_locked_files.py` - `--features-dir` flag
- `scripts/validate_spec.py` - `--feature` flag
- `scripts/CLAUDE.md` - documentation references

**Patterns using "feature":**
- `meta-process/patterns/11_terminology.md` - defines both terms as synonyms
- `meta-process/patterns/13_acceptance-gate-driven-development.md` - mixed usage
- `meta-process/patterns/14_acceptance-gate-linkage.md` - mixed usage
- `meta-process/patterns/15_plan-workflow.md` - references
- `meta-process/patterns/worktree-coordination/18_claim-system.md` - `--feature` in examples
- `meta-process/patterns/03_testing-strategy.md` - references

**Target:** All scripts and documentation use "gate" or "acceptance gate" terminology per META-ADR-0001.

**Evidence:** External LLM review (Gemini) identified this as an inconsistency that could confuse AI agents following the documentation.

---

## References Reviewed

- `meta-process/adr/0001-acceptance-gate-terminology.md` - The mandate
- Scripts listed above - Current usage
- Patterns listed above - Current usage

---

## Plan

### Phase 1: Script CLI Changes

Rename flags while maintaining backwards compatibility:

| Script | Change |
|--------|--------|
| `check_claims.py` | `--feature` → `--gate` (keep `--feature` as hidden alias) |
| `check_locked_files.py` | `--features-dir` → `--gates-dir` |
| `validate_spec.py` | `--feature` → `--gate` |

**Rename script:**
- `check_feature_coverage.py` → `check_gate_coverage.py`

### Phase 2: Pattern Documentation

Update patterns to use "gate" terminology:
- Pattern 11: Remove "Feature" as synonym, clarify "acceptance gate" only
- Pattern 13, 14: Replace "feature" with "gate" throughout
- Pattern 15, 18: Update examples
- Pattern 03: Update references

### Phase 3: Script Documentation

Update `scripts/CLAUDE.md` examples to use `--gate` instead of `--feature`.

### Phase 4: Legacy Alias Deprecation (Future)

After 30 days, emit deprecation warning when `--feature` is used. Remove aliases after 60 days.

---

## Open Questions

1. **Should `meta/acceptance_gates/` directory be renamed?** No - it already uses correct terminology.

2. **Should backwards-compatible aliases be kept forever?** Recommend deprecation path (Phase 4) to fully align with ADR.

---

## Required Tests

No new tests required - this is a terminology/documentation change. Existing tests should continue to pass.

| Validation | Command |
|------------|---------|
| Scripts work | `python scripts/check_claims.py --help` (verify --gate flag exists) |
| No regressions | `make check` |

---

## Acceptance Criteria

1. [ ] All script `--feature` flags renamed to `--gate` with backwards-compatible aliases
2. [ ] `check_feature_coverage.py` renamed to `check_gate_coverage.py`
3. [ ] All 6 patterns updated to use "gate" terminology
4. [ ] `scripts/CLAUDE.md` updated with new flag names
5. [ ] META-ADR-0001 marked as fully implemented

---

## Notes

- This is terminology cleanup, not functional change
- Backwards compatibility via hidden aliases minimizes disruption
- Aligns with META-ADR-0001 which has been accepted since 2026-01-18
