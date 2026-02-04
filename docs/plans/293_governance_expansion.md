# Plan #293: Governance Expansion

**Status:** ✅ Complete

**Verified:** 2026-02-04T14:56:16Z
**Verification Evidence:**
```yaml
completed_by: scripts/complete_plan.py
timestamp: 2026-02-04T14:56:16Z
tests:
  unit: skipped (--status-only, CI-validated)
  e2e_smoke: skipped (--status-only, CI-validated)
  e2e_real: skipped (--status-only, CI-validated)
  doc_coupling: skipped (--status-only, CI-validated)
commit: 8110668
```
**Priority:** P2 - Process improvement
**Complexity:** XS

## Context

Plan #292 added enforcement for critical files. Analysis of remaining 41 unmapped files identified 10 that have significant architectural logic and should have ADR governance.

## Goal

Add governance mappings for 10 significant files, improving coverage from 52% to 64%.

## Files Added

### World Module (6 files)
- `kernel_queries.py` - Query interface (ADR-0019, ADR-0020)
- `mcp_bridge.py` - MCP integration (ADR-0001, ADR-0014)
- `model_access.py` - Model quotas (ADR-0002, ADR-0011, ADR-0023)
- `usage_tracker.py` - LLM tracking (ADR-0020, ADR-0023)
- `resource_metrics.py` - Metrics (ADR-0020)
- `mint_tasks.py` - Task-based mint (ADR-0004)

### Agents Module (3 files)
- `component_loader.py` - Prompt components (ADR-0013, ADR-0026)
- `hooks.py` - Workflow hooks (ADR-0013)
- `agent_schema.py` - Schema validation (ADR-0013, ADR-0026)

### Simulation Module (1 file)
- `supervisor.py` - Crash recovery (ADR-0010, ADR-0014)

## Files NOT Mapped (32 files)

Intentionally unmapped:
- 9 `__init__.py` files (package markers)
- 13 dashboard files (visualization only)
- 10 helper/utility files (errors, types, config, etc.)

## Acceptance Criteria

- [x] 10 significant files have governance mappings
- [x] Source coverage at 64%
- [ ] CI check passes
