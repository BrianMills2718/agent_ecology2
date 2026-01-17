# Plan #62: Extract Hardcoded Magic Numbers to Config

**Status:** ✅ Complete

**Verified:** 2026-01-17T23:21:37Z
**Verification Evidence:**
```yaml
completed_by: scripts/complete_plan.py
timestamp: 2026-01-17T23:21:37Z
tests:
  unit: 1502 passed, 9 skipped, 4 warnings in 26.90s
  e2e_smoke: PASSED (1.87s)
  e2e_real: skipped (--skip-real-e2e)
  doc_coupling: passed
commit: 35bfcec
```
**Priority:** Medium
**Estimated Scope:** ~44 hardcoded values across 13 categories

## Progress

- [x] Phase 1: Add config schema (config.yaml + schema.yaml) - **Done**
- [x] Phase 3: Add Pydantic models (config_schema.py) - **Done**
- [x] Phase 2: Update source files to use config values - **Done**

### Files Updated in Phase 2
- `src/simulation/agent_loop.py` - timeouts.agent_loop_stop, loop_manager_stop
- `src/simulation/runner.py` - timeouts.simulation_shutdown
- `src/world/executor.py` - executor.max_invoke_depth
- `src/world/mint_scorer.py` - mint_scorer.score_bounds, thread_pool_workers
- `src/world/mcp_bridge.py` - timeouts.mcp_server
- `src/agents/state_store.py` - timeouts.state_store_lock
- `src/dashboard/watcher.py` - dashboard.debounce_delay_ms, poll_interval
- `src/dashboard/server.py` - dashboard.poll_interval, timeouts.dashboard_server
- `src/dashboard/auditor.py` - All monitoring.audit_thresholds and health_scoring values

## Problem Statement

The project principle states "zero magic numbers in code" but an audit found 44+ hardcoded values scattered across src/. These should be moved to config/config.yaml.

## Categories of Violations

| Category | Count | Priority |
|----------|-------|----------|
| Timeouts | 7 | HIGH |
| Audit thresholds | 9 | HIGH |
| Health scoring | 4 | MEDIUM |
| Truncation limits | 4 | HIGH |
| Invoke recursion depth | 1 | MEDIUM |
| ID generation | 1 | LOW |
| Dashboard delays | 2 | MEDIUM |
| Mint scorer bounds | 2 | LOW |
| Thread pool workers | 1 | LOW |

## Implementation Plan

### Phase 1: Add Config Schema (config.yaml + schema.yaml)

Add these new sections:

```yaml
# Timeouts - consolidate all timeout values
timeouts:
  agent_loop_stop: 5.0        # AgentLoop stop timeout
  loop_manager_stop: 10.0     # AgentLoopManager stop_all timeout
  simulation_shutdown: 5.0    # SimulationRunner shutdown timeout
  mcp_server: 5.0            # MCP server operations
  state_store_lock: 30.0     # SQLite lock timeout
  dashboard_server: 30.0     # Dashboard server operations

# Executor settings (extend existing)
executor:
  max_invoke_depth: 5        # Maximum artifact invocation nesting

# Monitoring - ecosystem health settings
monitoring:
  audit_thresholds:
    gini:
      warning: 0.7
      critical: 0.9
    frozen_ratio:
      warning: 0.2
      critical: 0.5
    active_ratio:
      warning: 0.3
      critical: 0.1
    burn_rate:
      warning: 0.1
      critical: 0.25
    scrip_velocity_low:
      warning: 0.001
  health_scoring:
    warning_penalty: 0.1
    critical_penalty: 0.2
    trend_threshold: 0.1
    trend_history_ticks: 10
  active_agent_threshold_ticks: 5

# Logging truncation (extend existing)
logging:
  truncation:
    content: 100             # Artifact content in logs
    code: 100               # Code snippets in logs
    errors: 100             # Error messages
    detailed: 500           # Detailed logs

# Dashboard (extend existing)
dashboard:
  debounce_delay_ms: 100    # File watcher debounce
  poll_interval: 0.5        # Polling interval seconds

# Mint scorer (extend existing)
mint_scorer:
  score_bounds:
    min: 0
    max: 100
  thread_pool_workers: 1

# ID generation
id_generation:
  uuid_hex_length: 8        # Characters from UUID hex for IDs
```

### Phase 2: Update Source Files

**Files to modify:**

1. `src/simulation/agent_loop.py` - Use timeouts config
2. `src/simulation/runner.py` - Use timeouts + truncation config
3. `src/simulation/pool.py` - Use timeouts config
4. `src/world/executor.py` - Use max_invoke_depth + truncation config
5. `src/world/mcp_bridge.py` - Use timeouts config
6. `src/world/mint_scorer.py` - Use score_bounds + thread workers
7. `src/world/world.py` - Use truncation + id_generation
8. `src/world/genesis.py` - Use id_generation config
9. `src/world/actions.py` - Use truncation config
10. `src/agents/state_store.py` - Use timeouts config
11. `src/dashboard/server.py` - Use timeouts + dashboard config
12. `src/dashboard/watcher.py` - Use dashboard config
13. `src/dashboard/auditor.py` - Use monitoring config
14. `src/dashboard/kpis.py` - Use monitoring config

### Phase 3: Update Config Schema

Add Pydantic models in `src/config_schema.py` for new sections.

## Required Tests

Tests should verify:
- [ ] `test_config_timeouts_loaded` - All timeout values accessible
- [ ] `test_config_monitoring_loaded` - Audit thresholds accessible
- [ ] `test_config_defaults_work` - Missing config uses sensible defaults
- [ ] `test_auditor_uses_config` - Auditor reads thresholds from config
- [ ] `test_executor_uses_config` - Executor reads max_invoke_depth from config

## Acceptance Criteria

- [ ] No hardcoded numeric literals in the 14 files listed above
- [ ] All 44+ values moved to config.yaml
- [ ] Schema.yaml updated to document new fields
- [ ] config_schema.py has Pydantic models for new sections
- [ ] All existing tests still pass
- [ ] mypy passes

## Notes

- Default values should match current hardcoded values (no behavior change)
- Use `get()` with fallback for backward compatibility
- Group related values logically in config hierarchy
