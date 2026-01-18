# Plan #38: Meta-Process Simplification

**Status:** ✅ Complete

**Verified:** 2026-01-14T04:32:44Z
**Verification Evidence:**
```yaml
completed_by: scripts/complete_plan.py
timestamp: 2026-01-14T04:32:44Z
tests:
  unit: 1199 passed, 1 skipped in 14.49s
  e2e_smoke: PASSED (2.06s)
  doc_coupling: passed
commit: 43df302
```
**Priority:** High
**Type:** Enabler
**Blocked By:** None
**Blocks:** None

---

## Gap

**Current:** Meta-process has accumulated complexity:
- Unclear whether file-level or feature-level claims are needed
- No exemption for trivial changes (typos, comments)
- Cross-cutting files (config.py, conftest.py) create false claim conflicts
- Design decisions scattered across conversation, not documented
- docs/meta/*.md files missing "Design Decisions" sections

**Target:** Simplified meta-process with:
- Clear 80/20 decisions documented
- Trivial exemption (`[Trivial]` prefix)
- Shared scope for cross-cutting files
- All design decisions recorded in relevant docs/meta/*.md files

---

## Design Decisions to Document

Based on analysis of real-world practices (DORA research, trunk-based development, Google/Spotify scaling patterns):

| Decision | Choice | Rationale |
|----------|--------|-----------|
| Claim granularity | Feature-level, not file-level | Git handles merges; file-level is over-restrictive |
| Trivial exemption | `[Trivial]` for <20 lines, no src/ | Reduces friction for tiny fixes |
| Shared scope | `acceptance_gates/shared.yaml` for cross-cutting | Prevents false conflicts on config, fixtures |
| File lists in plans | Not required | Impractical; derived from feature scope instead |
| AST/function tracking | Deferred | File-level sufficient for current needs |
| Custom edge types | Standard only | Unenforced conventions drift |

---

## Plan

### Changes Required

| File | Change |
|------|--------|
| `docs/meta/claim-system.md` | Add design decisions, document shared scope |
| `docs/meta/plan-workflow.md` | Add trivial exemption, remove file list requirement |
| `docs/meta/feature-linkage.md` | Clarify file-level not needed |
| `acceptance_gates/shared.yaml` | NEW: Define cross-cutting files |
| `.github/workflows/ci.yml` | Add trivial exemption check |
| `scripts/check_claims.py` | Skip claim check for `[Trivial]` commits |
| `CLAUDE.md` | Update to reference trivial exemption |

### Steps

1. Update docs/meta/*.md with design decisions (6 files already partially updated)
2. Create `acceptance_gates/shared.yaml` with cross-cutting files
3. Update CI to recognize `[Trivial]` prefix
4. Update `check_claims.py` to exempt trivial commits
5. Update CLAUDE.md with trivial workflow
6. Test the changes

---

## Required Tests

### New Tests (TDD)

| Test File | Test Function | What It Verifies |
|-----------|---------------|------------------|
| `tests/unit/test_check_claims.py` | `TestSharedScope::test_shared_files_always_claimed` | Shared files always considered claimed |
| `tests/unit/test_check_claims.py` | `TestSharedScope::test_shared_feature_never_conflicts` | Shared feature has no conflicts |
| `tests/unit/test_check_claims.py` | `TestSharedScope::test_other_features_still_conflict` | Non-shared features still conflict normally |

### Existing Tests (Must Pass)

| Test Pattern | Why |
|--------------|-----|
| `tests/` | All existing tests |

---

## Verification

- [x] docs/meta/claim-system.md has Design Decisions section
- [x] docs/meta/plan-workflow.md has Trivial Exemption section
- [x] `acceptance_gates/shared.yaml` exists with cross-cutting files
- [x] CI recognizes `[Trivial]` prefix
- [x] check_claims.py handles shared scope (no conflicts)
- [x] Tests pass (10 new tests for claims, 1192 total)
- [ ] PR created and merged

---

## Notes

This is an "eat our own dogfood" plan - improving the meta-process using the meta-process.

Evidence considered:
- DORA research: deployment frequency > process rigor
- Trunk-based development: small changes, trust git
- Spotify scaling: simple rules > complex coordination
- Google monorepo: anyone can modify common code, tests are the gate
