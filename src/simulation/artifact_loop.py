"""Autonomous artifact loop implementation (Plan #255).

Provides continuous, self-driving execution loops for artifacts with has_loop=True.
This enables V4 artifact-based agents that run autonomously and invoke services
like kernel_llm_gateway to "think".

Mirrors the structure of agent_loop.py but works with artifacts instead of
Agent instances. Artifacts execute their code via the sandbox executor.

Usage:
    from src.simulation.artifact_loop import ArtifactLoop, ArtifactLoopManager

    manager = ArtifactLoopManager(world, rate_tracker)
    manager.discover_loops()  # Find all has_loop=True artifacts
    await manager.start_all()
    # ... artifacts run autonomously ...
    await manager.stop_all()
"""

from __future__ import annotations

import asyncio
import logging
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import TYPE_CHECKING, Any

from ..config import get_validated_config

if TYPE_CHECKING:
    from ..world.rate_tracker import RateTracker
    from ..world.world import World


logger = logging.getLogger(__name__)


class ArtifactState(str, Enum):
    """State of an artifact's autonomous loop."""

    STARTING = "starting"
    RUNNING = "running"
    SLEEPING = "sleeping"
    PAUSED = "paused"  # Resource exhaustion or error limit
    STOPPING = "stopping"
    STOPPED = "stopped"


@dataclass
class ArtifactLoopConfig:
    """Configuration for an artifact's autonomous loop.

    Attributes:
        min_loop_delay: Minimum seconds between executions (default: 0.1)
        max_loop_delay: Maximum backoff delay on errors (default: 10.0)
        resource_check_interval: How often to check resources when paused (default: 1.0)
        max_consecutive_errors: Errors before forced pause (default: 5)
    """

    min_loop_delay: float = 0.1
    max_loop_delay: float = 10.0
    resource_check_interval: float = 1.0
    max_consecutive_errors: int = 5

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


