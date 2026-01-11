# Oracle Auction Design

## Overview

This document describes the redesign of the oracle submission system from fixed-cost to auction-based, along with related changes to genesis method costs and UBI distribution.

## Design Goals

1. **Emergent optimization** - Market-based pricing over hardcoded rules
2. **Encourage infrastructure** - Agents should build before submitting
3. **Scrip conservation** - No burning; scrip is redistributed as UBI
4. **Clean resource separation** - Compute for actions, scrip for trade

---

## Key Changes

### 1. Genesis Method Costs: Compute, Not Scrip

**Current:** Genesis methods cost scrip (burned).
**New:** Genesis methods cost compute (physical resource).

| Method | Old Cost | New Cost |
|--------|----------|----------|
| `genesis_ledger.transfer` | 1 scrip | 1 compute |
| `genesis_ledger.spawn_principal` | 1 scrip | 1 compute |
| `genesis_ledger.transfer_ownership` | 1 scrip | 1 compute |
| `genesis_rights_registry.transfer_quota` | 1 scrip | 1 compute |
| `genesis_escrow.deposit` | 1 scrip | 1 compute |
| `genesis_oracle.submit` | 5 scrip | **REMOVED** (auction only) |

**Rationale:** Compute is a physical resource (time/cycles). Scrip is purely economic. Genesis methods consume time, not money.

### 2. Oracle Auction System

**Current:** Any agent can submit anytime for 5 scrip.
**New:** Periodic auction; highest bidder wins submission slot.

#### Auction Mechanics

```
Configuration:
  oracle.auction_period: 50         # Ticks between auctions
  oracle.bidding_window: 10         # Ticks for bidding phase
  oracle.first_auction_tick: 50     # Grace period before first auction
  oracle.slots_per_auction: 1       # Submissions per auction (configurable)
  oracle.minimum_bid: 1             # Floor to prevent trivial bids

Timeline (for period=50, window=10):
  Tick 50:  Bidding opens for auction #1
  Tick 60:  Bidding closes, winner determined, artifact scored
  Tick 100: Bidding opens for auction #2
  ...
```

#### Bidding Flow

1. **Bid phase** (ticks N to N+window):
   - Agents call `genesis_oracle.bid([artifact_id, amount])`
   - Bids are sealed (not visible to other agents)
   - Multiple bids allowed; latest bid per agent counts
   - Bid scrip is held (not yet deducted)

2. **Resolution** (tick N+window):
   - Highest bidder wins
   - Winner pays **second-highest bid** (Vickrey auction)
   - If only one bidder, pays minimum_bid
   - Losing bidders' scrip is released (not deducted)

3. **Scoring**:
   - Winner's artifact is scored by LLM
   - Scrip minted based on score (score / mint_ratio)

4. **UBI Distribution**:
   - Winning bid amount is split equally among all agents
   - Example: 5 agents, winning bid 50 → each gets 10 scrip

#### New Oracle Methods

| Method | Args | Cost | Description |
|--------|------|------|-------------|
| `status` | `[]` | 0 | Auction status (phase, current tick, bids count) |
| `bid` | `[artifact_id, amount]` | 0 | Submit sealed bid (during bidding window) |
| `check` | `[artifact_id]` | 0 | Check if your artifact won/status |

**Removed:** `submit` (replaced by `bid`), `process` (automatic at auction close)

### 3. UBI Distribution

When an auction closes:
1. Winner pays their bid (second-price amount)
2. That scrip is divided equally among ALL agents (including winner)
3. Total scrip in system stays constant (minus minting which adds)

```
Example:
  5 agents, winner bids 50, second-place bid 30
  Winner pays: 30 (second-price)
  UBI per agent: 30 / 5 = 6 scrip each
  Winner net: -30 + 6 = -24 (plus whatever oracle mints)
  Others net: +6 each
```

---

## Configuration Changes

### New Config Section: `genesis.oracle`

```yaml
genesis:
  oracle:
    id: "genesis_oracle"
    description: "Auction-based oracle for artifact scoring"
    mint_ratio: 10

    # Auction configuration
    auction_period: 50          # Ticks between auctions
    bidding_window: 10          # Duration of bidding phase
    first_auction_tick: 50      # When first auction opens
    slots_per_auction: 1        # Winners per auction
    minimum_bid: 1              # Floor bid amount

    methods:
      status:
        cost: 0
        description: "Check auction status. Args: []"
      bid:
        cost: 0  # Compute cost, not scrip
        description: "Submit sealed bid. Args: [artifact_id, amount]"
      check:
        cost: 0
        description: "Check submission/bid status. Args: [artifact_id]"
```

