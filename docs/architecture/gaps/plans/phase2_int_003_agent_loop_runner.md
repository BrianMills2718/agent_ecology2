# INT-003: Integrate AgentLoop into Runner

**Priority:** 2 (Wave 2 - can run parallel with INT-002)
**Complexity:** L
**Risk:** Medium
**Depends on:** INT-001

---

## Summary

Wire the standalone AgentLoop module into SimulationRunner so agents can run autonomously when `use_autonomous_loops` is enabled.

---

## Current State

- `src/simulation/agent_loop.py` exists with AgentLoop and AgentLoopManager
- `src/simulation/runner.py` uses tick-based execution:
  - `run()` loops over ticks
  - Phase 1: parallel thinking
  - Phase 2: sequential execution
  - All agents synchronized to tick clock

---

## Target State

- Runner can use autonomous loops when `use_autonomous_loops=True`
- AgentLoopManager manages all agent loops
- Agents run independently, resource-gated
- Feature flag controls behavior
- Tick-based mode unchanged when flag is False

---

## Files to Modify

| File | Changes |
|------|---------|
| `src/simulation/runner.py` | Add autonomous loop support |
| `src/world/world.py` | Add loop_manager field |
| `tests/test_runner.py` | Add tests for autonomous mode |

---

## Implementation Steps

### Step 1: Add AgentLoopManager to World

```python
# In src/world/world.py

from src.simulation.agent_loop import AgentLoopManager

class World:
    def __init__(self, config: dict, ...):
        # ... existing init ...

        # Create loop manager if autonomous mode enabled
        execution_config = config.get("execution", {})
        self.use_autonomous_loops = execution_config.get("use_autonomous_loops", False)

        self.loop_manager: Optional[AgentLoopManager] = None
        if self.use_autonomous_loops:
            self.loop_manager = AgentLoopManager(self.ledger.rate_tracker)
```

### Step 2: Add Autonomous Run Mode to Runner

```python
# In src/simulation/runner.py

from src.simulation.agent_loop import AgentLoopManager, AgentLoopConfig

class SimulationRunner:
    def __init__(self, world: "World"):
        self.world = world
        self.use_autonomous_loops = world.use_autonomous_loops

    async def run(
        self,
        max_ticks: Optional[int] = None,
        duration: Optional[float] = None,
    ) -> None:
        """
        Run simulation.

        Args:
            max_ticks: Maximum ticks (tick-based mode)
            duration: Maximum seconds (autonomous mode)
        """
        if self.use_autonomous_loops:
            await self._run_autonomous(duration)
        else:
            await self._run_tick_based(max_ticks)

    async def _run_autonomous(self, duration: Optional[float] = None) -> None:
        """Run with autonomous agent loops."""
        if not self.world.loop_manager:
            raise RuntimeError("loop_manager not initialized")

        # Create loops for all agents
        for agent in self.world.agents.values():
            self._create_agent_loop(agent)

        # Start all loops
        await self.world.loop_manager.start_all()

        try:
            if duration:
                # Run for specified duration
                await asyncio.sleep(duration)
            else:
                # Run until all agents stop or interrupted
                while self.world.loop_manager.running_count > 0:
                    await asyncio.sleep(1.0)
        except asyncio.CancelledError:
            pass
        finally:
            # Graceful shutdown
            await self.world.loop_manager.stop_all()

    def _create_agent_loop(self, agent: "Agent") -> None:
        """Create agent loop with callbacks."""
        execution_config = self.world.config.get("execution", {})
        loop_config = execution_config.get("agent_loop", {})

        config = AgentLoopConfig(
            min_loop_delay=loop_config.get("min_loop_delay", 0.1),
            max_loop_delay=loop_config.get("max_loop_delay", 10.0),
            resource_check_interval=loop_config.get("resource_check_interval", 1.0),
            max_consecutive_errors=loop_config.get("max_consecutive_errors", 5),
            resources_to_check=loop_config.get("resources_to_check", ["llm_calls"]),
        )

        self.world.loop_manager.create_loop_for_agent(agent, config=config)

    async def _run_tick_based(self, max_ticks: Optional[int] = None) -> None:
        """Legacy tick-based execution."""
        # ... existing tick-based code unchanged ...
        tick = 0
        max_ticks = max_ticks or self.world.config.get("world", {}).get("max_ticks", 100)

        while tick < max_ticks:
            tick += 1
            # ... existing tick logic ...
```

