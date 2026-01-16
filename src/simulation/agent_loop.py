"""Autonomous agent loop implementation.

Provides continuous, self-driving execution loops for agents. Each agent runs
its own async loop that continues until resources are exhausted or the agent
is stopped.

This module implements GAP-EXEC-001: Continuous Autonomous Agent Loops.

Usage:
    from src.simulation.agent_loop import AgentLoop, AgentLoopManager, AgentLoopConfig

    manager = AgentLoopManager(world, rate_tracker)
    loop = manager.create_loop(agent, config)
    await loop.start()
    # ... agent runs autonomously ...
    await loop.stop()

See docs/architecture/gaps/plans/phase1_gap_exec_001_autonomous_loops.md for design.
"""

from __future__ import annotations

import asyncio
import logging
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import TYPE_CHECKING, Any, Callable, Awaitable, Literal, Protocol

from ..config import get_validated_config

if TYPE_CHECKING:
    from ..world.rate_tracker import RateTracker

logger = logging.getLogger(__name__)


class AgentState(str, Enum):
    """State of an agent's autonomous loop."""

    STARTING = "starting"
    RUNNING = "running"
    SLEEPING = "sleeping"
    PAUSED = "paused"  # Resource exhaustion or error limit
    STOPPING = "stopping"
    STOPPED = "stopped"


@dataclass
class WakeCondition:
    """Condition that wakes a sleeping agent.

    Attributes:
        condition_type: Type of wake condition - "time", "event", or "resource"
        value: Condition-specific value:
            - "time": float timestamp (seconds since epoch)
            - "event": str event name to wait for
            - "resource": tuple of (resource_name, threshold)
    """

    condition_type: str  # "time", "event", "resource"
    value: Any  # Depends on condition_type

    def __post_init__(self) -> None:
        """Validate condition type."""
        valid_types = {"time", "event", "resource"}
        if self.condition_type not in valid_types:
            raise ValueError(
                f"Invalid condition_type: {self.condition_type}. "
                f"Must be one of: {valid_types}"
            )


@dataclass
class AgentLoopConfig:
    """Configuration for an agent's autonomous loop.

    Attributes:
        min_loop_delay: Minimum seconds between actions (default: 0.1)
        max_loop_delay: Maximum backoff delay on errors (default: 10.0)
        resource_check_interval: How often to check resources when paused (default: 1.0)
        max_consecutive_errors: Errors before forced pause (default: 5)
        resources_to_check: List of resource types to check capacity for
        resource_exhaustion_policy: Policy when resources exhausted - "skip" or "block"
            - "skip": Skip action, sleep briefly, try again next iteration (default)
            - "block": Block until capacity available using wait_for_capacity
    """

    min_loop_delay: float = 0.1
    max_loop_delay: float = 10.0
    resource_check_interval: float = 1.0
    max_consecutive_errors: int = 5
    resources_to_check: list[str] = field(
        default_factory=lambda: ["llm_tokens", "llm_calls", "disk_writes", "bandwidth_bytes"]
    )
    resource_exhaustion_policy: Literal["skip", "block"] = "skip"

    def __post_init__(self) -> None:
        """Validate configuration values."""
        if self.min_loop_delay < 0:
            raise ValueError(f"min_loop_delay must be non-negative: {self.min_loop_delay}")
        if self.max_loop_delay < self.min_loop_delay:
            raise ValueError(
                f"max_loop_delay ({self.max_loop_delay}) must be >= "
                f"min_loop_delay ({self.min_loop_delay})"
            )
        if self.resource_check_interval <= 0:
            raise ValueError(
                f"resource_check_interval must be positive: {self.resource_check_interval}"
            )
        if self.max_consecutive_errors < 1:
            raise ValueError(
                f"max_consecutive_errors must be at least 1: {self.max_consecutive_errors}"
            )
        if self.resource_exhaustion_policy not in ("skip", "block"):
            raise ValueError(
                f"resource_exhaustion_policy must be 'skip' or 'block': "
                f"{self.resource_exhaustion_policy}"
            )


class AgentProtocol(Protocol):
    """Protocol defining the interface an agent must implement for autonomous loops."""

    @property
    def agent_id(self) -> str:
        """Unique identifier for the agent."""
        ...

    @property
    def alive(self) -> bool:
        """Whether the agent is still alive and should continue running."""
        ...

    async def decide_action(self) -> dict[str, Any] | None:
        """Decide what action to take next.

        Returns:
            Action dict or None to skip this iteration.
        """
        ...

    async def execute_action(self, action: dict[str, Any]) -> dict[str, Any]:
        """Execute a decided action.

        Args:
            action: The action to execute

        Returns:
            Result dict with success/error/result fields
        """
        ...


