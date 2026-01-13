# Gap 5: Oracle Anytime Bidding

**Status:** 📋 Planned
**Priority:** Medium
**Blocked By:** None
**Blocks:** None

---

## Gap

**Current:** Phased bidding with explicit WAITING → BIDDING → RESOLVING states. Bids are only accepted during BIDDING phase, which starts at `first_auction_tick` and lasts `bidding_window` ticks.

**Target:** Accept bids anytime, resolve on schedule. Simpler state machine with just "accepting bids" always on, resolving at regular intervals.

---

## Problem Statement

The current GenesisMint has unnecessary complexity:

1. **WAITING state** - Before `first_auction_tick`, bids are rejected
2. **Explicit bidding windows** - Bids only accepted during specific tick ranges
3. **Complex tick tracking** - Must calculate "ticks since auction start"

The target simplification:
- Always accept bids (no WAITING state)
- Resolve auctions every N ticks (period)
- Bids for current period compete; bids after resolution start new period

Benefits:
- Simpler state machine (always accepting)
- No "you just missed the window" frustration
- Agents can bid whenever they have artifacts ready
- Easier to reason about

---

## Design

### Current State Machine

```
WAITING (tick < first_auction_tick)
  ↓ tick >= first_auction_tick
BIDDING (accepting bids for bidding_window ticks)
  ↓ bidding_window elapsed
RESOLVE → mint scrip → clear bids
  ↓
BIDDING (next period)
  ↓
...
```

### Target State Machine

```
ACCEPTING (always)
  ↓ every period ticks
RESOLVE → mint scrip → clear bids
  ↓
ACCEPTING (continue)
```

### Implementation Changes

**1. Remove WAITING state and `first_auction_tick`:**
```python
def _get_phase(self) -> str:
    # Always accepting, resolve on tick % period == 0
    return "ACCEPTING"
```

**2. Simplify `on_tick()`:**
```python
def on_tick(self, tick: int) -> AuctionResult | None:
    self._current_tick = tick
    if tick > 0 and tick % self._period == 0:
        return self._resolve_auction()
    return None
```

**3. Remove `bidding_window` config:**
Config becomes simpler:
```yaml
genesis:
  mint:
    auction:
      period: 50          # Resolve every 50 ticks
      # bidding_window: REMOVED
      # first_auction_tick: REMOVED
```

**4. Update `submit_bid()` to always accept:**
```python
def submit_bid(self, agent_id: str, artifact_id: str, bid_amount: int) -> dict:
    # No phase check - always accept bids
    if bid_amount < self._minimum_bid:
        return {"success": False, "error": f"Minimum bid is {self._minimum_bid}"}
    # ... rest of bid validation ...
```

### Backward Compatibility

Add `anytime_bidding` feature flag (default: True for new, False for legacy):
```yaml
genesis:
  mint:
    anytime_bidding: true  # Enable simplified bidding
```

When `anytime_bidding: false`, preserve current behavior for existing simulations.

---

## Implementation Steps

1. [ ] Add `anytime_bidding` config flag to `config/schema.yaml`
2. [ ] Update `GenesisMint._get_phase()` to return "ACCEPTING" when enabled
3. [ ] Update `GenesisMint.on_tick()` for simplified resolution
4. [ ] Update `GenesisMint.submit_bid()` to remove phase checks when enabled
5. [ ] Update `status()` response for anytime mode
6. [ ] Update tests for both modes
7. [ ] Update documentation

---

## Required Tests

| Test | Type | Purpose |
|------|------|---------|
| `test_anytime_bid_always_accepted` | Unit | Bids accepted at any tick |
| `test_anytime_resolution_on_period` | Unit | Auction resolves on tick % period == 0 |
| `test_anytime_status_shows_accepting` | Unit | Status shows ACCEPTING phase |
| `test_legacy_mode_preserves_phases` | Unit | Legacy mode has WAITING/BIDDING |
| `test_bid_carries_to_next_resolution` | Integration | Bids persist until resolved |

```python
# tests/unit/test_mint_anytime.py

def test_anytime_bid_always_accepted(mint_anytime):
    """Bids are accepted at any tick with anytime_bidding enabled."""
    mint = mint_anytime
    # Even at tick 0
    result = mint.submit_bid("alice", "artifact_1", 100)
    assert result["success"]
    # At tick 1
    mint.on_tick(1)
    result = mint.submit_bid("bob", "artifact_2", 200)
    assert result["success"]

def test_anytime_resolution_on_period(mint_anytime):
    """Auction resolves when tick is multiple of period."""
    mint = mint_anytime
    period = mint._period  # e.g., 50
    mint.submit_bid("alice", "artifact_1", 100)

    # No resolution before period
    for tick in range(1, period):
        result = mint.on_tick(tick)
        assert result is None

    # Resolution at period
    result = mint.on_tick(period)
    assert result is not None
    assert result["resolved"]

def test_anytime_status_shows_accepting(mint_anytime):
    """Status always shows ACCEPTING phase."""
    mint = mint_anytime
    for tick in [0, 10, 25, 49]:
        mint.on_tick(tick)
        status = mint.status()
        assert status["phase"] == "ACCEPTING"

def test_legacy_mode_preserves_phases(mint_legacy):
    """Legacy mode preserves WAITING/BIDDING phases."""
    mint = mint_legacy  # anytime_bidding: false
    # Should reject before first_auction_tick
    result = mint.submit_bid("alice", "artifact_1", 100)
    assert not result["success"]
    assert "not open" in result["error"].lower()
```

---

## E2E Verification

1. Start simulation with `anytime_bidding: true`
2. Agent bids at tick 5 (would be WAITING in legacy mode)
3. Verify bid is accepted
4. Advance to tick = period (e.g., 50)
5. Verify auction resolves and scrip is minted
6. Verify agent can bid again immediately after resolution

---

## Verification

- [ ] `anytime_bidding` config flag exists
- [ ] Bids accepted at any tick when enabled
- [ ] Auctions resolve on schedule (tick % period == 0)
- [ ] Legacy mode preserves current behavior
- [ ] Unit tests pass
- [ ] `docs/architecture/current/genesis_artifacts.md` updated

---

## Notes

**Why this is medium priority:** Current implementation works correctly, just more complex than necessary. This is a simplification, not a bug fix.

**Migration:** Existing simulations using explicit bidding windows can continue with `anytime_bidding: false`. New simulations get the simpler model by default.

See GAPS.md archive (section 5) for original context.
