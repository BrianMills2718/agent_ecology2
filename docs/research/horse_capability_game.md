# HORSE: Capability Development Through Competitive Games

**Status:** Research/Design Phase
**Date:** 2026-01-24

## The Problem

How do we incentivize agents to develop increasing capability in a meaningful way without:
1. Exogenously defining what "capability" means (defeats emergence)
2. Creating broken economic incentives (inflation, farming)
3. Requiring agents to be sophisticated enough to play complex market games

The goal is an **endogenous mechanism** - pressure for capability development that arises from within the system, not imposed from outside.

## Why HORSE?

The basketball game HORSE has appealing properties:
- **Capability defined by demonstration** - You show what you can do, not describe it
- **Natural difficulty calibration** - Too easy = everyone matches. Impossible = you can't demonstrate first
- **Learning through imitation** - Trying to replicate is how you learn
- **Concrete targets** - "Do what I just did" is specific and observable

Children learn through this kind of play. "Watch what I can do!" → imitation → iteration.

## Design Evolution

### Initial Concept: Voluntary Challenges with Stakes

```
1. Agent A does something notable
2. A posts challenge: "I did X, bet you can't"
3. Agent B accepts, matches stake
4. B attempts replication
5. Judgment: success/failure
6. Stakes distributed
```

**Problems:**
- Leads to adverse selection (only compete where strong)
- Requires stake capital to participate
- Cold start: who issues first challenge?

### Alternative: Random Pairing with Alternating Challenges

```
1. Random pairing (forced)
2. Coin flip for who challenges first
3. Alternate rounds - each agent sets one challenge
4. Match continues until someone "spells HORSE"
```

**Problem:** Rewards generalists, punishes specialists. The opposite of what we want for division of labor and trade.

### Alternative: Observation-Based Implicit Challenges

```
1. Agent A does something (normal operation)
2. Observable in event log
3. Agent B sees it, tries to replicate
4. Success/failure tracked
```

**Problem:** Still needs economic incentives to work.

### Alternative: Bounty Model

```
1. Challenge posted: "Can anyone do X?"
2. First to demonstrate claims bounty
```

**Problem:** Bounties are exogenous - someone external defines what's valuable.

## The Judgment Problem

For any replication-based game, we need to determine: did Agent B successfully replicate Agent A's feat?

### The Gaming Problem

If you specify test cases upfront:
- Agent can hardcode: `if input == 9: return 3`
- Goodhart's Law: measure becomes target, ceases to be good measure

### Property-Based Verification (Preferred Approach)

Instead of input→output pairs, define **properties that must hold**:

```
Task: "Build a sqrt function"
Property: output² ≈ input (within tolerance)
Verification: Run on random/adversarial inputs, check property holds
```

**Advantages:**
- Can test with ANY input
- Don't need to know "right answer" in advance
- Verifiable by computation
- Challenger doesn't need correct implementation, just correct property

### Other Judgment Options

| Approach | Pros | Cons |
|----------|------|------|
| LLM judge | Flexible, handles any task | Costly, inconsistent, gameable |
| Property-based | Deterministic, cheap | Need properties defined |
| Peer voting | Decentralized | Complex, needs quorum |
| Hidden test cases | Simple | Challenger must create good cases |

## Economic Considerations

### Broken: Paying Both Parties

```
Copy succeeds: copier gets 5, original gets 2
```

**Problems:**
- Where does scrip come from? (inflation)
- No cost to attempt (spam)
- Agents could farm by copying each other

### Zero-Sum Games

**Pros:**
- Real stakes, meaningful competition
- No inflation
- Selection pressure
- Can't be farmed

**Cons:**
- Risk aversion - why attempt what you might lose?
- Rich get richer
- Cold start death spiral for new agents
- Discourages exploration

### Middle Grounds Considered

1. **Zero-sum game, but capability is real prize** - Scrip loss is "tuition"
2. **Reputation-based, not scrip-based** - Elo-style rating affects trade terms
3. **Asymmetric stakes** - Agents choose their risk level
4. **Negative-sum (house cut)** - Deflationary, makes games expensive

## Current Best Direction: Forced Dual-Task Competition

### The Game

```
1. Two agents paired (forced - random or by rating)
2. Each agent proposes one task
3. Both agents attempt BOTH tasks
4. Whoever performs better overall wins the pot
```

### Example

```
Agent A (sqrt specialist) vs Agent B (string specialist)
Wager: 10 scrip each (20 in pot)

A proposes: "compute sqrt to 6 decimal places"
B proposes: "parse nested JSON"

Results (pass/fail):
         Task A    Task B
Agent A:  pass      fail     = 1
Agent B:  fail      pass     = 1

Tie - each keeps their stake? Or some tiebreaker?
```

### Why This Might Work

| Property | Why It Helps |
|----------|--------------|
| Forced pairing | Can't hide in comfort zone |
| Each proposes a task | Specialists can play to strengths |
| Both do both | Tests breadth AND depth |
| Zero-sum wager | Real stakes, no inflation |
| Pass/fail scoring | Simpler to judge |

### What This Incentivizes

- Get really good at your specialty (win your proposed task)
- Don't be terrible at other things (limit losses on opponent's task)
- Propose tasks that maximize YOUR advantage
- Capability development through forced exposure to new challenges

## Open Questions

### Judgment
- How to verify pass/fail for arbitrary tasks?
- Property-based verification seems promising but needs more design
- LLM as fallback judge?

### Pairing
- Random pairing? Rating-based matching?
- How often are agents forced to compete?
- What if skill gap is huge?

### Economics
- What if an agent can't afford the wager?
- Fixed wager or variable?
- What happens to scrip in a tie?

### Task Proposal
- Any constraints on what tasks can be proposed?
- How to prevent impossible/trivial tasks?
- Time limits on task completion?

### Cold Start
- How do new agents enter the system?
- Protected period before forced competition?
- Starter stake?

## Relationship to Existing System

### Potential Implementation

New genesis artifact: `genesis_arena` or `genesis_dojo`

```python
# Methods
pair_agents() -> match_id           # System calls periodically
propose_task(match_id, task) -> ok  # Each agent proposes
attempt(match_id, task_id) -> result # Attempt a task
resolve(match_id) -> winner         # Determine outcome
```

### Integration Points

- **Event log**: All attempts observable
- **Ledger**: Wager transfers
- **Property verification**: New capability needed
- **Scheduler**: Periodic forced pairings

## References

- HORSE (basketball) - alternating challenge selection
- Elo rating systems - skill-based matching
- Goodhart's Law - measure as target problem
- Property-based testing - QuickCheck-style verification

## Next Steps

1. Decide on judgment mechanism (property-based + LLM fallback?)
2. Design task proposal constraints
3. Prototype `genesis_arena` artifact
4. Test with simple capability domain (math functions?)
5. Iterate based on observed behavior
