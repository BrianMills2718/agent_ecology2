# Plan #308: Wire Up Disconnected Features Found in Dead Code Audit

**Status:** 🟡 Proposed

## Background

A vulture-based dead code audit (Feb 2026) found that many "unused" methods aren't truly dead — they represent **built but disconnected features**. These methods were implemented, sometimes tested, but never wired into the call paths that agents or the runner actually use.

This plan tracks the HIGH and MEDIUM gaps. LOW items (truly dead code) were deleted separately. Dashboard items are tracked in Plan #307.

## HIGH — Functional Gaps

### 1. Agents can't update artifact metadata
- **Where:** `kernel_interface.py:966` — `update_artifact_metadata()` is fully implemented with permission checking and logging, but has zero call sites
- **Impact:** Escrow can't update `authorized_writer` after purchase (Plan #213). Agents can't update custom metadata on owned artifacts.
- **Fix:** Expose via `update_metadata` action type in action_executor.py

### 2. Agents can't discover mint tasks
- **Where:** `mint_tasks.py:240` — `get_available_tasks()` returns open tasks, never called
- **Impact:** Task-based mint system (Plan #269, marked "complete") has no agent-facing discovery. Agents are blind to available work.
- **Fix:** Expose via `query_kernel` with query_type `"mint_tasks"` (handler exists in kernel_queries.py but verify it calls get_available_tasks)

### 3. Model access quotas never refresh
- **Where:** `model_access.py:215` — `advance_window()` resets rate windows, never called
- **Impact:** If a per-agent model quota is depleted, it's depleted forever. Time-based quota refresh is broken.
- **Fix:** Call `advance_window()` from the simulation tick/runner at configured intervals

### 4. MCP bridge disconnected from bootstrap
- **Where:** `mcp_bridge.py:499` — `create_mcp_artifacts()` factory, never called from world init
- **Impact:** MCP config in config.yaml is non-functional. Agents can't use fetch/filesystem/web_search even when configured.
- **Fix:** Call factory from World.__init__ or genesis bootstrap, register resulting artifacts

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