@dataclass
class ArtifactLoop:
    """Autonomous execution loop for a single artifact with has_loop=True.

    The artifact loop:
    1. Checks if artifact still exists
    2. Checks resource availability (llm_budget)
    3. Executes artifact code via sandbox
    4. Handles results
    5. Sleeps
    6. Repeats

    Attributes:
        artifact_id: Unique identifier for the artifact
        world: World instance for execution context
        rate_tracker: Rate tracker for resource checking
        config: Loop configuration
    """

    artifact_id: str
    world: "World"
    rate_tracker: "RateTracker"
    config: ArtifactLoopConfig = field(default_factory=ArtifactLoopConfig)

    _state: ArtifactState = field(default=ArtifactState.STOPPED, init=False)
    _task: asyncio.Task[None] | None = field(default=None, init=False)
    _consecutive_errors: int = field(default=0, init=False)
    _wake_event: asyncio.Event = field(default_factory=asyncio.Event, init=False)
    _iteration_count: int = field(default=0, init=False)
    _crash_reason: str | None = field(default=None, init=False)

    @property
    def state(self) -> ArtifactState:
        """Current state of the loop."""
        return self._state

    @property
    def is_running(self) -> bool:
        """Whether the loop is actively running (not stopped)."""
        return self._state in (
            ArtifactState.STARTING,
            ArtifactState.RUNNING,
            ArtifactState.SLEEPING,
            ArtifactState.PAUSED,
        )

    @property
    def consecutive_errors(self) -> int:
        """Number of consecutive errors encountered."""
        return self._consecutive_errors

    @property
    def iteration_count(self) -> int:
        """Total number of iterations executed."""
        return self._iteration_count

    @property
    def crash_reason(self) -> str | None:
        """Reason for crash if loop stopped due to error."""
        return self._crash_reason

    def _artifact_exists(self) -> bool:
        """Check if the artifact still exists in the store."""
        artifact = self.world.artifacts.get(self.artifact_id)
        return artifact is not None

    def _has_budget(self) -> bool:
        """Check if artifact has LLM budget remaining."""
        try:
            budget = self.world.ledger.get_llm_budget(self.artifact_id)
            return budget > 0
        except Exception:
            # If artifact doesn't have a budget entry, assume it's ok
            # (might be using a different resource model)
            return True

    async def start(self) -> None:
        """Start the autonomous loop.

        If already running, logs a warning and returns without action.
        Creates an asyncio task to run the main loop.
        """
        if self._state != ArtifactState.STOPPED:
            logger.warning(
                f"Artifact {self.artifact_id} already running, state={self._state}"
            )
            return

        self._state = ArtifactState.STARTING
        self._consecutive_errors = 0
        self._iteration_count = 0
        self._wake_event.clear()
        self._task = asyncio.create_task(self._run_loop())
        logger.info(f"Artifact {self.artifact_id} loop started")

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
        if self._state == ArtifactState.STOPPED:
            return

        self._state = ArtifactState.STOPPING
        # Wake up any sleeping artifact so it can exit
        self._wake_event.set()

        if self._task:
            try:
                await asyncio.wait_for(self._task, timeout=timeout)
            except asyncio.TimeoutError:
                logger.warning(
                    f"Artifact {self.artifact_id} did not stop gracefully, cancelling"
                )
                self._task.cancel()
                try:
                    await self._task
                except asyncio.CancelledError:
                    pass

        self._state = ArtifactState.STOPPED
        self._task = None
        logger.info(f"Artifact {self.artifact_id} loop stopped")

    async def _run_loop(self) -> None:
        """Main autonomous loop.

        Runs until stop() is called or artifact no longer exists.
        Handles resource checking and error backoff.
        """
        self._state = ArtifactState.RUNNING
        delay = self.config.min_loop_delay

        while self._state not in (ArtifactState.STOPPING, ArtifactState.STOPPED):
            try:
                # Check if artifact still exists
                if not self._artifact_exists():
                    logger.info(f"Artifact {self.artifact_id} no longer exists, stopping")
                    break

                # Check resource availability
                if not self._has_budget():
                    if self._state != ArtifactState.PAUSED:
                        self._state = ArtifactState.PAUSED
                        logger.debug(f"Artifact {self.artifact_id} paused (no budget)")
                    await asyncio.sleep(self.config.resource_check_interval)
                    continue

                # Unpause if we were paused and now have resources
                if self._state == ArtifactState.PAUSED:
                    self._state = ArtifactState.RUNNING
                    logger.debug(f"Artifact {self.artifact_id} unpaused")

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
                        error_msg = result.get("error", "max_consecutive_errors reached")
                        logger.error(
                            f"Artifact {self.artifact_id} hit error limit "
                            f"({self._consecutive_errors}), pausing: {error_msg}"
                        )
                        self._crash_reason = f"error_limit: {error_msg}"
                        self._state = ArtifactState.PAUSED

                await asyncio.sleep(delay)

            except asyncio.CancelledError:
                logger.debug(f"Artifact {self.artifact_id} loop cancelled")
                break
            except Exception as e:
                logger.exception(f"Artifact {self.artifact_id} loop error: {e}")
                self._consecutive_errors += 1
                await asyncio.sleep(delay)

        self._state = ArtifactState.STOPPED

    async def _execute_iteration(self) -> dict[str, Any]:
        """Execute one iteration of the artifact loop.

        Executes the artifact's code via the sandbox executor.

        Returns:
            Result dict with success, result, and optional error fields.
        """
        try:
            # Get the artifact
            artifact = self.world.artifacts.get(self.artifact_id)
            if artifact is None:
                return {"success": False, "error": "Artifact not found"}

            # Get the artifact's code
            code = artifact.code
            if code is None:
                return {"success": False, "error": "Artifact has no code"}

            # Execute via world's execute mechanism
            # The artifact runs in a sandbox with kernel_state, kernel_actions,
            # and potentially _syscall_llm if it has can_call_llm capability
            from ..world.executor import SafeExecutor

            executor = SafeExecutor()
            # Use execute_with_invoke which supports world, kernel interfaces, and syscalls
            result = executor.execute_with_invoke(
                code=code,
                world=self.world,
                caller_id=self.artifact_id,
                artifact_id=self.artifact_id,
                artifact_store=self.world.artifacts,
            )

            return {
                "success": True,
                "result": result,
            }

        except Exception as e:
            logger.exception(f"Artifact {self.artifact_id} iteration error: {e}")
            return {"success": False, "error": str(e)}


