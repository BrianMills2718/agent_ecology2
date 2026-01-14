# ADR-0008: Token Bucket Rate Limiting for Flow Resources

**Status:** Accepted
**Date:** 2026-01-14
**Certainty:** 90%

## Context

Flow resources (CPU, LLM rate) need rate limiting. Two approaches considered:

1. **Discrete refresh** - Allocate N units per period, reset at period boundary
2. **Rolling window (token bucket)** - Continuous accumulation up to a cap

Discrete refresh creates "spend before reset" pressure, leading to wasteful behavior at period boundaries. Agents rush to use allocations before they're lost.

## Decision

**Use token bucket (rolling window) for all flow resources.** Capacity accumulates continuously at a fixed rate, capped at maximum.

```python
# Token bucket mechanics
available = min(capacity, balance + elapsed_time * rate)

# Example: rate = 10/sec, capacity = 100
# T=0:  balance = 100
# T=5:  spend 60 -> balance = 40
# T=10: balance = min(100, 40 + 5*10) = 90
```

**Properties:**
- No discrete "refresh" moments - smooth accumulation
- Capacity capped (can't hoard indefinitely)
- Unused capacity naturally fills over time
- Similar to API rate limits (tokens per minute)

## Consequences

### Positive

- **No gaming** - No artificial urgency at period boundaries
- **Smoother behavior** - Resources available when needed, not in bursts
- **Natural fairness** - Heavy users blocked, light users accumulate capacity
- **Intuitive** - Maps to familiar API rate limiting patterns

### Negative

- **More complex tracking** - Need timestamps, not just counts
- **Burst handling** - Can't burst past capacity even if period average is low
- **Strict allocation** - No "borrowing from next period" possible

### Neutral

- Rates calibrated to Docker container capacity, not host machine
- Creates trade incentive (strict limits = value in trading capacity)

## Related

- Gap #1: Rate Allocation
- Gap #31: Resource Measurement
- ADR-0006: Minimal External Dependencies (custom implementation vs library)
