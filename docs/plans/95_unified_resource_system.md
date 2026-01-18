# Plan 95: Unified Resource System

**Status:** 📋 Planned
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
- `src/world/rate_tracker.py` (delete)
- `src/world/world.py` (modify)

---

## Plan

See handoff notes for detailed implementation approach:
1. Create ResourceManager class consolidating Ledger.resources, RateTracker, World._quota_limits
2. Per-agent contractable quotas (Ostrom-style rights)
3. LLM costs in dollars via litellm

---

## Notes

Originally Plan #92 but renumbered due to collision with Worktree/Branch Mismatch Detection.
