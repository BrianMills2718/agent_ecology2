# Plan #143: Dashboard Bug Fixes

**Status:** 📋 Planned
**Priority:** High
**Blocked By:** None
**Blocks:** None

---

## Problem Statement

Bugs introduced in Plan #142 (Dashboard Improvements):

1. **Agent Filter Broken** - The agent thinking panel filter no longer works. The `/api/agents` endpoint now returns `{agents: [], total: N}` but `thinking.js` expects a plain array.

2. **API Budget Display** - Shows accumulated values across runs (e.g., "$6.81 / $1.00"). Need to investigate if this is a display issue or actual budget tracking issue.

---

## Implementation

### 1. Fix Agent Filter in thinking.js

**File:** `src/dashboard/static/js/panels/thinking.js`

Line 68 fetches `/api/agents` expecting an array but gets paginated response:
```javascript
// Current (broken):
const agents = await response.json();
agents.forEach(agent => {...})  // Fails - agents is {agents: [], total: N}

// Fix:
const data = await response.json();
const agents = Array.isArray(data) ? data : (data.agents || []);
```

### 2. Investigate API Budget Display

Check `src/dashboard/parser.py` and `src/dashboard/kpis.py` to understand how `api_cost_spent` is tracked. Determine if:
- It's accumulating across simulation restarts
- It's being calculated incorrectly
- It's just a display formatting issue

---

## Files Affected

- src/dashboard/static/js/panels/thinking.js (modify) - Fix agent filter
- src/dashboard/parser.py (investigate) - API cost tracking
- src/dashboard/kpis.py (investigate) - API cost calculation

---

## Acceptance Criteria

- [ ] Agent filter dropdown works in thinking panel
- [ ] Selecting an agent filters thinking history correctly
- [ ] API budget display shows reasonable values
- [ ] All existing tests pass
