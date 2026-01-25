# Plan #177: Dashboard Bug Fixes

**Status:** ✅ Complete

**Verified:** 2026-01-25T04:00:00Z
**Verification Evidence:**
```yaml
completed_by: Manual verification (renumbered from conflicting #143)
timestamp: 2026-01-25T04:00:00Z
original_commit: 0e71898 [Plan #143] Fix agent filter in thinking panel (#497)
notes: |
  Work was completed under original #143 but conflicted with 143_reflex_system.md.
  Renumbered to #177 to resolve conflict. The fix is verified working:
  - Agent filter handles paginated API response
  - API budget display issue was transient (log files properly cleared on new runs)
```

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

**Resolution:** The log files are properly cleared on each new simulation run (see `src/world/logger.py` lines 245, 272). The accumulated values issue was transient and is no longer reproducible.

---

## Files Affected

- src/dashboard/static/js/panels/thinking.js (modify) - Fix agent filter

---

## Acceptance Criteria

- [x] Agent filter dropdown works in thinking panel
- [x] Selecting an agent filters thinking history correctly
- [x] API budget display shows reasonable values
- [x] All existing tests pass
