# Plan #58: Dashboard Autonomous Mode Support

**Priority:** Medium
**Status:** ✅ Complete

**Verified:** 2026-01-16T14:08:11Z
**Verification Evidence:**
```yaml
completed_by: scripts/complete_plan.py
timestamp: 2026-01-16T14:08:11Z
tests:
  unit: 1405 passed, 7 skipped in 20.76s
  e2e_smoke: PASSED (1.58s)
  e2e_real: PASSED (5.40s)
  doc_coupling: passed
commit: 80f6a29
```
**Dependencies:** #57 (Agent Resource Management)

## Problem Statement

The dashboard was designed for tick-based execution but doesn't show agent activity in autonomous mode. When agents run independently via `--autonomous`, their thinking and actions aren't logged to the event stream the dashboard monitors.

## Solution

1. Add event logging callbacks in autonomous mode runner
2. Add dashboard panel for world configuration display
3. Update dashboard to read from per-run log directory

## Plan

### Implementation Steps

1. Add thinking/action event logging to `AutonomousCallback` in `runner.py`
2. Create new dashboard panel (`config.js`) showing world configuration
3. Update dashboard to read from `logs/latest/events.jsonl`
4. Add `logs/` to `.gitignore`

### Files Modified

- `src/simulation/runner.py` - Add event logging to autonomous callbacks
- `src/dashboard/static/js/panels/config.js` - New config panel
- `config/config.yaml` - Dashboard config updates
- `.gitignore` - Add logs directory

## Required Tests

### Existing Tests (Must Pass)

| Test Pattern | Why |
|--------------|-----|
| `tests/e2e/test_smoke.py` | Full simulation still works |

## Verification

- [ ] Run `python run.py --agents 3 --duration 60 --dashboard --autonomous`
- [ ] Verify thinking events appear in Agent Thinking panel
- [ ] Verify action events appear in Activity Feed
