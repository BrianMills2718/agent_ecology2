"""Agent Supervisor for automatic restart of crashed agents.

Implements Plan #145: Supervisor Auto-Restart.

The supervisor monitors agent loops and distinguishes between:
- Dumb Death: Runtime errors, bugs -> auto-restart with backoff
- Smart Death: Zero scrip, economic failure -> no restart
- Voluntary Death: Agent requested shutdown -> no restart

This ensures agents fail from economic/predictive inadequacy, not bugs.
"""

from __future__ import annotations

import asyncio
import logging
import random
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import TYPE_CHECKING, Callable

from src.config import get

if TYPE_CHECKING:
    from src.simulation.agent_loop import AgentLoop, AgentLoopManager
    from src.world.world import World

logger = logging.getLogger(__name__)


class DeathType(Enum):
    """Classification of why an agent stopped."""

    DUMB = "dumb"  # Runtime error, bug -> should restart
    SMART = "smart"  # Economic failure (zero scrip) -> no restart
    VOLUNTARY = "voluntary"  # Agent requested shutdown -> no restart
    UNKNOWN = "unknown"  # Could not determine


@dataclass
class RestartPolicy:
    """Configuration for supervisor restart behavior."""

    enabled: bool = True
    max_restarts_per_hour: int = 10
    initial_backoff_seconds: float = 5.0
    max_backoff_seconds: float = 300.0
    backoff_multiplier: float = 2.0
    jitter_factor: float = 0.1  # Add randomness to prevent thundering herd

    # What triggers a restart
    restart_on_error: bool = True
    restart_on_timeout: bool = True
    restart_on_resource_exhaustion: bool = False  # Wait for resources instead

    @classmethod
    def from_config(cls) -> RestartPolicy:
        """Load policy from config file."""
        supervisor_config = get("supervisor", {})
        policy_config = supervisor_config.get("restart_policy", {})

        return cls(
            enabled=supervisor_config.get("enabled", True),
            max_restarts_per_hour=policy_config.get("max_restarts_per_hour", 10),
            initial_backoff_seconds=policy_config.get("initial_backoff_seconds", 5.0),
            max_backoff_seconds=policy_config.get("max_backoff_seconds", 300.0),
            backoff_multiplier=policy_config.get("backoff_multiplier", 2.0),
            jitter_factor=policy_config.get("jitter_factor", 0.1),
            restart_on_error=policy_config.get("restart_on_error", True),
            restart_on_timeout=policy_config.get("restart_on_timeout", True),
            restart_on_resource_exhaustion=policy_config.get(
                "restart_on_resource_exhaustion", False
            ),
        )


@dataclass
class AgentRestartState:
    """Tracks restart state for a single agent."""

    restart_count: int = 0
    restart_timestamps: list[datetime] = field(default_factory=list)
    current_backoff: float = 0.0
    last_restart: datetime | None = None
    last_death_type: DeathType = DeathType.UNKNOWN
    permanently_dead: bool = False


@dataclass
class SupervisorState:
    """Global supervisor state tracking."""

    agents: dict[str, AgentRestartState] = field(default_factory=dict)
    total_restarts: int = 0
    total_permanent_deaths: int = 0
    started_at: datetime = field(default_factory=datetime.now)

    def get_agent_state(self, agent_id: str) -> AgentRestartState:
        """Get or create restart state for an agent."""
        if agent_id not in self.agents:
            self.agents[agent_id] = AgentRestartState()
        return self.agents[agent_id]


