# Gap 15: invoke() Genesis Support

**Status:** 📋 Planned (Post-V1)
**Priority:** Medium
**Blocked By:** None
**Blocks:** None

---

## Gap

**Current:** Genesis artifacts use separate method dispatch and cannot be invoked via executor's `invoke()`.

**Target:** Genesis artifacts invokable via same `invoke()` mechanism as user artifacts:
```python
invoke("genesis_mint", "bid", artifact_id, 100)  # Same as user artifacts
```

---

## Motivation

**Principle: Genesis artifacts have no special privilege** (Plan #39, ADR-0001).

Unifying invocation paths:
1. Reduces complexity
2. Ensures consistency
3. Treats genesis as cold-start convenience, not special entity

---

## Plan

### Phase 1: Register Genesis in ArtifactStore

1. Create wrapper `Artifact` for each `GenesisArtifact` with `executable=True`
2. Wrapper code dispatches to genesis methods
3. Register in artifact store during world init

### Phase 2: Unified invoke() Dispatch

1. Extend `invoke()` to handle method-based dispatch
2. For genesis: `invoke("genesis_mint", "bid", ...)` routes to `genesis_mint.methods["bid"]`
3. For user artifacts: existing behavior unchanged

### Phase 3: Deprecate Special Paths

1. Route `invoke_artifact()` through unified `invoke()`
2. Update agent prompts to new calling convention

---

## Required Tests

```
tests/unit/test_genesis_invoke.py::test_genesis_via_unified_invoke
tests/unit/test_genesis_invoke.py::test_method_dispatch
tests/unit/test_genesis_invoke.py::test_permissions_apply_to_genesis
```

---

## Verification

- [ ] `invoke("genesis_mint", "status")` works from artifact code
- [ ] Genesis appears in artifact store
- [ ] Tests pass
- [ ] Docs updated
