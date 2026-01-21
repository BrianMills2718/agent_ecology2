# Plan #142: Dashboard Improvements - KPI Trends, Pagination, WebSocket

**Status:** 📋 Planned
**Priority:** Medium
**Blocked By:** None
**Blocks:** Dashboard scalability

---

## Problem Statement

The dashboard needs three improvements for better observability at scale:

1. **KPI Trend Visualization** - Currently KPI history is computed (last 10 ticks) but not visualized. Users can't see trends over time.

2. **Table Pagination** - Agent and artifact tables render all rows at once. This will become slow as the ecosystem grows.

3. **WebSocket KPI Push** - KPIs are fetched via polling HTTP requests. Real-time push would reduce latency and server load.

---

## Implementation

### 1. KPI Trend Visualization

**Backend (`src/dashboard/kpis.py`):**
- Extend `EcosystemKPIs` dataclass with additional trend fields
- Increase history from 10 to 30 ticks
- Add trends for: gini_coefficient, active_agent_ratio, frozen_count

**Frontend (`src/dashboard/static/js/panels/emergence.js`):**
- Add sparkline charts using Chart.js (already loaded)
- Small inline charts (60px x 20px) next to metric values
- Color indicates trend direction (green up, red down)

### 2. Table Pagination

**Backend (`src/dashboard/server.py`):**
- Add `limit` and `offset` query params to `/api/agents` and `/api/artifacts`
- Return total count for pagination UI

**Frontend (`agents.js`, `artifacts.js`):**
- Add pagination state (currentPage, rowsPerPage)
- Add pagination controls (prev/next, page selector)
- Update fetch calls to use pagination params

### 3. WebSocket KPI Push

**Backend (`src/dashboard/server.py`):**
- In `on_file_change()`, broadcast KPI data via WebSocket
- New message type: `kpi_update`

**Frontend (`emergence.js`):**
- Listen for `kpi_update` WebSocket messages
- Update display without polling

---

## Files Affected

- src/dashboard/kpis.py (modify) - Add trend fields, extend history
- src/dashboard/server.py (modify) - Pagination params, WebSocket KPI broadcast
- src/dashboard/static/js/panels/agents.js (modify) - Pagination controls
- src/dashboard/static/js/panels/artifacts.js (modify) - Pagination controls
- src/dashboard/static/js/panels/emergence.js (modify) - Sparklines, WebSocket listener
- src/dashboard/static/index.html (modify) - Pagination control HTML
- src/dashboard/static/css/dashboard.css (modify) - Sparkline and pagination styles
- src/dashboard/static/js/api.js (modify) - Add pagination parameters to API calls

---

## Acceptance Criteria

- [ ] Sparkline charts appear next to KPI metrics in emergence panel
- [ ] Sparklines update in real-time via WebSocket
- [ ] Agent table shows pagination controls
- [ ] Artifact table shows pagination controls
- [ ] Pagination works correctly (prev/next, rows per page selector)
- [ ] All existing tests pass
