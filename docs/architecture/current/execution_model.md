# Current Execution Model

How agent execution works TODAY.

**Last verified:** 2026-01-12 (Phase 3 - RateTracker integration complete)

**See target:** [../target/execution_model.md](../target/execution_model.md)

---

## Tick-Synchronized Execution

Agents do NOT act autonomously. The runner controls when agents think and act.

### Main Loop (`SimulationRunner.run()`)

```python
while self.world.advance_tick():
    # Phase 1: Parallel thinking
    results = await asyncio.gather(*[agent.think() for agent in agents])

    # Phase 2: Sequential randomized execution
    random.shuffle(proposals)
    for proposal in proposals:
        execute(proposal)

    # Rate limit delay
    await asyncio.sleep(self.delay)  # Default: 15 seconds
```

---

## Two-Phase Commit

### Phase 1: Observe (Parallel)

**`SimulationRunner.run()` thinking phase**

1. Capture world state snapshot via `get_state_summary()`
2. All agents see IDENTICAL state (snapshot consistency)
3. Agents think in parallel via `asyncio.gather()`
4. Each produces an action proposal
5. Thinking cost deducted immediately from compute

```python
tick_state = self.world.get_state_summary()
thinking_tasks = [self._think_agent(agent, tick_state) for agent in self.agents]
thinking_results = await asyncio.gather(*thinking_tasks)
```

### Phase 2: Execute (Sequential Randomized)

**`SimulationRunner.run()` execution phase**

1. Shuffle proposals randomly (prevents ordering exploits)
2. Execute each action sequentially
3. World state mutates between executions
4. Later actions see effects of earlier ones

```python
random.shuffle(proposals)
for proposal in proposals:
    result = self.world.execute_action(proposal)
```

---

## The Narrow Waist: 4 Action Types

All agent actions must be one of these 4 types (`src/world/actions.py`):

| Action Type | Purpose |
|-------------|---------|
| `noop` | Do nothing |
| `read_artifact` | Read artifact content |
| `write_artifact` | Create/update artifact |
| `invoke_artifact` | Call method on artifact |

**Note:** There is no `transfer` action. All transfers go through `genesis_ledger.transfer()`.

---

## Tick Lifecycle

### advance_tick() (`World.advance_tick()`)

Called at start of each tick:

1. Increment tick counter
2. Reset flow resources for all principals
3. Log tick event
4. Return False if tick >= max_ticks

```python
def advance_tick(self) -> bool:
    if self.tick >= self.max_ticks:
        return False
    self.tick += 1

    # Reset flow resources to quota
    for pid in self.principal_ids:
        quota = self.rights_registry.get_all_quotas(pid).get("compute", 50)
        self.ledger.set_resource(pid, "llm_tokens", quota)

    return True
```

---

## Timing

| Phase | Duration |
|-------|----------|
| Thinking (Phase 1) | ~2-10 seconds (LLM latency) |
| Execution (Phase 2) | ~milliseconds |
| Inter-tick delay | 15 seconds (configurable) |
| **Total per tick** | ~17-25 seconds |

### Rate Limiting

- `config.llm.rate_limit_delay`: Delay between ticks (default 15s)
- Purpose: Avoid hitting LLM API rate limits
- Can be reduced for faster iteration

---

## Key Files

| File | Key Functions | Description |
|------|---------------|-------------|
| `src/simulation/runner.py` | `SimulationRunner.run()` | Main run loop (includes Phase 1 parallel gather) |
| `src/simulation/runner.py` | `SimulationRunner._think_agent()` | Single agent thinking |
| `src/simulation/runner.py` | `SimulationRunner._execute_proposals()` | Phase 2 sequential execution |
| `src/simulation/agent_loop.py` | `AgentLoop`, `AgentLoopManager` | Autonomous agent execution loops |
| `src/simulation/agent_loop.py` | `AgentState`, `AgentLoopConfig`, `WakeCondition` | Loop configuration and state |
| `src/world/world.py` | `World.advance_tick()` | Tick lifecycle |
| `src/world/world.py` | `World.execute_action()` | Action dispatcher |
| `src/world/actions.py` | `parse_intent_from_json()` | Action parsing (the "narrow waist") |
| `src/world/rate_tracker.py` | `RateTracker` | Rolling window rate limiting for autonomous mode |

---

## Implications

### Agents Are Passive
- Agents don't decide when to act
- System triggers all agents each tick
- No agent can act more/less frequently than others

### Snapshot Consistency
- All agents see same world state within a tick
- No races during thinking phase
- Races resolved in Phase 2 by randomized order

### Fixed Parallelism
- All N agents think in parallel
- All N agents get one action per tick
- No way for "fast" agents to do more

---

## Autonomous Execution Mode (Optional)

When `execution.use_autonomous_loops: true`, agents run independently instead of tick-synchronized.

### Configuration

```yaml
execution:
  use_autonomous_loops: false  # Default: tick-based
rate_limiting:
  enabled: false  # Enable RateTracker
  window_seconds: 60.0
  resources:
    llm_calls:
      max_per_window: 100
```

### How It Works

1. Each agent gets an `AgentLoop` from `AgentLoopManager`
2. Loops run continuously via `asyncio.create_task()`
3. Resource exhaustion pauses agent (doesn't crash)
4. `RateTracker` replaces tick-based resource reset

### AgentLoop States

| State | Description |
|-------|-------------|
| `RUNNING` | Actively deciding/executing |
| `SLEEPING` | Waiting for wake condition |
| `PAUSED` | Resource exhausted or error limit |
| `STOPPED` | Loop terminated |

### Resource Exhaustion Policy

```yaml
execution:
  resource_exhaustion_policy: skip  # or "block"
```

- `skip`: Agent skips iteration, continues next cycle
- `block`: Agent waits until resources available

---

## Differences from Target

| Current | Target |
|---------|--------|
| Tick-based default | Autonomous default |
| Optional RateTracker | RateTracker always on |
| Tick resets flow resources | Rolling window only |

See `docs/architecture/target/02_execution_model.md` for target architecture.
