# Plan #124: Config Documentation Sync

**Status:** ✅ Complete
**Priority:** **High**
**Blocked By:** None
**Blocks:** None

---

## Gap

**Current:** Multiple inconsistencies between config files and documentation:

1. **Cost mismatch:** `debt_contract.accept()` costs 0 in `config.yaml:168` but 1 in `genesis_artifacts.md:147`
2. **MCP undocumented:** `config.yaml` has full MCP section (lines 222+) but `schema.yaml` has zero MCP documentation
3. **Missing checkpoint docs:** `checkpoint_interval` and `checkpoint_on_end` in config but not schema
4. **Unit mismatch:** `active_agent_threshold_seconds` in config vs `_ticks` in schema
5. **Stale schema:** Schema still documents removed `resources.flow` section
6. **Missing option:** `require_interface_for_executables` in schema but not config

**Target:** All configuration options documented in schema, all costs match between config and docs.

**Why High:** Confusing for users and agents reading config; can lead to incorrect assumptions.

---

## References Reviewed

- `config/config.yaml` - Full configuration
- `config/schema.yaml` - Schema documentation
- `docs/architecture/current/genesis_artifacts.md` - Genesis artifact docs
- `docs/architecture/current/configuration.md` - Config overview

---

## Files Affected

- config/schema.yaml (modify)
- config/config.yaml (modify)
- docs/architecture/current/genesis_artifacts.md (modify)

---

## Plan

### Changes Required
| File | Change |
|------|--------|
| `config/config.yaml:168` | Verify `accept` cost matches design intent |
| `docs/architecture/current/genesis_artifacts.md:147` | Update to match actual config |
| `config/schema.yaml` | Add MCP section documentation |
| `config/schema.yaml` | Add `checkpoint_interval`, `checkpoint_on_end` |
| `config/schema.yaml` | Fix `active_agent_threshold` naming |
| `config/schema.yaml` | Remove stale `resources.flow` section |
| `config/config.yaml` | Add `require_interface_for_executables` if needed |

### Steps

1. **Fix debt_contract.accept cost:**
   - Review design intent in Plan #9
   - Update doc or config to match (likely doc should say 0)

2. **Document MCP in schema:**
   ```yaml
   mcp:
     fetch:
       enabled: <bool>     # Enable HTTP fetch capability
       command: <string>   # Command to run MCP server
       args: <list>        # Arguments for command
     web_search:
       enabled: <bool>     # Enable Brave web search
       command: <string>
       args: <list>
     filesystem:
       enabled: <bool>     # Enable sandboxed file I/O
       command: <string>
       args: <list>
   ```

3. **Add missing checkpoint options to schema**

4. **Fix threshold naming inconsistency:**
   - Standardize on `_seconds` (what config uses)
   - Update schema to match

5. **Remove stale flow resources from schema**

---

## Required Tests

### New Tests (TDD)

| Test File | Test Function | What It Verifies |
|-----------|---------------|------------------|
| `tests/unit/test_config_schema.py` | `test_mcp_config_documented` | MCP options in schema |
| `tests/unit/test_config_schema.py` | `test_checkpoint_config_documented` | Checkpoint options in schema |

### Existing Tests (Must Pass)

| Test Pattern | Why |
|--------------|-----|
| `tests/unit/test_config*.py` | Config validation unchanged |

---

## E2E Verification

Not needed - documentation-only changes.

---

## Verification

### Tests & Quality
- [x] All tests pass: `pytest tests/` (config schema tests: 18 passed)
- [x] Schema validates against config: schema matches actual config structure

### Documentation
- [x] Doc-coupling check passes: `python scripts/check_doc_coupling.py`
- [x] All config options documented in schema
- [x] Costs match between config and docs

### Completion Ceremony
- [x] Plan file status → `✅ Complete`
- [x] `plans/CLAUDE.md` index → `✅ Complete`

### Completion Evidence
- **PR:** #440 - Merged 2026-01-20

---

## Notes
Documentation drift is common as features are added. This plan consolidates multiple small inconsistencies into one fix.
