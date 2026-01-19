# Plan #75: Autonomous Mint Resolution

**Status:** ✅ Complete

**Verified:** 2026-01-19T03:50:02Z
**Verification Evidence:**
```yaml
completed_by: scripts/complete_plan.py
timestamp: 2026-01-19T03:50:02Z
tests:
  unit: 1705 passed, 9 skipped, 3 warnings in 52.18s
  e2e_smoke: PASSED (5.59s)
  e2e_real: PASSED (31.94s)
  doc_coupling: passed
commit: 60b3996
```
**Priority:** Critical
**Blocks:** Autonomous-only architecture

---

## Gap

**Current:** Mint resolution is tick-based. Auctions resolve every N ticks.

**Target:** Mint resolution is time-based. Auctions resolve every N seconds (wall-clock time) in autonomous mode.

**Why:** We're refactoring to an autonomous-only codebase (Plan #83). Tick-based resolution must be replaced with time-based resolution.

---

## Design

### Resolution Trigger (Implemented)

A background task (`_mint_update_loop`) in the autonomous runner polls `mint.update()` every second. The mint's `update()` method checks elapsed time and resolves auctions when `period_seconds` has passed since the last resolution.

**Why this approach (better than original design):**
- Decoupled from agent execution
- Provides predictable, wall-clock timing
- No overhead added to agent cycles
- Clean async coordination via background task

### Configuration (Implemented)

```yaml
genesis:
  mint:
    auction:
      period_seconds: 60.0           # Wall-clock seconds between auction starts
      bidding_window_seconds: 30.0   # Duration of bidding phase
      first_auction_delay_seconds: 30.0  # Delay before first auction
```

### Changes Implemented

| File | Change |
|------|--------|
| `src/simulation/runner.py` | `_mint_update_loop()` background task calls `mint.update()` every second |
| `src/world/genesis/mint.py` | `update()` method handles time-based auction phases and resolution |
| `src/config_schema.py` | `MintAuctionConfig` with `period_seconds`, `bidding_window_seconds`, `first_auction_delay_seconds` |

---

## Required Tests

| Test | Description |
|------|-------------|
| `tests/integration/test_mint_auction.py::TestMintAuctionPhases::test_phase_bidding_after_first_auction_delay` | Auction enters BIDDING phase after first_auction_delay_seconds |
| `tests/integration/test_mint_auction.py::TestMintAuctionPhases::test_phase_closed_after_bidding_window` | Auction enters CLOSED phase after bidding_window_seconds |
| `tests/integration/test_mint_auction.py::TestAuctionResolution::test_single_bidder_wins` | Resolution triggers and winner selected |
| `tests/unit/test_mint_anytime.py::TestBidTimingForAuctions::test_bid_after_resolution_applies_to_next_auction` | Timer resets after resolution, bids apply to next auction |

---

## Dependencies

- Plan #83 (Remove Tick-Based Execution) - this plan was implemented as part of #83

---

## Notes

**Implementation Note:** This functionality was implemented as part of Plan #83's time-based execution refactor. The design evolved from "check at agent cycle start" to "background polling task" which is cleaner and more decoupled.
