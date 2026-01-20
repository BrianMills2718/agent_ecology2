# Plan #84: Float/Decimal Consistency

**Status:** ✅ Complete
**Priority:** Low
**Blocks:** None

---

## Gap

**Current:** Mixed use of float and Decimal across resource tracking:
1. `ledger.py` stores resources as `float` but uses Decimal helpers for arithmetic
2. `world.py` quota tracking uses raw `float` operations
3. Scrip correctly uses `int` (discrete currency units)

**Target:** Consistent documentation of precision strategy; optionally standardize on Decimal.

**Why Low:** Current mitigations work. Risk is marginal.

---

## Current Mitigations

- `ledger.py` uses `_decimal_add()` / `_decimal_sub()` for resource arithmetic
- Quotas are typically whole numbers (bytes, seconds)
- Scrip is integer (no precision issues)

## Analysis

The check-then-act pattern in ledger operations is safe in asyncio because:
1. Asyncio is single-threaded - only one coroutine runs at a time
2. Synchronous ledger methods contain no `await` points - they complete atomically
3. Worker pool parallelizes thinking, not execution

The async methods (`transfer_scrip_async`, etc.) exist as forward-looking infrastructure
for potential multi-threaded scenarios.

---

## Plan

### Changes Required

| File | Change |
|------|--------|
| `src/world/ledger.py` | Add comments documenting float-storage, Decimal-arithmetic pattern |
| `src/world/world.py` | Add comments about quota tracking precision assumptions |

### Steps

1. Add documentation comments explaining the precision strategy
2. No code changes - documentation only

---

## Required Tests

None - this is documentation/consistency work.

---

## Notes

Created as deferred tech debt from codebase review (2026-01-18).
Recommended approach: Option B (document current approach, no code changes).