class ArtifactLoopManager:
    """Manages all artifact loops in the simulation.

    Provides centralized discovery, creation, starting, and stopping
    of artifact loops for has_loop=True artifacts.

    Attributes:
        world: World instance for artifact access
        rate_tracker: Rate tracker for resource checking
    """

    def __init__(self, world: "World", rate_tracker: "RateTracker") -> None:
        """Initialize the manager.

        Args:
            world: World instance for artifact access
            rate_tracker: Rate tracker for resource checking
        """
        self.world = world
        self.rate_tracker = rate_tracker
        self._loops: dict[str, ArtifactLoop] = {}

    def discover_loops(self) -> list[str]:
        """Discover all artifacts with has_loop=True and executable code.

        Only creates loops for artifacts that have actual code to execute.
        File-based agents (loaded via load_agents()) have has_loop=True but
        no code - they run through AgentLoopManager instead.

        Returns:
            List of artifact IDs for which loops were created.
        """
        discovered = []
        for artifact_id, artifact in self.world.artifacts.artifacts.items():
            # Only create loops for artifacts with actual code to execute
            # File-based agents have has_loop=True but code="" - skip them
            if artifact.has_loop and artifact.code and artifact_id not in self._loops:
                self.create_loop(artifact_id)
                discovered.append(artifact_id)
                logger.info(f"Discovered has_loop artifact: {artifact_id}")
        return discovered

    def create_loop(
        self,
        artifact_id: str,
        config: ArtifactLoopConfig | None = None,
    ) -> ArtifactLoop:
        """Create an artifact loop.

        Args:
            artifact_id: Unique identifier for the artifact
            config: Loop configuration (optional, uses defaults)

        Returns:
            The created ArtifactLoop

        Raises:
            ValueError: If a loop already exists for this artifact
            ValueError: If artifact doesn't exist or doesn't have has_loop=True
        """
        if artifact_id in self._loops:
            raise ValueError(f"Loop already exists for artifact {artifact_id}")

        # Verify artifact exists and has has_loop=True
        artifact = self.world.artifacts.get(artifact_id)
        if artifact is None:
            raise ValueError(f"Artifact {artifact_id} does not exist")
        if not artifact.has_loop:
            raise ValueError(f"Artifact {artifact_id} does not have has_loop=True")

        loop = ArtifactLoop(
            artifact_id=artifact_id,
            world=self.world,
            rate_tracker=self.rate_tracker,
            config=config or ArtifactLoopConfig(),
        )
        self._loops[artifact_id] = loop
        return loop

    async def start_all(self) -> None:
        """Start all artifact loops.

        Starts all registered loops concurrently.
        """
        await asyncio.gather(*[loop.start() for loop in self._loops.values()])

    async def stop_all(self, timeout: float | None = None) -> None:
        """Stop all artifact loops.

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

    def get_loop(self, artifact_id: str) -> ArtifactLoop | None:
        """Get loop by artifact ID.

        Args:
            artifact_id: ID of the artifact

        Returns:
            The ArtifactLoop if found, None otherwise
        """
        return self._loops.get(artifact_id)

    def remove_loop(self, artifact_id: str) -> bool:
        """Remove a loop by artifact ID.

        The loop must be stopped before removal.

        Args:
            artifact_id: ID of the artifact

        Returns:
            True if loop was removed, False if not found

        Raises:
            ValueError: If the loop is still running
        """
        loop = self._loops.get(artifact_id)
        if loop is None:
            return False
        if loop.is_running:
            raise ValueError(
                f"Cannot remove running loop for artifact {artifact_id}. Stop it first."
            )
        del self._loops[artifact_id]
        return True

    @property
    def running_count(self) -> int:
        """Count of running artifact loops."""
        return sum(1 for loop in self._loops.values() if loop.is_running)

    @property
    def loop_count(self) -> int:
        """Total count of registered loops."""
        return len(self._loops)

    def get_all_states(self) -> dict[str, ArtifactState]:
        """Get the state of all loops.

        Returns:
            Dict mapping artifact_id to ArtifactState
        """
        return {artifact_id: loop.state for artifact_id, loop in self._loops.items()}

    @property
    def loops(self) -> dict[str, ArtifactLoop]:
        """Access to all loops (for monitoring)."""
        return self._loops

    async def start_loop(self, artifact_id: str) -> None:
        """Start a single artifact loop.

        Args:
            artifact_id: ID of the artifact to start

        Raises:
            ValueError: If loop not found
        """
        loop = self._loops.get(artifact_id)
        if loop is None:
            raise ValueError(f"No loop found for artifact {artifact_id}")
        await loop.start()
