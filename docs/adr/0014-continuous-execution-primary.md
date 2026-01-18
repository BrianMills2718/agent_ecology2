# ADR-0014: Continuous Execution as Primary Model

**Status:** Proposed
**Date:** 2026-01-17

## Context

The agent ecology simulation supports two execution models:

1. **Continuous/Autonomous**: Agents run independent loops via `AgentLoop`, resource-gated by `RateTracker`. Each agent continuously decides and acts at its own pace.

2. **Tick-based**: All agents synchronized to discrete ticks. Runner controls when agents think (Phase 1: parallel) and act (Phase 2: sequential randomized).

Both are implemented and working. However, documentation (CLAUDE.md, agents.md, execution_model.md) presents tick-based as the primary model, with continuous as an "alternative." This causes confusion:

- Claude Code instances assume tick-based architecture when designing features
- New features (like configurable workflows) are designed around ticks instead of continuous loops
- The mental model in docs doesn't match the actual default behavior

### Analysis: Which Model Better Serves Emergence?

| Criterion | Tick-Based | Continuous |
|-----------|------------|------------|
| **Selection pressure** | All agents act same # of times | Efficient agents do more |
| **Strategy diversity** | Forced same cadence | Fast/slow strategies possible |
| **Resource scarcity** | Tick resets mask burn rate | Real resource competition |
| **Realism** | Artificial synchronization | Real systems are async |
| **Determinism** | Reproducible | Non-deterministic |
| **Debugging** | Easy to step through | Harder to reproduce |

For emergence - our core goal - continuous is superior because:
1. It creates selection pressure on efficiency
2. It enables strategy differentiation
3. It makes resource scarcity real, not artificial

Tick-based remains valuable for debugging and deterministic testing.

## Decision

**Continuous execution is the primary execution model.** Tick-based is a legacy/debug mode.

This means:
1. Documentation presents continuous as the default, tick-based as "debug mode"
2. Examples use `--duration` not `--ticks`
3. Features (workflows, etc.) are designed around continuous loops, not ticks
4. `AgentLoop._execute_iteration()` is the integration point for agent-internal logic

### CLI Implications

```bash
# Primary (continuous)
python run.py --duration 60 --agents 3

# Debug mode (tick-based)
python run.py --ticks 10 --agents 1
```

### Architecture Implications

New features integrate with:
```
AgentLoop._execute_iteration()
    -> agent.decide_action()   # Workflow logic lives here
    -> agent.execute_action()
```

NOT with tick-based `SimulationRunner.run()` tick loop.

## Consequences

### Positive

- Clearer mental model for developers and AI assistants
- Features designed for emergence, not artificial synchronization
- Documentation matches actual default behavior
- Enables proper selection pressure on agent strategies

### Negative

- Harder to reproduce specific scenarios (non-deterministic)
- More complex debugging (use tick-based mode for this)
- Race conditions possible (mitigated by artifact-level consistency)

### Neutral

- Both modes remain available; this is about primacy, not removal
- Existing tick-based tests continue to work

## Related

- Plan #2: Continuous Execution (implementation)
- Plan #65: Documentation alignment (updates docs to match this ADR)
- ADR-0013: Configurable Agent Workflows (should integrate with continuous, not ticks)
