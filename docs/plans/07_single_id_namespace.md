# Gap 7: Single ID Namespace

**Status:** 📋 Planned (Post-V1)
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

### Phase 1: Unified ID Registry

1. Create single `id_registry` in world state
2. All IDs (agents, artifacts, principals) registered here
3. Registration fails if ID exists

### Phase 2: Migration

1. Agents stored in artifact store (already partially true)
2. Principal tracking becomes artifact metadata (`has_standing=True`)
3. Ledger references by ID only, no type assumption

### Phase 3: Collision Prevention

1. ID generation includes type prefix for readability but uniqueness is global
2. Lookup by ID returns entity regardless of type

---

## Required Tests

```
tests/unit/test_id_namespace.py::test_no_duplicate_ids
tests/unit/test_id_namespace.py::test_lookup_by_id_only
tests/unit/test_id_namespace.py::test_agent_is_artifact
```

---

## Verification

- [ ] No ID collisions possible
- [ ] Single lookup mechanism works
- [ ] Tests pass
- [ ] Docs updated

---

## Notes

Low priority cleanup for architectural purity.
