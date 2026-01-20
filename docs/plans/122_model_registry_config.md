# Plan #122: Model Registry Config Fix

**Status:** ✅ Complete

**Verified:** 2026-01-20T13:22:33Z
**Verification Evidence:**
```yaml
completed_by: scripts/complete_plan.py
timestamp: 2026-01-20T13:22:33Z
tests:
  unit: 1892 passed, 10 skipped, 3 warnings in 65.24s (0:01:05)
  e2e_smoke: skipped (--skip-e2e)
  e2e_real: skipped (--skip-real-e2e)
  doc_coupling: passed
commit: e1fd626
```
**Priority:** **Critical**
**Blocked By:** None
**Blocks:** None

---

## Gap

**Current:** `genesis_model_registry` is implemented in `src/world/genesis/model_registry.py` and documented in `docs/architecture/current/genesis_artifacts.md`, but:
- `config/config.yaml` has no `model_registry` entry in `genesis.artifacts:`
- `config/schema.yaml` has no schema definition for `genesis.artifacts.model_registry`

The factory in `src/world/genesis/factory.py:146-148` tries to access `cfg.artifacts.model_registry.enabled`, which will crash with missing config.

**Target:** Add proper configuration entries for model_registry in both config files.

**Why Critical:** Will cause runtime crash when config validator tries to access undefined configuration path.

---

## References Reviewed

- `src/world/genesis/model_registry.py` - Implementation exists
- `src/world/genesis/factory.py:146-148` - Factory tries to create if enabled
- `config/config.yaml` - Missing entry
- `config/schema.yaml` - Missing schema
- `docs/architecture/current/genesis_artifacts.md:212-231` - Documented but not configurable

---

## Files Affected

- `config/config.yaml` (modify)
- `config/schema.yaml` (modify)

---

## Plan

### Changes Required
| File | Change |
|------|--------|
| `config/config.yaml` | Add `model_registry:` entry under `genesis.artifacts:` |
| `config/schema.yaml` | Add schema for `genesis.artifacts.model_registry` |

### Steps
1. Add to `config/config.yaml` under `genesis.artifacts:`:
   ```yaml
   model_registry:
     enabled: true
   ```

2. Add to `config/schema.yaml` under appropriate section:
   ```yaml
   model_registry:
     enabled: <bool>  # Enable genesis_model_registry artifact (Plan #113)
   ```

3. Verify factory code handles the config correctly

---

## Required Tests

### New Tests (TDD)

| Test File | Test Function | What It Verifies |
|-----------|---------------|------------------|
| `tests/unit/test_genesis_factory.py` | `test_model_registry_created_when_enabled` | Registry created when config enabled |
| `tests/unit/test_genesis_factory.py` | `test_model_registry_not_created_when_disabled` | Registry skipped when disabled |

### Existing Tests (Must Pass)

| Test Pattern | Why |
|--------------|-----|
| `tests/unit/test_model_registry.py` | Model registry tests |
| `tests/unit/test_genesis*.py` | Genesis artifact tests |

---

## E2E Verification

| Scenario | Steps | Expected Outcome |
|----------|-------|------------------|
| Model registry available | 1. Run simulation 2. Check genesis artifacts | `genesis_model_registry` appears in artifact list |

---

## Verification

### Tests & Quality
- [ ] New tests pass: `pytest tests/unit/test_genesis_factory.py -v`
- [ ] All existing tests pass: `pytest tests/`
- [ ] Type check passes: `python -m mypy src/ --ignore-missing-imports`

### Documentation
- [ ] Config schema documented

### Completion Ceremony
- [ ] Plan file status → `✅ Complete`
- [ ] `plans/CLAUDE.md` index → `✅ Complete`

---

## Notes
This config entry was apparently missed when Plan #113 (Contractable Model Access) was implemented. The implementation exists but the config enabling it was never added.
