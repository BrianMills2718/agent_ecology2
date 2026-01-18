# Plan 83: Remove Tick-Based Execution Model

**Status:** 🚧 In Progress
**Complexity:** High
**Prerequisites:** None (but should tag current state first)

## Goal

Remove all tick-based execution code and migrate to pure continuous/time-based execution. This eliminates cognitive anchoring on tick-based thinking and aligns the codebase with the target continuous operation model.

## Motivation

- Tick-based code influences Claude Code to suggest tick-based solutions
- Real agent systems operate continuously, not in discrete ticks
- Auctions/timing expressed in ticks are meaningless without knowing tick rate
- Already have `RateTracker` and `AgentLoop` for continuous operation
- Simplifies mental model: everything is time-based, not artificial tick-based

## Pre-Work

```bash
# Tag current state before any changes
git tag tick-based-v1 -m "Last version with tick-based execution model"
```

## Changes Required

### 1. Core World State (src/world/world.py)
- [ ] Remove self.tick counter
- [ ] Remove advance_tick() method
- [ ] Use timestamps for all state tracking
- [ ] Update get_state_summary() to not include tick

### 2. Simulation Runner (src/simulation/runner.py)
- [ ] Remove tick loop, use continuous AgentLoop execution
- [ ] Change --ticks N CLI to --duration 60s (or --duration 5m)
- [ ] Checkpointing by time interval instead of tick interval
- [ ] Remove tick-based progress display

### 3. Mint/Auction System (src/world/genesis/mint.py)
- [ ] Convert auction.period from ticks to seconds (e.g., 300 = 5 minutes)
- [ ] Convert auction.bidding_window from ticks to seconds
- [ ] Convert auction.first_auction_tick to first_auction_delay_seconds
- [ ] Use wall-clock time for auction phase transitions
- [ ] Handle edge cases: bids arriving near deadline (grace period?)

### 4. Resource System (src/world/ledger.py)
- [ ] Remove tick-based flow resource refresh
- [ ] Rely entirely on RateTracker for rate limiting
- [ ] Update resource distribution to not reference ticks

### 5. Event Logging (src/world/logger.py)
- [ ] Remove tick field from events (keep timestamp only)
- [ ] Update all event emission to not include tick

### 6. Agent Prompts (src/agents/*/system_prompt.md, agent.yaml)
- [ ] Remove tick references from prompts
- [ ] Update "Tick: {tick}" to timestamp or elapsed time
- [ ] Update workflow variables that reference tick

### 7. Config Schema (src/config_schema.py, config/schema.yaml)
- [ ] Convert tick-based configs to time-based:
  - auction.period -> seconds
  - auction.bidding_window -> seconds
  - checkpoint_interval -> seconds
  - active_agent_threshold_ticks -> active_agent_threshold_seconds
- [ ] Remove any tick-specific configs

### 8. Dashboard (src/dashboard/)
- [ ] Update displays to show timestamps, not ticks
- [ ] Update any tick-based filtering/grouping

### 9. Tests
- [ ] Update all tests that use advance_tick()
- [ ] Replace with time-based or event-based assertions
- [ ] May need to mock time for deterministic tests

### 10. Documentation
- [ ] Update docs/architecture/current/execution_model.md
- [ ] Update docs/architecture/current/resources.md
- [ ] Update CLAUDE.md references to ticks
- [ ] Update glossary (remove tick or mark deprecated)

### 11. Emergence Metrics (src/simulation/emergence_metrics.py)
- [ ] Remove tick-based analysis
- [ ] Use time windows for pattern detection

## What Stays

- RateTracker - rolling window rate limiting (already time-based)
- AgentLoop - autonomous continuous execution
- AgentLoopManager - manages multiple agent loops
- Timestamps on all events
- Checkpointing (converted to time-based)

## Migration Path

1. Tag current state: git tag tick-based-v1
2. Update config schema (tick -> seconds)
3. Update core world state
4. Update mint/auction system
5. Update runner
6. Update agents/prompts
7. Update tests
8. Update docs
9. Clean up dashboard

## Testing Strategy

- Unit tests: mock time.time() for determinism where needed
- Integration tests: use short durations (5-10 seconds)
- E2E tests: verify auctions work with wall-clock timing

## Rollback

```bash
# Full rollback
git checkout tick-based-v1

# Partial recovery (specific file)
git checkout tick-based-v1 -- src/world/world.py
```

## Files Affected

- src/config_schema.py (modify)
- config/config.yaml (modify)
- src/world/genesis/mint.py (modify)
- src/world/world.py (modify)
- src/simulation/runner.py (modify)
- src/world/ledger.py (modify)
- src/world/logger.py (modify)
- src/agents/state_store.py (modify)
- tests/integration/test_mint_auction.py (modify)
- tests/unit/test_mint_anytime.py (modify)
- tests/unit/test_world.py (modify)
- src/world/genesis/types.py (modify)
- docs/architecture/current/configuration.md (modify)
- docs/architecture/current/execution_model.md (modify)

## Notes

- This is a breaking change for any saved checkpoints
- Consider a checkpoint migration script or just accept old checkpoints won't load
- Auction timing will feel different - may need to tune default durations
- The --duration flag should accept formats like 60s, 5m, 1h
