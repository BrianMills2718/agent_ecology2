# Plan #308: Wire Up Disconnected Features Found in Dead Code Audit

**Status:** ✅ Complete

## Background

A vulture-based dead code audit (Feb 2026) found that many "unused" methods aren't truly dead — they represent **built but disconnected features**. These methods were implemented, sometimes tested, but never wired into the call paths that agents or the runner actually use.

This plan tracks the HIGH and MEDIUM gaps. LOW items (truly dead code) were deleted separately (PRs #1089, #1090). Dashboard items were resolved in Plan #307 (PR #1091).

## HIGH — Functional Gaps

### 1. ~~Agents can't update artifact metadata~~ — DONE
- **Implemented:** `update_metadata` action type added to actions.py, action_executor.py
- **Security:** Protected keys (`authorized_writer`, `authorized_principal`) guarded at executor level; kernel method stays unrestricted for escrow

### 2. ~~Agents can't discover mint tasks~~ — NOT A GAP
- **Finding:** Already fully wired via `query_kernel` with `query_type="mint_tasks"`. Handler at `kernel_queries.py:506` is complete. `get_available_tasks()` is unused because the handler reimplements with extra filtering (status param).

### 3. Model access quotas never refresh — DEFERRED
- **Where:** `model_access.py:215` — `advance_window()` resets rate windows, never called
- **Finding:** `ModelAccessManager` is fully built but 100% disconnected (zero production imports). `RateTracker` already handles time-based quota refresh via rolling windows.
- **Deferral rationale:** Needs design decision — is ModelAccessManager's value (per-model tradeable quotas) wanted, or is RateTracker sufficient? Not blocking any current work. Will revisit when per-agent rate allocation is implemented.

### 4. MCP bridge disconnected from bootstrap — DEFERRED
- **Where:** `mcp_bridge.py:499` — `create_mcp_artifacts()` factory, never called from world init
- **Finding:** Factory + classes complete, config validates, but requires Node.js/npm and spawns subprocesses.
- **Deferral rationale:** External dependency risk (Node.js/npm), needs dedicated E2E testing. Not blocking any current agent workflows.

## MEDIUM — Observability Gaps

### 5. Logger methods never called (ADR-0020 incomplete) — DEFERRED
- `record_artifact_created()` — summary metrics always show 0
- `log_resource_consumed()` — renewable resource consumption invisible
- `log_resource_allocated()` — quota grants invisible
- `log_resource_spent()` — LLM budget spending invisible
- **Deferral rationale:** Low impact — dashboard already reconstructs metrics from JSONL events. These logger calls would add redundant event types. Will wire when ADR-0020 compliance becomes a priority.

### 6. Error tracking infrastructure empty — DEFERRED
- **Where:** `runner.py:290` — `_record_error()` exists with ErrorStats class but never fed data
- **Impact:** Error summary at simulation end is always empty. Agent failures are invisible.
- **Deferral rationale:** Errors are already visible in JSONL logs and dashboard. The ErrorStats aggregation is convenience, not critical. Will wire when simulation observability is prioritized.

### 7. Incomplete index refactoring in ArtifactStore — DEFERRED
- `_remove_from_index()` — never called on artifact deletion (stale index entries)
- `_update_index()` — logic duplicated inline in write() instead of calling this
- `get_artifact_size()` — logic duplicated inline in get_creator_usage()
- **Deferral rationale:** Code duplication is minor (~10 lines each). Stale index entries don't cause bugs since queries filter by deletion status. Will clean up in next refactoring pass.

## Non-Gaps (KEEP as-is)

### External capabilities system (Plan #300)
- `has_capability()`, `request_capability()`, `use_capability()` in kernel_interface.py
- `SingleCapabilityConfig`, `ExternalCapabilitiesConfig` in config_schema.py
- Complete feature (manager, handlers, kernel interface, tests) with no agent consumers yet
- **Decision:** Keep. Feature is waiting for use cases, not broken.

## Completion Summary

| Item | Status | Resolution |
|------|--------|------------|
| 1. Metadata updates | ✅ Done | `update_metadata` action implemented |
| 2. Mint task discovery | ✅ Not a gap | Already wired via `query_kernel` |
| 3. Model access quotas | ⏸️ Deferred | Needs design decision (ModelAccessManager vs RateTracker) |
| 4. MCP bridge | ⏸️ Deferred | External dependency risk, needs E2E testing |
| 5. Logger methods | ⏸️ Deferred | Low impact, dashboard already has metrics |
| 6. Error tracking | ⏸️ Deferred | Errors visible in logs, aggregation is convenience |
| 7. Index refactoring | ⏸️ Deferred | Minor duplication, no functional bugs |

## Related
- Plan #307: Dashboard v1/v2 audit — ✅ Complete (PR #1091)
- PRs #1089, #1090: Dead code deletion (~4,460 lines)
- Plan #213: Escrow/transfer (needs update_artifact_metadata)
- Plan #254: Genesis removal (MCP factory built here)
- ADR-0020: Event schema (logger gaps)
