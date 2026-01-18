# Plan 91: Acceptance Gate Terminology and Documentation Cleanup

**Status:** 📋 Planned
**Priority:** High
**Type:** Refactor
**Blocked By:** None
**Blocks:** None

---

## Problem

The meta-process documentation has accumulated confusion:

1. **Terminology drift** - "feature" and "acceptance gate" used interchangeably
2. **Redundant documentation** - `docs/acceptance_gates/` duplicates content that should be in yaml or `docs/architecture/current/`
3. **Missing rationale** - No ADRs for meta-process decisions, so reasoning gets lost
4. **Unclear goal** - The anti-big-bang purpose of acceptance gates isn't documented

## Goal

Establish "acceptance gate" as the canonical term, document the rationale in meta-process ADRs, and eliminate redundant documentation.

---

## References Reviewed

- `docs/meta/11_terminology.md` - Uses both "feature" and "acceptance gate"
- `docs/meta/13_feature-driven-development.md` - 700 lines, "feature" throughout
- `docs/meta/14_feature-linkage.md` - References `features.yaml`
- `docs/acceptance_gates/CLAUDE.md` - Explains acceptance gates well
- `acceptance_gates/CLAUDE.md` - Root directory explanation
- `docs/GLOSSARY.md` - No entry for "acceptance gate"
- `docs/DOCUMENTATION_ASSESSMENT_2026_01_16.md` - Flags this confusion

---

## Files Affected

### Create
- docs/meta/adr/README.md (create)
- docs/meta/adr/0001-acceptance-gate-terminology.md (create)
- docs/meta/adr/0002-thin-slice-enforcement.md (create)
- docs/meta/adr/0003-plan-gate-hierarchy.md (create)
- docs/meta/adr/0004-gate-yaml-is-documentation.md (create)

### Modify
- docs/meta/11_terminology.md (modify) - Replace "feature" with "acceptance gate"
- docs/meta/13_feature-driven-development.md (modify) - Rename, update terminology
- docs/meta/14_feature-linkage.md (modify) - Rename, update terminology
- docs/meta/01_README.md (modify) - Update pattern names in index
- docs/meta/CLAUDE.md (modify) - Update references
- docs/GLOSSARY.md (modify) - Add "acceptance gate" definition

### Delete
- docs/acceptance_gates/README.md (delete)
- docs/acceptance_gates/CLAUDE.md (delete)
- docs/acceptance_gates/dashboard.md (delete) - merge to docs/architecture/current/
- docs/acceptance_gates/mint_auction.md (delete) - merge to docs/architecture/current/

---

## Plan

### Phase 1: Create Meta-Process ADRs

1. Create `docs/meta/adr/README.md` explaining the purpose
2. Create ADR-0001: Acceptance Gate Terminology
   - Decision: Use "acceptance gate" not "feature" for E2E checkpoints
   - Context: "Feature" is overloaded; "acceptance gate" conveys the mechanism
3. Create ADR-0002: Thin-Slice Enforcement
   - Decision: Acceptance gates exist to prevent big-bang development
   - Context: CC tends to work for days without E2E verification
4. Create ADR-0003: Plan-Gate Hierarchy
   - Decision: Plans contribute to gates; only gates require E2E
   - Context: Not every atomic task can/should have E2E tests
5. Create ADR-0004: Gate YAML Is Documentation
   - Decision: No separate markdown docs for gates; yaml contains problem/design
   - Context: Eliminates redundancy, single source of truth

### Phase 2: Update Terminology

6. Update Pattern 11 (Terminology)
   - Change hierarchy to use "Acceptance Gate" as primary term
   - Remove "Feature" as synonym

7. Update Pattern 13
   - Rename file to `13_acceptance-gate-driven-development.md`
   - Global replace "feature" → "acceptance gate" where referring to E2E checkpoint
   - Keep "feature" only when referring to general software features
   - Add prominent "Why This Exists" section about anti-big-bang goal

8. Update Pattern 14
   - Rename file to `14_acceptance-gate-linkage.md`
   - Update diagrams to use "acceptance gate" terminology
   - Update `features.yaml` references (keep filename but clarify purpose)

9. Update Pattern 01 (README)
   - Update pattern names in index

10. Update `docs/meta/CLAUDE.md`
    - Update any pattern references

### Phase 3: Consolidate Documentation

11. Merge `docs/acceptance_gates/dashboard.md` content
    - Target: `docs/architecture/current/supporting_systems.md` or `dashboard.md`

12. Merge `docs/acceptance_gates/mint_auction.md` content
    - Target: `docs/architecture/current/mint.md`

13. Delete `docs/acceptance_gates/` directory entirely

### Phase 4: Update Glossary

14. Add to `docs/GLOSSARY.md`:
    ```
    | **Acceptance Gate** | E2E checkpoint for a functional capability. Must pass with real (non-mocked) tests. Prevents big-bang integration. |
    ```

---

## Required Tests

### Existing Tests (Must Pass)

| Test Pattern | Why |
|--------------|-----|
| `pytest tests/` | No functional changes |
| `python scripts/check_doc_coupling.py` | Doc paths may change |

### Validation

| Check | Command |
|-------|---------|
| No broken links | Manual review of updated pattern cross-references |
| Terminology consistency | grep for "feature" in updated files, verify context |

---

## Verification

- [ ] Meta ADRs created in docs/meta/adr/
- [ ] Pattern 11 uses "acceptance gate" as primary term
- [ ] Pattern 13 renamed and updated
- [ ] Pattern 14 renamed and updated
- [ ] docs/acceptance_gates/ deleted
- [ ] Content merged to docs/architecture/current/
- [ ] Glossary updated
- [ ] All tests pass
- [ ] Doc-coupling check passes

---

## Notes

### Why "Acceptance Gate" Not "Feature"

1. "Feature" is overloaded - means different things everywhere
2. "Acceptance gate" conveys the mechanism - it's a gate you must pass
3. The name encodes the discipline - not optional, not a suggestion

### The Anti-Big-Bang Goal

The core purpose: Claude Code tends toward big-bang development, working for days without real E2E testing or review. Acceptance gates force thin-slice development by requiring functional capabilities to pass real E2E tests before being considered complete.

### Hierarchy Clarification

```
Acceptance Gate (functional capability)    ← E2E test required
└── Plan(s) (work coordination)            ← Unit/integration tests
    └── Task(s) (atomic work)              ← May have no tests
```

E2E makes sense at the functional capability level, not for every atomic task.
