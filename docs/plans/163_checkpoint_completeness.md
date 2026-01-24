# Plan 163: Checkpoint Completeness

**Status:** 📋 Planned
**Priority:** High
**Blocked By:** -
**Blocks:** Long-running simulations, reliable resume

---

## Problem Statement

The checkpoint system (55% maturity) has significant gaps that make resume unreliable:

### What's Saved
- Tick count
- Agent scrip/LLM token balances
- Cumulative API cost
- Artifacts (serialized via `to_dict()`)
- Agent IDs

### What's NOT Saved
- Agent memory (Mem0/ArtifactMemory contents)
- Agent state (current workflow state, working memory)
- Learned knowledge and experiences
- Relationships between agents
- Contract state
- Invocation history

### Consequences
- **Resume is non-deterministic** - Agents restart with amnesia
- **Long simulations are brittle** - Any interruption loses learned behavior
- **Can't pause and continue** - Only "start over with same balances"

---

## Evidence

From architecture review:
1. `checkpoint.py` only saves `ledger.get_all_balances()` and artifact dicts
2. `AgentStateStore` (SQLite) exists but isn't used in checkpoint flow
3. No artifact reconstruction logic - just raw dicts saved
4. Legacy format handling suggests evolution without version tracking

---

## Solution

### Phase 1: Agent State Persistence

Integrate `AgentStateStore` into checkpoint:

```python
def save_checkpoint(world, agents, path, reason):
    data = {
        "version": 2,  # ADD: Version for migration
        "tick": world.current_tick,
        "balances": world.ledger.get_all_balances(),
        "artifacts": [a.to_dict() for a in world.artifact_store.artifacts.values()],
        "agents": [agent.agent_id for agent in agents],
        "agent_states": {  # ADD: Full agent state
            agent.agent_id: {
                "current_state": agent.current_state,
                "working_memory": agent.working_memory,
                "turn_history": agent.turn_history[-20:],  # Last 20 turns
                "action_counts": agent.action_counts,
            }
            for agent in agents
        },
        "cumulative_api_cost": engine.cumulative_api_cost,
        "reason": reason,
        "timestamp": datetime.now().isoformat(),
    }
```

### Phase 2: Memory Artifact Persistence

If using ArtifactMemory (Plan #10), memories are already artifacts - they'll be saved.

If using Mem0/Qdrant, need explicit export:
```python
"agent_memories": {
    agent.agent_id: agent.memory.export_all()  # New method
    for agent in agents
    if hasattr(agent, 'memory')
}
```

### Phase 3: Atomic Writes

Prevent corruption from partial writes:
```python
def save_checkpoint(world, agents, path, reason):
    temp_path = f"{path}.tmp"
    with open(temp_path, 'w') as f:
        json.dump(data, f, indent=2)
    os.rename(temp_path, path)  # Atomic on POSIX
```

### Phase 4: Version Migration

Handle format evolution:
```python
def load_checkpoint(path):
    data = json.load(open(path))
    version = data.get("version", 1)

    if version == 1:
        data = migrate_v1_to_v2(data)

    return data
```

---

## Files Affected

- `src/simulation/checkpoint.py` (modify) - Full state save/restore
- `src/agents/agent.py` (modify) - Add `export_state()` / `restore_state()` methods
- `src/agents/memory.py` (modify) - Add `export_all()` method if using Mem0
- `src/simulation/runner.py` (modify) - Pass agent state to checkpoint
- `tests/test_checkpoint.py` (modify) - Test round-trip with agent state

---

## Required Tests

| Test | Verifies |
|------|----------|
| `test_checkpoint_saves_agent_state` | Agent current_state, working_memory saved |
| `test_checkpoint_roundtrip_preserves_memory` | Memories survive save/load |
| `test_checkpoint_atomic_write` | Partial write doesn't corrupt |
| `test_checkpoint_version_migration` | v1 format loads correctly |
| `test_resume_continues_behavior` | Agent doesn't repeat actions after resume |

---

## Success Criteria

1. Resume simulation after interruption with agent behavior continuity
2. Agent working memory preserved across checkpoint
3. No data loss on partial write
4. Format version tracked and migrateable

---

## Notes

This plan complements dashboard work (which visualizes state) by ensuring state can be reliably persisted and restored for long-running simulations.
