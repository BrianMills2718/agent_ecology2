# Plan 95: Unified Resource System

**Status:** 🚧 In Progress
**Priority:** Critical
**Blocked By:** None
**Blocks:** #93 (Agent Resource Visibility)

---

## Gap

**Current:** Three overlapping resource systems (Ledger.resources, RateTracker, World._quota_limits).

**Target:** Single unified ResourceManager with per-agent quotas and contractability.

**Why Critical:** Core economic mechanics for emergence thesis.

---

## Files Affected

- `src/world/resource_manager.py` (create)
- `src/world/ledger.py` (modify)
- `src/world/rate_tracker.py` (modify - keep but integrate)
- `src/world/world.py` (modify)
- `tests/unit/test_resource_manager.py` (create)

---

## Plan

Phase 1 (this plan):
1. Create ResourceManager class with unified API for:
   - Balance tracking (get/set/spend/credit)
   - Quota management (allocate/deallocate within limits)
   - Rate limiting (consume within rolling window limits)
   - Transfers between principals
2. Comprehensive unit tests (34 tests)
3. Three resource types: DEPLETABLE, ALLOCATABLE, RENEWABLE

Phase 2 (follow-up):
- Migrate Ledger to use ResourceManager internally
- Migrate World quota management to ResourceManager
- Full integration with existing systems

---

## Required Tests

- `tests/unit/test_resource_manager.py::TestResourceManagerInit::test_creates_empty_manager`
- `tests/unit/test_resource_manager.py::TestResourceManagerInit::test_custom_rate_window`
- `tests/unit/test_resource_manager.py::TestResourceTypes::test_register_depletable_resource`
- `tests/unit/test_resource_manager.py::TestResourceTypes::test_register_allocatable_resource`
- `tests/unit/test_resource_manager.py::TestResourceTypes::test_register_renewable_resource`
- `tests/unit/test_resource_manager.py::TestResourceTypes::test_unknown_resource_type_is_none`
- `tests/unit/test_resource_manager.py::TestPrincipalManagement::test_create_principal`
- `tests/unit/test_resource_manager.py::TestPrincipalManagement::test_create_principal_empty`
- `tests/unit/test_resource_manager.py::TestPrincipalManagement::test_principal_exists`
- `tests/unit/test_resource_manager.py::TestBalanceOperations::test_get_balance`
- `tests/unit/test_resource_manager.py::TestBalanceOperations::test_spend_success`
- `tests/unit/test_resource_manager.py::TestBalanceOperations::test_spend_insufficient`
- `tests/unit/test_resource_manager.py::TestQuotaManagement::test_set_quota`
- `tests/unit/test_resource_manager.py::TestQuotaManagement::test_allocate_within_quota`
- `tests/unit/test_resource_manager.py::TestQuotaManagement::test_allocate_exceeds_quota`
- `tests/unit/test_resource_manager.py::TestRateLimiting::test_set_rate_limit`
- `tests/unit/test_resource_manager.py::TestRateLimiting::test_consume_rate_limited`
- `tests/unit/test_resource_manager.py::TestRateLimiting::test_consume_rate_limited_exceeds`
- `tests/unit/test_resource_manager.py::TestTransfers::test_transfer_success`
- `tests/unit/test_resource_manager.py::TestTransfers::test_transfer_insufficient`
- `tests/unit/test_resource_manager.py::TestReporting::test_get_all_balances`
- `tests/unit/test_resource_manager.py::TestReporting::test_get_principal_summary`

---

## Progress

### Phase 1 Complete (2026-01-18)
- Created `src/world/resource_manager.py` with full API
- Created `tests/unit/test_resource_manager.py` with 34 passing tests
- ResourceType enum: DEPLETABLE, ALLOCATABLE, RENEWABLE
- All balance, quota, rate limiting, transfer, and reporting operations working

---

## Notes

Originally Plan #92 but renumbered due to collision with Worktree/Branch Mismatch Detection.
