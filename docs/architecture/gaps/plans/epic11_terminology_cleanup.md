# Epic 11: Terminology Cleanup

**Status:** 📋 Ready
**Priority:** Medium
**Epic:** 11
**Blocks:** Epic 12 (Per-Agent LLM Budget)
**Sub-gaps:** GAP-INFRA-015, GAP-INFRA-016, GAP-INFRA-017

---

## Problem

Current terminology is inconsistent and misleading:

| Location | Term | What It Actually Means |
|----------|------|------------------------|
| Config | `resources.flow.compute` | LLM token rate limit |
| Code | `llm_tokens` | LLM token rate limit |
| DESIGN_CLARIFICATIONS | `compute` | Local CPU capacity |

The word "compute" incorrectly suggests CPU usage when it actually tracks LLM API access rate.

---

## Target Terminology

From DESIGN_CLARIFICATIONS.md resource table:

| Term | Meaning | Type | Unit |
|------|---------|------|------|
| `llm_budget` | Real $ for API calls | Stock | USD |
| `llm_rate` | Rate-limited token access | Flow | tokens/sec |
| `compute` | Local CPU capacity | Flow (future) | CPU-units |
| `disk` | Storage quota | Stock | bytes |
| `scrip` | Internal currency | Currency | scrip |

---

## Implementation Steps

### Phase 1: Config Structure

**Before:**
```yaml
resources:
  stock:
    llm_budget: {total: 1.00, unit: dollars}
    disk: {...}
  flow:
    compute: {per_tick: 1000, unit: token_units}
```

**After:**
```yaml
resources:
  budget:
    max_api_cost_usd: 1.00

  rate_limits:
    llm:
      rate: 100          # tokens per second
      capacity: 1000     # max burst (token bucket)

  stock:
    disk:
      total: 50000
      unit: bytes

  # Future: when we track local CPU
  # flow:
  #   compute:
  #     rate: ...
  #     capacity: ...
```

### Phase 2: Code Cleanup

1. **Keep ledger's `llm_tokens`** - It's accurate (tracks token units)
2. **Remove deprecated wrappers:**
   - `get_compute()` → use `get_resource('llm_tokens')`
   - `spend_compute()` → use `spend_resource('llm_tokens')`
   - `reset_compute()` → remove (token bucket doesn't reset)
3. **Update comments** - Remove "compute" references to LLM

### Phase 3: Documentation

1. Update `docs/architecture/current/resources.md`
2. Update `docs/AGENT_HANDBOOK.md` if it references compute
3. Update `CLAUDE.md` terminology section

---

## Files Affected

| File | Change |
|------|--------|
| `config/config.yaml` | Restructure resources section |
| `config/schema.yaml` | Update schema to match |
| `src/config_schema.py` | Update Pydantic models |
| `src/world/ledger.py` | Remove deprecated compute methods |
| `src/simulation/runner.py` | Update resource initialization |
| `docs/architecture/current/resources.md` | Update terminology |

---

## Decisions

### Token Rate Only (2026-01-11)

Start with token rate tracking only. Add RPM (requests per minute) tracking later when scaling to 1000s of agents requires it.

**Rationale:** Small testing scale doesn't need RPM. Add complexity when scale demands it.

### Keep `llm_tokens` in Ledger

The ledger's internal name `llm_tokens` is accurate - it tracks token units. No need to rename to `llm_rate` internally; that's the config/conceptual name.

---

## Sub-gap Mapping

| Sub-gap | Description | This Plan Covers |
|---------|-------------|------------------|
| GAP-INFRA-015 | Rename flow→compute | Phase 1 config restructure |
| GAP-INFRA-016 | Rename stock→budget | Phase 1 config restructure |
| GAP-INFRA-017 | Update all references | Phase 2-3 code and docs |

---

## Testing

1. All existing tests should pass after rename
2. Add deprecation warnings to old method names
3. Verify config loading with new structure

---

## Acceptance Criteria

- [ ] Config uses new terminology structure
- [ ] No "compute" used to mean LLM tokens in code comments
- [ ] Documentation reflects correct terminology
- [ ] All 832+ tests still pass
- [ ] Deprecation warnings added for old method names
