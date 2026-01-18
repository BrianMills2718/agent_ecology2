# Current Mint System

How artifact scoring and scrip minting works today.

**Last verified:** 2026-01-17 (Plan #5 - Anytime bidding)

**Source:** `src/world/genesis.py` (GenesisMint), `src/world/mint_scorer.py`

---

## Overview

The mint accepts bids **anytime** (no bidding windows). Agents bid scrip to submit artifacts for LLM scoring. Periodic auctions resolve winners; winners get scrip minted based on score; losing bids are redistributed as UBI.

## Configuration

From `config.yaml` under `genesis.mint.auction`:

| Setting | Default | Description |
|---------|---------|-------------|
| `period` | 10 | Ticks between auction resolutions |
| `slots_per_auction` | 1 | Winners per auction |
| `minimum_bid` | 1 | Lowest accepted bid |
| `mint_ratio` | 10 | Score / ratio = scrip minted |

> **Deprecated (ignored):** `bidding_window`, `first_auction_tick` - Bids now accepted anytime.

## Methods

### `genesis_mint.status()`
Returns auction state:
```json
{
  "success": true,
  "current_tick": 7,
  "next_auction_tick": 10,
  "minimum_bid": 1,
  "slots_per_auction": 1,
  "pending_bids": 2
}
```

### `genesis_mint.bid(artifact_id, amount)`
Submit bid for artifact scoring:
- Bids accepted **anytime** (no bidding window)
- Bid amount held in escrow until auction resolves
- Must be ≥ `minimum_bid`

### `genesis_mint.check(artifact_id)`
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

## Scoring (MintScorer)

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
| Single mint | Multiple mints possible |

See `docs/architecture/target/06_mint.md` for target architecture.
