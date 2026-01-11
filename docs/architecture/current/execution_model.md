# Current Execution Model

How agent execution works TODAY.

**Last verified:** 2026-01-11

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

**`SimulationRunner._think_all_agents()`**

1. Capture world state snapshot via `get_state_summary()`
2. All agents see IDENTICAL state (snapshot consistency)
3. Agents think in parallel via `asyncio.gather()`
4. Each produces an action proposal
5. Thinking cost deducted immediately from compute

```python
world_state = self.world.get_state_summary(agent_id)
proposals = await asyncio.gather(*thinking_tasks)
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

## Tick Lifecycle

### advance_tick() (`World.advance_tick()`)

Called at start of each tick:

1. Increment tick counter
2. Reset flow resources for all principals
3. Log tick event
4. Return False if tick >= max_ticks

```python
def advance_tick(self) -> bool:
    self.tick += 1
    if self.tick >= self.max_ticks:
        return False

    # Reset flow resources to quota
    for pid in self.principal_ids:
        quota = self.rights_registry.get_quota(pid, "compute")
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
| `src/simulation/runner.py` | `SimulationRunner.run()` | Main run loop |
| `src/simulation/runner.py` | `SimulationRunner._think_agent()` | Single agent thinking |
| `src/simulation/runner.py` | `SimulationRunner._think_all_agents()` | Phase 1 parallel gather |
| `src/world/world.py` | `World.advance_tick()` | Tick lifecycle |
| `src/world/world.py` | `World.execute_action()` | Action dispatcher |

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
