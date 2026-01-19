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

- src/world/resource_manager.py (create)
- src/world/ledger.py (modify)
- src/world/rate_tracker.py (modify)
- src/world/world.py (modify)
- tests/unit/test_resource_manager.py (create)
- tests/integration/test_resource_integration.py (create)
- docs/architecture/current/execution_model.md (modify)

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

### Phase 1 - Unit Tests
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

### Phase 2 - Integration Tests
- `tests/integration/test_resource_integration.py::TestWorldResourceManagerIntegration::test_world_has_resource_manager`
- `tests/integration/test_resource_integration.py::TestWorldResourceManagerIntegration::test_set_quota_updates_resource_manager`
- `tests/integration/test_resource_integration.py::TestWorldResourceManagerIntegration::test_get_quota_reads_from_resource_manager`
- `tests/integration/test_resource_integration.py::TestWorldResourceManagerIntegration::test_consume_quota_uses_resource_manager_allocate`
- `tests/integration/test_resource_integration.py::TestWorldResourceManagerIntegration::test_consume_quota_respects_limit`
- `tests/integration/test_resource_integration.py::TestWorldResourceManagerIntegration::test_get_available_capacity_uses_resource_manager`
- `tests/integration/test_resource_integration.py::TestWorldResourceManagerIntegration::test_multiple_resources_tracked_independently`
- `tests/integration/test_resource_integration.py::TestWorldResourceManagerIntegration::test_multiple_principals_tracked_independently`
- `tests/integration/test_resource_integration.py::TestResourceManagerInWorld::test_resource_manager_principal_created_on_set_quota`
- `tests/integration/test_resource_integration.py::TestResourceManagerInWorld::test_resource_manager_principal_created_on_consume_quota`

---

## Progress

### Phase 1 Complete (2026-01-18)
- Created `src/world/resource_manager.py` with full API
- Created `tests/unit/test_resource_manager.py` with 34 passing tests
- ResourceType enum: DEPLETABLE, ALLOCATABLE, RENEWABLE
- All balance, quota, rate limiting, transfer, and reporting operations working

### Phase 2 Complete (2026-01-19)
- Integrated ResourceManager into World for quota management
- World.set_quota/get_quota/consume_quota/get_quota_usage/get_available_capacity now delegate to ResourceManager
- Removed `_quota_limits` and `_quota_usage` dicts from World (replaced by ResourceManager)
- Created integration tests verifying World-ResourceManager integration (10 tests)
- All existing kernel quota tests (13) continue to pass
- Note: Ledger integration deferred to follow-up work - Ledger continues to work independently

---

## Notes

Originally Plan #92 but renumbered due to collision with Worktree/Branch Mismatch Detection.
