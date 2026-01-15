# Gap 7: Single ID Namespace

**Status:** 🚧 In Progress
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

```
tests/unit/test_id_registry.py::TestIDRegistry::test_no_duplicate_ids
tests/unit/test_id_registry.py::TestIDRegistry::test_lookup_by_id_only
tests/unit/test_id_registry.py::TestAgentIsArtifact::test_agent_is_artifact
tests/unit/test_id_registry.py::TestWorldIntegration::test_artifact_cannot_use_principal_id
tests/unit/test_id_registry.py::TestWorldIntegration::test_new_artifact_gets_registered
```

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