### Changed: Genesis Method Costs

All genesis method `cost` fields now represent **compute**, not scrip:

```yaml
genesis:
  ledger:
    methods:
      transfer:
        cost: 1  # 1 COMPUTE (was: 1 scrip)
```

---

## Files to Modify

### Documentation
| File | Changes |
|------|---------|
| `docs/AGENT_HANDBOOK.md` | Update genesis costs, oracle section, add auction docs |
| `CLAUDE.md` | Update scrip/resource model description |
| `config/config.yaml` | Add auction config, update cost comments |
| `config/schema.yaml` | Document new fields |

### Code
| File | Changes |
|------|---------|
| `src/config_schema.py` | Add `OracleAuctionConfig` Pydantic model |
| `src/world/genesis.py` | Rewrite `GenesisOracle` for auction; add bid tracking |
| `src/world/world.py` | Change method cost deduction: compute not scrip |
| `src/world/ledger.py` | Add `distribute_ubi(amount)` method |
| `src/simulation/runner.py` | Add auction tick handling (resolve auctions) |

### Tests
| File | Changes |
|------|---------|
| `tests/test_oracle_auction.py` | New: auction bidding, resolution, UBI |
| `tests/test_genesis_costs.py` | Update: verify compute deduction |
| `tests/test_ledger.py` | Add: UBI distribution tests |

---

## Uncertainties and Questions

### Resolved (by user)
- [x] Auction frequency: 50 ticks (configurable)
- [x] Multiple slots: configurable
- [x] Bootstrapping: grace period (first_auction_tick)
- [x] Genesis fees: compute, not scrip
- [x] UBI scope: oracle bids only (genesis fees are compute)

### Open Questions

1. **Tie-breaking**: If two agents bid the same amount, who wins?
   - Option A: Random selection
   - Option B: First bid submitted wins
   - **Recommendation:** Random (fairer)

2. **Bid visibility**: Can agents see current bid count during bidding?
   - Option A: Fully sealed (no info)
   - Option B: Show count but not amounts
   - **Recommendation:** Show count (adds strategy without revealing amounts)

3. **Bid updates**: Can an agent update their bid during the window?
   - Option A: Latest bid counts (can increase/decrease)
   - Option B: Bids are final once submitted
   - **Recommendation:** Allow updates (more flexible)

4. **Failed scoring**: What if LLM scoring fails?
   - Option A: Refund winner's bid
   - Option B: Winner still pays, no scrip minted
   - **Recommendation:** Refund (fairer to winner)

5. **Empty auction**: What if no one bids?
   - Option A: Auction passes, nothing happens
   - Option B: Carry over to next period
   - **Recommendation:** Pass (simpler)

6. **Multi-slot ordering**: If slots > 1, how are winners ordered?
   - Top N bidders, each pays their own second-price?
   - Or uniform price for all winners?
   - **Recommendation:** Each pays next-lower bid (generalized Vickrey)

---

## Implementation Order

1. **Config first**: Add all new config fields with defaults
2. **Ledger**: Add `distribute_ubi()` method
3. **World**: Change method cost deduction to compute
4. **Genesis Oracle**: Rewrite with auction state machine
5. **Runner**: Add auction resolution at tick boundaries
6. **Tests**: Cover all new behavior
7. **Docs**: Update handbook and CLAUDE.md

---

## State Machine: Oracle Auction

```
States:
  WAITING    - Before first_auction_tick
  BIDDING    - Accepting bids (bidding_window ticks)
  CLOSED     - Bidding ended, ready to resolve
  SCORING    - Winner determined, scoring in progress

Transitions:
  WAITING → BIDDING    at tick >= first_auction_tick
  BIDDING → CLOSED     after bidding_window ticks
  CLOSED  → SCORING    immediately (resolve auction)
  SCORING → BIDDING    after scoring complete (next period)

Data:
  current_bids: dict[agent_id, (artifact_id, amount)]
  auction_start_tick: int
  last_winner: Optional[agent_id]
  last_score: Optional[int]
```
