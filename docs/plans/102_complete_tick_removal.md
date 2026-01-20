# Plan 102: Complete Tick Removal (Cosmetic Cleanup)

**Status:** ✅ Complete

**Priority:** Low
**Blocked By:** None
**Blocks:** None

---

## Gap

**Current:** Plan #83 removed tick-based execution. What remains is:
- `self.tick` as an event counter for logging (intentionally kept)
- `advance_tick()` as a deprecated wrapper (tests depend on it)
- A few stale config fallbacks and dashboard labels referencing "per_tick"

**Target:** Clean up cosmetic references to "per_tick" without changing functionality.

**Why:**
- Misleading labels like "Compute/Tick" in dashboard confuse the model
- Stale config fallbacks reference removed config paths
- Comments already explain the new model; this is just label cleanup

---

## Scope Clarification

This plan was originally overscoped. After investigation:

1. **Tick-based execution was already removed in Plan #83** - the execution model is now time-based/continuous
2. **`self.tick` is just an event counter** - useful for log ordering, not execution control
3. **Renaming tick → iteration doesn't make sense** - "iteration" implies per-agent, but this is a global counter

### What This Plan Does (Cosmetic Only)

| Change | File | Why |
|--------|------|-----|
| Remove `per_tick` config fallback | `src/world/genesis/factory.py` | Fallback reads removed config path |
| Update "Compute/Tick" label | `src/dashboard/static/js/panels/config.js` | Misleading label |

### What This Plan Does NOT Do

- Mass rename of tick → iteration (doesn't make conceptual sense)
- Remove `advance_tick()` (tests depend on it, has deprecation notice)
- Remove `self.tick` counter (useful for event ordering in logs)
- Change dashboard `last_action_tick` metric (event counter is still useful)

---

## Changes Made

### 1. Remove per_tick Config Fallback

```python
# Before (factory.py:101)
compute_fallback: int = get("resources.flow.compute.per_tick") or 50

# After
compute_fallback: int = 50  # Note: compute uses rate_limiting now
```

### 2. Update Dashboard Label

```javascript
// Before (config.js:88)
'Compute/Tick': flow.compute?.per_tick || 'N/A',

// After
'Compute Quota': flow.compute?.per_tick || 'N/A',
```

---

## Files Affected

- `src/world/genesis/factory.py` - Remove per_tick config fallback
- `src/dashboard/static/js/panels/config.js` - Update misleading label

---

## Verification

- [x] All 1870 tests pass
- [x] No functional changes (cosmetic only)
- [x] Dashboard label no longer mentions "tick"
- [x] Config fallback no longer references removed path

---

## Notes

- Plan #83 did the heavy lifting of removing tick-based execution
- The remaining "tick" references are intentional (event counter for logging)
- Comments throughout the codebase already explain the new time-based model
