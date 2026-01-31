# Plan 238: Defer Tokenized Rights

**Status:** ✅ Complete
**Priority:** Medium
**Complexity:** Low

## Problem

The rights-as-artifacts system (Plan #166 Phase 3-5) was implemented but:
1. **Never wired into enforcement** - `consume_from_*_right()` functions exist but are never called
2. **Missing critical invariants** - No atomicity, content is forgeable, no holder semantics
3. **Dead code tax** - Adds cognitive overhead without providing value

Meanwhile, the ledger/quota system (`ledger.spend_resource()`, `world.get_available_capacity()`) handles all actual resource enforcement.

## Solution

Defer tokenized rights by:
1. Documenting the deferral decision (ADR-0025)
2. Updating Plan #166 status to reflect partial completion
3. Deleting the dead code
4. Preserving recovery path via git history

## Implementation

### Phase 1: Documentation

1. Create `docs/adr/0025-deferred-tokenized-rights.md` capturing:
   - Decision and rationale
   - Required invariants for future implementation
   - Git commits for code recovery

2. Update `docs/plans/166_resource_rights_model.md`:
   - Change Phase 4 status to "Deferred"
   - Add "Deferral Note" section explaining current state

### Phase 2: Code Removal

1. Delete `src/world/rights.py` (565 lines)

2. Remove from `src/world/kernel_interface.py`:
   - `get_dollar_budget_right_amount()` method
   - `get_rate_capacity_right_amount()` method
   - `get_disk_quota_right_amount()` method
   - `can_afford_llm_call_with_rights()` method
   - `consume_from_dollar_budget_right()` method
   - `consume_from_disk_quota_right()` method
   - Related imports

3. Delete `tests/unit/test_rights.py` (14 tests)

4. Remove from `tests/unit/test_kernel_interface.py`:
   - `TestKernelStateRights` class (7 tests)
   - `TestKernelActionsRights` class (6 tests)

### Phase 3: Verification

1. Run full test suite - all tests pass
2. Run mypy - no type errors
3. Verify `genesis/rights_registry.py` (quotas) is untouched

## What Gets Preserved

| What | Where |
|------|-------|
| RightData schema | Plan #166 |
| Design rationale | Plan #166 |
| Required invariants | ADR-0025 |
| Actual code | Git history (commit 8072654) |
| Split/merge patterns | Git history |

## Required Invariants for Resumption

When/if tokenized rights are needed, must implement:

1. **Type immutability** - `type` cannot change after artifact creation
2. **No direct write/edit** - Right content only mutable via kernel primitives
3. **Holder semantics** - `holder_id` distinct from `created_by`
4. **Atomic settlement** - Locking for check-then-debit operations

## Files Affected

- docs/adr/0025-deferred-tokenized-rights.md (create)
- docs/plans/166_resource_rights_model.md (modify)
- docs/plans/235_kernel_protected_artifacts.md (modify - remove rights.py references)
- docs/architecture/current/resources.md (modify - remove rights-as-artifacts section)
- docs/DESIGN_CLARIFICATIONS.md (modify - update code reference)
- src/world/rights.py (delete)
- src/world/kernel_interface.py (modify)
- tests/unit/test_rights.py (delete)
- tests/unit/test_kernel_interface.py (modify)

## NOT Affected

- `src/world/genesis/rights_registry.py` - This is the quota system, KEEP IT
- Test configs with `"rights": {...}` - These refer to genesis_rights_registry

## Testing

- [x] All existing tests pass after removal (2774 passed)
- [x] mypy passes (same 84 pre-existing errors, no new ones)
- [x] ADR-0025 documents recovery path (with git tag, restore recipe, PR references)
- [x] Plan #166 updated with deferral status
- [x] Git tag `token-rights-deferred-v1` created for stable recovery

## Dependencies

None - this is cleanup work.

## Estimated Effort

~1.5 hours total
