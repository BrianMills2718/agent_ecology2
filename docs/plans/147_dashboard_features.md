# Plan #147: Dashboard Features - Latency, Search, Comparison

**Status:** 📋 Planned
**Priority:** Medium
**Blocked By:** None
**Blocks:** None

---

## Problem Statement

Three dashboard features to improve usability:

1. **Latency Diagnostics** - Show WebSocket and API response times
2. **Global Search** - Search across all agents, artifacts, and events
3. **Agent Comparison** - Side-by-side comparison of two agents

---

## Implementation

### 1. Latency Diagnostics Badge

**Location:** Footer or header status area

- Track WebSocket message latency (ping/pong)
- Track last API response time
- Display: "WS: 45ms | API: 120ms"
- Color code: green (<100ms), yellow (<500ms), red (>500ms)

**Files:**
- src/dashboard/static/js/websocket.js - Add latency tracking
- src/dashboard/static/index.html - Add latency badge
- src/dashboard/static/css/dashboard.css - Latency badge styles

### 2. Global Search

**Location:** Header, always visible

- Search box with typeahead
- Search across: agent IDs, artifact IDs, event descriptions
- Show results in dropdown with category labels
- Click result to navigate (open modal or scroll to item)

**Files:**
- src/dashboard/static/js/search.js - New search component
- src/dashboard/server.py - Add /api/search endpoint
- src/dashboard/static/index.html - Add search box
- src/dashboard/static/css/dashboard.css - Search styles

### 3. Agent Comparison Mode

**Location:** Agent detail modal enhancement

- "Compare" button on agent rows
- Select two agents to compare
- Side-by-side modal showing: scrip, resources, action count, status
- Highlight differences

**Files:**
- src/dashboard/static/js/panels/agents.js - Add comparison logic
- src/dashboard/static/index.html - Add comparison modal
- src/dashboard/static/css/dashboard.css - Comparison styles

---

## Acceptance Criteria

- [ ] Latency badge shows WS and API latency
- [ ] Global search finds agents, artifacts by ID
- [ ] Clicking search result opens detail modal
- [ ] Can compare two agents side-by-side
- [ ] All existing tests pass
