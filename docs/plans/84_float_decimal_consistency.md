# Plan #84: Float/Decimal Consistency

**Status:** 📋 Deferred (Post-V1)
**Priority:** Low
**Blocks:** None

## Problem

Mixed use of float and Decimal across resource tracking:

1. `ledger.py` stores resources as `float` but uses Decimal helpers for arithmetic
2. `world.py` quota tracking uses raw `float` operations
3. Scrip correctly uses `int` (discrete currency units)

This inconsistency could cause subtle precision issues if:
- Very small fractional resources are summed many times
- Resource amounts flow into scrip calculations

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

## Proposed Solution

**Option A: Standardize on Decimal throughout**
- Change `resources: dict[str, dict[str, float]]` to `Decimal`
- Update quota tracking to use Decimal
- Pro: Consistent, no precision concerns
- Con: API friction (need to convert at boundaries)

**Option B: Document current approach (Recommended)**
- Add comments explaining the float-storage, Decimal-arithmetic pattern
- Ensure quota operations use the same pattern if fractional values ever used
- Pro: Minimal change
- Con: Still inconsistent

## Recommendation

Option B for now. The current approach works and the risk is low. Revisit if precision issues are observed.

## Required Tests

None - this is documentation/consistency work.

## Notes

Created as deferred tech debt from codebase review (2026-01-18).
