# GAP-EXEC-001: Continuous Autonomous Agent Loops Implementation Plan

**Gap ID:** GAP-EXEC-001
**Complexity:** XL (500+ lines, cross-component)
**Risk:** High
**Phase:** 1 - Foundations

---

## Summary

Transform the execution model from tick-synchronized to continuous autonomous agent loops. Each agent becomes self-driving, running its own async loop that continues until resources are exhausted or the agent is stopped. This is the most fundamental architectural change.

---

## Current State

- `SimulationRunner` drives all agents via ticks
- `runner.tick()` calls `agent.act()` for each agent sequentially
- Agents are passive - only execute when prompted
- All agents synchronized to same tick clock
- Resource refresh tied to ticks

---

## Target State

- Agents run independent `async` loops
- Agents decide when to act based on their own logic
- No global tick synchronization
- Resource checking before each action (via RateTracker)
- Agents can sleep and wake on conditions
- Agents can be started/stopped independently

---

## Files to Modify

| File | Changes |
|------|---------|
| `src/simulation/agent_loop.py` | **NEW FILE** - Autonomous loop implementation |
| `src/agents/agent.py` | Add `alive` flag, refactor `act()` for loop compatibility |
| `src/simulation/runner.py` | Remove tick-based triggering, manage agent lifecycle |
| `src/world/world.py` | Track running agents, coordinate shutdown |
| `config/schema.yaml` | Add agent loop configuration |
| `tests/test_agent_loop.py` | **NEW FILE** - Agent loop tests |

---

## Implementation Steps

### Step 1: Create Agent Loop Module

Create `src/simulation/agent_loop.py`:

```python
import asyncio
import logging
from typing import Optional, Callable, Awaitable
from dataclasses import dataclass, field
from enum import Enum

logger = logging.getLogger(__name__)

class AgentState(str, Enum):
    STARTING = "starting"
    RUNNING = "running"
    SLEEPING = "sleeping"
    PAUSED = "paused"  # Resource exhaustion
    STOPPING = "stopping"
    STOPPED = "stopped"

@dataclass
class WakeCondition:
    """Condition that wakes a sleeping agent."""
    condition_type: str  # "time", "event", "resource"
    value: any  # time in seconds, event name, resource threshold

@dataclass
class AgentLoopConfig:
    """Configuration for an agent's autonomous loop."""
    min_loop_delay: float = 0.1  # Minimum seconds between actions
    max_loop_delay: float = 10.0  # Maximum backoff delay
    resource_check_interval: float = 1.0  # How often to check resources when paused
    max_consecutive_errors: int = 5  # Errors before forced pause

@dataclass
class AgentLoop:
    """
    Autonomous execution loop for a single agent.

    The agent loop:
    1. Checks if agent is alive
    2. Checks resource capacity
    3. Calls agent.decide_action()
    4. Executes the action
    5. Handles results
    6. Repeats
    """

    agent_id: str
    agent: "Agent"
    world: "World"
    config: AgentLoopConfig = field(default_factory=AgentLoopConfig)

    _state: AgentState = field(default=AgentState.STOPPED)
    _task: Optional[asyncio.Task] = field(default=None)
    _consecutive_errors: int = field(default=0)
    _wake_condition: Optional[WakeCondition] = field(default=None)

    @property
    def state(self) -> AgentState:
        return self._state

    @property
    def is_running(self) -> bool:
        return self._state in (AgentState.RUNNING, AgentState.SLEEPING, AgentState.PAUSED)

    async def start(self) -> None:
        """Start the autonomous loop."""
        if self._state != AgentState.STOPPED:
            logger.warning(f"Agent {self.agent_id} already running, state={self._state}")
            return

        self._state = AgentState.STARTING
        self._task = asyncio.create_task(self._run_loop())
        logger.info(f"Agent {self.agent_id} loop started")

    async def stop(self, timeout: float = 5.0) -> None:
        """Stop the autonomous loop gracefully."""
        if self._state == AgentState.STOPPED:
            return

        self._state = AgentState.STOPPING

        if self._task:
            try:
                await asyncio.wait_for(self._task, timeout=timeout)
            except asyncio.TimeoutError:
                self._task.cancel()
                try:
                    await self._task
                except asyncio.CancelledError:
                    pass

        self._state = AgentState.STOPPED
        logger.info(f"Agent {self.agent_id} loop stopped")

    def sleep(self, wake_condition: WakeCondition) -> None:
        """Put agent to sleep until wake condition is met."""
        self._wake_condition = wake_condition
        self._state = AgentState.SLEEPING
        logger.debug(f"Agent {self.agent_id} sleeping until {wake_condition}")

    def wake(self) -> None:
        """Wake a sleeping agent."""
        if self._state == AgentState.SLEEPING:
            self._wake_condition = None
            self._state = AgentState.RUNNING
            logger.debug(f"Agent {self.agent_id} woken")

    async def _run_loop(self) -> None:
        """Main autonomous loop."""
        self._state = AgentState.RUNNING
        delay = self.config.min_loop_delay

        while self._state not in (AgentState.STOPPING, AgentState.STOPPED):
            try:
                # Handle sleeping state
                if self._state == AgentState.SLEEPING:
                    if await self._check_wake_condition():
                        self.wake()
                    else:
                        await asyncio.sleep(self.config.resource_check_interval)
                        continue

                # Check resource capacity
                if not await self._has_resources():
                    self._state = AgentState.PAUSED
                    logger.debug(f"Agent {self.agent_id} paused (no resources)")
                    await asyncio.sleep(self.config.resource_check_interval)
                    continue

                # Unpause if we were paused and now have resources
                if self._state == AgentState.PAUSED:
                    self._state = AgentState.RUNNING
                    logger.debug(f"Agent {self.agent_id} unpaused")

                # Execute one iteration
                result = await self._execute_iteration()

                # Handle result
                if result.get("success"):
                    self._consecutive_errors = 0
                    delay = self.config.min_loop_delay
                else:
                    self._consecutive_errors += 1
                    delay = min(delay * 2, self.config.max_loop_delay)

                    if self._consecutive_errors >= self.config.max_consecutive_errors:
                        logger.error(f"Agent {self.agent_id} hit error limit, pausing")
                        self._state = AgentState.PAUSED

                await asyncio.sleep(delay)

            except asyncio.CancelledError:
                logger.debug(f"Agent {self.agent_id} loop cancelled")
                break
            except Exception as e:
                logger.exception(f"Agent {self.agent_id} loop error: {e}")
                self._consecutive_errors += 1
                await asyncio.sleep(delay)

        self._state = AgentState.STOPPED

    async def _has_resources(self) -> bool:
        """Check if agent has capacity for at least one action."""
        rate_tracker = self.world.rate_tracker

        # Check all resource types
        for resource in ["llm_calls", "disk_writes", "bandwidth"]:
            if not rate_tracker.has_capacity(self.agent_id, resource):
                return False

        return True

    async def _check_wake_condition(self) -> bool:
        """Check if wake condition is satisfied."""
        if not self._wake_condition:
            return True

        cond = self._wake_condition

        if cond.condition_type == "time":
            import time
            return time.time() >= cond.value

        if cond.condition_type == "event":
            # Check event bus for matching event
            return self.world.event_bus.has_event(self.agent_id, cond.value)

        if cond.condition_type == "resource":
            # Check if resource threshold met
            resource, threshold = cond.value
            return self.world.rate_tracker.get_remaining(self.agent_id, resource) >= threshold

        return False

    async def _execute_iteration(self) -> dict:
        """Execute one iteration of the agent loop."""
        try:
            # Let agent decide what to do
            action = await self.agent.decide_action()

            if action is None:
                # Agent chose to do nothing
                return {"success": True, "action": None}

            # Execute the action
            result = await self.agent.execute_action(action)

            return {
                "success": result.get("success", False),
                "action": action,
                "result": result,
            }

        except Exception as e:
            logger.exception(f"Agent {self.agent_id} iteration error: {e}")
            return {"success": False, "error": str(e)}


class AgentLoopManager:
    """Manages all agent loops in the simulation."""

    def __init__(self, world: "World"):
        self.world = world
        self._loops: dict[str, AgentLoop] = {}

    def create_loop(self, agent: "Agent", config: Optional[AgentLoopConfig] = None) -> AgentLoop:
        """Create an agent loop."""
        if agent.agent_id in self._loops:
            raise ValueError(f"Loop already exists for agent {agent.agent_id}")

        loop = AgentLoop(
            agent_id=agent.agent_id,
            agent=agent,
            world=self.world,
            config=config or AgentLoopConfig(),
        )
        self._loops[agent.agent_id] = loop
        return loop

    async def start_all(self) -> None:
        """Start all agent loops."""
        await asyncio.gather(*[loop.start() for loop in self._loops.values()])

    async def stop_all(self, timeout: float = 10.0) -> None:
        """Stop all agent loops."""
        await asyncio.gather(*[loop.stop(timeout) for loop in self._loops.values()])

    def get_loop(self, agent_id: str) -> Optional[AgentLoop]:
        """Get loop by agent ID."""
        return self._loops.get(agent_id)

    @property
    def running_count(self) -> int:
        """Count of running agent loops."""
        return sum(1 for loop in self._loops.values() if loop.is_running)
```

### Step 2: Update Agent Class

Update `src/agents/agent.py`:

```python
@dataclass
class Agent:
    agent_id: str
    # ... existing fields ...

    # NEW: Loop control
    alive: bool = True

    async def decide_action(self) -> Optional[dict]:
        """
        Decide what action to take next.
        Called by autonomous loop each iteration.

        Returns:
            Action dict or None to skip this iteration.
        """
        if not self.alive:
            return None

        # Generate action via LLM or other logic
        return await self._generate_action()

    async def execute_action(self, action: dict) -> dict:
        """
        Execute a decided action.

        Args:
            action: The action to execute

        Returns:
            Result dict with success/error/result
        """
        # Call executor with action
        return await self.world.executor.execute_agent_action(self, action)

    def shutdown(self) -> None:
        """Mark agent for shutdown."""
        self.alive = False
```

