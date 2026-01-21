# Plan #145: Dashboard Quick Wins

**Status:** 📋 Planned
**Priority:** Medium
**Blocked By:** None
**Blocks:** None

---

## Problem Statement

Several low-effort, high-value UX improvements for the dashboard.

---

## Implementation

### 1. Real-time Alerts Banner
- Add sticky banner at top of dashboard
- Show warnings like "5 agents frozen" or "API budget 90% consumed"
- Subscribe to KPI WebSocket updates
- Color-code by severity (warning yellow, critical red)

### 2. Panel State Persistence
- Save collapsed/expanded state of panels to localStorage
- Restore state on page load
- Users set up layout once, persists across sessions

### 3. Frozen Agent Diagnostics
- Add tooltip to "frozen" status badge
- Show reason: "LLM tokens exhausted" or "Out of scrip"
- Show tick when agent froze

### 4. CSV Export Buttons
- Add export button to Agents table header
- Add export button to Artifacts table header
- Export visible/filtered data as CSV download

---

## Files Affected

- src/dashboard/static/index.html - Add alerts banner, export buttons
- src/dashboard/static/js/panels/agents.js - Export function, frozen tooltip
- src/dashboard/static/js/panels/artifacts.js - Export function
- src/dashboard/static/js/main.js - Panel persistence logic
- src/dashboard/static/js/websocket.js - Alerts subscription
- src/dashboard/static/css/dashboard.css - Alert banner styles

---

## Acceptance Criteria

- [ ] Alerts banner appears when agents freeze or budget low
- [ ] Panel collapsed state persists across page refresh
- [ ] Hovering "frozen" shows reason tooltip
- [ ] Export buttons download CSV files
- [ ] All existing tests pass
