# Plan #233: Refactor CONCEPTUAL_MODEL.yaml for Conciseness

**Status:** ✅ Complete
**Priority:** Medium
**Blocks:** None
**Created:** 2026-01-29

## Problem

CONCEPTUAL_MODEL.yaml is 1500 lines but should be ~500-700. It has accumulated historical reasoning that belongs in explorations per our established pattern:

- ADRs = concise decisions (for implementing)
- Explorations = full reasoning (for questioning)
- Conceptual model = what IS (clean, current)

The model currently mixes current state (~40%) with resolved questions (~30%) and journey documentation (~30%).

## Goal

Reduce CONCEPTUAL_MODEL.yaml to ~500-700 lines containing only current state, with historical reasoning moved to explorations.

## Changes

### Move to `docs/explorations/`

| Section | Target | Lines |
|---------|--------|-------|
| `open_questions` (resolved items) | `resolved_questions.md` | ~250 |
| `stress_test_insights` | `escrow_stress_test.md` | ~200 |
| `artifact_self_handling` migration/comparison | Already in `access_control.md` | ~150 |
| `ostrom_analysis` | `ostrom_rights_mapping.md` | ~100 |

### Keep in Model (streamlined)

| Section | Purpose |
|---------|---------|
| `artifact` | Core structure |
| `interface` | Required fields |
| `properties` | Structural properties |
| `labels` | Convenience labels |
| `examples` | Usage examples |
| `relationships` | Key relationships |
| `actions` | Core/kernel/convenience |
| `resources` | Types and concerns |
| `contracts` | Brief (references ADR-0024) |
| `kernel_responsibilities` | Brief (references ADR-0024) |
| `layers` | System layers diagram |

### For resolved `open_questions`

Replace full resolution text with:
```yaml
kernel_vs_artifact_system:
  status: "RESOLVED - ADR-0024"

contract_regress:
  status: "RESOLVED - ADR-0024, depth limit"
```

Keep only status and pointer, not the full reasoning.

## Acceptance Criteria

- [x] CONCEPTUAL_MODEL.yaml is 500-700 lines (actual: 333 lines)
- [x] All historical reasoning moved to explorations
- [x] Each moved section has clear ADR/exploration reference
- [x] No information lost (just relocated)
- [x] Explorations index updated

## Test Plan

- Doc-code coupling passes
- All ADR references valid
- All exploration references valid

## Notes

This is documentation-only work. No code changes.
