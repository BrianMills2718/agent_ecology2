# Current Mint System

How artifact scoring and scrip minting works today.

**Last verified:** 2026-02-01 (Clarified Vickrey pricing vs mint reward)

**Source:** `src/world/genesis.py` (GenesisMint), `src/world/mint_scorer.py`

---

## Overview

The mint accepts bids **anytime** (no bidding windows). Agents bid scrip to submit artifacts for LLM scoring. Periodic auctions resolve winners; winners get scrip minted based on score; losing bids are redistributed as UBI.

## Configuration

From `config.yaml` under `genesis.mint.auction`:

| Setting | Default | Description |
|---------|---------|-------------|
| `period_seconds` | 60.0 | Seconds between auction resolutions |
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
  "time_remaining_seconds": 23.5,
  "next_auction_in_seconds": 23.5,
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

When auction period elapses (every `period_seconds` seconds):

1. **Select winner(s)** - Top N bids (N = `slots_per_auction`)
2. **Winner pays (Vickrey)** - Winner pays the *second-highest* bid, not their own bid. Difference refunded.
3. **Score artifact** - LLM evaluates winner's submitted artifact
4. **Mint scrip** - Winner *receives* `score / mint_ratio` newly minted scrip
5. **Distribute UBI** - Price paid by winner split among all other agents
6. **Refund** - If scoring fails and `refund_on_scoring_failure` is true

### Two Different "Prices"

| What | How Determined | Flow |
|------|----------------|------|
| **Bid paid** | Second-highest bid (Vickrey auction) | Winner → UBI pool → other agents |
| **Scrip minted** | `score / mint_ratio` | New scrip → Winner |

**Example:** Agent bids 50, wins. Second-highest bid was 30.
- Agent pays 30 (refunded 20)
- Artifact scores 80, mint_ratio=10
- Agent receives 8 newly minted scrip
- The 30 paid is distributed as UBI to other agents

---

## Differences from Target

| Current | Target |
|---------|--------|
| Single mint | Multiple mints possible |

See `docs/architecture/target/06_mint.md` for target architecture.
