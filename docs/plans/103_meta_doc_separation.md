# Plan 103: Meta-Process Documentation Separation

**Status:** 📋 Planned

**Priority:** Medium
**Blocked By:** None
**Blocks:** #104, #105

---

## Gap

**Current:** Meta-process patterns live in `docs/meta/` alongside project documentation. This creates confusion:
- `docs/` contains both agent_ecology docs AND reusable meta-process patterns
- Users/CCs may not realize which docs are project-specific vs. portable
- Hard to extract meta-process for use in other projects

**Target:** Clear separation with `meta/` at root level:
- `docs/` = agent_ecology project documentation only
- `meta/` = reusable meta-process patterns (portable to other projects)

**Why:** Reduces confusion, prepares for future extraction as standalone package.

---

## Scope

This plan covers **Phase 1-2** of meta-process separation:
- Phase 1: Move `docs/meta/*.md` → `meta/patterns/`
- Phase 2: Move `acceptance_gates/` → `meta/acceptance_gates/`

Later phases (deferred):
- Phase 3: Move `hooks/` → `meta/hooks/` (Plan #104)
- Phase 4: Move meta scripts → `meta/scripts/` (Plan #105)

---

## Changes Required

### Directory Structure

```
meta/                           # NEW root directory
├── CLAUDE.md                   # Meta-process overview (moved from docs/meta/)
├── patterns/                   # Reusable patterns
│   ├── 01_README.md
│   ├── 02_claude-md-authoring.md
│   ├── ... (all pattern files)
│   ├── archive/
│   └── build_meta_review_package.sh
└── acceptance_gates/           # Feature specs (moved from root)
    ├── CLAUDE.md
    ├── shared.yaml
    ├── escrow.yaml
    └── ...
```

### Files to Move

| From | To |
|------|-----|
| `docs/meta/CLAUDE.md` | `meta/CLAUDE.md` |
| `docs/meta/*.md` | `meta/patterns/*.md` |
| `docs/meta/archive/` | `meta/patterns/archive/` |
| `docs/meta/build_meta_review_package.sh` | `meta/patterns/build_meta_review_package.sh` |
| `acceptance_gates/` | `meta/acceptance_gates/` |

### References to Update

| File | Change |
|------|--------|
| `CLAUDE.md` (root) | Update paths to `meta/patterns/` |
| `docs/CLAUDE.md` | Remove reference to `docs/meta/` |
| `scripts/doc_coupling.yaml` | Update `docs/meta/` → `meta/patterns/` |
| `scripts/check_feature_coverage.py` | Update `acceptance_gates/` path |
| `scripts/validate_spec.py` | Update `acceptance_gates/` path |
| `scripts/check_claims.py` | Update `acceptance_gates/` path |
| `.github/workflows/ci.yml` | Update any `acceptance_gates/` references |

---

## Files Affected

- CLAUDE.md (modify)
- docs/CLAUDE.md (modify)
- scripts/doc_coupling.yaml (modify)
- scripts/check_feature_coverage.py (modify)
- scripts/validate_spec.py (modify)
- scripts/check_claims.py (modify)
- scripts/check_locked_files.py (modify)
- scripts/complete_plan.py (modify)
- scripts/parse_plan.py (modify)
- tests/unit/test_check_claims.py (modify)
- tests/unit/test_template.py (modify)
- tests/integration/test_mint_acceptance.py (modify)
- tests/integration/test_escrow_acceptance.py (modify)
- tests/integration/test_artifacts_acceptance.py (modify)
- tests/integration/test_rate_limiting_acceptance.py (modify)
- tests/integration/test_agent_loop_acceptance.py (modify)
- tests/integration/test_agent_workflow.py (modify)
- tests/integration/test_ledger_acceptance.py (modify)
- tests/integration/test_contracts_acceptance.py (modify)
- tests/conftest.py (modify)
- meta/CLAUDE.md (create)
- meta/patterns/01_README.md (create)
- meta/acceptance_gates/CLAUDE.md (create)

---

## Implementation Steps

1. Create `meta/` directory structure
2. Move `docs/meta/` content to `meta/patterns/`
3. Move `acceptance_gates/` to `meta/acceptance_gates/`
4. Update all path references in scripts
5. Update CLAUDE.md files
6. Update doc_coupling.yaml
7. Run tests to verify nothing breaks
8. Update any CI references

---

## Required Tests

### Existing Tests (Must Pass)

| Test Pattern | Why |
|--------------|-----|
| `tests/` | All existing tests must pass |

### Manual Verification

- [ ] `python scripts/validate_spec.py --all` finds specs in new location
- [ ] `python scripts/check_feature_coverage.py` works
- [ ] `python scripts/check_claims.py --list-features` works
- [ ] `python scripts/check_doc_coupling.py --suggest` works

---

## Acceptance Criteria

- [ ] `meta/` directory exists at root level
- [ ] All pattern files accessible at `meta/patterns/`
- [ ] All acceptance gates accessible at `meta/acceptance_gates/`
- [ ] No references to `docs/meta/` remain (except in git history)
- [ ] No references to root `acceptance_gates/` remain
- [ ] All CI checks pass
- [ ] Scripts find files in new locations

---

## Notes

This is Phase 1-2 of a larger separation effort. The goal is to eventually make the meta-process fully portable to other projects.

Future phases:
- Plan #104: Move hooks (medium risk)
- Plan #105: Move scripts (high risk, many path changes)

---

## Related

- Plan #104: Meta-Process Hooks Separation (Phase 3)
- Plan #105: Meta-Process Scripts Separation (Phase 4)
