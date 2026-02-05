# Simulation Module

Orchestrates autonomous artifact loops and manages persistence.

## Module Responsibilities

| File | Responsibility |
|------|----------------|
| `__init__.py` | Module exports (SimulationRunner, checkpoint, types, agent loop) |
| `runner.py` | Main SimulationRunner, artifact loop orchestration |
| `checkpoint.py` | Save/restore world state to JSON |
| `types.py` | Type definitions for simulation |
| `agent_loop.py` | Individual agent loop management |
| `artifact_loop.py` | V4 artifact loop management (Plan #255) |
| `supervisor.py` | AgentSupervisor: auto-restart crashed agents with backoff and death classification |

## Execution Model (Plan #102 - Autonomous Only)

**Time-based autonomous execution:**

Artifact-based agents run independently in their own loops, resource-gated by RateTracker.
ArtifactLoopManager discovers has_loop artifacts and creates loops for each.

Each artifact loop:
1. Check resource availability (rate limits)
2. Get world state snapshot
3. Invoke artifact's run() method
4. Sleep/backoff as needed
5. Repeat

**Key characteristics:**
- Agents are artifact-based (3-artifact clusters: strategy + state + loop)
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
