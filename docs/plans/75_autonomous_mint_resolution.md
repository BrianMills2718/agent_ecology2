# Plan #75: Autonomous Mint Resolution

**Status:** 📋 Planned
**Priority:** Critical
**Blocks:** Autonomous-only architecture

---

## Gap

**Current:** Mint resolution is tick-based. Auctions resolve every N ticks.

**Target:** Mint resolution is time-based. Auctions resolve every N seconds (wall-clock time) in autonomous mode.

**Why:** We're refactoring to an autonomous-only codebase (Plan #83). Tick-based resolution must be replaced with time-based resolution.

---

## Design

### Resolution Trigger

Check elapsed time at the start of each agent cycle in the autonomous runner. If `resolution_interval_seconds` has passed since last resolution, trigger mint resolution before processing the next agent.

**Why this approach:**
- Simple - no background tasks or async coordination
- Safe - no race conditions, stays in main event loop
- Accurate enough - agents cycle frequently in autonomous mode

### Configuration

```yaml
genesis:
  mint:
    resolution_interval_seconds: 60  # Wall-clock seconds between resolutions
```

### Changes Required

| File | Change |
|------|--------|
| `src/simulation/runner.py` | Check elapsed time, trigger resolution in autonomous loop |
| `src/world/genesis.py` | Add time-based resolution method to GenesisMint |
| `src/world/world.py` | Track last resolution timestamp |
| `config/schema.yaml` | Add `resolution_interval_seconds` config |
| `config/config.yaml` | Set default resolution interval |

---

## Required Tests

| Test | Description |
|------|-------------|
| `tests/unit/test_mint_resolution.py::test_time_based_resolution_triggers` | Resolution triggers after interval passes |
| `tests/unit/test_mint_resolution.py::test_resolution_resets_timer` | Timer resets after each resolution |
| `tests/integration/test_autonomous_mint.py::test_mint_resolves_on_schedule` | Full integration test of timed resolution |

---

## Dependencies

- Plan #83 (Remove Tick-Based Execution) - related refactor, can proceed in parallel

---

## Notes

Part of the autonomous-only architecture refactor. Once Plan #83 completes, tick-based resolution code can be removed entirely.
