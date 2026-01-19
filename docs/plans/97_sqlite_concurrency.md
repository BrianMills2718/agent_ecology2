# Plan #97: SQLite Concurrency Fix

**Status:** 📋 Planned
**Priority:** High
**Created:** 2026-01-19

## Problem

`AgentStateStore` uses SQLite for agent state persistence but has no retry logic for transient lock errors. When multiple worker threads access the database concurrently (via `WorkerPool`), SQLite can throw `OperationalError('database is locked')` if the configured timeout (30s) is exceeded under heavy contention.

This is a **production bug** - agent turns can fail intermittently under load.

### Evidence

The test `tests/unit/test_state_store.py::TestAgentStateStore::test_concurrent_access` correctly identifies this issue and fails intermittently in CI with:
```
AssertionError: Workers had errors: [OperationalError('database is locked')]
```

### Root Cause Analysis

1. `WorkerPool` uses `ThreadPoolExecutor` to run agent turns in parallel
2. Each worker creates its own `AgentStateStore` instance pointing to the same SQLite file
3. SQLite's WAL mode helps but doesn't eliminate lock contention
4. When locks are held longer than timeout, SQLite throws instead of retrying
5. The `save()` method has no retry logic for transient errors

## Solution

Add retry logic with exponential backoff to `AgentStateStore` operations that can encounter transient lock errors.

### Design

1. **Retry wrapper** - Create a decorator/helper for retrying on `sqlite3.OperationalError` when the error message contains "database is locked"
2. **Configurable retry parameters**:
   - `max_retries`: Maximum retry attempts (default: 5)
   - `base_delay`: Initial backoff delay in seconds (default: 0.1)
   - `max_delay`: Maximum backoff delay cap (default: 5.0)
3. **Apply to write operations** - `save()`, `delete()`, `clear()`
4. **Optional: Apply to reads** - Though WAL mode should handle concurrent reads, edge cases exist

### Configuration

Add to `config/schema.yaml` under `timeouts`:
```yaml
state_store_retry_max: <int>      # Max retry attempts (default: 5)
state_store_retry_base: <number>  # Base backoff delay seconds (default: 0.1)
state_store_retry_max_delay: <number>  # Max backoff delay seconds (default: 5.0)
```

## Required Tests

```
tests/unit/test_state_store.py::TestRetryLogic::test_retries_on_database_locked
tests/unit/test_state_store.py::TestRetryLogic::test_gives_up_after_max_retries
tests/unit/test_state_store.py::TestRetryLogic::test_exponential_backoff_timing
tests/unit/test_state_store.py::TestRetryLogic::test_passes_through_other_errors
tests/unit/test_state_store.py::TestAgentStateStore::test_concurrent_access (existing - should now pass reliably)
```

## Implementation Steps

1. Add retry configuration to `config/schema.yaml` and `config/config.yaml`
2. Create retry helper function in `src/agents/state_store.py`
3. Apply retry logic to `save()`, `delete()`, and `clear()` methods
4. Add unit tests for retry behavior
5. Verify `test_concurrent_access` passes reliably (run 10+ times)
6. Update module docstring to document retry behavior

## Acceptance Criteria

- [ ] `test_concurrent_access` passes reliably (no flaky failures)
- [ ] New retry tests pass
- [ ] Retry parameters are configurable via config
- [ ] Errors other than "database is locked" are not retried
- [ ] Logging shows retry attempts for debugging

## Files to Modify

- `src/agents/state_store.py` - Add retry logic
- `config/schema.yaml` - Add retry config options
- `config/config.yaml` - Add default values
- `tests/unit/test_state_store.py` - Add retry tests

## Related

- `WorkerPool` in `src/simulation/pool.py` - Creates concurrent access pattern
- `Ledger` in `src/world/ledger.py` - Has async locks, could inform pattern
