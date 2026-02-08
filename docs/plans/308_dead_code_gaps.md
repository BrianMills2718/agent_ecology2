# Plan #308: Wire Up Disconnected Features Found in Dead Code Audit

**Status:** 🚧 In Progress

## Background

A vulture-based dead code audit (Feb 2026) found that many "unused" methods aren't truly dead — they represent **built but disconnected features**. These methods were implemented, sometimes tested, but never wired into the call paths that agents or the runner actually use.

This plan tracks the HIGH and MEDIUM gaps. LOW items (truly dead code) were deleted separately. Dashboard items are tracked in Plan #307.

## HIGH — Functional Gaps

### 1. ~~Agents can't update artifact metadata~~ — DONE
- **Implemented:** `update_metadata` action type added to actions.py, action_executor.py
- **Security:** Protected keys (`authorized_writer`, `authorized_principal`) guarded at executor level; kernel method stays unrestricted for escrow

### 2. ~~Agents can't discover mint tasks~~ — NOT A GAP
- **Finding:** Already fully wired via `query_kernel` with `query_type="mint_tasks"`. Handler at `kernel_queries.py:506` is complete. `get_available_tasks()` is unused because the handler reimplements with extra filtering (status param).

### 3. Model access quotas never refresh — DEFERRED
- **Where:** `model_access.py:215` — `advance_window()` resets rate windows, never called
- **Finding:** `ModelAccessManager` is fully built but 100% disconnected (zero production imports). `RateTracker` already handles time-based quota refresh via rolling windows. Needs design decision: is ModelAccessManager's value (per-model tradeable quotas) wanted, or is RateTracker sufficient?

### 4. MCP bridge disconnected from bootstrap — DEFERRED
- **Where:** `mcp_bridge.py:499` — `create_mcp_artifacts()` factory, never called from world init
- **Finding:** Factory + classes complete, config validates, but requires Node.js/npm and spawns subprocesses. Deferred due to external dependency risk and need for end-to-end testing.

## MEDIUM — Observability Gaps

### 5. Logger methods never called (ADR-0020 incomplete)
- `record_artifact_created()` — summary metrics always show 0
- `log_resource_consumed()` — renewable resource consumption invisible
- `log_resource_allocated()` — quota grants invisible
- `log_resource_spent()` — LLM budget spending invisible
- **Fix:** Add calls at appropriate points in action_executor.py, ledger.py, world.py

### 6. Error tracking infrastructure empty
- **Where:** `runner.py:290` — `_record_error()` exists with ErrorStats class but never fed data
- **Impact:** Error summary at simulation end is always empty. Agent failures are invisible.
- **Fix:** Call `_record_error()` from exception handlers in the agent loop

### 7. Incomplete index refactoring in ArtifactStore
- `_remove_from_index()` — never called on artifact deletion (stale index entries)
- `_update_index()` — logic duplicated inline in write() instead of calling this
- `get_artifact_size()` — logic duplicated inline in get_creator_usage()
- **Fix:** Wire extracted methods into their callers, remove inline duplication

## Non-Gaps (KEEP as-is)

### External capabilities system (Plan #300)
- `has_capability()`, `request_capability()`, `use_capability()` in kernel_interface.py
- `SingleCapabilityConfig`, `ExternalCapabilitiesConfig` in config_schema.py
- Complete feature (manager, handlers, kernel interface, tests) with no agent consumers yet
- **Decision:** Keep. Feature is waiting for use cases, not broken.

## Related
- Plan #307: Dashboard v1/v2 audit
- Plan #213: Escrow/transfer (needs update_artifact_metadata)
- Plan #269: Task-based mint (marked complete but missing discoverability)
- Plan #254: Genesis removal (MCP factory built here)
- ADR-0020: Event schema (logger gaps)
