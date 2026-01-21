# Plan #144: Per-Entity Activity Timelines

**Status:** ✅ Complete
**Priority:** Medium
**Blocked By:** None
**Blocks:** None

---

## Problem Statement

Users want to view all activity for a specific agent or artifact over time. Currently:
- The Activity panel shows all activity but only filters by type
- Agent detail modal shows recent actions but not full activity history
- Artifact detail modal shows ownership history but not invocation/usage timeline

---

## Implementation

### 1. Backend: Add artifact_id filter to /api/activity

**File:** `src/dashboard/server.py`
- Add `artifact_id` query parameter to `/api/activity` endpoint

**File:** `src/dashboard/parser.py`
- Extend `get_activity_feed()` to filter by artifact_id

### 2. Frontend: Activity Panel Entity Filters

**File:** `src/dashboard/static/js/panels/activity.js`
- Add agent dropdown filter (populated from /api/agents)
- Add artifact dropdown filter (populated from /api/artifacts)
- Update loadActivity() to pass filters to API

**File:** `src/dashboard/static/index.html`
- Add filter dropdowns to activity panel header

### 3. Frontend: Agent Detail Activity Tab

**File:** `src/dashboard/static/js/panels/agents.js`
- Add activity timeline section to agent modal
- Fetch from `/api/activity?agent_id=X`

### 4. Frontend: Artifact Detail Activity Tab

**File:** `src/dashboard/static/js/panels/activity.js`
- Add activity timeline section to artifact modal
- Fetch from `/api/activity?artifact_id=X`

---

## Files Affected

- src/dashboard/server.py (modify) - Add artifact_id filter
- src/dashboard/parser.py (modify) - Extend get_activity_feed()
- src/dashboard/static/js/panels/activity.js (modify) - Add entity filters
- src/dashboard/static/js/panels/agents.js (modify) - Add activity to modal
- src/dashboard/static/index.html (modify) - Add filter dropdowns
- src/dashboard/static/css/dashboard.css (modify) - Styles for filters

---

## Acceptance Criteria

- [ ] Activity panel has agent filter dropdown
- [ ] Activity panel has artifact filter dropdown
- [ ] Selecting an agent shows only that agent's activity
- [ ] Selecting an artifact shows only activity involving that artifact
- [ ] Agent detail modal shows activity timeline
- [ ] Artifact detail modal shows activity timeline
- [ ] All existing tests pass
