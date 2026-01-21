"""Tests for Agent Supervisor (Plan #145).

Tests that the supervisor:
- Detects crashed/paused agents
- Restarts "dumb deaths" (runtime errors, bugs)
- Does NOT restart "smart deaths" (zero scrip, economic failure)
- Applies exponential backoff
- Enforces restart limits per hour
- Preserves agent state across restarts
"""

import asyncio
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.simulation.agent_loop import AgentLoop, AgentLoopManager, AgentState
from src.simulation.supervisor import (
    AgentSupervisor,
    DeathType,
    RestartPolicy,
    AgentRestartState,
    SupervisorState,
)


class TestDeathType:
    """Tests for DeathType enum."""

    def test_death_types_exist(self) -> None:
        """Verify all death types are defined."""
        assert DeathType.DUMB.value == "dumb"
        assert DeathType.SMART.value == "smart"
        assert DeathType.VOLUNTARY.value == "voluntary"
        assert DeathType.UNKNOWN.value == "unknown"


class TestRestartPolicy:
    """Tests for RestartPolicy configuration."""

    def test_default_policy(self) -> None:
        """Test default policy values."""
        policy = RestartPolicy()
        assert policy.enabled is True
        assert policy.max_restarts_per_hour == 10
        assert policy.initial_backoff_seconds == 5.0
        assert policy.max_backoff_seconds == 300.0
        assert policy.backoff_multiplier == 2.0
        assert policy.jitter_factor == 0.1
        assert policy.restart_on_error is True
        assert policy.restart_on_timeout is True
        assert policy.restart_on_resource_exhaustion is False

    def test_custom_policy(self) -> None:
        """Test custom policy values."""
        policy = RestartPolicy(
            enabled=False,
            max_restarts_per_hour=5,
            initial_backoff_seconds=1.0,
            max_backoff_seconds=60.0,
        )
        assert policy.enabled is False
        assert policy.max_restarts_per_hour == 5
        assert policy.initial_backoff_seconds == 1.0
        assert policy.max_backoff_seconds == 60.0

    def test_from_config_fallback(self) -> None:
        """Test that from_config returns defaults when no config."""
        with patch("src.simulation.supervisor.get", return_value={}):
            policy = RestartPolicy.from_config()
            assert policy.enabled is True  # Default when config empty


class TestAgentRestartState:
    """Tests for AgentRestartState tracking."""

    def test_default_state(self) -> None:
        """Test default restart state."""
        state = AgentRestartState()
        assert state.restart_count == 0
        assert state.restart_timestamps == []
        assert state.current_backoff == 0.0
        assert state.last_restart is None
        assert state.last_death_type == DeathType.UNKNOWN
        assert state.permanently_dead is False


class TestSupervisorState:
    """Tests for SupervisorState tracking."""

    def test_get_agent_state_creates_new(self) -> None:
        """Test that get_agent_state creates new state if not exists."""
        state = SupervisorState()
        assert "agent1" not in state.agents

        agent_state = state.get_agent_state("agent1")
        assert agent_state is not None
        assert "agent1" in state.agents
        assert agent_state.restart_count == 0

    def test_get_agent_state_returns_existing(self) -> None:
        """Test that get_agent_state returns existing state."""
        state = SupervisorState()
        agent_state1 = state.get_agent_state("agent1")
        agent_state1.restart_count = 5

        agent_state2 = state.get_agent_state("agent1")
        assert agent_state2.restart_count == 5
        assert agent_state1 is agent_state2


