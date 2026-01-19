# Plan 114: Interface Discovery

**Status:** 📋 Planned
**Priority:** High
**Blocked By:** None
**Blocks:** Emergent cross-agent collaboration

---

## Gap

**Current:** Artifacts have an `interface` field (Plan #14) with StructGPT-inspired schema (Plan #54), and interface validation works at invoke time (Plan #86). However, agents **cannot discover** artifact interfaces - `genesis_store.get()` and `genesis_store.list()` do not return the `interface` field.

**Target:** Agents can query artifact interfaces before invoking, enabling them to learn method signatures, input schemas, and usage examples.

**Evidence of Problem:**
- Simulation analysis: 74 cross-agent **reads** but 0% cross-agent **invokes**
- Agents discover artifacts exist but don't know how to call them
- Plan #14 Phase 4 explicitly marked as "future" and never implemented

---

## Problem Statement

The interface discovery gap creates a catch-22:
1. Agent A creates an artifact with a well-defined interface
2. Agent B discovers the artifact via `genesis_store.list()`
3. Agent B wants to invoke it but doesn't know the method signature
4. Agent B reads the artifact content, but that's the code, not the interface
5. Agent B either guesses wrong or gives up

This is blocking emergent cross-agent collaboration - agents can see each other's artifacts but can't figure out how to use them.

---

## Solution

### Phase 1: Expose Interface in Store Responses

Update `GenesisStore._artifact_to_dict()` to include the `interface` field:

```python
def _artifact_to_dict(self, artifact: Any) -> dict[str, Any]:
    result: dict[str, Any] = {
        "id": artifact.id,
        "type": artifact.type,
        "owner_id": artifact.owner_id,
        "content": artifact.content,
        "has_standing": artifact.has_standing,
        "can_execute": artifact.can_execute,
        "executable": artifact.executable,
        "interface": artifact.interface,  # ADD THIS
    }
    # ... rest unchanged
```

This immediately enables interface discovery via existing methods.

### Phase 2: Add Dedicated get_interface Method

Add `get_interface(artifact_id)` method to GenesisStore:

```python
def _get_interface(self, args: list[Any], invoker_id: str) -> dict[str, Any]:
    """Get interface schema for an artifact.

    Args: [artifact_id]
    Returns: {"success": True, "interface": {...}} or {"success": False, "error": "..."}
    """
    if not args:
        return {"success": False, "error": "get_interface requires [artifact_id]"}

    artifact_id = str(args[0])
    artifact = self.artifact_store.get(artifact_id)

    if not artifact:
        return {"success": False, "error": f"Artifact '{artifact_id}' not found"}

    return {
        "success": True,
        "artifact_id": artifact_id,
        "interface": artifact.interface,
        "executable": artifact.executable,
    }
```

Register in `__init__`:
```python
self.register_method(
    name="get_interface",
    handler=self._get_interface,
    cost=0,  # Free - encourage discovery
    description="Get interface schema for an artifact"
)
```

### Phase 3: Update Handbook

Add interface discovery guidance to the agent handbook:

```markdown
## Discovering How to Use Artifacts

Before invoking an artifact, query its interface:

1. **Quick check:** `genesis_store.get(artifact_id)` returns `interface` field
2. **Dedicated method:** `genesis_store.get_interface(artifact_id)`

The interface contains:
- `description`: What the artifact does
- `methods`: Available operations with `inputSchema`
- `examples`: Sample invocations
- `dataType`: Category hint (service, table, document)
```

---

## Files Affected

| File | Change |
|------|--------|
| `src/world/genesis/store.py` | Add `interface` to `_artifact_to_dict()`, add `get_interface()` method |
| `config/schema.yaml` | Add `get_interface` method config under `genesis.store.methods` |
| `src/config_schema.py` | Add `get_interface` to StoreMethodsConfig |
| `src/agents/_handbook/tools.md` | Add interface discovery guidance |
| `tests/unit/test_genesis_store.py` | Test interface exposure and get_interface method |
| `docs/architecture/current/genesis_artifacts.md` | Document new method |

---

## Required Tests

| Test | Description |
|------|-------------|
| `test_genesis_store.py::test_get_returns_interface` | `get()` includes interface field |
| `test_genesis_store.py::test_list_returns_interfaces` | `list()` includes interface fields |
| `test_genesis_store.py::test_get_interface_method` | Dedicated method works |
| `test_genesis_store.py::test_get_interface_not_found` | Returns error for missing artifact |
| `test_genesis_store.py::test_get_interface_null_interface` | Works when interface is None |

---

## Success Criteria

| Criterion | Measurement |
|-----------|-------------|
| Interface exposed in store responses | `genesis_store.get()` returns `interface` field |
| Dedicated method works | `genesis_store.get_interface()` returns interface |
| Handbook updated | Agents have guidance on discovery |
| Tests pass | All new tests green |
| Cross-agent invokes increase | Re-run simulation, measure invoke rate |

---

## Complexity & Risk

**Effort:** Small (S) - ~50-100 lines of code
**Risk:** Low - additive change, no breaking changes

---

## References

- Plan #14: Artifact Interface Schema (Phase 4 deferred)
- Plan #54: Interface Reserved Terms (StructGPT-inspired fields)
- Plan #86: Interface Validation
- `docs/architecture/current/artifacts_executor.md`: Interface schema documentation
- `docs/archive/agent_research_2026-01/prioritized_actions.md`: StructGPT pattern reference

---

## Notes

This completes Plan #14 Phase 4 which was explicitly marked as "future":
> `- [ ] Interface discoverable via genesis_store (Phase 4 - future)`

The StructGPT pattern (Read → Linearize → Reason → Iterate) is partially enabled by Plan #54's `linearization` field, but agents can't access it without interface discovery.
