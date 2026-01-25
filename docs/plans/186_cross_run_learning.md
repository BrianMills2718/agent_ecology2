# Plan #186: Cross-Run Learning for Genesis Agents

**Status:** In Progress
**Priority:** Medium
**Complexity:** Low
**Blocks:** Cumulative agent improvement

## Problem

Genesis agents (_3 generation) write learnings to `{agent_id}_working_memory` artifacts during simulation via `learn_from_outcome` workflow steps. However, these learnings are lost between simulation runs because:

1. Each run starts with fresh agent artifacts
2. No mechanism to load learnings from previous runs
3. Agents can't improve over multiple simulations

## Solution

Add ability to load agent working_memory from a previous run's checkpoint file.

### Config Options

```yaml
# In config.yaml
learning:
  cross_run:
    enabled: true                    # Enable cross-run learning
    prior_checkpoint: null           # Path to checkpoint file (null = auto-discover)
    auto_discover: true              # Auto-find latest checkpoint in logs/
    load_working_memory: true        # Load working_memory from prior run
    load_failure_history: false      # Optionally load failure history too
```

### Implementation

1. **Add config options** to schema.yaml and config.yaml
2. **Add `_load_prior_learnings()` method** to SimulationRunner
3. **Call in `_create_agents()`** after agents are created
4. **Only restore working_memory** (not action_history which is per-run)

### Code Changes

```python
# In SimulationRunner._create_agents():
def _create_agents(self, agent_configs):
    # ... existing agent creation ...

    # Load prior learnings if enabled
    if self.config.get("learning", {}).get("cross_run", {}).get("enabled", False):
        prior_states = self._load_prior_learnings()
        for agent in agents:
            if agent.agent_id in prior_states:
                # Only restore working_memory, not per-run state
                wm = prior_states[agent.agent_id].get("working_memory")
                if wm:
                    agent._working_memory = wm

    return agents

def _load_prior_learnings(self) -> dict[str, dict]:
    """Load agent states from previous run checkpoint."""
    config = self.config.get("learning", {}).get("cross_run", {})

    checkpoint_path = config.get("prior_checkpoint")
    if not checkpoint_path and config.get("auto_discover", True):
        checkpoint_path = self._find_latest_checkpoint()

    if not checkpoint_path or not os.path.exists(checkpoint_path):
        return {}

    checkpoint = load_checkpoint(checkpoint_path)
    return checkpoint.get("agent_states", {}) if checkpoint else {}
```

## Files Affected

- config/schema.yaml (modify) - Add learning.cross_run config options
- config/config.yaml (modify) - Add default values
- src/simulation/runner.py (modify) - Add _load_prior_learnings() method

## Testing

1. Run simulation, verify checkpoint saved with working_memory
2. Start new run with `prior_checkpoint` set, verify working_memory loaded
3. Verify agents can use restored learnings in prompts
4. Test auto-discover finds latest checkpoint

## Acceptance Criteria

1. Config option to enable cross-run learning
2. Working memory restored from prior checkpoint
3. Auto-discover latest checkpoint works
4. Agents use restored learnings in their prompts