@dataclass
class AgentLoop:
    """Autonomous execution loop for a single agent.

    The agent loop:
    1. Checks if agent is alive
    2. Checks resource capacity
    3. Calls agent.decide_action()
    4. Executes the action
    5. Handles results
    6. Repeats

    Attributes:
        agent_id: Unique identifier for the agent
        decide_action: Async callback to decide next action
        execute_action: Async callback to execute an action
        rate_tracker: Rate tracker for resource checking
        config: Loop configuration
        is_alive: Callback to check if agent is still alive
    """

    agent_id: str
    decide_action: Callable[[], Awaitable[dict[str, Any] | None]]
    execute_action: Callable[[dict[str, Any]], Awaitable[dict[str, Any]]]
    rate_tracker: "RateTracker"
    config: AgentLoopConfig = field(default_factory=AgentLoopConfig)
    is_alive: Callable[[], bool] = field(default=lambda: True)

    _state: AgentState = field(default=AgentState.STOPPED, init=False)
    _task: asyncio.Task[None] | None = field(default=None, init=False)
    _consecutive_errors: int = field(default=0, init=False)
    _wake_condition: WakeCondition | None = field(default=None, init=False)
    _wake_event: asyncio.Event = field(default_factory=asyncio.Event, init=False)
    _iteration_count: int = field(default=0, init=False)

    @property
    def state(self) -> AgentState:
        """Current state of the loop."""
        return self._state

    @property
    def is_running(self) -> bool:
        """Whether the loop is actively running (not stopped)."""
        return self._state in (
            AgentState.STARTING,
            AgentState.RUNNING,
            AgentState.SLEEPING,
            AgentState.PAUSED,
        )

    @property
    def consecutive_errors(self) -> int:
        """Number of consecutive errors encountered."""
        return self._consecutive_errors

    @property
    def iteration_count(self) -> int:
        """Total number of iterations executed."""
        return self._iteration_count

    async def start(self) -> None:
        """Start the autonomous loop.

        If already running, logs a warning and returns without action.
        Creates an asyncio task to run the main loop.
        """
        if self._state != AgentState.STOPPED:
            logger.warning(
                f"Agent {self.agent_id} already running, state={self._state}"
            )
            return

        self._state = AgentState.STARTING
        self._consecutive_errors = 0
        self._iteration_count = 0
        self._wake_event.clear()
        self._task = asyncio.create_task(self._run_loop())
        logger.info(f"Agent {self.agent_id} loop started")

    async def stop(self, timeout: float | None = None) -> None:
        """Stop the autonomous loop gracefully.

        Sets state to STOPPING and waits for the loop to exit.
        If timeout is reached, cancels the task.

        Args:
            timeout: Maximum seconds to wait for graceful stop.
                     Defaults to config timeouts.agent_loop_stop.
        """
        if timeout is None:
            timeout = get_validated_config().timeouts.agent_loop_stop
        if self._state == AgentState.STOPPED:
            return

        self._state = AgentState.STOPPING
        # Wake up any sleeping agent so it can exit
        self._wake_event.set()

        if self._task:
            try:
                await asyncio.wait_for(self._task, timeout=timeout)
            except asyncio.TimeoutError:
                logger.warning(
                    f"Agent {self.agent_id} did not stop gracefully, cancelling"
                )
                self._task.cancel()
                try:
                    await self._task
                except asyncio.CancelledError:
                    pass

        self._state = AgentState.STOPPED
        self._task = None
        logger.info(f"Agent {self.agent_id} loop stopped")

    def sleep(self, wake_condition: WakeCondition) -> None:
        """Put agent to sleep until wake condition is met.

        Args:
            wake_condition: Condition that will wake the agent
        """
        self._wake_condition = wake_condition
        self._state = AgentState.SLEEPING
        self._wake_event.clear()
        logger.debug(
            f"Agent {self.agent_id} sleeping until {wake_condition.condition_type}="
            f"{wake_condition.value}"
        )

    def wake(self) -> None:
        """Wake a sleeping agent.

        Only affects agents in SLEEPING state.
        """
        if self._state == AgentState.SLEEPING:
            self._wake_condition = None
            self._state = AgentState.RUNNING
            self._wake_event.set()
            logger.debug(f"Agent {self.agent_id} woken")

    async def _run_loop(self) -> None:
        """Main autonomous loop.

        Runs until stop() is called or agent becomes not alive.
        Handles sleeping, resource checking, and error backoff.
        """
        self._state = AgentState.RUNNING
        delay = self.config.min_loop_delay

        while self._state not in (AgentState.STOPPING, AgentState.STOPPED):
            try:
                # Check if agent is still alive
                if not self.is_alive():
                    logger.info(f"Agent {self.agent_id} is no longer alive, stopping")
                    break

                # Handle sleeping state
                if self._state == AgentState.SLEEPING:
                    if await self._check_wake_condition():
                        self.wake()
                    else:
                        # Wait for wake event or timeout
                        try:
                            await asyncio.wait_for(
                                self._wake_event.wait(),
                                timeout=self.config.resource_check_interval,
                            )
                        except asyncio.TimeoutError:
                            pass
                        continue

                # Check resource capacity
                if not self._has_resources():
                    if self.config.resource_exhaustion_policy == "block":
                        # Block: wait for resources to become available
                        logger.debug(
                            f"Agent {self.agent_id} blocking until resources available"
                        )
                        acquired = await self._wait_for_resources()
                        if not acquired:
                            # Timeout or stop requested, continue to check loop condition
                            continue
                        logger.debug(f"Agent {self.agent_id} resources acquired, continuing")
                    else:
                        # Skip: pause and try again next iteration
                        if self._state != AgentState.PAUSED:
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
                self._iteration_count += 1

                # Handle result
                if result.get("success"):
                    self._consecutive_errors = 0
                    delay = self.config.min_loop_delay
                else:
                    self._consecutive_errors += 1
                    delay = min(delay * 2, self.config.max_loop_delay)

                    if self._consecutive_errors >= self.config.max_consecutive_errors:
                        logger.error(
                            f"Agent {self.agent_id} hit error limit "
                            f"({self._consecutive_errors}), pausing"
                        )
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

    def _has_resources(self) -> bool:
        """Check if agent has capacity for at least one action.

        Returns:
            True if agent has capacity in all required resources.
        """
        for resource in self.config.resources_to_check:
            if not self.rate_tracker.has_capacity(self.agent_id, resource):
                return False
        return True

    async def _wait_for_resources(self) -> bool:
        """Wait until all required resources have capacity.

        Used when resource_exhaustion_policy is "block".
        Waits for each resource in sequence using wait_for_capacity.

        Returns:
            True if all resources acquired, False if timeout or stop requested.
        """
        for resource in self.config.resources_to_check:
            if not self.rate_tracker.has_capacity(self.agent_id, resource):
                # Check if we should stop before waiting
                if self._state in (AgentState.STOPPING, AgentState.STOPPED):
                    return False

                # Wait for this resource with a periodic check interval
                acquired = await self.rate_tracker.wait_for_capacity(
                    self.agent_id,
                    resource,
                    amount=1.0,
                    timeout=self.config.resource_check_interval,
                )
                if not acquired:
                    # Timeout - let loop check state and try again
                    return False
        return True

    async def _check_wake_condition(self) -> bool:
        """Check if wake condition is satisfied.

        Returns:
            True if condition is met or no condition is set.
        """
        if not self._wake_condition:
            return True

        cond = self._wake_condition

        if cond.condition_type == "time":
            return bool(time.time() >= cond.value)

        if cond.condition_type == "event":
            # Event-based waking would require an event bus
            # For now, always return False (external caller must use wake())
            return False

        if cond.condition_type == "resource":
            # Check if resource threshold met
            resource, threshold = cond.value
            return bool(self.rate_tracker.get_remaining(self.agent_id, resource) >= threshold)

        return False

    async def _execute_iteration(self) -> dict[str, Any]:
        """Execute one iteration of the agent loop.

        Returns:
            Result dict with success, action, and optional error fields.
        """
        try:
            # Let agent decide what to do
            action = await self.decide_action()

            if action is None:
                # Agent chose to do nothing
                return {"success": True, "action": None}

            # Execute the action
            result = await self.execute_action(action)

            return {
                "success": result.get("success", False),
                "action": action,
                "result": result,
            }

        except Exception as e:
            logger.exception(f"Agent {self.agent_id} iteration error: {e}")
            return {"success": False, "error": str(e)}


