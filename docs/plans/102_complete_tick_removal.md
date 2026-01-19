# Plan 102: Complete Tick Removal

**Status:** 🚧 In Progress

**Priority:** High
**Blocked By:** None
**Blocks:** Plan #101 (config cleanup depends on tick removal)

---

## Gap

**Current:** Plan #83 (Remove Tick-Based Execution) was marked complete but **434 tick references** remain in src/. Key tick-based code still exists:

- `_run_tick_based()` method in runner.py
- `advance_tick()` in world.py
- `per_tick` config fields
- `current_tick`, `max_ticks` throughout
- Dashboard tracks `last_action_tick`, `actions_per_tick`

**Target:** Zero tick-based code. Pure time-based/continuous execution model.

**Why:**
- Tick-based code anchors Claude Code to suggest tick-based solutions
- Real systems operate continuously, not in discrete ticks
- Simplifies mental model: everything is time-based

---

## Current State Analysis

```
Tick references in src/: 434
Key methods still present:
- src/simulation/runner.py:_run_tick_based()
- src/world/world.py:advance_tick()
- src/config.py:get_flow_resource(field="per_tick")
- src/dashboard/*:last_action_tick, actions_per_tick
```

---

## Changes Required

### 1. Remove Tick Execution Path (runner.py)

| Remove | Replace With |
|--------|--------------|
| `_run_tick_based()` method | Only autonomous execution |
| `--ticks N` CLI argument | `--duration 60s` or `--iterations N` |
| Tick-based progress display | Time-based progress |

### 2. Remove Tick State (world.py)

| Remove | Replace With |
|--------|--------------|
| `self.tick` counter | `self.start_time`, `self.elapsed_seconds` |
| `advance_tick()` method | N/A (continuous execution) |
| `max_ticks` config | `max_duration_seconds` or `max_iterations` |

### 3. Remove Tick Config (config.yaml, config_schema.py)

| Remove | Replace With |
|--------|--------------|
| `resources.flow.*.per_tick` | Remove flow section entirely (use rate_limiting) |
| `world.max_ticks` | `world.max_duration_seconds` |
| `monitoring.active_agent_threshold_ticks` | `monitoring.active_agent_threshold_seconds` |
| `budget.checkpoint_interval` (ticks) | Already time-based (keep) |

### 4. Update Dashboard (dashboard/)

| Change | From | To |
|--------|------|-----|
| `last_action_tick` | Tick number | `last_action_time` (ISO timestamp) |
| `actions_per_tick` | Actions/tick | `actions_per_minute` |
| `current_tick` display | Tick counter | Elapsed time |

### 5. Update Ledger (ledger.py)

| Remove | Replace With |
|--------|--------------|
| Tick-based balance check | Rate limiter check only |
| Tick-based balance refresh | N/A (RateTracker handles) |

### 6. Update Tests

- Replace `advance_tick()` calls with time-based or event-based assertions
- Mock `time.time()` for deterministic tests where needed
- Update assertions from tick counts to time durations

---

## Files Affected

- src/simulation/runner.py (modify - remove _run_tick_based)
- src/world/world.py (modify - remove tick state)
- src/config.py (modify - remove per_tick helpers)
- src/config_schema.py (modify - remove tick configs)
- config/config.yaml (modify - remove tick configs)
- src/world/ledger.py (modify - remove tick references)
- src/dashboard/server.py (modify)
- src/dashboard/kpis.py (modify)
- src/dashboard/models.py (modify)
- src/dashboard/parser.py (modify)
- src/dashboard/static/js/panels/events.js (modify - fix undefined display)
- src/dashboard/static/js/panels/progress.js (modify - show time not ticks)
- src/dashboard/static/js/panels/agents.js (modify - resource tracking)
- src/dashboard/static/js/panels/network.js (modify - include genesis)
- src/dashboard/dependency_graph.py (modify - fix timezone handling)
- tests/conftest.py (modify - remove max_ticks from fixtures)
- tests/unit/test_world.py (modify)
- tests/unit/test_runner.py (modify)
- tests/unit/test_runner_output.py (modify - update for autonomous-only mode)
- tests/integration/test_runner.py (modify)
- tests/integration/test_escrow.py (modify)
- tests/integration/test_debt_contract.py (modify)
- tests/integration/test_integration.py (modify)
- tests/integration/test_action_logging.py (modify)
- tests/integration/test_vulture_observability.py (modify)
- tests/integration/test_dashboard_api.py (modify)
- tests/integration/test_dashboard_kpis.py (modify)
- tests/unit/test_fixtures.py (modify)
- tests/unit/test_freeze_events.py (modify)
- tests/unit/test_kpis.py (modify)
- tests/unit/test_auditor.py (modify)
- tests/unit/test_kernel_interface.py (modify)
- tests/unit/test_dependency_graph.py (modify)
- tests/unit/test_config_schema.py (modify)
- Makefile (modify - add worktree protection)
- docs/architecture/current/execution_model.md (modify)
- docs/architecture/current/resources.md (modify)
- docs/architecture/current/supporting_systems.md (modify - doc coupling verification)
- docs/architecture/current/agents.md (modify - doc coupling verification)
- docs/architecture/current/configuration.md (modify - doc coupling verification)
- CLAUDE.md (modify - update terminology and add worktree exit rule)
- docs/GLOSSARY.md (modify - deprecate tick)

---

## Required Tests

### New Tests (TDD)

| Test File | Test Function | What It Verifies |
|-----------|---------------|------------------|
| `tests/unit/test_world.py` | `test_no_tick_attribute` | World has no tick counter |
| `tests/unit/test_runner.py` | `test_no_tick_based_method` | Runner has no _run_tick_based |
| `tests/unit/test_config.py` | `test_no_per_tick_config` | Config has no per_tick fields |

### Existing Tests (Must Pass)

| Test Pattern | Why |
|--------------|-----|
| `tests/e2e/test_smoke.py` | Simulation still works |
| `tests/e2e/test_real_e2e.py` | Real LLM integration works |
| `tests/integration/test_runner.py` | Runner orchestration works |

---

## Migration

### CLI Changes

```bash
# Old (remove)
python run.py --ticks 50

# New
python run.py --duration 5m
python run.py --iterations 50  # Optional: for deterministic runs
```

### Config Migration

```yaml
# Old (remove)
world:
  max_ticks: 100
resources:
  flow:
    compute:
      per_tick: 1000

# New
world:
  max_duration_seconds: 300  # 5 minutes
# flow section removed - use rate_limiting only
```

---

## Verification

- [ ] `grep -r "tick" src/ | wc -l` returns < 50 (only comments/docs)
- [ ] `grep -r "advance_tick\|per_tick\|_run_tick" src/` returns nothing
- [ ] All tests pass
- [ ] E2E smoke test passes
- [ ] Real E2E test passes

---

## Notes

- Plan #83 was marked complete prematurely - this plan finishes that work
- Breaking change for saved checkpoints (acceptable)
- Dashboard will show elapsed time instead of tick count
- `--duration` flag should accept formats: `60s`, `5m`, `1h`
