# Plan 63: Artifact Dependencies (Composition)

**Status:** 📋 Planned
**Priority:** High
**Blocked By:** None
**Blocks:** Dashboard capital structure visualization

---

## Gap

**Current:** Artifacts cannot invoke other artifacts. Agents must manually orchestrate all calls. This prevents:
- Building composable services/pipelines
- True capital structure (A→B→C dependency chains)
- Encapsulation (hiding internal complexity)

**Target:** Artifacts can declare dependencies on other artifacts. When invoked, dependencies are resolved and injected into execution context.

**Why High:** Core to proving "capital structure emergence" — the spec's primary success metric. Without this, the dependency graph is always flat (agent→artifact only).

---

## Design

### Dependency Model: Declared, Not Runtime

Artifacts declare dependencies at creation time:

```python
artifact = {
    "id": "my_pipeline",
    "depends_on": ["helper_lib", "data_processor"],  # declared deps
    "code": """
def run(args, context):
    # context.dependencies contains resolved deps
    helper = context.dependencies["helper_lib"]
    result = helper.invoke("process", args["data"])
    return result
"""
}
```

### Key Properties

| Property | Design Choice | Rationale |
|----------|---------------|-----------|
| Declaration time | At artifact creation | Enables static validation, no runtime surprises |
| Cycle detection | At creation, reject cycles | Prevents infinite recursion |
| Permission model | Invoker must have access to deps | No privilege escalation |
| Resource attribution | Invoker pays for all nested calls | Simple, predictable |
| Depth limit | Configurable (default: 10) | Prevents deep chains |
| Genesis as deps | Allowed | Genesis artifacts are valid dependencies |
| Transitive deps | Allowed with depth limit | Deps can have deps |

### Permission Model

When Agent X invokes Artifact B which depends on A:
1. Check: Can X invoke B? (existing check)
2. Check: Can X invoke A? (new check for each dep)
3. If any dep denied → invocation fails with clear error

**No privilege escalation:** B cannot use A if its invoker can't.

### Deleted Dependency Handling

If a dependency is deleted after artifact creation:
- Invocation fails with clear error: "Dependency 'X' not found"
- Artifact itself remains valid (soft failure)
- Dashboard shows broken dependency link

### Dependency Resolution

```
Agent X invokes B
    ↓
Resolve B.depends_on: [A, C]
    ↓
Check permissions: X→A, X→C
    ↓
Create dependency wrappers
    ↓
Execute B with context.dependencies = {A: wrapper, C: wrapper}
    ↓
If B uses A: log "B invoked A" (nested invocation)
    ↓
Return result to X
```

---

## Plan

### Changes Required

| File | Change |
|------|--------|
| `src/world/artifacts.py` | Add `depends_on: list[str]` to Artifact dataclass |
| `src/world/executor.py` | Resolve deps, inject into context, track nested invocations |
| `src/world/world.py` | Cycle detection at artifact creation, depth validation |
| `src/world/kernel_interface.py` | Add dependency wrapper for sandboxed dep access |
| `config/schema.yaml` | Add `artifact_dependency_depth_limit` config |
| `src/agents/schema.py` | Update ACTION_SCHEMA for depends_on |
| `src/dashboard/server.py` | Add `/api/dependency-graph` endpoint |

### Steps

1. **Schema changes**
   - Add `depends_on: list[str] = []` to Artifact dataclass
   - Add config for depth limit (default: 10)

2. **Validation at creation**
   - Check all deps exist
   - Check no cycles (topological sort)
   - Check transitive depth limit not exceeded
   - Genesis artifacts allowed as deps

3. **Executor changes**
   - Before execution: resolve dependencies recursively
   - Permission check for each dep (invoker must have access)
   - Create callable wrappers that track invocations
   - Inject via `context.dependencies`

4. **Nested invocation tracking**
   - When dep wrapper is called, log nested invocation
   - Track: parent_artifact, child_artifact, method, invoker, tick, duration
   - Feed into invocation registry

5. **Dashboard integration**
   - New API endpoint: `/api/dependency-graph`
   - Return artifact→artifact edges from depends_on fields
   - Include runtime invocation counts
   - Calculate "depth" metric (longest chain)

---

## Required Tests

### New Tests (TDD)