class TestAgentSupervisor:
    """Tests for AgentSupervisor functionality."""

    @pytest.fixture
    def mock_rate_tracker(self) -> MagicMock:
        """Create a mock rate tracker."""
        tracker = MagicMock()
        tracker.has_capacity.return_value = True
        return tracker

    @pytest.fixture
    def mock_loop_manager(self, mock_rate_tracker: MagicMock) -> AgentLoopManager:
        """Create a real loop manager with mock rate tracker."""
        return AgentLoopManager(mock_rate_tracker)

    @pytest.fixture
    def mock_world(self) -> MagicMock:
        """Create a mock world."""
        world = MagicMock()
        world.ledger = MagicMock()
        world.ledger.get_scrip.return_value = 100  # Agent has scrip
        return world

    @pytest.fixture
    def supervisor(
        self, mock_loop_manager: AgentLoopManager, mock_world: MagicMock
    ) -> AgentSupervisor:
        """Create a supervisor with mocks."""
        policy = RestartPolicy(
            initial_backoff_seconds=0.1,  # Fast for tests
            max_backoff_seconds=1.0,
        )
        return AgentSupervisor(mock_loop_manager, mock_world, policy)

    def test_supervisor_init(
        self, mock_loop_manager: AgentLoopManager, mock_world: MagicMock
    ) -> None:
        """Test supervisor initialization."""
        supervisor = AgentSupervisor(mock_loop_manager, mock_world)
        assert supervisor.loop_manager is mock_loop_manager
        assert supervisor.world is mock_world
        assert supervisor.policy.enabled is True
        assert supervisor._running is False

    @pytest.mark.asyncio
    async def test_start_stop(self, supervisor: AgentSupervisor) -> None:
        """Test supervisor start and stop."""
        await supervisor.start()
        assert supervisor._running is True
        assert supervisor._task is not None

        await supervisor.stop()
        assert supervisor._running is False
        assert supervisor._task is None

    @pytest.mark.asyncio
    async def test_start_idempotent(self, supervisor: AgentSupervisor) -> None:
        """Test that starting twice doesn't create duplicate tasks."""
        await supervisor.start()
        task1 = supervisor._task

        await supervisor.start()  # Second start
        task2 = supervisor._task

        assert task1 is task2  # Same task
        await supervisor.stop()

    def test_classify_death_smart_no_scrip(
        self, supervisor: AgentSupervisor, mock_world: MagicMock
    ) -> None:
        """Test that zero scrip = smart death."""
        mock_world.ledger.get_scrip.return_value = 0
        death_type = supervisor._classify_death("agent1")
        assert death_type == DeathType.SMART

    def test_classify_death_smart_negative_scrip(
        self, supervisor: AgentSupervisor, mock_world: MagicMock
    ) -> None:
        """Test that negative scrip = smart death."""
        mock_world.ledger.get_scrip.return_value = -10
        death_type = supervisor._classify_death("agent1")
        assert death_type == DeathType.SMART

    def test_classify_death_dumb_with_scrip(
        self, supervisor: AgentSupervisor, mock_world: MagicMock
    ) -> None:
        """Test that error with scrip = dumb death."""
        mock_world.ledger.get_scrip.return_value = 100
        death_type = supervisor._classify_death("agent1")
        assert death_type == DeathType.DUMB

    def test_classify_death_voluntary(
        self,
        supervisor: AgentSupervisor,
        mock_loop_manager: AgentLoopManager,
        mock_rate_tracker: MagicMock,
    ) -> None:
        """Test that voluntary shutdown = voluntary death."""
        # Create a loop and mark it as voluntary shutdown
        loop = mock_loop_manager.create_loop(
            "agent1",
            decide_action=AsyncMock(return_value=None),
            execute_action=AsyncMock(return_value={"success": True}),
        )
        loop.voluntary_shutdown = True

        death_type = supervisor._classify_death("agent1")
        assert death_type == DeathType.VOLUNTARY

    def test_can_restart_under_limit(self, supervisor: AgentSupervisor) -> None:
        """Test that restart is allowed under hourly limit."""
        assert supervisor._can_restart("agent1") is True

    def test_can_restart_at_limit(self, supervisor: AgentSupervisor) -> None:
        """Test that restart is blocked at hourly limit."""
        state = supervisor.state.get_agent_state("agent1")
        # Add max restarts in the last hour
        now = datetime.now()
        state.restart_timestamps = [
            now - timedelta(minutes=i) for i in range(10)
        ]

        assert supervisor._can_restart("agent1") is False
        assert state.permanently_dead is True

    def test_can_restart_prunes_old_timestamps(
        self, supervisor: AgentSupervisor
    ) -> None:
        """Test that old restart timestamps are pruned."""
        state = supervisor.state.get_agent_state("agent1")
        # Add some old restarts (more than 1 hour ago)
        state.restart_timestamps = [
            datetime.now() - timedelta(hours=2),
            datetime.now() - timedelta(hours=3),
        ]

        assert supervisor._can_restart("agent1") is True
        assert len(state.restart_timestamps) == 0  # Old ones pruned

    def test_backoff_expired_first_time(self, supervisor: AgentSupervisor) -> None:
        """Test backoff is expired on first restart."""
        assert supervisor._backoff_expired("agent1") is True

    def test_backoff_expired_after_wait(self, supervisor: AgentSupervisor) -> None:
        """Test backoff expires after waiting."""
        state = supervisor.state.get_agent_state("agent1")
        state.last_restart = datetime.now() - timedelta(seconds=10)
        state.current_backoff = 5.0

        assert supervisor._backoff_expired("agent1") is True

    def test_backoff_not_expired(self, supervisor: AgentSupervisor) -> None:
        """Test backoff not expired before wait time."""
        state = supervisor.state.get_agent_state("agent1")
        state.last_restart = datetime.now()
        state.current_backoff = 100.0

        assert supervisor._backoff_expired("agent1") is False

    def test_calculate_backoff_initial(self, supervisor: AgentSupervisor) -> None:
        """Test initial backoff calculation."""
        backoff = supervisor._calculate_backoff("agent1")
        # Should be near initial_backoff_seconds (0.1) with jitter
        assert 0.0 <= backoff <= 0.2

    def test_calculate_backoff_exponential(self, supervisor: AgentSupervisor) -> None:
        """Test exponential backoff increase."""
        state = supervisor.state.get_agent_state("agent1")
        state.current_backoff = 0.1

        backoff = supervisor._calculate_backoff("agent1")
        # Should be 0.1 * 2.0 = 0.2 with jitter
        assert 0.15 <= backoff <= 0.25

    def test_calculate_backoff_capped(self, supervisor: AgentSupervisor) -> None:
        """Test backoff is capped at max."""
        state = supervisor.state.get_agent_state("agent1")
        state.current_backoff = 10.0  # Already at max

        backoff = supervisor._calculate_backoff("agent1")
        # Should be capped at max_backoff_seconds (1.0) with jitter
        assert backoff <= 1.2  # Max + jitter

    @pytest.mark.asyncio
    async def test_restart_agent(
        self,
        supervisor: AgentSupervisor,
        mock_loop_manager: AgentLoopManager,
        mock_rate_tracker: MagicMock,
    ) -> None:
        """Test restarting an agent."""
        # Create and start a loop
        loop = mock_loop_manager.create_loop(
            "agent1",
            decide_action=AsyncMock(return_value=None),
            execute_action=AsyncMock(return_value={"success": True}),
        )

        # Track restart
        restart_count = 0

        def on_restart(agent_id: str) -> None:
            nonlocal restart_count
            restart_count += 1

        supervisor.restart_callback = on_restart

        # Simulate a crash (set state to PAUSED)
        loop._state = AgentState.PAUSED
        loop._consecutive_errors = 5
        loop._crash_reason = "test error"

        # Restart the agent
        await supervisor._restart_agent("agent1")

        # Verify state was updated
        state = supervisor.state.get_agent_state("agent1")
        assert state.restart_count == 1
        assert state.last_restart is not None
        assert supervisor.state.total_restarts == 1
        assert restart_count == 1

    @pytest.mark.asyncio
    async def test_restart_preserves_scrip(
        self,
        supervisor: AgentSupervisor,
        mock_loop_manager: AgentLoopManager,
        mock_world: MagicMock,
        mock_rate_tracker: MagicMock,
    ) -> None:
        """Test that restart preserves agent scrip."""
        # Create a loop
        loop = mock_loop_manager.create_loop(
            "agent1",
            decide_action=AsyncMock(return_value=None),
            execute_action=AsyncMock(return_value={"success": True}),
        )
        loop._state = AgentState.PAUSED

        initial_scrip = 100
        mock_world.ledger.get_scrip.return_value = initial_scrip

        await supervisor._restart_agent("agent1")

        # Scrip should not be modified (ledger.transfer should not be called)
        mock_world.ledger.transfer.assert_not_called()

    @pytest.mark.asyncio
    async def test_reset_clears_errors(
        self,
        supervisor: AgentSupervisor,
        mock_loop_manager: AgentLoopManager,
        mock_rate_tracker: MagicMock,
    ) -> None:
        """Test that reset clears error counters."""
        loop = mock_loop_manager.create_loop(
            "agent1",
            decide_action=AsyncMock(return_value=None),
            execute_action=AsyncMock(return_value={"success": True}),
        )
        loop._state = AgentState.PAUSED
        loop._consecutive_errors = 5
        loop._crash_reason = "test error"

        await supervisor._reset_and_restart_loop("agent1", loop)

        assert loop.consecutive_errors == 0
        assert loop.crash_reason is None
        assert loop.voluntary_shutdown is False

    def test_get_status(self, supervisor: AgentSupervisor) -> None:
        """Test supervisor status reporting."""
        # Add some state
        state = supervisor.state.get_agent_state("agent1")
        state.restart_count = 3
        state.last_death_type = DeathType.DUMB
        supervisor.state.total_restarts = 5
        supervisor.state.total_permanent_deaths = 1

        status = supervisor.get_status()

        assert status["running"] is False
        assert status["policy_enabled"] is True
        assert status["total_restarts"] == 5
        assert status["total_permanent_deaths"] == 1
        assert "agents" in status
        assert "agent1" in status["agents"]
        assert status["agents"]["agent1"]["restart_count"] == 3

    def test_reset_agent_backoff(self, supervisor: AgentSupervisor) -> None:
        """Test resetting backoff on successful iteration."""
        state = supervisor.state.get_agent_state("agent1")
        state.current_backoff = 100.0

        supervisor.reset_agent_backoff("agent1")

        assert state.current_backoff == 0.0

    @pytest.mark.asyncio
    async def test_evaluate_agent_skips_permanently_dead(
        self,
        supervisor: AgentSupervisor,
        mock_loop_manager: AgentLoopManager,
        mock_rate_tracker: MagicMock,
    ) -> None:
        """Test that permanently dead agents are skipped."""
        loop = mock_loop_manager.create_loop(
            "agent1",
            decide_action=AsyncMock(return_value=None),
            execute_action=AsyncMock(return_value={"success": True}),
        )
        loop._state = AgentState.PAUSED

        # Mark as permanently dead
        state = supervisor.state.get_agent_state("agent1")
        state.permanently_dead = True

        await supervisor._evaluate_agent("agent1")

        # Should not have been restarted
        assert state.restart_count == 0

    @pytest.mark.asyncio
    async def test_evaluate_agent_marks_smart_death_permanent(
        self,
        supervisor: AgentSupervisor,
        mock_loop_manager: AgentLoopManager,
        mock_world: MagicMock,
        mock_rate_tracker: MagicMock,
    ) -> None:
        """Test that smart deaths are marked permanent."""
        loop = mock_loop_manager.create_loop(
            "agent1",
            decide_action=AsyncMock(return_value=None),
            execute_action=AsyncMock(return_value={"success": True}),
        )
        loop._state = AgentState.PAUSED
        mock_world.ledger.get_scrip.return_value = 0  # Zero scrip

        await supervisor._evaluate_agent("agent1")

        state = supervisor.state.get_agent_state("agent1")
        assert state.permanently_dead is True
        assert state.last_death_type == DeathType.SMART
        assert supervisor.state.total_permanent_deaths == 1


