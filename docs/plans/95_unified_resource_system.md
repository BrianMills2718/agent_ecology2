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

```
tests/unit/test_resource_manager.py::TestResourceManagerInit
tests/unit/test_resource_manager.py::TestResourceTypes
tests/unit/test_resource_manager.py::TestPrincipalManagement
tests/unit/test_resource_manager.py::TestBalanceOperations
tests/unit/test_resource_manager.py::TestQuotaManagement
tests/unit/test_resource_manager.py::TestRateLimiting
tests/unit/test_resource_manager.py::TestTransfers
tests/unit/test_resource_manager.py::TestReporting
```

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
