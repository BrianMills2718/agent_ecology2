# Plan 239: Fix Broken _execute_edit() and Related Bugs

**Status:** ✅ Complete
**Priority:** Critical
**Blocked By:** None
**Blocks:** None

---

## Gap

**Current:** Three confirmed bugs identified via cross-document audit:

1. **`_execute_edit()` completely broken** - The method in `action_executor.py` accesses `intent.content`, `intent.code`, `intent.executable`, `intent.price`, `intent.interface`, `intent.access_contract_id`, `intent.metadata` - none of which exist on `EditArtifactIntent` (which only has `artifact_id`, `old_string`, `new_string`). It also calls `w.artifacts.update()` which doesn't exist. Any agent sending `edit_artifact` would crash.

2. **`depends_on` split-brain** - `kernel_queries.py:472` queries `artifact.metadata.get("depends_on", [])` instead of `artifact.depends_on` field. The real field is on the Artifact dataclass at `artifacts.py:185`.

3. **Action type count mismatch** - `execution_model.md:48` says "6 Action Types" but `ActionType` enum has 11 values (noop, read, write, edit, invoke, delete, query_kernel, subscribe, unsubscribe, configure_context, modify_system_prompt).

**Target:** All three bugs fixed. `_execute_edit()` properly delegates to `ArtifactStore.edit_artifact()`. Dependencies query uses the correct field. Documentation reflects actual action count.

**Why Critical:** Bug #1 is a hard crash - edit_artifact is completely unusable. This action type exists in the narrow waist, is documented in agent handbooks, but will crash on any use.

---

## References Reviewed

- `src/world/action_executor.py:385-532` - Broken `_execute_edit()` implementation
- `src/world/actions.py:143-167` - `EditArtifactIntent` (only has artifact_id, old_string, new_string)
- `src/world/actions.py:76-106` - `WriteArtifactIntent` (has content, code, executable, etc.)
- `src/world/artifacts.py:1279-1354` - Working `ArtifactStore.edit_artifact()` method
- `src/world/artifacts.py:185` - `depends_on: list[str]` field on Artifact dataclass
- `src/world/kernel_queries.py:460-481` - `depends_on` query using metadata
- `src/world/actions.py:13-27` - ActionType enum with 11 values
- `docs/architecture/current/execution_model.md:48-60` - "6 Action Types" documentation
- `tests/unit/test_edit_artifact.py` - Existing tests for `ArtifactStore.edit_artifact()`
- `docs/plans/131_edit_artifact_action.md` - Original plan (shows intended design)

---

## Open Questions

### Resolved

1. [x] **Question:** Does `ArtifactStore.edit_artifact()` work correctly?
   - **Status:** ✅ RESOLVED
   - **Answer:** Yes - 11 passing tests in `tests/unit/test_edit_artifact.py`. The store-level method is correct; only the action_executor dispatch is broken.
   - **Verified in:** `src/world/artifacts.py:1279-1354`, `tests/unit/test_edit_artifact.py`

2. [x] **Question:** What should `_execute_edit()` actually do?
   - **Status:** ✅ RESOLVED
   - **Answer:** It should check permissions (genesis protection, kernel_protected, contract permission), then delegate to `w.artifacts.edit_artifact()` for the actual string replacement, then log the result. It should NOT try to do partial field updates.
   - **Verified in:** Plan #131 design, `EditArtifactIntent` class definition

3. [x] **Question:** Where is `depends_on` actually stored?
   - **Status:** ✅ RESOLVED
   - **Answer:** `artifact.depends_on` is a `list[str]` field on the Artifact dataclass (line 185). It is NOT in metadata.
   - **Verified in:** `src/world/artifacts.py:185`

---

## Files Affected

- `src/world/action_executor.py` (modify - rewrite `_execute_edit()`)
- `src/world/kernel_queries.py` (modify - fix `depends_on` query)
- `docs/architecture/current/execution_model.md` (modify - fix action count)
- `tests/unit/test_action_executor_edit.py` (create - integration test for `_execute_edit()` dispatch)

---

## Plan

### Changes Required

