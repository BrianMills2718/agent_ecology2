# Gap 17: Agent Discovery

**Status:** ✅ Complete

**Verified:** 2026-01-13T18:30:38Z
**Verification Evidence:**
```yaml
completed_by: scripts/complete_plan.py
timestamp: 2026-01-13T18:30:38Z
tests:
  unit: 997 passed in 10.66s
  e2e_smoke: PASSED (2.00s)
  doc_coupling: passed
commit: d7ca40d
```
**Priority:** Medium
**Blocked By:** #16 (Complete)
**Blocks:** None

---

## Gap

**Current:** No way to discover other agents

**Target:** Discover agents via genesis_store (agents are artifacts)

---

## Implementation

**Implemented as part of Gap #16 (Artifact Discovery).**

The `genesis_store` artifact provides agent discovery via:

| Method | Description |
|--------|-------------|
| `list_agents()` | List all agent artifacts (has_standing=True AND has_loop=True) |
| `list_principals()` | List all principals (artifacts with has_standing=True) |

Agents can also use the general `list()` method with filters:
```python
# Find all agents
invoke("genesis_store", "list_agents", [])

# Find agents owned by a specific principal
invoke("genesis_store", "list", [{"type": "agent", "owner": "some_owner"}])

# Find all principals (includes agents + contracts with standing)
invoke("genesis_store", "list_principals", [])
```

---

## Verification

- [x] Tests pass (covered by test_genesis_store.py)
- [x] Docs updated (genesis_artifacts.md)
- [x] Implementation matches target

---

## Notes

This gap was completed as a natural part of Gap #16 implementation. Since agents are artifacts with `has_standing=True` and `has_loop=True`, the unified artifact discovery system handles agent discovery automatically.