### Step 3: Update SimulationRunner

Update `src/simulation/runner.py`:

```python
class SimulationRunner:
    """Manages simulation lifecycle with autonomous agents."""

    def __init__(self, world: "World", use_autonomous_loops: bool = True):
        self.world = world
        self.use_autonomous_loops = use_autonomous_loops
        self.loop_manager = AgentLoopManager(world) if use_autonomous_loops else None

    async def run(self, duration: Optional[float] = None) -> None:
        """
        Run simulation.

        Args:
            duration: Maximum run time in seconds (None = run until stopped)
        """
        if self.use_autonomous_loops:
            await self._run_autonomous(duration)
        else:
            await self._run_tick_based(duration)

    async def _run_autonomous(self, duration: Optional[float]) -> None:
        """Run with autonomous agent loops."""
        # Create loops for all agents
        for agent in self.world.agents.values():
            self.loop_manager.create_loop(agent)

        # Start all loops
        await self.loop_manager.start_all()

        try:
            if duration:
                await asyncio.sleep(duration)
            else:
                # Run until interrupted
                while True:
                    await asyncio.sleep(1)
                    if self.loop_manager.running_count == 0:
                        break
        finally:
            await self.loop_manager.stop_all()

    async def _run_tick_based(self, duration: Optional[float]) -> None:
        """Legacy tick-based execution."""
        # ... existing tick-based code ...
        pass
```

### Step 4: Add Configuration

Update `config/schema.yaml`:

```yaml
execution:
  use_autonomous_loops: true  # Feature flag
  agent_loop:
    min_loop_delay: 0.1
    max_loop_delay: 10.0
    resource_check_interval: 1.0
    max_consecutive_errors: 5
```

---

## Interface Definition

```python
class AgentLoop(Protocol):
    agent_id: str
    state: AgentState
    is_running: bool

    async def start(self) -> None: ...
    async def stop(self, timeout: float = 5.0) -> None: ...
    def sleep(self, wake_condition: WakeCondition) -> None: ...
    def wake(self) -> None: ...

class AgentLoopManager(Protocol):
    def create_loop(self, agent: Agent, config: Optional[AgentLoopConfig] = None) -> AgentLoop: ...
    async def start_all(self) -> None: ...
    async def stop_all(self, timeout: float = 10.0) -> None: ...
    def get_loop(self, agent_id: str) -> Optional[AgentLoop]: ...
    running_count: int
```

---

## Migration Strategy

1. **Phase 1A:** Add `use_autonomous_loops: false` flag
2. **Phase 1B:** Implement AgentLoop and AgentLoopManager
3. **Phase 1C:** Add `decide_action()` and `execute_action()` to Agent
4. **Phase 1D:** Run tests with both modes, verify equivalent behavior
5. **Phase 1E:** Enable `use_autonomous_loops: true` by default
6. **Phase 2:** Remove tick-based code

---

## Test Cases

| Test | Description | Expected |
|------|-------------|----------|
| `test_loop_starts` | Loop starts successfully | State becomes RUNNING |
| `test_loop_stops` | Loop stops gracefully | State becomes STOPPED |
| `test_loop_pauses_no_resources` | No resources → PAUSED | State becomes PAUSED |
| `test_loop_resumes_resources` | Resources restored → RUNNING | Resumes execution |
| `test_loop_sleeps` | Sleep with condition | State becomes SLEEPING |
| `test_loop_wakes_time` | Wake on time condition | Wakes after delay |
| `test_loop_wakes_event` | Wake on event | Wakes on matching event |
| `test_loop_error_backoff` | Errors cause backoff | Delay increases |
| `test_loop_error_limit` | Too many errors → PAUSED | Pauses after limit |
| `test_multiple_agents` | Many agents run concurrently | All execute independently |
| `test_agent_shutdown` | Agent.alive=False stops loop | Loop exits cleanly |

---

## Acceptance Criteria

- [ ] Agents run independently without tick synchronization
- [ ] Agents can start/stop independently
- [ ] Resource exhaustion pauses agent (doesn't crash)
- [ ] Agent sleep/wake system works
- [ ] Error handling with backoff
- [ ] Graceful shutdown
- [ ] Feature flag for migration
- [ ] All tests pass

---

## Rollback Plan

If issues arise:
1. Set `use_autonomous_loops: false` in config
2. System falls back to tick-based execution
3. Debug autonomous loops in isolation
4. Fix and re-enable

---

## Dependencies

- **Requires:** GAP-RES-001 (RateTracker for resource checking)
- **Required for:** GAP-EXEC-002 (agent sleep system)
- **Required for:** GAP-AGENT-002 (autonomous execution loop integration)
- **Blocks:** Phase 2 execution stream