| File | Change |
|------|--------|
| `src/world/action_executor.py` | Rewrite `_execute_edit()` to use `old_string`/`new_string` and delegate to `ArtifactStore.edit_artifact()` |
| `src/world/kernel_queries.py` | Change `artifact.metadata.get("depends_on")` to `artifact.depends_on` |
| `docs/architecture/current/execution_model.md` | Update "6 Action Types" header and table to reflect all 11 |
| `tests/unit/test_action_executor_edit.py` | Test `_execute_edit()` through action executor |

### Steps

1. **Fix `_execute_edit()`** - Rewrite the method to:
   - Keep existing checks: artifact exists, genesis protection, kernel_protected, contract permission
   - Calculate size delta from old_string→new_string (not from non-existent fields)
   - Check disk quota if content grows
   - Delegate to `w.artifacts.edit_artifact(intent.artifact_id, intent.old_string, intent.new_string)`
   - Handle result (success/failure from edit_artifact)
   - Log the edit event
   - Return appropriate ActionResult

2. **Fix `depends_on` query** - Change line 472 from `artifact.metadata.get("depends_on", [])` to `artifact.depends_on`; same for dependents (line 473 - check if `dependents` is a field or correctly in metadata)

3. **Update execution_model.md** - Update the section header and table to list all 11 action types with their purpose

4. **Add integration tests** - Test `_execute_edit()` through the action executor to catch regressions

---

## Required Tests

### New Tests (TDD)

| Test File | Test Function | What It Verifies |
|-----------|---------------|------------------|
| `tests/unit/test_action_executor_edit.py` | `test_execute_edit_success` | edit_artifact through executor works |
| `tests/unit/test_action_executor_edit.py` | `test_execute_edit_not_found` | Fails for missing artifact |
| `tests/unit/test_action_executor_edit.py` | `test_execute_edit_genesis_protected` | Genesis artifacts blocked |
| `tests/unit/test_action_executor_edit.py` | `test_execute_edit_kernel_protected` | kernel_protected artifacts blocked |
| `tests/unit/test_action_executor_edit.py` | `test_execute_edit_old_string_not_found` | Fails when old_string not in content |
| `tests/unit/test_action_executor_edit.py` | `test_execute_edit_not_unique` | Fails when old_string appears multiple times |

### Existing Tests (Must Pass)

| Test Pattern | Why |
|--------------|-----|
| `tests/unit/test_edit_artifact.py` | ArtifactStore.edit_artifact() unchanged |
| `tests/unit/test_actions.py` | ActionIntent parsing unchanged |
| `tests/unit/test_kernel_protected.py` | kernel_protected checks preserved |

---

## E2E Verification

| Scenario | Steps | Expected Outcome |
|----------|-------|------------------|
| Edit artifact in simulation | Agent sends edit_artifact action | Content updated via string replacement (no crash) |

```bash
pytest tests/e2e/test_real_e2e.py -v --run-external
```

---

## Verification

### Tests & Quality
- [ ] All required tests pass: `python scripts/check_plan_tests.py --plan 239`
- [ ] Full test suite passes: `pytest tests/`
- [ ] Type check passes: `python -m mypy src/ --ignore-missing-imports`
- [ ] **E2E verification passes:** `pytest tests/e2e/test_real_e2e.py -v --run-external`

### Documentation
- [ ] `docs/architecture/current/execution_model.md` updated
- [ ] Doc-coupling check passes: `python scripts/check_doc_coupling.py`

### Completion Ceremony
- [ ] Plan file status -> `✅ Complete`
- [ ] `plans/CLAUDE.md` index -> `✅ Complete`
- [ ] Branch merged or PR created

---

## Notes

- The `_execute_edit()` method was likely copy-pasted from `_execute_write()` and adapted for a "partial field update" pattern, but `EditArtifactIntent` was designed for Claude Code-style string replacement (Plan #131). The two designs are incompatible.
- `ArtifactStore.edit_artifact()` already works correctly (11 passing tests). The fix is to properly delegate to it.
- The `dependents` field in kernel_queries.py (line 473) may also be wrong - need to check if it's a real field or only in metadata.
