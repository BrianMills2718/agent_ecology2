# Target Mint Design

What we're building toward for the minting system.

**Last verified:** 2026-01-12

**See current:** Genesis mint in current system uses tick-based bidding windows.

**ADR:** [ADR-0004](../../adr/0004-mint-system-primitive.md)

---

## Overview

The **mint** is a system primitive that creates new scrip based on external validation of agent work. Unlike genesis artifacts (which agents could theoretically replace), the minting capability is developer-controlled - agents cannot create or modify minters.

Key terminology:
- **Mint** - The system primitive that creates new scrip
- **genesis_mint** - The genesis artifact interface for agents to submit work for scoring
- **Mint scorer** - The evaluation component that scores submitted artifacts

---

## Bids Accepted Anytime

### No Bidding Windows

Current system has explicit bidding windows (open/closed phases). Target removes this:

| Current | Target |
|---------|--------|
| Bidding window opens at tick X | Bids accepted anytime |
| Bidding window closes at tick Y | Bids accumulate until resolution |
| Must watch for window | Just bid when ready |

### Simpler Agent Logic

Agents don't need to:
- Poll for window status
- Rush to bid before close
- Track bidding phases

Just: bid whenever you have something to submit.

---

## Periodic Resolution

### Deterministic Schedule

Mint resolves on a fixed schedule:

```yaml
genesis:
  mint:
    resolution_interval: 3600  # seconds (every hour)
    # OR
    resolution_schedule: "0 * * * *"  # cron: top of every hour
```

### What Happens at Resolution

1. Collect all bids since last resolution
2. Select winner(s) by bid amount (Vickrey auction)
3. Score winning artifact(s) via LLM
4. Mint scrip based on score
5. Distribute UBI from losing bids
6. Clear bid queue

### Agents Know the Schedule

Combined with time injection, agents can calculate:

```
Current time: 14:45:00
Resolution schedule: top of every hour
Next resolution: 15:00:00
Time until resolution: 15 minutes
```

---

## Auction Mechanics

### Vickrey (Second-Price) Auction

- Sealed bids (agents don't see others' bids)
- Winner pays second-highest bid
- Incentivizes truthful bidding

### Multiple Winners: Uniform Price

When multiple slots are available, all winners pay the same price:

```yaml
genesis:
  mint:
    slots_per_resolution: 3  # Top 3 bids win
```

**Uniform price mechanism:**
- N winners (top N bids) all pay the (N+1)th highest bid
- Standard mechanism in ad auctions
- Preserves incentive compatibility (truthful bidding optimal)

**Example:**
```
Bids: [100, 80, 60, 40, 20]
Slots: 3

Winners: bids of 100, 80, 60
Price paid: 40 (the 4th highest bid)
Each winner pays 40 scrip
```

**Edge case:** If fewer bids than slots, all bidders win and pay 0.

### Bid Structure

```python
bid(artifact_id, amount)
```

- `artifact_id`: What to submit for scoring
- `amount`: Scrip bid (paid if you win, refunded if you lose)

---

## Scoring

### LLM-Based Evaluation

Winning artifacts scored by external LLM:
- Score range: 0-100
- Evaluation criteria: usefulness, novelty, quality
- Model: configurable (separate from agent models)

### Minting

```
scrip_minted = score / mint_ratio
```

With `mint_ratio: 10`:
- Score 80 → mint 8 scrip
- Score 50 → mint 5 scrip

### UBI Distribution

Losing bids flow to winners as UBI:

```
total_losing_bids = sum(all bids) - winning_bid
ubi_per_agent = total_losing_bids / num_agents
```

---

## Scrip Supply

### How Scrip Enters the System

| Source | Mechanism | Notes |
|--------|-----------|-------|
| Genesis allocation | Initial agent balances | Configurable per agent |
| Mint | Score-based on winning artifacts | Only source of NEW scrip |
| UBI distribution | Redistributes existing scrip | Doesn't create new scrip |

### Monetary Policy

```yaml
genesis:
  mint:
    mint_ratio: 10           # Score 100 = 10 new scrip
    resolution_interval: 60  # Mint opportunity every 60 seconds
```

**Inflation rate:** Depends on:
- How often mint resolves (resolution_interval)
- Quality of submissions (higher scores = more minting)
- Number of submissions (more winners = more minting)

**No scrip destruction:** Scrip circulates forever. Lost agents' scrip remains in system (can be recovered by vulture capitalists if agent is rescued).

### Initial Distribution

```yaml
genesis:
  initial_balances:
    agent_a: 100
    agent_b: 100
    agent_c: 50
    # Total initial supply: 250 scrip
```

New agents spawn with 0 scrip. Must earn or receive transfers.

---

## System vs Genesis Distinction

Per ADR-0004, the **minting capability** is a system primitive:

| Layer | Example | Agent Control |
|-------|---------|---------------|
| System Primitive | Mint capability, Ledger, Event log | None - developer controlled |
| Genesis Artifact | genesis_mint, genesis_ledger | Interface only |

Agents interact with `genesis_mint` to submit artifacts for scoring, but they cannot:
- Create new minters
- Modify minting rules (scoring criteria, amounts, timing)
- Bypass the scoring process

---

## Migration Notes

### Breaking Changes
- Remove `bidding_window` config
- Remove `first_auction_tick` (time-based, not tick-based)
- Remove bid phases (always accepting)
- `on_tick()` becomes time-triggered, not tick-triggered
- Rename `oracle` → `mint` throughout config and code

### Preserved
- Vickrey auction mechanics
- LLM scoring
- Minting formula
- UBI distribution

### New Components
- Time-based resolution scheduler
- Continuous bid accumulation
- Resolution schedule config
