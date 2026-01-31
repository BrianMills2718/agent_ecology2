# Plan 234: ADR-0024 Handle Request Migration

**Status:** 📋 Planned
**Priority:** Medium
**Blocked By:** None
**Blocks:** Full artifact autonomy, custom access control patterns

---

## Gap

**Current:** Kernel-mediated permission checking (ADR-0019 model)
- Kernel checks `access_contract_id` BEFORE artifact code runs
- Artifacts use `run(*args)` interface with `caller_id` injected as global
- Permission decisions happen outside artifact code
- Contracts are special artifacts the kernel executes

**Target:** Artifact self-handled access control (ADR-0024 model)
- Kernel routes requests to artifact's `handle_request(caller, operation, args)`
- Artifact code decides permissions (inline or delegated)
- Kernel only provides verified caller identity
- Contracts are just artifacts that others invoke

**Why Medium:** Current system is functional. This is an architectural improvement for flexibility, not a bug fix. However, the conceptual model describes this as the architecture, causing confusion.

---

## References Reviewed

- `docs/adr/0024-artifact-self-handled-access.md` - The decision to move to artifact-handled access
- `docs/explorations/access_control.md` - Full reasoning and alternatives analysis
- `docs/CONCEPTUAL_MODEL_FULL.yaml:1515-1549` - Migration path defined
- `src/world/executor.py:610-632` - Current `run()` validation
- `src/world/permission_checker.py:102-150` - Current kernel permission checking
- `src/world/action_executor.py:129-189` - Where kernel checks happen before artifact access

---

## Open Questions

### Before Planning

1. [x] **Question:** Can we support both `run()` and `handle_request()` during migration?
   - **Status:** ✅ RESOLVED
   - **Answer:** Yes - check for `handle_request` first, fall back to `run()` for backwards compatibility
   - **Verified in:** Migration path in CONCEPTUAL_MODEL_FULL.yaml:1544-1549

2. [x] **Question:** What happens to existing contracts?
   - **Status:** ✅ RESOLVED
   - **Answer:** They become normal artifacts. Artifacts that want to delegate invoke them explicitly.
   - **Verified in:** `docs/explorations/access_control.md:98-121`

3. [ ] **Question:** How do we handle artifacts with no code (data artifacts)?
   - **Status:** ❓ OPEN
   - **Why it matters:** Current model allows `code: ""` for data artifacts. With handle_request, do they need stub handlers?

4. [ ] **Question:** Performance impact of routing every operation through artifact code?
   - **Status:** ❓ OPEN
   - **Why it matters:** Currently permission checks use lightweight Python contracts. Full artifact execution is heavier.

---

## Files Affected

- `src/world/executor.py` (modify) - Add handle_request support
- `src/world/action_executor.py` (modify) - Route to artifact handler instead of kernel permission check
- `src/world/permission_checker.py` (modify/deprecate) - Phase out kernel permission checking
- `src/world/artifacts.py` (modify) - Default handler for data artifacts
- `tests/unit/test_executor.py` (modify) - Test handle_request interface
- `tests/integration/test_handle_request.py` (create) - Integration tests
- `docs/architecture/current/contracts.md` (modify) - Update to reflect new model
- `docs/architecture/current/artifacts_executor.md` (modify) - Document handle_request

---

## Plan

### Phase 1: Add handle_request Support (Backwards Compatible)

| File | Change |
|------|--------|
| `src/world/executor.py` | Add `validate_handle_request()` alongside `validate_code()` |
| `src/world/executor.py` | In `execute_with_invoke()`, check for `handle_request` first |
| `src/world/action_executor.py` | For artifacts with `handle_request`, route directly instead of checking permission first |

**Key change:** If artifact code defines `handle_request(caller, operation, args)`, use it. Otherwise fall back to current `run()` + kernel permission model.

### Phase 2: Remove Kernel Permission Checking

| File | Change |
|------|--------|
| `src/world/action_executor.py` | Remove `executor._check_permission()` calls before artifact access |
| `src/world/permission_checker.py` | Deprecate or remove |
| `config/config.yaml` | Remove `contracts.default_when_null` and `contracts.default_on_missing` |

### Phase 3: Require handle_request on All Artifacts