class AgentLoopManager:
    """Manages all agent loops in the simulation.

    Provides centralized creation, starting, and stopping of agent loops.

    Attributes:
        rate_tracker: Rate tracker for resource checking
    """

    def __init__(self, rate_tracker: "RateTracker") -> None:
        """Initialize the manager.

        Args:
            rate_tracker: Rate tracker for resource checking
        """
        self.rate_tracker = rate_tracker
        self._loops: dict[str, AgentLoop] = {}

    def create_loop(
        self,
        agent_id: str,
        decide_action: Callable[[], Awaitable[dict[str, Any] | None]],
        execute_action: Callable[[dict[str, Any]], Awaitable[dict[str, Any]]],
        config: AgentLoopConfig | None = None,
        is_alive: Callable[[], bool] | None = None,
    ) -> AgentLoop:
        """Create an agent loop.

        Args:
            agent_id: Unique identifier for the agent
            decide_action: Async callback to decide next action
            execute_action: Async callback to execute an action
            config: Loop configuration (optional, uses defaults)
            is_alive: Callback to check if agent is still alive (optional)

        Returns:
            The created AgentLoop

        Raises:
            ValueError: If a loop already exists for this agent
        """
        if agent_id in self._loops:
            raise ValueError(f"Loop already exists for agent {agent_id}")

        loop = AgentLoop(
            agent_id=agent_id,
            decide_action=decide_action,
            execute_action=execute_action,
            rate_tracker=self.rate_tracker,
            config=config or AgentLoopConfig(),
            is_alive=is_alive or (lambda: True),
        )
        self._loops[agent_id] = loop
        return loop

    def create_loop_for_agent(
        self,
        agent: AgentProtocol,
        config: AgentLoopConfig | None = None,
    ) -> AgentLoop:
        """Create an agent loop from an agent implementing AgentProtocol.

        This is a convenience method that extracts the required callbacks
        from an agent object.

        Args:
            agent: Agent implementing AgentProtocol
            config: Loop configuration (optional, uses defaults)

        Returns:
            The created AgentLoop

        Raises:
            ValueError: If a loop already exists for this agent
        """
        return self.create_loop(
            agent_id=agent.agent_id,
            decide_action=agent.decide_action,
            execute_action=agent.execute_action,
            config=config,
            is_alive=lambda: agent.alive,
        )

    async def start_all(self) -> None:
        """Start all agent loops.

        Starts all registered loops concurrently.
        """
        await asyncio.gather(*[loop.start() for loop in self._loops.values()])

    async def stop_all(self, timeout: float | None = None) -> None:
        """Stop all agent loops.

        Stops all registered loops concurrently.

        Args:
            timeout: Maximum seconds to wait for each loop to stop.
                     Defaults to config timeouts.loop_manager_stop.
        """
        if timeout is None:
            timeout = get_validated_config().timeouts.loop_manager_stop
        await asyncio.gather(
            *[loop.stop(timeout) for loop in self._loops.values()]
        )

    def get_loop(self, agent_id: str) -> AgentLoop | None:
        """Get loop by agent ID.

        Args:
            agent_id: ID of the agent

        Returns:
            The AgentLoop if found, None otherwise
        """
        return self._loops.get(agent_id)

    def remove_loop(self, agent_id: str) -> bool:
        """Remove a loop by agent ID.

        The loop must be stopped before removal.

        Args:
            agent_id: ID of the agent

        Returns:
            True if loop was removed, False if not found

        Raises:
            ValueError: If the loop is still running
        """
        loop = self._loops.get(agent_id)
        if loop is None:
            return False
        if loop.is_running:
            raise ValueError(
                f"Cannot remove running loop for agent {agent_id}. Stop it first."
            )
        del self._loops[agent_id]
        return True

    @property
    def running_count(self) -> int:
        """Count of running agent loops."""
        return sum(1 for loop in self._loops.values() if loop.is_running)

    @property
    def loop_count(self) -> int:
        """Total count of registered loops."""
        return len(self._loops)

    def get_all_states(self) -> dict[str, AgentState]:
        """Get the state of all loops.

        Returns:
            Dict mapping agent_id to AgentState
        """
        return {agent_id: loop.state for agent_id, loop in self._loops.items()}
