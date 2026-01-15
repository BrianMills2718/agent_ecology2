# Gap 5: Oracle Anytime Bidding

**Status:** ✅ Complete

**Verified:** 2026-01-15T00:45:39Z
**Verification Evidence:**
```yaml
completed_by: scripts/complete_plan.py
timestamp: 2026-01-15T00:45:39Z
tests:
  unit: 1353 passed, 7 skipped in 16.64s
  e2e_smoke: PASSED (1.85s)
  e2e_real: PASSED (4.75s)
  doc_coupling: passed
commit: 2e88dfb
```
**Priority:** Medium
**Blocked By:** None
**Blocks:** None

---

## Gap

**Current:** Phase-based bidding with WAITING → BIDDING → CLOSED states. Bids only accepted during bidding window.

**Target:** Accept bids anytime, resolve on schedule. No waiting period.

---

## Problem Statement

The current mint uses phased bidding:
1. **WAITING** (tick 0-49): No bids accepted
2. **BIDDING** (tick 50-59): Bids accepted
3. **CLOSED** (tick 60+): No bids, auction resolves

This creates friction:
- Agents must wait until bidding window opens
- Agents must track auction timing
- Missed windows mean waiting for next period

The target model is simpler:
- Bids accepted anytime
- Auctions resolve on fixed schedule (every N ticks)
- Bids for current period are included in next resolution

---

## Plan

### Phase 1: Remove Phase Checks

Modify `GenesisMint._bid()` to accept bids regardless of phase:

```python
def _bid(self, args: list[Any], caller_id: str) -> dict[str, Any]:
    # Remove phase check - accept bids anytime
    # Bids apply to NEXT auction resolution
    ...
```

### Phase 2: Track Bid Timing

Add field to track which auction a bid applies to:

```python
@dataclass
class Bid:
    agent_id: str
    artifact_id: str
    amount: int
    timestamp: float
    target_auction: int  # Which auction number this applies to
```

### Phase 3: Update Resolution Logic

Modify `_resolve_auction()` to:
1. Only consider bids for current auction number
2. Roll over late bids to next auction (or reject with message)

### Phase 4: Simplify Configuration

Remove or deprecate:
- `first_auction_tick` - no longer needed
- `bidding_window` - always open

Keep:
- `period` - time between resolutions
- `minimum_bid` - still enforced
- `tie_breaking` - still needed

---

## Changes Required

| File | Change |
|------|--------|
| `src/world/genesis.py` | Remove phase checks in `_bid()`, update resolution logic |
| `config/schema.yaml` | Mark `first_auction_tick`, `bidding_window` as deprecated |
| `docs/architecture/current/genesis_artifacts.md` | Update mint documentation |

---

## Required Tests

### Unit Tests
| Test Pattern | Why |
|--------------|-----|
| `tests/unit/test_mint_anytime.py::TestAnytimeBidding::test_bid_before_first_auction` | Bids accepted before tick 50 |
| `tests/unit/test_mint_anytime.py::TestAnytimeBidding::test_bid_during_closed_phase` | Bids accepted during CLOSED phase |
| `tests/unit/test_mint_anytime.py::TestAnytimeBidding::test_continuous_bidding` | Bids accepted at any tick |
| `tests/unit/test_mint_anytime.py::TestBidTimingForAuctions::test_early_bid_included_in_first_auction` | Early bids included in first auction |
| `tests/unit/test_mint_anytime.py::TestBidTimingForAuctions::test_bid_after_resolution_applies_to_next_auction` | Bid after resolution applies to next auction |

### Existing Tests (Must Pass)
| Test Pattern | Why |
|--------------|-----|
| `tests/integration/test_mint_auction.py` | Existing mint tests still pass |

---

## E2E Verification

```bash
# Run simulation, submit bids at various ticks
python run.py --ticks 100 --agents 2
# Check run.jsonl for successful bids before tick 50
grep "mint_bid" run.jsonl | jq 'select(.tick < 50)'
```

---

## Backward Compatibility

- Old configs with `first_auction_tick` and `bidding_window` should still work (ignored)
- Log deprecation warning if these config values are present

---

## Verification

- [ ] Tests pass
- [ ] Docs updated
- [ ] Bids accepted at any tick
- [ ] Deprecation warnings for old config

---

## Notes

This simplifies the mint model significantly. Agents no longer need to track auction phases - they just bid when they want to, and auctions resolve on schedule.

The second-price (Vickrey) auction mechanism remains unchanged.
