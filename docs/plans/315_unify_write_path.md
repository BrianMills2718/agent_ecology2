# Plan 315: Unify Write Path for Disk Quota Enforcement

**Status:** ✅ Complete
**Priority:** Medium
**Blocked By:** -
**Blocks:** -

---

## Gap

**Current:** `kernel_actions.write_artifact()` calls `artifacts.write()` directly, bypassing disk quota enforcement, code validation, and structured logging. Disk usage shows 0 bytes despite agents writing artifacts.

**Target:** All writes route through `ActionExecutor._execute_write()` for consistent permission checking, disk quota enforcement, and logging.

**Why Medium:** Disk quota is a key scarcity lever. Without enforcement, agents have unlimited storage — undermining the economics of the simulation.

---

## References Reviewed

- `src/world/kernel_interface.py:420-494` - Old write_artifact bypasses action executor
- `src/world/action_executor.py:260-420` - _execute_write with disk quota enforcement
- `src/world/resource_manager.py:246-266` - allocate() checks quota math
- `src/world/world.py:307-310` - Quota initialization per principal

---

## Open Questions

### Resolved

1. [x] **Question:** What happens when disk quota is 0 (unconfigured)?
   - **Status:** ✅ RESOLVED
   - **Answer:** defaultdict returns 0.0, which blocks ALL writes. Quota 0 should mean unlimited (scarcity is opt-in).
   - **Verified in:** `src/world/resource_manager.py:65-72` (defaultdict), `src/world/action_executor.py:302-313` (check)

2. [x] **Question:** Does artifacts.write() reject type changes on updates?
   - **Status:** ✅ RESOLVED
   - **Answer:** Yes — "Cannot change artifact type". kernel_actions must preserve existing type on updates.
   - **Verified in:** `src/world/artifacts.py:661`

---

## Files Affected

- `src/world/kernel_interface.py` (modify) - Delegate write_artifact to action executor
- `src/world/action_executor.py` (modify) - Guard disk quota on quota > 0

---

## Plan

### Changes Required
| File | Change |
|------|--------|
| `kernel_interface.py` | Replace 50-line write body with WriteArtifactIntent delegation |
| `action_executor.py` | Guard disk check/consume on `disk_quota > 0` |

### Steps
1. Replace `kernel_actions.write_artifact()` body with `WriteArtifactIntent` → `execute_action()`
2. Preserve existing artifact type/executable on updates (callers don't re-specify)
3. Fix disk quota enforcement: quota=0 means unlimited (opt-in scarcity)
4. Run tests, mypy

---

## Required Tests

### Existing Tests (Must Pass)

| Test Pattern | Why |
|--------------|-----|
| `tests/unit/test_kernel_interface.py::TestWriteArtifactHasStanding` | Write + principal creation preserved |
| `tests/unit/test_kernel_interface.py` | All kernel interface behavior preserved |
| `tests/integration/` | Integration behavior unchanged |

---

## Verification

### Tests & Quality
- [x] All required tests pass
- [x] Full test suite passes (1642 passed, 4 pre-existing failures)
- [x] Type check passes: mypy clean
- [x] Net -26 lines (simpler code)

---

## Notes

The old `kernel_actions.write_artifact()` was a parallel implementation that duplicated permission checking but skipped disk quota, code validation, and structured logging. By routing through the action executor, we get all enforcement for free and remove 50 lines of duplicate code.