### Step 3: Add Agent Protocol Support

The Agent class needs to implement the callbacks expected by AgentLoop:

```python
# In src/agents/agent.py

class Agent:
    # ... existing code ...

    @property
    def alive(self) -> bool:
        """Whether agent should continue running."""
        return self._alive

    @alive.setter
    def alive(self, value: bool) -> None:
        self._alive = value

    async def decide_action(self) -> Optional[dict]:
        """
        Decide what action to take.
        Called by autonomous loop each iteration.
        """
        if not self.alive:
            return None

        # Generate action via existing LLM logic
        return await self.propose_action_async(self.world.get_state_summary())

    async def execute_action(self, action: dict) -> dict:
        """
        Execute a decided action.
        Called by autonomous loop after decide_action.
        """
        return self.world.execute_action(self.agent_id, action)
```

### Step 4: Add Graceful Shutdown

```python
# In src/simulation/runner.py

async def shutdown(self) -> None:
    """Gracefully stop the simulation."""
    if self.use_autonomous_loops and self.world.loop_manager:
        await self.world.loop_manager.stop_all(timeout=5.0)
    # ... any other cleanup ...
```

### Step 5: Add Tests

```python
# In tests/test_runner.py

class TestAutonomousMode:
    """Tests for autonomous agent loop execution."""

    @pytest.mark.asyncio
    async def test_autonomous_mode_disabled_by_default(self, runner):
        """Autonomous mode not used by default."""
        assert runner.use_autonomous_loops is False

    @pytest.mark.asyncio
    async def test_autonomous_mode_enabled_from_config(self):
        """Autonomous mode enabled when configured."""
        config = {"execution": {"use_autonomous_loops": True}}
        world = World(config=config, ...)
        runner = SimulationRunner(world)
        assert runner.use_autonomous_loops is True

    @pytest.mark.asyncio
    async def test_autonomous_creates_loops_for_agents(self):
        """Autonomous mode creates loop per agent."""
        config = {
            "execution": {"use_autonomous_loops": True},
            "rate_limiting": {"enabled": True}
        }
        world = World(config=config, agents=[agent1, agent2])
        runner = SimulationRunner(world)

        # Don't actually run, just check setup
        assert world.loop_manager is not None

    @pytest.mark.asyncio
    async def test_autonomous_runs_for_duration(self):
        """Autonomous mode runs for specified duration."""
        # Create mock agents that do nothing
        config = {"execution": {"use_autonomous_loops": True}}
        world = create_test_world(config)
        runner = SimulationRunner(world)

        start = time.time()
        await runner.run(duration=0.5)
        elapsed = time.time() - start

        assert elapsed >= 0.5
        assert elapsed < 1.0

    @pytest.mark.asyncio
    async def test_tick_based_unchanged(self):
        """Tick-based mode works as before."""
        config = {"execution": {"use_autonomous_loops": False}}
        world = create_test_world(config)
        runner = SimulationRunner(world)

        await runner.run(max_ticks=5)
        assert world.tick >= 5
```

---

## Interface Definition

```python
class SimulationRunner:
    use_autonomous_loops: bool

    async def run(self, max_ticks: int | None = None, duration: float | None = None) -> None: ...
    async def _run_autonomous(self, duration: float | None = None) -> None: ...
    async def _run_tick_based(self, max_ticks: int | None = None) -> None: ...
    def _create_agent_loop(self, agent: Agent) -> None: ...
    async def shutdown(self) -> None: ...

class World:
    use_autonomous_loops: bool
    loop_manager: AgentLoopManager | None
```

---

## Acceptance Criteria

- [ ] `use_autonomous_loops: true` enables autonomous mode
- [ ] AgentLoopManager created when autonomous mode enabled
- [ ] Agents run independent loops in autonomous mode
- [ ] `run(duration=X)` runs for X seconds in autonomous mode
- [ ] Graceful shutdown stops all loops
- [ ] Tick-based mode unchanged when flag is False
- [ ] All existing runner tests pass
- [ ] New autonomous mode tests pass

---

## Verification

```bash
pytest tests/test_runner.py -v
pytest tests/ -v
python -m mypy src/simulation/runner.py --ignore-missing-imports
```

---

## Dependencies

- **Requires:** GAP-EXEC-001 (AgentLoop) - COMPLETE ✓
- **Requires:** INT-001 (RateTracker in Ledger for resource checking)
- **Blocks:** CAP-002 (async locks needed for concurrent execution)
