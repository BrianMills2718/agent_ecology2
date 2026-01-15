# Gap 15: invoke() Genesis Support

**Status:** ✅ Complete

**Verified:** 2026-01-15T09:16:20Z
**Verification Evidence:**
```yaml
completed_by: scripts/complete_plan.py
timestamp: 2026-01-15T09:16:20Z
tests:
  unit: 1402 passed, 7 skipped, 5 warnings in 19.94s
  e2e_smoke: PASSED (2.00s)
  e2e_real: PASSED (35.49s)
  doc_coupling: passed
commit: b2b6ce1
```
**Priority:** Medium
**Blocked By:** None
**Blocks:** None

---

## Gap

**Current:** Genesis artifacts use separate code path in `_execute_invoke()` - checked via `self.genesis_artifacts` dict before regular artifacts.

**Target:** Single unified invoke path - genesis artifacts stored in ArtifactStore like any other artifact.

---

## Motivation

**Principle: Genesis artifacts have no special privilege** (Plan #39, ADR-0001).

Unifying invocation paths:
1. Removes code smell (dual lookup paths)
2. Genesis artifacts appear in artifact store like any artifact
3. Single `_execute_invoke` code path with dispatch based on artifact type

---

## Plan

### Phase 1: Add genesis_methods to Artifact

1. Add optional `genesis_methods: dict[str, GenesisMethod] | None` field to Artifact class
2. Artifacts with this field use method dispatch instead of code execution

### Phase 2: Register Genesis in ArtifactStore

1. After creating GenesisArtifact instances, also create corresponding Artifact in store
2. Attach `genesis_methods` from GenesisArtifact to Artifact
3. Keep `self.genesis_artifacts` dict for direct references (GenesisMint.set_world() etc.)

### Phase 3: Unify _execute_invoke

1. Remove the `if artifact_id in self.genesis_artifacts` check at top
2. Look up from artifact store only
3. Check if artifact has `genesis_methods` - if so, use method dispatch; otherwise use code execution

---

## Required Tests

```
tests/unit/test_genesis_invoke.py::test_genesis_in_artifact_store
tests/unit/test_genesis_invoke.py::test_genesis_invoke_via_unified_path
tests/unit/test_genesis_invoke.py::test_user_artifact_invoke_unchanged
tests/unit/test_genesis_invoke.py::test_genesis_method_not_found
tests/unit/test_genesis_invoke.py::test_genesis_method_cost_charged
```

---

## Verification

- [ ] Genesis artifacts appear in `self.artifacts` store
- [ ] `_execute_invoke` has single lookup path
- [ ] All existing tests pass (no behavior change)
- [ ] New tests pass
- [ ] Docs updated
