# Gap 17: Agent Discovery

**Status:** ✅ Complete
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
| `list_agents()` | List all agent artifacts (has_standing=True AND can_execute=True) |
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

This gap was completed as a natural part of Gap #16 implementation. Since agents are artifacts with `has_standing=True` and `can_execute=True`, the unified artifact discovery system handles agent discovery automatically.
