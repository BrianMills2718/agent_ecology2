# Gap 16: Artifact Discovery (genesis_store)

**Status:** ✅ Complete

**Verified:** 2026-01-13T18:30:11Z
**Verification Evidence:**
```yaml
completed_by: scripts/complete_plan.py
timestamp: 2026-01-13T18:30:11Z
tests:
  unit: 997 passed in 10.69s
  e2e_smoke: PASSED (1.98s)
  doc_coupling: passed
commit: d7ca40d
```
**Priority:** High
**Blocked By:** #6 (Complete)
**Blocks:** #17, #22

---

## Gap

**Current:** No programmatic way to discover artifacts. Agents see artifacts in world state but can't search/filter/browse them via invoke.

**Target:** `genesis_store` artifact with list/search/browse methods that agents can invoke.

**Why High Priority:** Agents need to discover what exists before they can trade, collaborate, or build on others' work. This is foundational for the emergent economy.

---

## Implementation

### GenesisStore Methods

| Method | Args | Cost | Description |
|--------|------|------|-------------|
| `list` | `[filter?]` | 0 | List artifacts with optional filter |
| `get` | `[artifact_id]` | 0 | Get single artifact details |
| `search` | `[query, field?, limit?]` | 0 | Search by content match |
| `list_by_type` | `[type]` | 0 | List artifacts of specific type |
| `list_by_owner` | `[owner_id]` | 0 | List artifacts by owner |
| `list_agents` | `[]` | 0 | List all agent artifacts |
| `list_principals` | `[]` | 0 | List all principals (agents + contracts with standing) |
| `count` | `[filter?]` | 0 | Count artifacts matching filter |

### Filter Object (for `list` and `count`)

```python
{
    "type": "agent" | "memory" | "data" | "executable" | "genesis",
    "owner": "owner_id",
    "has_standing": True | False,
    "can_execute": True | False,
    "limit": 100,
    "offset": 0
}
```

### Files Changed

| File | Change |
|------|--------|
| `src/world/genesis.py` | Added `GenesisStore` class |
| `src/config_schema.py` | Added `StoreConfig`, `StoreMethodsConfig` |
| `config/config.yaml` | Added `genesis.store` section |
| `config/schema.yaml` | Added `genesis.store` documentation |
| `docs/architecture/current/genesis_artifacts.md` | Documented genesis_store |

---

## Tests

All tests in `tests/test_genesis_store.py` (26 tests):
- List/filter/pagination tests
- Get/search tests
- Agent/principal listing tests
- Count tests
- Registration tests
- Method cost tests

---

## Design Decisions

1. **All methods cost 0** - Discovery is system-subsidized to encourage market formation
2. **Simple string search** - No vector/semantic search (that's agent-built capability)
3. **Returns dicts, not Artifacts** - Consistent with other genesis methods
4. **Pagination via limit/offset** - Scales with large artifact counts

---

## Completion

- [x] Config schema for genesis_store methods
- [x] GenesisStore class implementation
- [x] Registration in create_genesis_artifacts()
- [x] TDD tests (26 tests, all passing)
- [x] Documentation updated
- [x] Type check passes
