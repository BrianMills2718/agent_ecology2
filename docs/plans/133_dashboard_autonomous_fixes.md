# Plan #133: Dashboard Autonomous Mode Fixes

**Status:** 🔄 In Progress
**PR:** #460
**Priority:** High
**Blocked By:** None
**Blocks:** Simulation observability

---

## Problem Statement

Plan #110 (Dashboard Overhaul) was marked complete but Phase 1 has critical gaps:

| Issue | Root Cause |
|-------|------------|
| "0.00 events/sec" always | `parser.py` line 892 requires `current_tick > 0` which never happens in autonomous mode |
| "0s \| 0 events" | Same - elapsed time calculation skipped |
| Agent compute/disk 0% | `disk_used` never updated; `llm_tokens_used` may not get `thinking_cost` |
| Agent filter not populated | Timing issue - filter loads before agents available |
| No contract/access info | `access_contract_id` not parsed or displayed |
| Auto-refresh unreliable | watchdog doesn't work well on WSL2 |

## Solution

### Phase 1: Fix Progress Metrics

**File:** `src/dashboard/parser.py`

1. Remove `current_tick > 0` requirement (line 892)
2. Track `action_count` as event counter instead of ticks
3. Calculate `events_per_second` from action count

```python
def get_progress(self) -> SimulationProgress:
    elapsed = 0.0
    events_per_sec = 0.0
    # Count total actions across all agents
    total_actions = sum(a.action_count for a in self.state.agents.values())

    if self.state.start_time:  # Remove current_tick > 0 requirement
        try:
            start = datetime.fromisoformat(self.state.start_time)
            now = datetime.now()
            elapsed = (now - start).total_seconds()
            events_per_sec = total_actions / elapsed if elapsed > 0 else 0
        except (ValueError, TypeError):
            pass

    return SimulationProgress(
        current_tick=total_actions,  # Use action count as "events"
        ...
    )
```

### Phase 2: Add Contract/Access Info to Artifacts

**Files:**
- `src/dashboard/parser.py` - Parse `access_contract_id` from artifact events
- `src/dashboard/models.py` - Add field to ArtifactSummary
- `src/dashboard/static/js/panels/artifacts.js` - Display in modal

### Phase 3: Add Polling Mode Config

**Files:**
- `config/schema.yaml` - Add `use_polling: bool` option
- `src/dashboard/server.py` - Use PollingWatcher when configured

### Phase 4: Fix Agent Filter Timing

**File:** `src/dashboard/static/js/panels/thinking.js`

Load agents before first refresh, or retry if empty.

## Files Affected

- src/dashboard/parser.py (modify)
- src/dashboard/models.py (modify)
- src/dashboard/server.py (modify)
- src/dashboard/static/js/panels/artifacts.js (modify)
- src/dashboard/static/js/panels/thinking.js (modify)
- src/dashboard/static/index.html (modify)
- config/schema.yaml (modify)
- config/config.yaml (modify)

## Verification

- [ ] Progress shows non-zero events/sec during simulation
- [ ] Elapsed time displays correctly
- [ ] Artifact modal shows access contract info
- [ ] Agent filter populates correctly
- [ ] Dashboard updates in real-time (with polling fallback)
- [ ] All existing tests pass

## Notes

- This completes the unfinished Phase 1 work from Plan #110
- Polling mode is opt-in to avoid breaking existing setups
- Contract info display is read-only (no editing)
