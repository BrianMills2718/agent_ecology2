# Gap 7: Single ID Namespace

**Status:** ✅ Complete

**Verified:** 2026-01-16T14:01:34Z
**Verification Evidence:**
```yaml
completed_by: scripts/complete_plan.py
timestamp: 2026-01-16T14:01:34Z
tests:
  unit: 1405 passed, 7 skipped in 18.88s
  e2e_smoke: PASSED (1.56s)
  e2e_real: PASSED (5.63s)
  doc_coupling: passed
commit: 80f6a29
```
**Priority:** Low
**Blocked By:** None
**Blocks:** None

---

## Gap

**Current:** Separate tracking for principals vs artifacts allows ID collisions.

**Target:** Single namespace where every ID is unique across all entity types.

---

## Motivation

With "everything is an artifact" (ADR-0001), the distinction between principals and artifacts blurs. An agent IS an artifact. Having separate namespaces:
1. Creates collision risk
2. Requires type-checking before lookups
3. Complicates references

---

## Plan

### Phase 1: Unified ID Registry ✅

1. Create single `id_registry` in world state → `src/world/id_registry.py`
2. All IDs (agents, artifacts, principals) registered here
3. Registration fails if ID exists → `IDCollisionError`

### Phase 2: Migration (Partial)

1. Agents stored in artifact store (already partially true via `create_agent_artifact()`)
2. Principal tracking becomes artifact metadata (`has_standing=True`) - existing
3. Ledger references by ID only, no type assumption - existing

### Phase 3: Collision Prevention ✅

1. ID generation includes type prefix for readability but uniqueness is global
2. Lookup by ID returns entity regardless of type → `IDRegistry.lookup()`

---

## Implementation Details

**New Files:**
- `src/world/id_registry.py` - IDRegistry class with collision detection

**Modified Files:**
- `src/world/artifacts.py` - ArtifactStore now accepts optional IDRegistry
- `src/world/ledger.py` - Ledger now accepts optional IDRegistry
- `src/world/world.py` - World creates IDRegistry and injects it

**Key Classes:**
- `IDRegistry` - Central registry for global ID uniqueness
- `IDCollisionError` - Raised when attempting to register duplicate ID

**Entity Types:**
- `"agent"` - Autonomous agents
- `"artifact"` - Data/executable artifacts
- `"principal"` - Ledger principals
- `"genesis"` - Genesis artifacts

---

## Required Tests

### New Tests (TDD)

| Test File | Test Function | What It Verifies |
|-----------|---------------|------------------|
| `tests/unit/test_id_registry.py` | `test_no_duplicate_ids` | Same ID cannot be registered twice |
| `tests/unit/test_id_registry.py` | `test_lookup_by_id_only` | Lookup works by ID regardless of type |
| `tests/unit/test_id_registry.py` | `test_agent_is_artifact` | Agents stored as artifacts |
| `tests/unit/test_id_registry.py` | `test_artifact_cannot_use_principal_id` | Cross-system collision prevention |
| `tests/unit/test_id_registry.py` | `test_new_artifact_gets_registered` | New artifacts registered in namespace |

---

## Verification

- [x] No ID collisions possible (via IDRegistry checks)
- [x] Single lookup mechanism works (`IDRegistry.lookup()`)
- [x] Tests pass (16 tests in test_id_registry.py)
- [x] Docs updated (plan file)

---

## Notes

Low priority cleanup for architectural purity. Implemented Phase 1 and Phase 3.
Phase 2 migration is already partially complete via existing `has_standing` pattern.
