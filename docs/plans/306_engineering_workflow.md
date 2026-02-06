# Plan #306: Meta-Process Engineering Workflow + Documentation Cleanup

**Status:** 🚧 In Progress

## Summary

Formalize a 7-phase engineering workflow (Pattern #34) that prevents recurring
architectural violations by requiring context loading before implementation.
Clean up stale documentation. Dogfood the new workflow on the `created_by`
access control fix (Workstream C).

## Motivation

Recurring `created_by` misuse revealed a systemic meta-process failure: ADR-0016
says "informational only," but kernel contracts, `relationships.yaml`, and
`DESIGN_CLARIFICATIONS.md` all encode the opposite pattern. The information
existed but was never surfaced at the right time during implementation.

## Workstreams

### A: Meta-Process Improvements (Complete)

| Step | Description | Status |
|------|-------------|--------|
| A1 | Pattern #34: 7-phase engineering workflow | Done |
| A2 | `scripts/file_context.py`: unified context loader | Done |
| A3 | `custom_docs` section in meta-process.yaml | Done |
| A4 | `docs/UNCERTAINTIES.md`: human review queue | Done |
| A5 | Quiz integration (defer to future) | Deferred |

### B: Documentation Cleanup (Complete)

| Step | Description | Status |
|------|-------------|--------|
| B1 | Decompose DESIGN_CLARIFICATIONS.md | Done |
| B2 | Prune architecture gaps + freshness check | Done |

### C: `created_by` Fix (Dogfood) — Future

Use the full Pattern #34 workflow to fix `created_by` in access control.
This is the largest workstream and will be a separate PR.

## Changes (Workstreams A + B)

| File | Change |
|------|--------|
| `meta-process/patterns/34_engineering-workflow.md` | NEW: 7-phase workflow pattern |
| `scripts/file_context.py` | NEW: unified context loader |
| `docs/UNCERTAINTIES.md` | NEW: human review queue with 7 seeded questions |
| `meta-process.yaml` | Add `custom_docs` section |
| `CLAUDE.md` | Reference Pattern #34 |
| `docs/CLAUDE.md` | Add UNCERTAINTIES.md, update doc types |
| `docs/architecture/CLAUDE.md` | Point to UNCERTAINTIES.md instead of DESIGN_CLARIFICATIONS |
| `scripts/CLAUDE.md` | Add file_context.py entry |
| `docs/DESIGN_CLARIFICATIONS.md` | Decomposed to tombstone |
| `docs/DEFERRED_FEATURES.md` | Absorb sections 6, 7, 10 from DESIGN_CLARIFICATIONS |
| `docs/architecture/gaps/GAPS_SUMMARY.yaml` | Pruned: 65→75 closed, updated freshness |
| `docs/architecture/gaps/CLAUDE.md` | Updated metrics |
| `scripts/check.sh` | Advisory gap freshness warning |

## Verification

```bash
# file_context.py works
python scripts/file_context.py src/world/contracts.py

# CI passes
bash scripts/check.sh

# Custom docs surface correctly
python scripts/file_context.py src/simulation/runner.py  # Should show simulation_learnings
```
