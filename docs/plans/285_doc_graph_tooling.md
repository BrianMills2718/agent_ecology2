# Plan #285: Documentation Graph Tooling

**Status:** ✅ Complete

**Verified:** 2026-02-04T11:12:31Z
**Verification Evidence:**
```yaml
completed_by: scripts/complete_plan.py
timestamp: 2026-02-04T11:12:31Z
tests:
  unit: skipped (--status-only, CI-validated)
  e2e_smoke: skipped (--status-only, CI-validated)
  e2e_real: skipped (--status-only, CI-validated)
  doc_coupling: skipped (--status-only, CI-validated)
commit: bd05bf9
```
**Created:** 2026-02-04

## Problem

The documentation graph (ADR-0005) exists in relationships.yaml but:
1. Claude doesn't automatically see graph context when editing files
2. There's no visualization of the graph

## Solution

1. **Enhance `get_governance_context.py`** - Show both ADR governance AND coupled docs
2. **Create `visualize_doc_graph.py`** - Generate graph visualization (DOT/PNG/SVG)

## Implementation

### Enhanced Context Script

The existing hook (`inject-governance-context.sh`) calls `get_governance_context.py` which now shows:
- ADR governance (which decisions govern this file)
- Coupled docs (which docs must be updated)
- Context notes

Example output when editing `ledger.py`:
```
"This file is governed by ADR-0001 (Everything is an artifact), ADR-0002 (No compute debt).
Related docs (update required): resources.md.
Related docs (advisory): GLOSSARY.md, CONCEPTUAL_MODEL.yaml, CORE_SYSTEMS.md.
Governance context: All balance mutations go through here. Never allow negative balances - fail loud."
```

### Visualization Script

New script `visualize_doc_graph.py` generates:
- Text output: `--text` flag for ASCII representation
- DOT file: `--format dot` for graphviz source
- PNG/SVG: `--format png|svg` (requires graphviz installed)

## Files Changed

| File | Change |
|------|--------|
| `scripts/get_governance_context.py` | Enhanced to show couplings, not just governance |
| `scripts/visualize_doc_graph.py` | New visualization script |

## Usage

```bash
# See context for a file
python scripts/get_governance_context.py src/world/ledger.py

# Full JSON output
python scripts/get_governance_context.py src/world/ledger.py --full

# Text visualization
python scripts/visualize_doc_graph.py --text

# Generate PNG (requires graphviz)
python scripts/visualize_doc_graph.py --format png -o doc_graph.png
```

## Acceptance Criteria

- [x] `get_governance_context.py` shows ADRs AND coupled docs
- [x] `visualize_doc_graph.py` generates text representation
- [x] `visualize_doc_graph.py` generates DOT file for graphviz
- [ ] Hook injects context when editing governed files (already exists)