| File | Change |
|------|--------|
| `src/world/artifacts.py` | Add default `handle_request` stub for data artifacts |
| `src/world/executor.py` | Remove `run()` fallback |
| All tests | Update to use handle_request interface |

### Steps

1. **Phase 1a:** Add handle_request detection to executor
2. **Phase 1b:** Route handle_request artifacts directly in action_executor
3. **Phase 1c:** Test with new artifacts while old artifacts still work
4. **Phase 2a:** Add deprecation warnings for kernel permission checks
5. **Phase 2b:** Remove kernel permission checks after migration
6. **Phase 3a:** Add default handlers for data artifacts
7. **Phase 3b:** Remove run() fallback
8. **Phase 3c:** Update all tests and documentation

---

## Required Tests

### New Tests (TDD)

| Test File | Test Function | What It Verifies |
|-----------|---------------|------------------|
| `tests/unit/test_executor.py` | `test_handle_request_validation` | Code with handle_request passes validation |
| `tests/unit/test_executor.py` | `test_handle_request_receives_caller` | Caller identity passed correctly |
| `tests/unit/test_executor.py` | `test_handle_request_receives_operation` | Operation type passed correctly |
| `tests/integration/test_handle_request.py` | `test_artifact_denies_access` | Artifact can deny in handler |
| `tests/integration/test_handle_request.py` | `test_artifact_delegates_to_contract` | Artifact can invoke contract |
| `tests/integration/test_handle_request.py` | `test_backwards_compat_run` | Old run() artifacts still work |

### Existing Tests (Must Pass)

| Test Pattern | Why |
|--------------|-----|
| `tests/unit/test_executor.py` | Existing execution still works |
| `tests/integration/test_escrow.py` | Trading patterns unchanged |
| `tests/integration/test_contracts.py` | Contract invocation unchanged |

---

## E2E Verification

| Scenario | Steps | Expected Outcome |
|----------|-------|------------------|
| Agent creates artifact with handle_request | 1. Run simulation 2. Agent writes artifact with handle_request code 3. Another agent invokes it | Handler receives caller, operation, can allow/deny |
| Backwards compatibility | 1. Run with existing artifacts using run() | All existing functionality works |

```bash
# Run E2E verification
pytest tests/e2e/test_real_e2e.py -v --run-external
```

---

## Verification

### Tests & Quality
- [ ] All required tests pass: `python scripts/check_plan_tests.py --plan 234`
- [ ] Full test suite passes: `pytest tests/`
- [ ] Type check passes: `python -m mypy src/ --ignore-missing-imports`
- [ ] **E2E verification passes:** `pytest tests/e2e/test_real_e2e.py -v --run-external`

### Documentation
- [ ] `docs/architecture/current/contracts.md` updated
- [ ] `docs/architecture/current/artifacts_executor.md` updated
- [ ] Doc-coupling check passes: `python scripts/check_doc_coupling.py`
- [ ] CONCEPTUAL_MODEL.yaml reflects implementation status

### Completion Ceremony
- [ ] Plan file status → `✅ Complete`
- [ ] `plans/CLAUDE.md` index → `✅ Complete`
- [ ] Claim released from Active Work table (root CLAUDE.md)
- [ ] Branch merged or PR created

---

## Uncertainties

| Question | Status | Resolution |
|----------|--------|------------|
| Data artifacts need handlers? | ❓ Open | - |
| Performance impact? | ❓ Open | - |
| Genesis artifacts need migration? | ❓ Open | Likely yes - they should use handle_request too |

---

## Notes

### Why This Matters

ADR-0024 was accepted to:
1. Make artifacts fully autonomous (they decide their own access)
2. Simplify the kernel (just routes, doesn't interpret)
3. Follow smart contract model (code IS access control)
4. Eliminate "owner" confusion (no kernel defaults)

### Migration Strategy

The 3-phase approach allows:
- Phase 1: New artifacts can use handle_request immediately
- Phase 2: Remove kernel overhead for handle_request artifacts
- Phase 3: Complete migration, cleaner codebase

### Relationship to Other Plans

- Plan #229 (Conceptual Model) - This implements what that describes
- Plan #230 (Rename has_loop) - Terminology cleanup, independent
- Plan #165 (Genesis Contracts as Artifacts) - Related, contracts become normal artifacts
