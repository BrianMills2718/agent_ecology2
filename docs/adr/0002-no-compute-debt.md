# ADR-0002: No Compute Debt

**Status:** Accepted
**Date:** 2026-01-12
**Certainty:** 90%

## Context

How should the system handle agents that exceed their resource allocation?

Options considered:
1. **Allow debt** - Agent goes negative, must repay later
2. **Block until available** - Agent waits for resources to replenish
3. **Fail the action** - Action rejected, agent must retry

Scrip (economic currency) is separate from compute (physical resource).

## Decision

**No debt for renewable resources. Agents are blocked until window has capacity.**

- **Scrip cannot go negative** - Debt as a concept is implemented via contract artifacts (IOUs), not negative balances
- **Compute cannot go negative** - If agent exceeds rate allocation, blocked until rolling window allows more
- **No burst** - Use it or lose it (aligns with LLM provider rate limits anyway)

```python
# When agent tries to use compute:
if not rate_tracker.can_consume(agent_id, tokens_needed):
    # Block or skip - do NOT go negative
    raise ResourceExhausted("Rate limit exceeded, retry later")
```

## Consequences

### Positive

- **Simpler accounting** - No negative balance tracking, no debt collection
- **Predictable behavior** - Agent knows exactly what resources it has
- **Strong trade incentive** - Can't borrow, must acquire from others
- **Aligns with reality** - LLM providers enforce rate limits this way

### Negative

- **Harsh on burst workloads** - Agent with spiky usage pattern may be blocked often
- **No credit system** - Can't "advance" resources to promising agents
- **Starvation risk** - Agent with 0 resources is stuck (must trade scrip for compute)

### Neutral

- Scrip debt CAN exist via contract artifacts (IOU pattern) - just not as negative ledger balances
- Frozen agents can still be rescued via vulture market

## Related

- Gap #1: Rate Allocation (implements this decision)
- Gap #12: Per-Agent LLM Budget
- ADR-0001: Everything is an artifact (debt contracts would be artifacts)
