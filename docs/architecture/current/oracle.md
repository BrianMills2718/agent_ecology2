# Current Oracle System

How artifact scoring and scrip minting works today.

**Last verified:** 2026-01-12

**Source:** `src/world/genesis.py` (GenesisOracle), `src/world/oracle_scorer.py`

---

## Overview

The oracle runs periodic auctions where agents bid scrip to submit artifacts for LLM scoring. Winners get scrip minted based on score; losing bids are redistributed as UBI.

## Auction Phases

| Phase | Description |
|-------|-------------|
| `WAITING` | Before `first_auction_tick` |
| `BIDDING` | Accepting bids (during `bidding_window`) |
| `CLOSED` | Between auctions, processing results |

## Configuration

From `config.yaml` under `genesis.oracle.auction`:

| Setting | Default | Description |
|---------|---------|-------------|
| `period` | 10 | Ticks between auctions |
| `bidding_window` | 5 | Ticks to accept bids |
| `first_auction_tick` | 5 | When first auction starts |
| `slots_per_auction` | 1 | Winners per auction |
| `minimum_bid` | 1 | Lowest accepted bid |
| `mint_ratio` | 10 | Score / ratio = scrip minted |

## Methods

### `genesis_oracle.status()`
Returns auction state:
```json
{
  "success": true,
  "phase": "BIDDING",
  "current_tick": 7,
  "next_auction_tick": 10,
  "minimum_bid": 1,
  "slots_per_auction": 1
}
```

### `genesis_oracle.bid(artifact_id, amount)`
Submit bid for artifact scoring:
- Bid amount held in escrow
- Must be ≥ `minimum_bid`
- Only during BIDDING phase

### `genesis_oracle.check(artifact_id)`
Check submission status:
```json
{
  "success": true,
  "submission": {
    "status": "scored",
    "score": 75,
    "reason": "Well-structured utility function"
  }
}
```

---

## Scoring (OracleScorer)

LLM evaluates submitted artifacts on:
- Correctness and functionality
- Usefulness (solves real problem)
- Code structure and readability
- Error handling
- Originality (duplicate detection via content hash)

**Score ranges:**
| Range | Meaning |
|-------|---------|
| 0-10 | Broken, trivial, or useless |
| 11-30 | Minimal utility, poor quality |
| 31-50 | Basic functionality |
| 51-70 | Solid tool, good quality |
| 71-90 | Excellent utility |
| 91-100 | Exceptional, innovative |

**Duplicate detection:** Content hashed (MD5). Exact duplicates score 0.

---

## Auction Resolution

When bidding window closes:

1. **Select winner(s)** - Top N bids (N = `slots_per_auction`)
2. **Score artifact** - LLM evaluates winner's submitted artifact
3. **Mint scrip** - `score / mint_ratio` scrip to winner
4. **Distribute UBI** - Losing bids split among all agents (excluding winner)
5. **Refund** - If scoring fails and `refund_on_scoring_failure` is true

---

## Differences from Target

| Current | Target |
|---------|--------|
| Tick-based auction phases | Bids anytime, periodic resolution |
| Bidding window required | No bidding window |
| Single oracle | Multiple oracles possible |

See `docs/architecture/target/06_oracle.md` for target architecture.
