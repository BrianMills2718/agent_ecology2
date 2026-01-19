# Current Execution Model

How agent execution works TODAY.

**Last verified:** 2026-01-19 (Plan #80 - log truncation)

**See target:** [../target/execution_model.md](../target/execution_model.md)

---

## Agent Initialization

SimulationRunner creates artifact-backed agents by default (Plan #6: Unified Ontology).

```python
# 1. Load agent configs from disk
agent_configs = load_agents()

# 2. Create artifact representations in world.artifacts
create_agent_artifacts(world.artifacts, agent_configs, create_memory=True)

# 3. Load Agent instances from artifacts
agents = load_agents_from_store(world.artifacts, log_dir, run_id, default_model)
```

Each agent gets:
- An agent artifact with `has_standing=True`, `can_execute=True`
- A linked memory artifact with `is_memory=True`
- Properties set via `_load_from_artifact()`

See `docs/architecture/current/agents.md` for artifact-backed agent details.

---

## Execution Modes

**Default: Autonomous mode** (`use_autonomous_loops: true`)
- Agents run independently via `AgentLoop`
- Resource-gated by `RateTracker` (rolling window)
- No tick synchronization

**Legacy: Tick-synchronized mode** (`--ticks N` CLI flag)
- Runner controls when agents think and act
- Two-phase commit per tick
- Useful for debugging/deterministic replay

---

## Tick-Synchronized Execution (Legacy Mode)

When using `--ticks N`, agents do NOT act autonomously. The runner controls when agents think and act.

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

1. Check per-agent `llm_budget` if configured (Plan #12)
2. Capture world state snapshot via `get_state_summary()`
3. All agents see IDENTICAL state (snapshot consistency)
4. Agents think in parallel via `asyncio.gather()`
5. Each produces an action proposal
6. Thinking cost deducted from compute AND per-agent `llm_budget` (if configured)

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

## The Narrow Waist: 4 Action Types + Reasoning

All agent actions must be one of these 4 types (`src/world/actions.py`):

| Action Type | Purpose |
|-------------|---------|
| `noop` | Do nothing |
| `read_artifact` | Read artifact content |
| `write_artifact` | Create/update artifact |
| `invoke_artifact` | Call method on artifact |

**Note:** There is no `transfer` action. All transfers go through `genesis_ledger.transfer()`.

### Reasoning Field (Plan #49)

Every `ActionIntent` includes a `reasoning` field that captures why the agent chose this action:

```python
@dataclass
class ActionIntent:
    action_type: ActionType
    principal_id: str
    reasoning: str = ""  # Required explanation for this action
```

The reasoning flows from agent's `thought_process` through the narrow waist:
1. Agent produces `ActionResponse` with `thought_process`
2. Runner maps `thought_process` → `reasoning` in action JSON
3. `parse_intent_from_json()` extracts `reasoning`
4. Action event logged includes `reasoning` in `intent.to_dict()`

This enables LLM-native monitoring: analyzing reasoning quality, extracting strategies, detecting anomalies.

---

## Time-Based Mint Auctions (Plan #83)

The mint system uses wall-clock time for auction phases, not ticks. This enables proper auction operation in autonomous/duration mode.

### Auction Configuration (Time-Based)

```yaml
auction:
  period_seconds: 60.0           # Seconds between auction starts
  bidding_window_seconds: 30.0   # Duration of bidding phase (seconds)
  first_auction_delay_seconds: 30.0  # Delay before first auction starts
```

### Auction Phases

| Phase | Duration | Description |
|-------|----------|-------------|
| WAITING | `first_auction_delay_seconds` | Before first auction starts |
| BIDDING | `bidding_window_seconds` | Bids accepted and held in escrow |
| CLOSED | Until period ends | Auction resolved, bids apply to next cycle |

### Background Mint Updates (Autonomous Mode)

In autonomous mode, `SimulationRunner._mint_update_loop()` runs as a background task:

```python
async def _mint_update_loop(self) -> None:
    """Periodically call mint.update() for time-based auctions."""
    while True:
        result = self._handle_mint_update()
        if result:
            # Log auction resolution
        await asyncio.sleep(1.0)
```

The mint's `update()` method:
1. Checks elapsed time since simulation start
2. Starts auctions after `first_auction_delay_seconds`
3. Resolves auctions after `bidding_window_seconds`
4. Schedules next auction after `period_seconds`

### Anytime Bidding (Plan #5)

Bids are accepted at any time, not just during the BIDDING phase. Early bids are held until the next auction resolution.

---

## Tick Lifecycle (Legacy Mode)

> **Note:** `advance_tick()` is deprecated for time-based execution (Plan #83).
> In autonomous/duration mode, use wall-clock time instead of tick-based progression.

### advance_tick() (`World.advance_tick()`)

Called at start of each tick:

1. Increment tick counter
2. Reset renewable resources for all principals
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

## Tick Summary Logging (Plan #60)

Each tick-based run generates summary statistics for observability via `TickSummaryCollector`.

### What's Tracked

| Metric | Description |
|--------|-------------|
| `agents_active` | Agents that produced valid proposals |
| `actions_executed` | Total actions in Phase 2 |
| `actions_by_type` | Breakdown by action type (read, write, invoke, noop) |
| `total_llm_tokens` | Combined input+output tokens for all agents |
| `total_scrip_transferred` | Scrip moved via genesis_ledger invocations |
| `artifacts_created` | New artifacts written this tick |
| `errors` | Failed action count |
| `highlights` | Notable events (artifact creation, etc.) |

### Collection Points

```
1. advance_tick()              # Tick starts
2. _tick_collector = new       # Initialize collector
3. Phase 1: _think_agent()     # Record LLM tokens
4. Phase 2: _execute_proposals() # Record actions, transfers, artifacts
5. _tick_collector.finalize()  # Compute summary
6. summary_logger.log_tick_summary() # Write to summary.jsonl
```

### Output

Summary data written to `summary.jsonl` via `SummaryLogger`:

```json
{"type": "tick_summary", "tick": 5, "agents_active": 3, "actions_executed": 3,
 "actions_by_type": {"invoke_artifact": 2, "write_artifact": 1},
 "total_llm_tokens": 4523, "total_scrip_transferred": 100, ...}
```

Use `python scripts/view_log.py --summary` to view aggregated tick summaries.

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

### Autonomous Mode (Primary)

| File | Key Functions | Description |
|------|---------------|-------------|
| `src/simulation/agent_loop.py` | `AgentLoop._execute_iteration()` | **Primary integration point** for agent features |
| `src/simulation/agent_loop.py` | `AgentLoopManager` | Manages agent loops lifecycle |
| `src/agents/rate_tracker.py` | `RateTracker` | Rolling window resource gating |
| `src/world/world.py` | `World.execute_action()` | Action dispatcher |
| `src/world/actions.py` | `parse_intent_from_json()` | Action parsing (the "narrow waist") |

### Tick Mode (Debug)

| File | Key Functions | Description |
|------|---------------|-------------|
| `src/simulation/runner.py` | `SimulationRunner.run()` | Legacy tick loop (includes Phase 1 parallel gather) |
| `src/simulation/runner.py` | `SimulationRunner._think_agent()` | Single agent thinking |
| `src/simulation/runner.py` | `SimulationRunner._execute_proposals()` | Phase 2 sequential execution |
| `src/world/world.py` | `World.advance_tick()` | Tick lifecycle |

---

## Implications

### Autonomous Mode (Default)
- Agents decide their own pace via `AgentLoop`
- Resource exhaustion (RateTracker) gates actions, not ticks
- Efficient agents can act more frequently → selection pressure
- Strategy diversity: fast/slow strategies emerge naturally

### Tick Mode (Debug Only)
- Agents don't decide when to act
- System triggers all agents each tick
- No agent can act more/less frequently than others
- Useful for deterministic testing and debugging

### Snapshot Consistency (Tick Mode Only)
- All agents see same world state within a tick
- No races during thinking phase
- Races resolved in Phase 2 by randomized order

---

## Autonomous Execution Mode (Default)

Autonomous mode is the default (`execution.use_autonomous_loops: true`). Agents run independently via `AgentLoop`, resource-gated by `RateTracker`.

### CLI Usage

```bash
# Run autonomous mode for 60 seconds (default)
python run.py --duration 60

# Run autonomous mode with dashboard
python run.py --duration 120 --dashboard

# Run legacy tick-based mode (for debugging)
python run.py --ticks 10
```

### Configuration

```yaml
execution:
  use_autonomous_loops: false  # Enable via --duration or --autonomous CLI flags
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
| Autonomous default (ADR-0014) | Autonomous default ✅ |
| Optional RateTracker | RateTracker always on |
| Tick resets flow resources | Rolling window only |

See `docs/architecture/target/02_execution_model.md` for target architecture.

---

## Worker Pool Mode (Plan #53)

Optional process-per-agent-turn architecture for scaling to 100+ agents.

### Why Worker Pool?

- Current: All agents in one Python process → OOM with 50+ agents
- Worker pool: Agent state persisted to SQLite, workers load/execute/save
- Enables ~10x scale increase with same memory footprint

### Architecture

```
┌─────────────────────────────────────────────────────────────┐
│  Agent State Store (SQLite)                                  │
│  - WAL mode for concurrency                                  │
│  - Agent state serialized as JSON                            │
└─────────────────────────────────────────────────────────────┘
          │
          ▼
┌─────────────┐ ┌─────────────┐ ┌─────────────┐
│ Worker 1    │ │ Worker 2    │ │ Worker N    │
│ (thread)    │ │ (thread)    │ │ (thread)    │
│             │ │             │ │             │
│ Load agent  │ │ Load agent  │ │ Load agent  │
│ Run turn    │ │ Run turn    │ │ Run turn    │
│ Measure res │ │ Measure res │ │ Measure res │
│ Save state  │ │ Save state  │ │ Save state  │
│ Next agent  │ │ Next agent  │ │ Next agent  │
└─────────────┘ └─────────────┘ └─────────────┘
```

### Configuration

```yaml
execution:
  use_worker_pool: true  # Enable worker pool mode
  worker_pool:
    num_workers: 4       # Number of parallel workers
    state_db_path: "agent_state.db"  # SQLite database path
```

### How It Works

1. **State Persistence**: Each agent's state serialized to SQLite via `AgentStateStore`
2. **Worker Pool**: `ThreadPoolExecutor` runs N workers concurrently
3. **Turn Execution**: Worker loads agent, runs turn, measures resources, saves state
4. **Resource Attribution**: Per-agent CPU/memory tracked via `psutil`

### Key Components

| File | Purpose |
|------|---------|
| `src/agents/state_store.py` | SQLite-backed agent state persistence |
| `src/simulation/worker.py` | Worker process that runs agent turns |
| `src/simulation/pool.py` | Worker pool manager |

### Agent State Serialization

```python
# Agent.to_state() - serialize
state = AgentState(
    agent_id=self.agent_id,
    model=self.model,
    system_prompt=self.system_prompt,
    history=list(self.history),
    rag_enabled=self.rag_enabled,
)

# Agent.from_state() - deserialize
agent = Agent.from_state(state, log_dir=log_dir, run_id=run_id)
```

### Resource Measurement Per-Turn

| Resource | Measurement Method | Accuracy |
|----------|-------------------|----------|
| CPU | `time.process_time()` | ~90% |
| Memory | `psutil.Process().memory_info().rss` | ~90% |

### Limitations

- Workers are threads, not processes (GIL contention)
- ~10% measurement error from shared Python runtime
- State serialization overhead (~10ms per turn)
