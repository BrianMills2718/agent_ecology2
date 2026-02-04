# Plan #286: Interactive Documentation Graph Visualization

**Status:** ✅ Complete

**Verified:** 2026-02-04T11:19:52Z
**Verification Evidence:**
```yaml
completed_by: scripts/complete_plan.py
timestamp: 2026-02-04T11:19:52Z
tests:
  unit: skipped (--status-only, CI-validated)
  e2e_smoke: skipped (--status-only, CI-validated)
  e2e_real: skipped (--status-only, CI-validated)
  doc_coupling: skipped (--status-only, CI-validated)
commit: 6e413da
```
**Created:** 2026-02-04

## Problem

The static DOT/PNG visualization from Plan #285 requires graphviz and isn't interactive.
Users want to explore the documentation graph interactively in their browser.

## Solution

Create an interactive HTML visualization using D3.js force-directed graph that:
- Shows all nodes (ADRs, docs, source files)
- Shows relationships (governs, documented_by, implements)
- Allows dragging nodes
- Supports zooming and panning
- Has search/filter capability
- Shows details on click
- Is self-contained (single HTML file with CDN dependencies)

## Implementation

`scripts/generate_doc_graph_html.py` generates a standalone HTML file with:
- D3.js force-directed graph
- Color-coded nodes by type (ADRs, orientation, reference, current, target, source)
- Labeled edges showing relationship types
- Sidebar with legend and details panel
- Search box to filter nodes
- Controls for adjusting physics

## Files Changed

| File | Change |
|------|--------|
| `scripts/generate_doc_graph_html.py` | New interactive visualization generator |
| `scripts/CLAUDE.md` | Document new script |

## Usage

```bash
# Generate HTML file
python scripts/generate_doc_graph_html.py

# Generate and open in browser
python scripts/generate_doc_graph_html.py --serve

# Custom output path
python scripts/generate_doc_graph_html.py -o custom_graph.html
```

## Features

- **Drag nodes** - Rearrange the graph layout
- **Zoom/Pan** - Mouse wheel to zoom, drag background to pan
- **Search** - Filter nodes by name
- **Click details** - See node info and connections
- **Adjustable physics** - Tune link distance and charge strength

## Acceptance Criteria

- [x] Generates valid HTML with embedded D3.js visualization
- [x] Shows all node types with distinct colors
- [x] Shows governance, coupling, and hierarchy edges
- [x] Interactive: drag, zoom, search, click for details
