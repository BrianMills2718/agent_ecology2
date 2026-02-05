# Current Mint System

How artifact scoring and scrip minting works today.

**Last verified:** 2026-02-05 (Plan #303: fail-loud audit)

**Source:** `src/world/mint_auction.py` (MintAuction), `src/world/mint_scorer.py`

---

## Overview

The mint is a **kernel primitive** (Plan #254). Agents submit artifacts for scoring via the `mint` kernel action. Periodic auctions resolve winners; winners get scrip minted based on score; losing bids are redistributed as UBI.

**Key change (Plan #254):** Minting moved from `genesis_mint` artifact to kernel action.

## Kernel Action

```json
{"action_type": "mint", "artifact_id": "my_tool", "bid": 5}
```

Returns submission confirmation:
```json
{
  "success": true,
  "submission_id": "mint_sub_abc123",
  "artifact_id": "my_tool",
  "bid": 5
}
```

## Configuration

From `config.yaml` under `genesis.mint.auction`:

| Setting | Default | Description |
|---------|---------|-------------|
| `period_seconds` | 120.0 | Seconds between auction resolutions |
| `bidding_window_seconds` | 60.0 | Duration of bidding phase |
| `first_auction_delay_seconds` | 30.0 | Delay before first auction |
| `minimum_bid` | 1 | Lowest accepted bid |
| `mint_ratio` | 10 | Score / ratio = scrip minted |

## Query Submissions

Use `query_kernel` to check mint status:

```json
{"action_type": "query_kernel", "query_type": "mint_submissions", "params": {}}
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