class TestAgentLoopCrashReason:
    """Tests for AgentLoop crash_reason and voluntary_shutdown attributes."""

    @pytest.fixture
    def mock_rate_tracker(self) -> MagicMock:
        """Create a mock rate tracker."""
        tracker = MagicMock()
        tracker.has_capacity.return_value = True
        return tracker

    def test_crash_reason_attribute(self, mock_rate_tracker: MagicMock) -> None:
        """Test crash_reason property."""
        loop = AgentLoop(
            agent_id="agent1",
            decide_action=AsyncMock(return_value=None),
            execute_action=AsyncMock(return_value={"success": True}),
            rate_tracker=mock_rate_tracker,
        )

        assert loop.crash_reason is None

        loop.crash_reason = "test error"
        assert loop.crash_reason == "test error"

        loop.crash_reason = None
        assert loop.crash_reason is None

    def test_voluntary_shutdown_attribute(self, mock_rate_tracker: MagicMock) -> None:
        """Test voluntary_shutdown property."""
        loop = AgentLoop(
            agent_id="agent1",
            decide_action=AsyncMock(return_value=None),
            execute_action=AsyncMock(return_value={"success": True}),
            rate_tracker=mock_rate_tracker,
        )

        assert loop.voluntary_shutdown is False

        loop.voluntary_shutdown = True
        assert loop.voluntary_shutdown is True

    def test_consecutive_errors_setter(self, mock_rate_tracker: MagicMock) -> None:
        """Test consecutive_errors setter."""
        loop = AgentLoop(
            agent_id="agent1",
            decide_action=AsyncMock(return_value=None),
            execute_action=AsyncMock(return_value={"success": True}),
            rate_tracker=mock_rate_tracker,
        )

        assert loop.consecutive_errors == 0

        loop.consecutive_errors = 5
        assert loop.consecutive_errors == 5

        loop.consecutive_errors = 0
        assert loop.consecutive_errors == 0


