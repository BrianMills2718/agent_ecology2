# Gap 81: Handbook Audit

**Status:** ✅ Complete

**Verified:** 2026-01-19T10:45:03Z
**Verification Evidence:**
```yaml
completed_by: scripts/complete_plan.py
timestamp: 2026-01-19T10:45:03Z
tests:
  unit: 1715 passed, 9 skipped, 3 warnings in 60.97s (0:01:00)
  e2e_smoke: PASSED (7.38s)
  e2e_real: PASSED (31.11s)
  doc_coupling: passed
commit: d38fe85
```

**Priority:** Medium
**Blocked By:** None
**Blocks:** Agent capability

---

## Gap

**Current:** Handbook documentation in `src/agents/_handbook/` is out of sync with actual genesis artifact implementations. Several methods are undocumented.

**Target:** Handbook accurately documents all genesis artifact methods with correct signatures.

**Why Medium:** Agents rely on handbook for learning the API. Missing methods means agents can't discover available functionality.

---

## References Reviewed

- `src/world/genesis/ledger.py` - Found undocumented methods: spawn_principal, transfer_budget, get_budget
- `src/world/genesis/store.py` - Found undocumented methods: list_principals, count
- `src/world/genesis/rights_registry.py` - Verified methods match docs
- `src/world/genesis/debt_contract.py` - Verified methods match docs
- `src/world/genesis/event_log.py` - Verified methods match docs
- `src/world/genesis/escrow.py` - Verified (defers to handbook_trading)
- `src/world/genesis/mint.py` - Verified (defers to handbook_mint)
- `src/agents/_handbook/genesis.md` - Current state of docs

---

## Files Affected

- src/agents/_handbook/genesis.md (modify)

---

## Plan

### Discrepancies Found

**genesis_ledger (handbook missing):**
| Method | Args | Cost | Description |
|--------|------|------|-------------|
| `spawn_principal` | `[]` | ? | Create new principal with 0 scrip/compute |
| `transfer_budget` | `[to_id, amount]` | ? | Transfer LLM budget |
| `get_budget` | `[agent_id]` | ? | Check LLM budget |

**genesis_store (handbook missing):**
| Method | Args | Cost | Description |
|--------|------|------|-------------|
| `list_principals` | `[]` | 0 | List all principals (has_standing=True) |
| `count` | `[filter?]` | 0 | Count artifacts matching filter |

### Steps

1. Update `genesis.md` to add missing ledger methods
2. Update `genesis.md` to add missing store methods
3. Verify costs from config.yaml

---

## Required Tests

### Existing Tests (Must Pass)

| Test Pattern | Why |
|--------------|-----|
| `tests/unit/test_genesis_*.py` | Genesis artifact behavior unchanged |
| `tests/integration/test_genesis_*.py` | Integration unchanged |

---

## Verification

### Tests & Quality
- [ ] Full test suite passes: `pytest tests/`
- [ ] Type check passes: `python -m mypy src/ --ignore-missing-imports`

### Documentation
- [ ] Handbook matches actual code
- [ ] All genesis methods documented

### Completion Ceremony
- [ ] Plan file status → `✅ Complete`
- [ ] `plans/CLAUDE.md` index → `✅ Complete`
- [ ] Claim released
- [ ] Branch merged or PR created

---

## Notes

This is a documentation-only change. No code modifications needed.
