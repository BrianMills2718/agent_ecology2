# Plan #320: Log artifact reads and kernel query params

**Status:** ✅ Complete — PR #TBD

## Context

Plan #319 added thinking events — we can now see agent reasoning. But the simulation still has blind spots: **we can't see what agents read or what they search for**.

From a 120s simulation run:
- 37 `kernel_query` events logged — but with **empty params** (we can't see what agents searched for)
- 0 `artifact_read` events — agents ARE reading (their reasoning says `read_artifact("discourse_corpus")`) but reads produce **no typed event**
- `KernelState.read_artifact()` (used by code-based agents in the sandbox) has **zero logging**

The generic `action` event captures reads, but it truncates content to 1000 bytes and isn't consumed by analysis scripts for read-specific metrics. Meanwhile `artifact_written` gets its own typed event with full metadata.

## Design: Four Surgical Changes

### 1. Add `params` to `kernel_query` event (sandbox path)

**File:** `src/world/kernel_interface.py` — `KernelState.query()`

Added `"params": params or {}` to the existing `kernel_query` log call.

### 2. Add `kernel_query` event to action path

**File:** `src/world/action_executor.py` — `_execute_query_kernel()`

The action-based query path (`query_kernel` action type) went through `kernel_query_handler.execute()` directly, bypassing `kernel_interface.query()`. Added a `kernel_query` log call with params here too.

### 3. Add `artifact_read` typed event in `_execute_read()`

**File:** `src/world/action_executor.py`

Added `artifact_read` event on successful read with `artifact_id`, `principal_id`, `artifact_type`, `read_price_paid`, `scrip_recipient`, and `content_size`.

### 4. Add logging to `KernelState.read_artifact()`

**File:** `src/world/kernel_interface.py`

Sandbox reads don't go through `_execute_read()` so they need their own `artifact_read` log call. Same event schema for consistency.

## Files Modified

| File | Change |
|------|--------|
| `src/world/kernel_interface.py` | Add `params` to kernel_query log; add `artifact_read` log to `read_artifact()` |
| `src/world/action_executor.py` | Add `artifact_read` log to `_execute_read()`; add `kernel_query` log to `_execute_query_kernel()` |
| `docs/architecture/current/artifacts_executor.md` | Note read/query logging |
| `tests/unit/test_executor.py` | 3 tests: read event on success, query params included, no read event on not-found |

## Verification

- 1667 tests pass, 0 failures
- `artifact_read` event emitted on successful reads with correct fields
- `kernel_query` event includes params for both action and sandbox paths
- No `artifact_read` event on failed reads (not found)
