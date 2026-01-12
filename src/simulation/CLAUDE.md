# Simulation Module

Orchestrates the tick loop and manages persistence.

## Module Responsibilities

| File | Responsibility |
|------|----------------|
| `runner.py` | Main SimulationRunner, tick loop, two-phase execution |
| `checkpoint.py` | Save/restore world state to JSON |
| `types.py` | Type definitions for simulation |

## Execution Model (Current)

**Tick-synchronized, two-phase commit:**

```
1. advance_tick()           # Increment tick, reset flow resources
2. oracle.on_tick()         # Resolve any pending auctions
3. get_state_summary()      # Snapshot world state for agents
4. PHASE 1: parallel think  # asyncio.gather() all agents
5. PHASE 2: sequential exec # Randomized order for fairness
6. Optional checkpoint      # Save state periodically
7. Sleep rate_limit_delay   # Respect API rate limits
8. Repeat
```

## Key Patterns

### Two-Phase Commit
```python
# Phase 1: All agents think in parallel (no side effects)
intents = await asyncio.gather(*[a.propose_action_async() for a in agents])

# Phase 2: Execute in randomized order (side effects happen)
random.shuffle(intents)
for intent in intents:
    world.execute_action(intent)
```

### Checkpoint Round-Trip
```python
# Save
checkpoint.save(world, "checkpoint.json", reason="periodic")

# Restore
world = checkpoint.load("checkpoint.json")
```

## Strict Couplings

Changes to `runner.py` MUST update `docs/architecture/current/execution_model.md`.

## Autonomous Execution Mode (Phase 2)

When `execution.use_autonomous_loops: true`, agents run independently instead of tick-synchronized.

```python
# Autonomous mode: Each agent runs via AgentLoop
from src.world.agent_loop import AgentLoopManager

manager = AgentLoopManager(config)
for agent in agents:
    manager.start_loop(agent)

# Loops run continuously, RateTracker replaces tick-based resource reset
```

Key differences from tick-based:
- Agents run independently (no synchronization)
- `RateTracker` for rolling-window rate limiting
- Resource exhaustion pauses agent (doesn't crash)

See `docs/architecture/current/execution_model.md` for full details.

## Testing

```bash
pytest tests/test_runner.py tests/test_checkpoint.py -v
```
