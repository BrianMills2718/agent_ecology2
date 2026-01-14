# ADR-0010: Continuous Agent Loops

**Status:** Accepted
**Date:** 2026-01-14
**Certainty:** 90%

## Context

Two execution models considered:

1. **Tick-synchronized** - All agents execute once per tick, sequentially
2. **Continuous autonomous** - Each agent runs its own loop independently

Tick-synchronized execution artificially constrains agent productivity and creates unrealistic synchronization. Real agents (humans, programs) don't wait for a global clock.

## Decision

**Agents are continuous autonomous loops.** Each agent runs independently: `while alive: think -> act -> repeat`.

```python
# Agent execution model
async def run_agent(agent: Agent):
    while agent.is_alive():
        # Agent decides when and what to do
        intent = await agent.think()
        result = await executor.execute(intent)
        await agent.reflect(result)
        # No tick dependency - agent controls its pace
```

**Ticks become metrics windows, not execution triggers:**
- Tick = time window for aggregating metrics
- Agents don't "wait for tick" to act
- Multiple agents can act concurrently

## Consequences

### Positive

- **Natural productivity** - Agents work at their own pace
- **Realistic model** - Matches how real autonomous agents behave
- **Concurrency** - Multiple agents can work simultaneously
- **No artificial waiting** - Resources used as available, not on schedule

### Negative

- **Complexity** - Async coordination more complex than turn-based
- **Race conditions** - Concurrent access needs proper handling
- **Observation harder** - No clean "state at tick N" snapshots
- **Significant refactor** - Current code is tick-synchronized

### Neutral

- Rate limiting (ADR-0008) naturally throttles over-active agents
- Event log provides observability without sync points

## Related

- ADR-0008: Token Bucket Rate Limiting (natural throttling)
- Gap #2: Continuous Execution
- Gap #21: Testing for Continuous Execution