class AgentSupervisor:
    """Monitors agent loops and restarts crashed agents.

    The supervisor runs as a background task alongside the simulation,
    periodically checking for crashed agents and restarting them with
    exponential backoff.

    Key behaviors:
    - Only restarts "dumb deaths" (bugs, errors)
    - Does NOT restart "smart deaths" (economic failure, zero scrip)
    - Applies exponential backoff to prevent thrashing
    - Enforces per-agent restart limits per hour
    - Preserves agent state (memory, scrip) across restarts
    """

    def __init__(
        self,
        loop_manager: AgentLoopManager,
        world: World,
        policy: RestartPolicy | None = None,
        restart_callback: Callable[[str], None] | None = None,
    ):
        """Initialize supervisor.

        Args:
            loop_manager: The AgentLoopManager to monitor
            world: World instance for checking agent state
            policy: Restart policy configuration
            restart_callback: Called when an agent is restarted (for testing/hooks)
        """
        self.loop_manager = loop_manager
        self.world = world
        self.policy = policy or RestartPolicy.from_config()
        self.restart_callback = restart_callback
        self.state = SupervisorState()
        self._running = False
        self._task: asyncio.Task[None] | None = None
        self._check_interval = 1.0  # Seconds between checks

    async def start(self) -> None:
        """Start the supervisor monitoring loop."""
        if self._running:
            logger.warning("Supervisor already running")
            return

        self._running = True
        self._task = asyncio.create_task(self._monitor_loop())
        logger.info(
            "Supervisor started",
            extra={
                "policy_enabled": self.policy.enabled,
                "max_restarts_per_hour": self.policy.max_restarts_per_hour,
            },
        )

    async def stop(self) -> None:
        """Stop the supervisor monitoring loop."""
        self._running = False
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
            self._task = None
        logger.info("Supervisor stopped")

    async def _monitor_loop(self) -> None:
        """Main monitoring loop - checks all agents periodically."""
        while self._running:
            try:
                await self._check_all_agents()
            except Exception as e:
                logger.error(f"Supervisor monitor error: {e}")
            await asyncio.sleep(self._check_interval)

    async def _check_all_agents(self) -> None:
        """Check all agent loops and restart if needed."""
        if not self.policy.enabled:
            return

        states = self.loop_manager.get_all_states()

        for agent_id, agent_state in states.items():
            # Import here to avoid circular dependency
            from src.simulation.agent_loop import AgentState

            # Check if agent is in a crashed/paused state
            if agent_state in (AgentState.PAUSED, AgentState.STOPPED):
                await self._evaluate_agent(agent_id)

    async def _evaluate_agent(self, agent_id: str) -> None:
        """Evaluate whether a paused/stopped agent should be restarted."""
        restart_state = self.state.get_agent_state(agent_id)

        # Skip if permanently dead
        if restart_state.permanently_dead:
            return

        # Classify the death
        death_type = self._classify_death(agent_id)
        restart_state.last_death_type = death_type

        # Only restart dumb deaths
        if death_type != DeathType.DUMB:
            if not restart_state.permanently_dead:
                restart_state.permanently_dead = True
                self.state.total_permanent_deaths += 1
                logger.info(
                    f"Agent {agent_id} permanently dead",
                    extra={"death_type": death_type.value, "agent_id": agent_id},
                )
            return

        # Check restart eligibility
        if not self._can_restart(agent_id):
            return

        # Check backoff
        if not self._backoff_expired(agent_id):
            return

        # Restart the agent
        await self._restart_agent(agent_id)

    def _classify_death(self, agent_id: str) -> DeathType:
        """Determine why an agent stopped.

        Returns:
            DeathType indicating the cause of death
        """
        # Check for economic death (zero scrip)
        try:
            scrip = self.world.ledger.get_scrip(agent_id)
            if scrip <= 0:
                logger.debug(f"Agent {agent_id} has zero scrip - smart death")
                return DeathType.SMART
        except Exception as e:
            logger.warning(f"Could not check scrip for {agent_id}: {e}")

        # Check for voluntary shutdown
        loop = self.loop_manager.loops.get(agent_id)
        if loop and getattr(loop, "voluntary_shutdown", False):
            return DeathType.VOLUNTARY

        # Check if loop has a recorded crash reason
        if loop:
            crash_reason = getattr(loop, "crash_reason", None)
            if crash_reason:
                # Resource exhaustion - only restart if configured
                if "resource" in str(crash_reason).lower():
                    if self.policy.restart_on_resource_exhaustion:
                        return DeathType.DUMB
                    return DeathType.SMART  # Treat as economic

                # Timeout - restart if configured
                if "timeout" in str(crash_reason).lower():
                    if self.policy.restart_on_timeout:
                        return DeathType.DUMB
                    return DeathType.SMART

                # Other errors - restart if configured
                if self.policy.restart_on_error:
                    return DeathType.DUMB

        # Default: assume dumb death (bug)
        return DeathType.DUMB

    def _can_restart(self, agent_id: str) -> bool:
        """Check if agent is eligible for restart."""
        restart_state = self.state.get_agent_state(agent_id)

        # Prune old restart timestamps (older than 1 hour)
        cutoff = datetime.now() - timedelta(hours=1)
        restart_state.restart_timestamps = [
            ts for ts in restart_state.restart_timestamps if ts > cutoff
        ]

        # Check hourly limit
        if len(restart_state.restart_timestamps) >= self.policy.max_restarts_per_hour:
            logger.warning(
                f"Agent {agent_id} exceeded restart limit",
                extra={
                    "restart_count": len(restart_state.restart_timestamps),
                    "limit": self.policy.max_restarts_per_hour,
                    "agent_id": agent_id,
                },
            )
            restart_state.permanently_dead = True
            self.state.total_permanent_deaths += 1
            return False

        return True

    def _backoff_expired(self, agent_id: str) -> bool:
        """Check if backoff period has elapsed."""
        restart_state = self.state.get_agent_state(agent_id)

        if restart_state.last_restart is None:
            return True

        elapsed = (datetime.now() - restart_state.last_restart).total_seconds()
        return elapsed >= restart_state.current_backoff

    def _calculate_backoff(self, agent_id: str) -> float:
        """Calculate next backoff duration with jitter."""
        restart_state = self.state.get_agent_state(agent_id)

        if restart_state.current_backoff == 0:
            base = self.policy.initial_backoff_seconds
        else:
            base = restart_state.current_backoff * self.policy.backoff_multiplier

        # Cap at max
        base = min(base, self.policy.max_backoff_seconds)

        # Add jitter
        jitter = base * self.policy.jitter_factor * random.uniform(-1, 1)
        return max(0, base + jitter)

    async def _restart_agent(self, agent_id: str) -> None:
        """Restart a crashed agent."""
        restart_state = self.state.get_agent_state(agent_id)

        # Calculate and apply backoff
        backoff = self._calculate_backoff(agent_id)
        restart_state.current_backoff = backoff

        logger.info(
            f"Restarting agent {agent_id}",
            extra={
                "agent_id": agent_id,
                "attempt": restart_state.restart_count + 1,
                "backoff": backoff,
            },
        )

        try:
            # Get the agent loop
            loop = self.loop_manager.loops.get(agent_id)
            if not loop:
                logger.error(f"Cannot restart {agent_id}: loop not found")
                return

            # Reset loop state and restart
            await self._reset_and_restart_loop(agent_id, loop)

            # Update state
            restart_state.restart_count += 1
            restart_state.restart_timestamps.append(datetime.now())
            restart_state.last_restart = datetime.now()
            self.state.total_restarts += 1

            # Call callback if provided
            if self.restart_callback:
                self.restart_callback(agent_id)

            logger.info(
                f"Agent {agent_id} restarted successfully",
                extra={
                    "agent_id": agent_id,
                    "total_restarts": restart_state.restart_count,
                },
            )

        except Exception as e:
            logger.error(f"Failed to restart agent {agent_id}: {e}")

    async def _reset_and_restart_loop(
        self, agent_id: str, loop: AgentLoop
    ) -> None:
        """Reset loop state and restart it.

        Preserves:
        - Agent memory
        - Agent scrip
        - Agent artifacts

        Resets:
        - Error counters
        - Loop state
        """
        # Reset error tracking
        loop.consecutive_errors = 0

        # Clear crash reason
        if hasattr(loop, "crash_reason"):
            loop.crash_reason = None

        # Mark as no longer voluntarily shutdown
        if hasattr(loop, "voluntary_shutdown"):
            loop.voluntary_shutdown = False

        # Restart the loop
        # The loop manager's start method handles the state transition
        await self.loop_manager.start_loop(agent_id)

    def get_status(self) -> dict[str, object]:
        """Get current supervisor status for observability."""
        return {
            "running": self._running,
            "policy_enabled": self.policy.enabled,
            "total_restarts": self.state.total_restarts,
            "total_permanent_deaths": self.state.total_permanent_deaths,
            "uptime_seconds": (
                datetime.now() - self.state.started_at
            ).total_seconds(),
            "agents": {
                agent_id: {
                    "restart_count": state.restart_count,
                    "current_backoff": state.current_backoff,
                    "last_death_type": state.last_death_type.value,
                    "permanently_dead": state.permanently_dead,
                }
                for agent_id, state in self.state.agents.items()
            },
        }

    def reset_agent_backoff(self, agent_id: str) -> None:
        """Reset backoff for an agent (called on successful iteration)."""
        restart_state = self.state.get_agent_state(agent_id)
        restart_state.current_backoff = 0.0
