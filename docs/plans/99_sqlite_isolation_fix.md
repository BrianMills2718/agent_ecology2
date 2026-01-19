# Plan #99: SQLite Isolation Level Fix

**Status:** 🚧 In Progress
**Priority:** High
**Created:** 2026-01-19
**Blocked By:** None

## Problem

Plan #97 added retry logic for SQLite "database is locked" errors, but this treats the symptom, not the root cause. The actual problem is that **all connections use `isolation_level="IMMEDIATE"`**, which:

1. Acquires a RESERVED (exclusive write) lock immediately on connection
2. Applies to ALL operations, including read-only ones (`load()`, `list_agents()`)
3. Serializes all database access, defeating WAL mode's concurrency benefits

### Evidence

```python
# Current code (state_store.py:218-222)
conn = sqlite3.connect(
    str(self.db_path),
    timeout=timeout,
    isolation_level="IMMEDIATE",  # ← Problem: applied to reads too
)
```

With this configuration:
- 5 threads doing concurrent reads = **serialized** (one at a time)
- WAL mode's concurrent reader capability = **disabled**

### Impact

| Scenario | Current (Broken) | Expected (WAL) |
|----------|------------------|----------------|
| 4 concurrent reads | ~400ms (serialized) | ~10ms (parallel) |
| 4 concurrent writes | ~400ms | ~400ms (correct) |
| Read during write | Blocked | Concurrent |

The `test_concurrent_access` flakiness is a symptom of this misconfiguration.

## Solution

Separate read and write connection handling:

1. **Read operations** (`load`, `list_agents`): Use default isolation (DEFERRED) - no lock until write attempted
2. **Write operations** (`save`, `delete`, `clear`): Use IMMEDIATE to prevent deadlocks

### Design

```python
@contextmanager
def _connect_read(self) -> Iterator[sqlite3.Connection]:
    """Connection for read-only operations. Allows concurrent readers."""
    conn = sqlite3.connect(str(self.db_path), timeout=timeout)
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    try:
        yield conn
    finally:
        conn.close()

@contextmanager
def _connect_write(self) -> Iterator[sqlite3.Connection]:
    """Connection for write operations. Uses IMMEDIATE to prevent deadlocks."""
    conn = sqlite3.connect(
        str(self.db_path),
        timeout=timeout,
        isolation_level="IMMEDIATE",
    )
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    try:
        yield conn
    finally:
        conn.close()
```

### Why IMMEDIATE for Writes Only

Without IMMEDIATE on writes, this deadlock can occur:

```
Thread 1: BEGIN (deferred), SELECT → acquires SHARED lock
Thread 2: BEGIN (deferred), SELECT → acquires SHARED lock
Thread 1: INSERT → tries to upgrade to RESERVED, blocked by Thread 2's SHARED
Thread 2: INSERT → tries to upgrade to RESERVED, blocked by Thread 1's SHARED
→ DEADLOCK
```

With IMMEDIATE on writes:
```
Thread 1: BEGIN IMMEDIATE → acquires RESERVED lock
Thread 2: BEGIN IMMEDIATE → waits (no deadlock, just queuing)
```

Reads don't need IMMEDIATE because they never upgrade to write locks.

## Required Tests

```
tests/unit/test_state_store.py::TestConcurrentReads::test_concurrent_reads_are_parallel
tests/unit/test_state_store.py::TestConcurrentReads::test_read_during_write_succeeds
tests/unit/test_state_store.py::TestConcurrentReads::test_write_during_read_succeeds
tests/unit/test_state_store.py::TestAgentStateStore::test_concurrent_access (existing - should now pass reliably)
```

## Implementation Steps

1. Add `_connect_read()` context manager for read-only connections
2. Add `_connect_write()` context manager for write connections (keeps IMMEDIATE)
3. Update `load()` to use `_connect_read()`
4. Update `list_agents()` to use `_connect_read()`
5. Update `save()`, `delete()`, `clear()` to use `_connect_write()`
6. Add new tests for concurrent read behavior
7. Verify `test_concurrent_access` passes reliably (10+ runs)
8. Remove or reduce retry parameters if no longer needed

## Acceptance Criteria

- [ ] Read operations use DEFERRED isolation (no IMMEDIATE)
- [ ] Write operations use IMMEDIATE isolation (prevents deadlocks)
- [ ] `test_concurrent_access` passes 10/10 runs
- [ ] New concurrent read tests pass
- [ ] No regression in existing tests

## Files Affected

- src/agents/state_store.py (modify)
- src/config_schema.py (modify)
- tests/unit/test_state_store.py (modify)
- docs/architecture/current/configuration.md (modify)
- config/config.yaml (modify)
- config/schema.yaml (modify)

## Performance Expectation

After fix:
- 4 workers reading different agents: **truly concurrent**
- 4 workers writing different agents: **still serialized** (SQLite limitation, acceptable)
- Mixed read/write workload: **readers don't block on writers** (WAL benefit)

## Related

- Plan #97: SQLite Concurrency Fix (added retry logic - treats symptom)
- Plan #53: Scalable Resource Architecture (introduced worker pool)
- ADR-0006: Minimal External Dependencies (documents SQLite → PostgreSQL path)
