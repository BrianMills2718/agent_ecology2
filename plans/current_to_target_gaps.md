# Current Implementation to Target Architecture Gaps

> **⚠️ DEPRECATED:** This document has been migrated to:
> - **Gap tracking:** [docs/architecture/GAPS.md](../docs/architecture/GAPS.md)
>
> This file is kept for historical reference. Do not update.

---

This document tracks gaps between the current implementation and the target architecture described in `docs/DESIGN_CLARIFICATIONS.md`.

---

## Critical Gaps

### 1. ~~No `invoke()` in Executor~~ IMPLEMENTED

**Status**: DONE (CC-03, 2025-01-11)

**Implementation**:
- Added `execute_with_invoke()` method to `src/world/executor.py`
- Injects `invoke(artifact_id, *args)` function into execution namespace
- Returns `{"success": bool, "result": any, "error": str, "price_paid": int}`
- Original caller pays for all nested invocations
- Max recursion depth: 5 (configurable via `DEFAULT_MAX_INVOKE_DEPTH`)
- Updated `src/world/world.py` to use `execute_with_invoke()` for artifact execution
- Updated agent prompts with correct `invoke()` usage examples

---

### 2. Tick-Based Execution Model

**Current**: Agents execute in tick-synchronized rounds. `src/world/runner.py` loops through ticks, each agent acts once per tick.

**Target**: Agents run as continuous autonomous loops. Ticks are just metrics windows, not execution triggers.

**Impact**: Fast/efficient agents are held back by tick rate. Artificial constraint on productivity.

**Location**: `src/world/runner.py`, agent execution loop

**Proposed fix**: Refactor to continuous loops with async execution. Significant architectural change.

---

### 3. Flow Resource Refresh Model

**Current**: Compute refreshes discretely at tick boundaries (`per_tick: 1000` in config).

**Target**: Token bucket / rolling window. Continuous accumulation capped at max capacity.

**Impact**: Current model creates "spend before reset" pressure. Target model is smoother.

**Location**: `src/world/ledger.py`, resource management

**Proposed fix**: Implement token bucket algorithm with continuous accumulation.

---

### 4. Oracle Bidding Windows

**Current**: Config has `bidding_window: 10` and `first_auction_tick: 50`. Time-bounded bidding phases.

**Target**: Bids accepted anytime, oracle resolves on periodic schedule.

**Impact**: Agents must watch for window open/close. Target is simpler.

**Location**: `src/world/genesis.py` (GenesisOracle), `config/config.yaml`

**Proposed fix**: Remove bidding window concept. Accept bids anytime, resolve periodically.

---

## Documentation Gaps

### 5. ~~AGENT_HANDBOOK.md Errors~~ FIXED

**Status**: DONE (CC-03, 2025-01-11)

**Fixes applied**:
- Changed "LLM Tokens" to "LLM API $" (stock resource, never refreshes)
- Fixed recovery: "Frozen until you acquire from others"
- Fixed `run(*args)` signature (removed ctx param)
- Added "Trading Resources" section emphasizing tradeability
- Added invoke() composition documentation
- Updated failure states table
- Added author/date attribution
- Deprecated RESOURCE_MODEL.md with pointer to AGENT_HANDBOOK.md

**Location**: `docs/AGENT_HANDBOOK.md`

---

### 6. Config Terminology

**Current**: Uses "compute" as flow resource name with `per_tick` setting.

**Target**: Clearer distinction between:
- LLM API $ (stock, real dollars)
- LLM rate limit (flow, provider TPM/RPM)
- Compute (flow, local CPU)

**Location**: `config/config.yaml`, `config/schema.yaml`

---

## Minor Gaps

### 7. Time Injection

**Current**: Agents don't receive current timestamp in context.

**Target**: System injects timestamp into every LLM context for time-based coordination.

**Location**: Agent prompt construction

---

### 8. Agent Sleep (Self-Managed)

**Current**: No sleep mechanism.

**Target**: Agents can put themselves to sleep with wake conditions (duration, event, predicate).

**Location**: Not implemented

---

## Status

| Gap | Priority | Complexity | Status |
|-----|----------|------------|--------|
| invoke() in executor | High | Medium | **DONE** (CC-03) |
| Tick-based execution | High | High | Open |
| Flow resource model | Medium | Medium | Open |
| Oracle bidding | Medium | Low | Open |
| AGENT_HANDBOOK | Medium | Low | **DONE** (CC-03) |
| Config terminology | Low | Low | Open |
| Time injection | Low | Low | Open |
| Agent sleep | Low | Medium | Open |

---

## Notes

- CC-03 now maintaining this document (as of 2025-01-11)
- This document should be updated as gaps are closed
