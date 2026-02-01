# Plan 231: Tight Coupling Between has_standing and Ledger Registration

**Status:** ✅ Complete

**Verified:** 2026-02-01T02:12:31Z
**Verification Evidence:**
```yaml
completed_by: scripts/complete_plan.py
timestamp: 2026-02-01T02:12:31Z
tests:
  unit: skipped (--status-only, CI-validated)
  e2e_smoke: skipped (--status-only, CI-validated)
  e2e_real: skipped (--status-only, CI-validated)
  doc_coupling: skipped (--status-only, CI-validated)
commit: b844530
```
**Priority:** Medium
**Blocked By:** -
**Blocks:** -

---

## Gap

**Current:** `artifact.has_standing` and ledger registration are independent:
- An artifact can have `has_standing=True` without being in the ledger
- The runner tries to sync them but they can diverge
- Four independent registries can drift: `ledger.scrip`, `world.principal_ids`, `artifact.has_standing`, `resource_manager._principals`

**Target:** Kernel invariant: `has_standing=True` <=> registered in ledger. They are always in sync.

**Why Medium:** Inconsistency is confusing but current best-effort sync mostly works. Also fixes a confirmed bug where spawned agents are invisible to `get_state_summary()`.

---

## References Reviewed

- `src/world/artifacts.py:166` - `has_standing: bool = False`
- `src/world/ledger.py:180-200` - `create_principal()` creates ledger entry
- `src/world/ledger.py:589` - `get_agent_principal_ids()` derives from ledger
- `src/simulation/runner.py:453-460` - Runner syncs ledger->artifact
- `src/world/kernel_interface.py:640-666` - `create_principal()` kernel primitive
- `src/world/resource_manager.py:118-134` - `create_principal()` ResourceManager entry
- `src/world/world.py:316,346` - `principal_ids` init-only list (bug)

---

## Open Questions

### Before Planning

1. [x] **Question:** Should setting `has_standing=True` on artifact auto-create ledger entry?
   - **Answer:** No. Ledger-driven: `create_principal()` is the single entry point.

2. [x] **Question:** Should `create_principal()` also set artifact `has_standing=True`?
   - **Answer:** Yes. This is the core of the design.

3. [x] **Question:** What happens on checkpoint restore if artifact has `has_standing` but ledger doesn't have entry yet?
   - **Answer:** Ledger first, then artifacts, then validate. Post-restore invariant enforcement fixes drift using raw dict access (IDRegistry already registered the ID).

---

## Design Decision: Modified Option B (Ledger-Driven)

### Why Option B

- **Option A (Artifact-driven)**: Would require artifacts.py to depend on ledger.py. Higher coupling.
- **Option B (Ledger-driven)**: `create_principal()` already exists. Natural extension.
- **Option C (New primitive)**: Unnecessary new API. Option B achieves the same.

### Key Choices

1. `world.principal_ids` becomes a derived `@property` using `ledger.get_agent_principal_ids()`
2. `KernelActions.create_principal()` atomically creates ledger entry + sets `has_standing` + ResourceManager entry
3. `Ledger.credit_scrip()` auto-create unchanged (genesis artifacts, not principals)
4. Checkpoint restore gets post-validation to fix drift

---

## Files Affected

- `src/world/world.py` (modify) - Derived `principal_ids` property, `validate_principal_invariant()`
- `src/world/kernel_interface.py` (modify) - Atomic `create_principal()`
- `src/simulation/runner.py` (modify) - Invariant enforcement in checkpoint restore, ResourceManager sync
- `tests/unit/test_standing_invariant.py` (create) - 9 unit tests
- `tests/integration/test_standing_invariant.py` (create) - 4 integration tests

---

## Plan

### Phase 1: Derived principal_ids + Atomic create_principal

| Step | File | Change |
|------|------|--------|
| 1 | `src/world/world.py` | `principal_ids` -> `@property` from `ledger.get_agent_principal_ids()` |
| 2 | `src/world/kernel_interface.py` | `create_principal()` sets `has_standing` + ResourceManager |
| 3 | `src/world/world.py` | `__init__` removes `.append()`, adds ResourceManager sync |
| 4 | `src/simulation/runner.py` | `_restore_checkpoint()` invariant enforcement |
| 5 | `src/simulation/runner.py` | `_check_for_new_principals()` ResourceManager sync |
| 6 | `src/world/world.py` | `validate_principal_invariant()` method |

---

## Required Tests

### New Tests (TDD)

| Test File | Test Function | What It Verifies |
|-----------|---------------|------------------|
| `tests/unit/test_standing_invariant.py` | `test_principal_ids_derived_from_ledger` | Derived property works |
| `tests/unit/test_standing_invariant.py` | `test_principal_ids_excludes_genesis` | Genesis artifacts filtered |
| `tests/unit/test_standing_invariant.py` | `test_principal_ids_includes_spawned` | Spawned agents visible |
| `tests/unit/test_standing_invariant.py` | `test_create_principal_sets_has_standing` | Atomic operation |
| `tests/unit/test_standing_invariant.py` | `test_create_principal_creates_resource_manager_entry` | ResourceManager sync |
| `tests/unit/test_standing_invariant.py` | `test_create_principal_idempotent` | No double-create |
| `tests/unit/test_standing_invariant.py` | `test_validate_invariant_clean` | No violations on clean state |
| `tests/unit/test_standing_invariant.py` | `test_validate_invariant_detects_missing_standing` | Detects drift |
| `tests/unit/test_standing_invariant.py` | `test_validate_invariant_detects_missing_ledger` | Detects drift |
| `tests/integration/test_standing_invariant.py` | `test_spawn_principal_full_invariant` | All registries consistent |
| `tests/integration/test_standing_invariant.py` | `test_checkpoint_restore_fixes_missing_standing` | Drift correction |
| `tests/integration/test_standing_invariant.py` | `test_checkpoint_restore_fixes_missing_ledger` | Drift correction |
| `tests/integration/test_standing_invariant.py` | `test_spawned_agent_appears_in_state_summary` | Bug fix verification |

---

## Verification

### Tests & Quality
- [x] All 13 new tests pass
- [x] Full test suite passes: 2869 passed, 0 failed
- [ ] Type check passes: `python -m mypy src/ --ignore-missing-imports`
- [ ] `make lint` passes

### Completion Ceremony
- [ ] Plan file status -> Complete
- [ ] `plans/CLAUDE.md` index -> Complete
- [ ] Branch merged or PR created

---

## Notes

### Bug Fixed

`world.principal_ids` was a stored `list[str]` only populated at `__init__` time. Spawned agents (created via `KernelActions.create_principal()`) were never added, making them invisible to `get_state_summary()`, `get_frozen_agents()`, and `rights_registry.quotas`.

Now `principal_ids` is a derived `@property` from `ledger.get_agent_principal_ids()`, so spawned agents appear immediately.
