# Gap 58: Dashboard Support for Autonomous Mode

**Status:** 📋 Planned
**Priority:** **High**
**Blocked By:** -
**Blocks:** -

---

## Gap

**Current:** Dashboard features (resources chart, thinking panel) don't work in autonomous mode because:
1. `advance_tick()` is never called - all events have `"tick": 0`
2. `"tick"` events (with compute/scrip snapshots) are never logged
3. `"thinking"` events are never logged (only happen in tick-based `_process_thinking_results()`)

The dashboard parser (`src/dashboard/parser.py`) relies on:
- `_handle_tick()` to populate `compute_history` and `scrip_history` for charts
- `_handle_thinking()` to populate thinking panel data

**Target:** Dashboard works correctly in autonomous mode:
- Resources chart shows live/periodic resource state
- Thinking panel shows agent reasoning
- Activity feed continues working (already functional)

**Why High:** V1 defaults to autonomous mode, making dashboard observability non-functional for the primary use case.

---

## Analysis

### Event Requirements

| Dashboard Feature | Required Event | Tick-Based | Autonomous |
|-------------------|----------------|------------|------------|
| Resources Chart | `tick` with `compute`, `scrip` | Yes | No |
| Thinking Panel | `thinking` with `thought_process` | Yes | No |
| Action Feed | `action` events | Yes | Yes |
| Activity Feed | Various genesis events | Yes | Yes |

### Options

**Option A: Periodic Snapshot Events (Recommended)**
- Add a background task that logs `tick`-like snapshots every N seconds
- Log `thinking` events from autonomous agent loops
- Minimal changes to dashboard parser
- Events include real timestamp + synthetic "tick" based on elapsed time

**Option B: Live State Queries**
- Dashboard queries live world state via API
- More complex, requires SimulationRunner reference
- Real-time but doesn't work for historical analysis

**Option C: Tick Simulation**
- Periodically call `advance_tick()` in autonomous mode
- Conflicts with rate-tracker resource model
- Not recommended - breaks autonomous semantics

---

## Plan

**Approach:** Option A - Periodic Snapshot Events

### Changes Required

| File | Change |
|------|--------|
| `src/simulation/runner.py` | ADD - `_log_autonomous_snapshot()` method, background task |
| `src/simulation/agent_loop.py` | UPDATE - Log `thinking` events after agent decisions |
| `src/dashboard/parser.py` | UPDATE - Handle `snapshot` events as tick-like data |
| `docs/architecture/current/execution_model.md` | UPDATE - Document autonomous logging |

### Steps

1. **Add snapshot logging to autonomous runner**
   - Create `_log_autonomous_snapshot()` method that logs resource state
   - Start background asyncio task in `_run_autonomous()`
   - Log snapshot every `dashboard.snapshot_interval` seconds (default: 5)
   - Use elapsed seconds as synthetic "tick" for chart compatibility

2. **Add thinking events to autonomous agent loop**
   - After `decide_action` returns, log `thinking` event with token usage
   - Include `thought_process` if available from agent response

3. **Update dashboard parser**
   - Add `_handle_snapshot()` handler as alias for tick data
   - Handle both `tick` and `snapshot` event types

4. **Configuration**
   - Add `dashboard.snapshot_interval` config option
   - Default to 5 seconds

---

## Required Tests

### New Tests (TDD)

```
tests/unit/test_runner_autonomous_logging.py::test_autonomous_logs_snapshots
tests/unit/test_runner_autonomous_logging.py::test_autonomous_logs_thinking
tests/unit/test_dashboard_parser.py::test_parser_handles_snapshot_events
tests/integration/test_autonomous_dashboard.py::test_dashboard_shows_resources_autonomous
```

### Existing Tests (Must Pass)

```
tests/e2e/test_smoke.py
tests/unit/test_runner.py
tests/unit/test_dashboard_parser.py
```

---

## Acceptance Criteria

- [ ] Running dashboard with autonomous simulation shows resource charts
- [ ] Thinking panel populated with agent reasoning
- [ ] Snapshot interval is configurable
- [ ] No regressions in tick-based mode
- [ ] E2E smoke test passes

---

## Notes

- This is a V1 regression - dashboard worked in tick-based mode but autonomous mode became default
- Consider whether synthetic tick numbers are appropriate or if dashboard should use timestamps natively (Post-V1)
