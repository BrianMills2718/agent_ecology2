# Plan 79: Time-Based Auctions

**Status:** 🚧 In Progress
**Priority:** Medium
**Blocked By:** #83 (Remove Tick-Based Execution) ✅ Complete
**Blocks:** None

---

## Gap

**Current:** Legacy tick-based auction code remains alongside new time-based code. Both `on_tick()` and `update()` exist in mint, and runner has separate code paths.

**Target:** Pure time-based auctions. Remove all legacy tick-based auction code, ensure timing works well in practice.

**Why:** Autonomous mode purity - no vestigial tick-based code confusing future development.

---

## Scope

### 1. Remove Legacy Code

| File | Remove | Replace With |
|------|--------|--------------|
| `src/simulation/runner.py` | `_handle_mint_tick()` method (lines 333-356) | Use `_handle_mint_update()` everywhere |
| `src/simulation/runner.py` | Tick-mode mint handling (lines 926-929) | Call `_handle_mint_update()` in tick mode too |
| `src/world/genesis/mint.py` | `on_tick()` method (lines 480-486) | Remove entirely (deprecated) |

### 2. Auction Timing Validation

Verify current defaults work well:
- `period_seconds: 60` - 1 minute between auctions
- `bidding_window_seconds: 30` - 30s to submit bids
- `first_auction_delay_seconds: 30` - 30s warmup before first auction

Edge cases to test:
- Auction resolution when `update()` called infrequently
- Multiple periods passing between `update()` calls
- Bid submission timing near window boundaries

---

## Files Affected

- src/simulation/runner.py (modify)
- src/world/genesis/mint.py (modify)
- tests/unit/test_mint_anytime.py (modify)
- tests/integration/test_mint_auction.py (modify)
- tests/integration/test_runner.py (modify)

---

## Required Tests

### New Tests (Plan #79)
| Test File | Test Function | What It Verifies |
|-----------|---------------|------------------|
| `tests/unit/test_mint_anytime.py` | `test_no_on_tick_method` | `on_tick` removed from GenesisMint |
| `tests/unit/test_mint_anytime.py` | `test_update_handles_missed_periods` | Multiple periods pass, only one resolution |

### Existing Tests (Must Continue to Pass)
| Test File | Coverage |
|-----------|----------|
| `tests/unit/test_mint_anytime.py` | All time-based auction tests (8 tests) |
| `tests/integration/test_mint_auction.py` | Auction phase and resolution tests (13 tests) |

---

## Implementation Steps

1. Remove `on_tick()` from `GenesisMint`
2. Update runner tick-mode to use `_handle_mint_update()` instead of `_handle_mint_tick()`
3. Remove `_handle_mint_tick()` from runner
4. Update/remove any tests that use `on_tick()`
5. Add test for missed periods handling
6. Verify all existing tests pass

---

## Notes

This is cleanup work following Plan #83. The time-based auction logic already works - this just removes the legacy code paths that are no longer needed.