| Test File | Test Function | What It Verifies |
|-----------|---------------|------------------|
| `tests/unit/test_artifact_deps.py` | `test_depends_on_field_exists` | Schema has field |
| `tests/unit/test_artifact_deps.py` | `test_create_with_dependencies` | Can create artifact with deps |
| `tests/unit/test_artifact_deps.py` | `test_cycle_detection_direct` | A→A rejected |
| `tests/unit/test_artifact_deps.py` | `test_cycle_detection_indirect` | A→B→A rejected |
| `tests/unit/test_artifact_deps.py` | `test_missing_dep_rejected` | Dep must exist at creation |
| `tests/unit/test_artifact_deps.py` | `test_depth_limit_enforced` | Too-deep chains rejected |
| `tests/unit/test_artifact_deps.py` | `test_genesis_as_dependency` | Genesis artifacts allowed as deps |
| `tests/integration/test_artifact_deps.py` | `test_invoke_with_deps` | Deps injected and callable |
| `tests/integration/test_artifact_deps.py` | `test_dep_permission_required` | Invoker needs dep access |
| `tests/integration/test_artifact_deps.py` | `test_nested_invocation_logged` | Dep usage tracked |
| `tests/integration/test_artifact_deps.py` | `test_dep_resource_attribution` | Invoker pays for dep calls |
| `tests/integration/test_artifact_deps.py` | `test_deleted_dep_fails_gracefully` | Clear error if dep deleted |
| `tests/integration/test_artifact_deps.py` | `test_transitive_deps` | A depends on B depends on C works |

### Existing Tests (Must Pass)

| Test Pattern | Why |
|--------------|-----|
| `tests/unit/test_executor.py` | Execution unchanged for dep-free artifacts |
| `tests/integration/test_escrow.py` | Genesis artifacts still work |
| `tests/integration/test_integration.py` | Full simulation unaffected |

---

## E2E Verification

| Scenario | Steps | Expected Outcome |
|----------|-------|------------------|
| Agent creates composable artifact | 1. Agent creates helper lib 2. Agent creates pipeline with depends_on=[helper] 3. Another agent invokes pipeline | Pipeline executes, uses helper, nested invocation logged |
| Capital structure forms | 1. Run simulation 2. Check dependency graph | Graph shows artifact→artifact edges, depth > 1 |

```bash
pytest tests/e2e/test_artifact_deps_e2e.py -v --run-external
```

---

## Verification

### Tests & Quality
- [ ] All required tests pass: `python scripts/check_plan_tests.py --plan 63`
- [ ] Full test suite passes: `pytest tests/`
- [ ] Type check passes: `python -m mypy src/ --ignore-missing-imports`
- [ ] E2E verification passes

### Documentation
- [ ] `docs/architecture/current/artifacts_executor.md` updated
- [ ] Doc-coupling check passes

### Completion Ceremony
- [ ] Plan file status → `✅ Complete`
- [ ] `plans/CLAUDE.md` index → `✅ Complete`
- [ ] Claim released
- [ ] Branch merged or PR created

---

## Notes

### Design Decisions

1. **Genesis artifacts as dependencies:** Yes — allows pipelines to use genesis_ledger, genesis_store, etc.

2. **Transitive dependencies:** Yes with depth limit — A can depend on B which depends on C. Depth limit (default 10) prevents pathological chains.

3. **Deleted dependency handling:** Invocation fails with clear error. Artifact remains valid but unusable until dep restored or artifact updated.

### Alternatives Considered

**Runtime invoke (rejected):**
- Artifact code calls `invoke("other", ...)` at runtime
- More flexible but: harder to validate, recursion risk, unpredictable costs
- Declared deps are simpler and match "observability" philosophy

**No dependencies (status quo):**
- Agents orchestrate everything
- Simple but prevents true capital structure
- Can't prove A→B→C emergence

### Future Extensions

1. **Version pinning:** `depends_on: ["helper@v2"]`
2. **Optional deps:** `optional_depends_on: ["cache"]` (uses if available)
3. **Lazy resolution:** Only resolve deps when actually accessed
4. **Dep interface validation:** Check dep has required methods before creation
5. **Dep substitution:** Allow invoker to override a dep with compatible replacement

### Relation to Governance

Artifact dependencies enable the "Capital Structure Tracking" metric from the governance spec:
- Dependency graph shows A→B→C chains
- "Depth" metric measures capital accumulation
- High-reuse artifacts visible as highly-depended-on nodes