class TestAgentLoopManagerExtensions:
    """Tests for AgentLoopManager extensions for supervisor."""

    @pytest.fixture
    def mock_rate_tracker(self) -> MagicMock:
        """Create a mock rate tracker."""
        tracker = MagicMock()
        tracker.has_capacity.return_value = True
        return tracker

    def test_loops_property(self, mock_rate_tracker: MagicMock) -> None:
        """Test loops property exposes internal dict."""
        manager = AgentLoopManager(mock_rate_tracker)
        manager.create_loop(
            "agent1",
            decide_action=AsyncMock(return_value=None),
            execute_action=AsyncMock(return_value={"success": True}),
        )

        loops = manager.loops
        assert "agent1" in loops
        assert loops["agent1"].agent_id == "agent1"

    @pytest.mark.asyncio
    async def test_start_loop(self, mock_rate_tracker: MagicMock) -> None:
        """Test starting individual loop."""
        manager = AgentLoopManager(mock_rate_tracker)
        loop = manager.create_loop(
            "agent1",
            decide_action=AsyncMock(return_value=None),
            execute_action=AsyncMock(return_value={"success": True}),
        )

        assert loop.state == AgentState.STOPPED

        await manager.start_loop("agent1")
        assert loop.state != AgentState.STOPPED

        await loop.stop()

    @pytest.mark.asyncio
    async def test_start_loop_not_found(self, mock_rate_tracker: MagicMock) -> None:
        """Test starting non-existent loop raises error."""
        manager = AgentLoopManager(mock_rate_tracker)

        with pytest.raises(ValueError, match="No loop found"):
            await manager.start_loop("nonexistent")
