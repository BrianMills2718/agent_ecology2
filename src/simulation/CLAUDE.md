# Simulation Module

Orchestrates autonomous agent loops and manages persistence.

## Module Responsibilities

| File | Responsibility |
|------|----------------|
| `runner.py` | Main SimulationRunner, autonomous agent loops |
| `checkpoint.py` | Save/restore world state to JSON |
| `types.py` | Type definitions for simulation |
| `agent_loop.py` | Individual agent loop management |

## Execution Model (Plan #102 - Autonomous Only)

**Time-based autonomous execution:**

Agents run independently in their own loops, resource-gated by RateTracker.
Each agent loop:
1. Check resource availability (rate limits)
2. Get world state snapshot
3. Decide action (LLM call)
4. Execute action
5. Sleep/backoff as needed
6. Repeat

```python
# Autonomous mode: Each agent runs via AgentLoop
from src.world.agent_loop import AgentLoopManager

manager = AgentLoopManager(rate_tracker)
for agent in agents:
    manager.create_loop(agent_id, decide_fn, execute_fn)

manager.start_all()  # Agents run continuously
# RateTracker handles rate limiting via rolling windows
```

**Key characteristics:**
- Agents run independently (no synchronization)
- `RateTracker` for rolling-window rate limiting
- Resource exhaustion pauses agent (doesn't crash)
- Time-based auctions via periodic mint update

## Key Patterns

### Checkpoint Round-Trip
```python
# Save
checkpoint.save(world, "checkpoint.json", reason="periodic")

# Restore
world = checkpoint.load("checkpoint.json")
```

## Strict Couplings

Changes to `runner.py` MUST update `docs/architecture/current/execution_model.md`.

## Testing

```bash
pytest tests/integration/test_runner.py tests/test_checkpoint.py -v
```
