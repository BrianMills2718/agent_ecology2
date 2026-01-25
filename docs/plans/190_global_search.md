# Plan #190: Global Search in Dashboard v2

**Status:** ✅ Complete
**Priority:** Medium
**Blocked By:** None
**Blocks:** None

---

## Problem Statement

Users need a quick way to find agents and artifacts by ID without scrolling through lists.

---

## Solution

Add a global search dialog with keyboard shortcut (Cmd/Ctrl+K) that searches across agents and artifacts.

---

## Files Affected

- dashboard-v2/src/components/shared/SearchDialog.tsx (create)
- dashboard-v2/src/stores/search.ts (create)
- dashboard-v2/src/stores/selection.ts (create)
- dashboard-v2/src/components/layout/Header.tsx (modify)
- dashboard-v2/src/App.tsx (modify)
- dashboard-v2/src/api/queries.ts (modify)
- dashboard-v2/src/types/api.ts (modify)
- dashboard-v2/src/components/panels/AgentsPanel.tsx (modify)
- dashboard-v2/src/components/panels/ArtifactsPanel.tsx (modify)
- src/dashboard/server.py (modify)

---

## Implementation

### 1. Backend: Search Endpoint

Add `/api/search?q=query` endpoint that searches:
- Agent IDs (partial match)
- Artifact IDs (partial match)

Returns: `{agents: [...], artifacts: [...]}`

### 2. Frontend: Search Dialog

- Modal dialog triggered by Cmd/Ctrl+K or clicking search icon
- Debounced input (300ms)
- Grouped results: Agents, Artifacts
- Click result to open detail modal
- Escape to close

---

## Acceptance Criteria

- [x] Search endpoint returns matching agents and artifacts
- [x] Cmd/Ctrl+K opens search dialog
- [x] Clicking result opens detail modal
- [x] `npm run build` passes
