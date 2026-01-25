# Incentive Architecture: Future Considerations

**Status:** Research notes
**Date:** 2026-01-25

---

## Context

Discussion about separating incentive-based code to enable experimentation with different incentive systems.

## Key Insight: What Are Incentives?

**Incentives = Prompts + Mechanisms**

- **Prompts** tell agents what to value ("maximize scrip", "survive", "cooperate")
- **Mechanisms** reward/punish behaviors that advance those values (mint, pricing, UBI)

Without prompts saying "scrip matters," the mint creates scrip but provides no behavioral incentive. They're inseparable.

## Current State

### Already Configurable (via config.yaml)
- Mint ratio (score → scrip conversion)
- Auction timing, slots, minimum bid
- Genesis method costs
- LLM pricing per model
- Resource quotas and rate limits

### Hardcoded
- Mint = only reward mechanism (creates scrip)
- LLM scoring = only quality signal
- UBI distribution tied to auction mechanics
- "What makes an artifact good" = embedded in scoring prompt

## Implemented: Prompt Injection (Plan #180)

Simple infrastructure to inject mandatory content into all agent prompts:

```yaml
prompt_injection:
  enabled: true
  scope: "all"  # "none" | "genesis" | "all"
  mandatory_prefix: |
    You exist in a resource-constrained environment...
```

This allows experimenting with different goal framings without code changes.

---

## Future: Full Incentive Experimentation Architecture

If we want to experiment with fundamentally different incentive mechanisms (not just different parameters), here's what that might look like:

### Abstraction Layer

```python
class RewardMechanism(Protocol):
    """Interface for different ways to reward agent behavior."""

    def evaluate_contribution(
        self,
        agent_id: str,
        contribution: Contribution  # artifact, action, collaboration, etc.
    ) -> RewardResult:
        """Determine if/how much to reward this contribution."""
        ...

    def distribute(
        self,
        reward_pool: int,
        eligible: list[str],
        context: DistributionContext
    ) -> dict[str, int]:
        """Distribute rewards among agents."""
        ...
```

### Potential Mechanism Implementations

| Mechanism | Rewards | Signal |
|-----------|---------|--------|
| **MintAuction** (current) | Artifact creation | LLM quality score |
| **UsageBased** | Artifacts that get invoked | Invocation count |
| **PeerReview** | Peer-rated contributions | Agent votes |
| **Collaboration** | Joint work | Shared artifact ownership |
| **Reputation** | Consistent good behavior | Historical success rate |
| **Market** | Whatever others will pay | Willingness to pay |

### Configuration Vision

```yaml
incentives:
  mechanisms:
    - type: "mint_auction"
      weight: 0.5
      config:
        scoring: "llm"  # or "usage", "peer_review"
        distribution: "second_price_ubi"

    - type: "usage_royalties"
      weight: 0.3
      config:
        royalty_percent: 10

    - type: "collaboration_bonus"
      weight: 0.2
      config:
        min_contributors: 2
```

### Architectural Requirements

1. **Mechanism registry** - Plug in different reward types
2. **Contribution tracking** - Record what agents do (already have via events)
3. **Reward aggregation** - Combine multiple mechanisms
4. **Distribution strategies** - UBI, proportional, winner-take-all, etc.

### Estimated Effort

- Abstract reward mechanism interface: ~200 lines
- Refactor mint to implement interface: ~300 lines
- Add 2-3 alternative mechanisms: ~500 lines each
- Config-driven mechanism selection: ~100 lines

**Total: ~2 weeks of focused work**

### When to Build This

Build when we have:
1. Specific hypotheses about alternative incentive structures
2. Evidence that current mint isn't producing desired emergence
3. Concrete alternative mechanisms we want to test

Don't build speculatively - the current system is sufficient for observing emergence.

---

## Related Questions

- How do we measure if incentives are "working"? (emergence metrics)
- Can agents themselves propose/vote on incentive changes? (meta-governance)
- Should negative incentives exist? (penalties, scrip decay)
- How do incentives interact with agent prompts/goals?

---

## References

- `src/world/mint_auction.py` - Current auction logic
- `src/world/mint_scorer.py` - LLM-based artifact scoring
- `src/world/genesis/mint.py` - Genesis mint wrapper
- `src/agents/agent.py:732` - Prompt injection point
- `config/schema.yaml` - All configurable parameters
