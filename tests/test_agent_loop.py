"""Unit tests for the agent loop module.

Tests autonomous agent loop functionality including:
- AgentState enum and transitions
- WakeCondition validation
- AgentLoopConfig validation
- AgentLoop lifecycle (start, stop, sleep, wake)
- Resource-gated continuation
- Error backoff behavior
- AgentLoopManager operations
"""

from __future__ import annotations

import asyncio
import time
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.simulation.agent_loop import (
    AgentState,
    WakeCondition,
    AgentLoopConfig,
    AgentLoop,
    AgentLoopManager,
)
from src.world.rate_tracker import RateTracker


# =============================================================================
# Test Fixtures
# =============================================================================


@pytest.fixture
def rate_tracker() -> RateTracker:
    """Create a rate tracker with default limits."""
    tracker = RateTracker(window_seconds=60.0)
    tracker.configure_limit("llm_calls", max_per_window=100.0)
    tracker.configure_limit("disk_writes", max_per_window=1000.0)
    tracker.configure_limit("bandwidth_bytes", max_per_window=10485760.0)
    return tracker


@pytest.fixture
def mock_decide_action() -> AsyncMock:
    """Mock decide_action callback that returns a simple action."""
    mock = AsyncMock(return_value={"action_type": "noop"})
    return mock


@pytest.fixture
def mock_execute_action() -> AsyncMock:
    """Mock execute_action callback that returns success."""
    mock = AsyncMock(return_value={"success": True})
    return mock


@pytest.fixture
def agent_loop(
    rate_tracker: RateTracker,
    mock_decide_action: AsyncMock,
    mock_execute_action: AsyncMock,
) -> AgentLoop:
    """Create an AgentLoop with mocked callbacks."""
    config = AgentLoopConfig(
        min_loop_delay=0.01,  # Fast for testing
        max_loop_delay=0.1,
        resource_check_interval=0.01,
        max_consecutive_errors=3,
    )
    return AgentLoop(
        agent_id="test_agent",
        decide_action=mock_decide_action,
        execute_action=mock_execute_action,
        rate_tracker=rate_tracker,
        config=config,
    )


@pytest.fixture
def loop_manager(rate_tracker: RateTracker) -> AgentLoopManager:
    """Create an AgentLoopManager."""
    return AgentLoopManager(rate_tracker)


# =============================================================================
# AgentState Tests
# =============================================================================


class TestAgentState:
    """Tests for AgentState enum."""

    def test_state_values(self) -> None:
        """Verify all state values exist."""
        assert AgentState.STARTING == "starting"
        assert AgentState.RUNNING == "running"
        assert AgentState.SLEEPING == "sleeping"
        assert AgentState.PAUSED == "paused"
        assert AgentState.STOPPING == "stopping"
        assert AgentState.STOPPED == "stopped"

    def test_state_is_string_enum(self) -> None:
        """AgentState is a string enum for JSON serialization."""
        assert isinstance(AgentState.RUNNING, str)
        # The value is "running", not str() which gives "AgentState.RUNNING"
        assert AgentState.RUNNING.value == "running"
        assert AgentState.RUNNING == "running"  # Comparison works due to str inheritance


# =============================================================================
# WakeCondition Tests
# =============================================================================


class TestWakeCondition:
    """Tests for WakeCondition dataclass."""

    def test_time_condition(self) -> None:
        """Can create a time-based wake condition."""
        future_time = time.time() + 10.0
        cond = WakeCondition(condition_type="time", value=future_time)
        assert cond.condition_type == "time"
        assert cond.value == future_time

    def test_event_condition(self) -> None:
        """Can create an event-based wake condition."""
        cond = WakeCondition(condition_type="event", value="resource_available")
        assert cond.condition_type == "event"
        assert cond.value == "resource_available"

    def test_resource_condition(self) -> None:
        """Can create a resource-based wake condition."""
        cond = WakeCondition(condition_type="resource", value=("llm_calls", 50.0))
        assert cond.condition_type == "resource"
        assert cond.value == ("llm_calls", 50.0)

    def test_invalid_condition_type_raises(self) -> None:
        """Invalid condition type raises ValueError."""
        with pytest.raises(ValueError, match="Invalid condition_type"):
            WakeCondition(condition_type="invalid", value=None)


# =============================================================================
# AgentLoopConfig Tests
# =============================================================================


class TestAgentLoopConfig:
    """Tests for AgentLoopConfig validation."""

    def test_default_values(self) -> None:
        """Default config values are set correctly."""
        config = AgentLoopConfig()
        assert config.min_loop_delay == 0.1
        assert config.max_loop_delay == 10.0
        assert config.resource_check_interval == 1.0
        assert config.max_consecutive_errors == 5
        assert "llm_calls" in config.resources_to_check
        assert config.resource_exhaustion_policy == "skip"

    def test_custom_values(self) -> None:
        """Can set custom config values."""
        config = AgentLoopConfig(
            min_loop_delay=0.5,
            max_loop_delay=30.0,
            resource_check_interval=2.0,
            max_consecutive_errors=10,
            resources_to_check=["llm_calls"],
        )
        assert config.min_loop_delay == 0.5
        assert config.max_loop_delay == 30.0
        assert config.resource_check_interval == 2.0
        assert config.max_consecutive_errors == 10
        assert config.resources_to_check == ["llm_calls"]

    def test_negative_min_delay_raises(self) -> None:
        """Negative min_loop_delay raises ValueError."""
        with pytest.raises(ValueError, match="min_loop_delay must be non-negative"):
            AgentLoopConfig(min_loop_delay=-1.0)

    def test_max_less_than_min_raises(self) -> None:
        """max_loop_delay less than min_loop_delay raises ValueError."""
        with pytest.raises(ValueError, match="max_loop_delay.*must be >= min_loop_delay"):
            AgentLoopConfig(min_loop_delay=5.0, max_loop_delay=1.0)

    def test_zero_resource_check_interval_raises(self) -> None:
        """Zero resource_check_interval raises ValueError."""
        with pytest.raises(ValueError, match="resource_check_interval must be positive"):
            AgentLoopConfig(resource_check_interval=0.0)

    def test_zero_max_errors_raises(self) -> None:
        """Zero max_consecutive_errors raises ValueError."""
        with pytest.raises(ValueError, match="max_consecutive_errors must be at least 1"):
            AgentLoopConfig(max_consecutive_errors=0)

    def test_invalid_resource_exhaustion_policy_raises(self) -> None:
        """Invalid resource_exhaustion_policy raises ValueError."""
        with pytest.raises(ValueError, match="resource_exhaustion_policy must be 'skip' or 'block'"):
            AgentLoopConfig(resource_exhaustion_policy="invalid")  # type: ignore[arg-type]

    def test_valid_resource_exhaustion_policy_skip(self) -> None:
        """Can set resource_exhaustion_policy to 'skip'."""
        config = AgentLoopConfig(resource_exhaustion_policy="skip")
        assert config.resource_exhaustion_policy == "skip"

    def test_valid_resource_exhaustion_policy_block(self) -> None:
        """Can set resource_exhaustion_policy to 'block'."""
        config = AgentLoopConfig(resource_exhaustion_policy="block")
        assert config.resource_exhaustion_policy == "block"


# =============================================================================
# AgentLoop Basic Tests
# =============================================================================


class TestAgentLoopInit:
    """Tests for AgentLoop initialization."""

    def test_initial_state(self, agent_loop: AgentLoop) -> None:
        """Agent loop starts in STOPPED state."""
        assert agent_loop.state == AgentState.STOPPED
        assert not agent_loop.is_running
        assert agent_loop.consecutive_errors == 0
        assert agent_loop.iteration_count == 0

    def test_agent_id(self, agent_loop: AgentLoop) -> None:
        """Agent loop has correct agent_id."""
        assert agent_loop.agent_id == "test_agent"


# =============================================================================
# AgentLoop Lifecycle Tests
# =============================================================================


class TestAgentLoopStart:
    """Tests for AgentLoop.start()."""

    @pytest.mark.asyncio
    async def test_start_changes_state(self, agent_loop: AgentLoop) -> None:
        """Starting loop changes state to STARTING then RUNNING."""
        await agent_loop.start()
        # Give it a moment to transition
        await asyncio.sleep(0.02)

        assert agent_loop.state == AgentState.RUNNING
        assert agent_loop.is_running

        await agent_loop.stop()

    @pytest.mark.asyncio
    async def test_start_when_already_running(self, agent_loop: AgentLoop) -> None:
        """Starting an already running loop logs warning and returns."""
        await agent_loop.start()
        await asyncio.sleep(0.02)

        # Try to start again
        await agent_loop.start()

        # Should still be running, not error
        assert agent_loop.state == AgentState.RUNNING

        await agent_loop.stop()

    @pytest.mark.asyncio
    async def test_start_executes_actions(
        self,
        agent_loop: AgentLoop,
        mock_decide_action: AsyncMock,
        mock_execute_action: AsyncMock,
    ) -> None:
        """Started loop calls decide and execute callbacks."""
        await agent_loop.start()
        await asyncio.sleep(0.05)

        assert mock_decide_action.called
        assert mock_execute_action.called

        await agent_loop.stop()


class TestAgentLoopStop:
    """Tests for AgentLoop.stop()."""

    @pytest.mark.asyncio
    async def test_stop_changes_state(self, agent_loop: AgentLoop) -> None:
        """Stopping loop changes state to STOPPED."""
        await agent_loop.start()
        await asyncio.sleep(0.02)

        await agent_loop.stop()

        assert agent_loop.state == AgentState.STOPPED
        assert not agent_loop.is_running

    @pytest.mark.asyncio
    async def test_stop_when_already_stopped(self, agent_loop: AgentLoop) -> None:
        """Stopping an already stopped loop is a no-op."""
        assert agent_loop.state == AgentState.STOPPED

        await agent_loop.stop()

        assert agent_loop.state == AgentState.STOPPED

    @pytest.mark.asyncio
    async def test_stop_graceful_timeout(
        self,
        rate_tracker: RateTracker,
    ) -> None:
        """Stop waits for graceful shutdown then cancels on timeout."""
        # Create a slow-running action
        async def slow_decide() -> dict[str, Any]:
            await asyncio.sleep(10.0)  # Very long
            return {"action_type": "noop"}

        async def slow_execute(action: dict[str, Any]) -> dict[str, Any]:
            return {"success": True}

        loop = AgentLoop(
            agent_id="slow_agent",
            decide_action=slow_decide,
            execute_action=slow_execute,
            rate_tracker=rate_tracker,
            config=AgentLoopConfig(min_loop_delay=0.01),
        )

        await loop.start()
        await asyncio.sleep(0.02)

        # Stop with short timeout
        start_time = time.time()
        await loop.stop(timeout=0.1)
        elapsed = time.time() - start_time

        assert loop.state == AgentState.STOPPED
        # Should have timed out, not waited 10 seconds
        assert elapsed < 1.0


# =============================================================================
# AgentLoop Sleep/Wake Tests
# =============================================================================


class TestAgentLoopSleep:
    """Tests for AgentLoop sleep functionality."""

    @pytest.mark.asyncio
    async def test_sleep_changes_state(self, agent_loop: AgentLoop) -> None:
        """Putting agent to sleep changes state to SLEEPING."""
        await agent_loop.start()
        await asyncio.sleep(0.02)

        agent_loop.sleep(WakeCondition(condition_type="time", value=time.time() + 100))

        assert agent_loop.state == AgentState.SLEEPING

        await agent_loop.stop()

    @pytest.mark.asyncio
    async def test_wake_changes_state(self, agent_loop: AgentLoop) -> None:
        """Waking a sleeping agent changes state to RUNNING."""
        await agent_loop.start()
        await asyncio.sleep(0.02)

        agent_loop.sleep(WakeCondition(condition_type="time", value=time.time() + 100))
        assert agent_loop.state == AgentState.SLEEPING

        agent_loop.wake()
        assert agent_loop.state == AgentState.RUNNING

        await agent_loop.stop()

    @pytest.mark.asyncio
    async def test_wake_on_non_sleeping_no_effect(self, agent_loop: AgentLoop) -> None:
        """Waking a non-sleeping agent has no effect."""
        await agent_loop.start()
        await asyncio.sleep(0.02)

        assert agent_loop.state == AgentState.RUNNING

        agent_loop.wake()  # Should be no-op

        assert agent_loop.state == AgentState.RUNNING

        await agent_loop.stop()

    @pytest.mark.asyncio
    async def test_time_based_wake(
        self,
        rate_tracker: RateTracker,
    ) -> None:
        """Agent wakes automatically when time condition is met."""
        mock_decide = AsyncMock(return_value={"action_type": "noop"})
        mock_execute = AsyncMock(return_value={"success": True})

        loop = AgentLoop(
            agent_id="time_wake_agent",
            decide_action=mock_decide,
            execute_action=mock_execute,
            rate_tracker=rate_tracker,
            config=AgentLoopConfig(min_loop_delay=0.01, resource_check_interval=0.02),
        )

        await loop.start()
        await asyncio.sleep(0.02)

        # Sleep until 50ms in the future
        wake_time = time.time() + 0.05
        loop.sleep(WakeCondition(condition_type="time", value=wake_time))

        assert loop.state == AgentState.SLEEPING

        # Wait for wake time
        await asyncio.sleep(0.1)

        assert loop.state == AgentState.RUNNING

        await loop.stop()

    @pytest.mark.asyncio
    async def test_resource_based_wake(
        self,
        rate_tracker: RateTracker,
    ) -> None:
        """Agent wakes when resource threshold is met."""
        mock_decide = AsyncMock(return_value={"action_type": "noop"})
        mock_execute = AsyncMock(return_value={"success": True})

        loop = AgentLoop(
            agent_id="resource_wake_agent",
            decide_action=mock_decide,
            execute_action=mock_execute,
            rate_tracker=rate_tracker,
            config=AgentLoopConfig(min_loop_delay=0.01, resource_check_interval=0.02),
        )

        # Consume most resources
        rate_tracker.consume("resource_wake_agent", "llm_calls", 90.0)

        await loop.start()
        await asyncio.sleep(0.02)

        # Sleep until we have 50 remaining
        loop.sleep(WakeCondition(condition_type="resource", value=("llm_calls", 50.0)))

        assert loop.state == AgentState.SLEEPING

        # Reset resources to trigger wake
        rate_tracker.reset(agent_id="resource_wake_agent", resource="llm_calls")

        # Wait for check
        await asyncio.sleep(0.1)

        assert loop.state == AgentState.RUNNING

        await loop.stop()


# =============================================================================
# AgentLoop Resource-Gated Execution Tests
# =============================================================================


class TestAgentLoopResourceGating:
    """Tests for resource-gated loop continuation."""

    @pytest.mark.asyncio
    async def test_pauses_on_no_resources(
        self,
        rate_tracker: RateTracker,
        mock_decide_action: AsyncMock,
        mock_execute_action: AsyncMock,
    ) -> None:
        """Loop pauses when resources are exhausted."""
        # Consume all resources
        rate_tracker.consume("test_agent", "llm_calls", 100.0)

        loop = AgentLoop(
            agent_id="test_agent",
            decide_action=mock_decide_action,
            execute_action=mock_execute_action,
            rate_tracker=rate_tracker,
            config=AgentLoopConfig(min_loop_delay=0.01, resource_check_interval=0.02),
        )

        await loop.start()
        await asyncio.sleep(0.05)

        assert loop.state == AgentState.PAUSED

        await loop.stop()

    @pytest.mark.asyncio
    async def test_resumes_when_resources_available(
        self,
        rate_tracker: RateTracker,
        mock_decide_action: AsyncMock,
        mock_execute_action: AsyncMock,
    ) -> None:
        """Loop resumes when resources become available."""
        # Consume all resources
        rate_tracker.consume("resume_agent", "llm_calls", 100.0)

        loop = AgentLoop(
            agent_id="resume_agent",
            decide_action=mock_decide_action,
            execute_action=mock_execute_action,
            rate_tracker=rate_tracker,
            config=AgentLoopConfig(min_loop_delay=0.01, resource_check_interval=0.02),
        )

        await loop.start()
        await asyncio.sleep(0.05)

        assert loop.state == AgentState.PAUSED

        # Reset resources
        rate_tracker.reset(agent_id="resume_agent", resource="llm_calls")

        await asyncio.sleep(0.05)

        assert loop.state == AgentState.RUNNING

        await loop.stop()


# =============================================================================
# AgentLoop Resource Exhaustion Policy Tests
# =============================================================================


class TestResourceExhaustionPolicy:
    """Tests for resource_exhaustion_policy (skip/block) behavior."""

    @pytest.mark.asyncio
    async def test_skip_policy_pauses_immediately(
        self,
        rate_tracker: RateTracker,
        mock_decide_action: AsyncMock,
        mock_execute_action: AsyncMock,
    ) -> None:
        """With skip policy, loop pauses immediately when resources exhausted."""
        # Consume all resources
        rate_tracker.consume("skip_agent", "llm_calls", 100.0)

        loop = AgentLoop(
            agent_id="skip_agent",
            decide_action=mock_decide_action,
            execute_action=mock_execute_action,
            rate_tracker=rate_tracker,
            config=AgentLoopConfig(
                min_loop_delay=0.01,
                resource_check_interval=0.02,
                resource_exhaustion_policy="skip",
            ),
        )

        await loop.start()
        await asyncio.sleep(0.05)

        # Should be paused, not blocked
        assert loop.state == AgentState.PAUSED
        # No actions should have been executed
        mock_execute_action.assert_not_called()

        await loop.stop()

    @pytest.mark.asyncio
    async def test_block_policy_waits_for_resources(
        self,
        rate_tracker: RateTracker,
        mock_decide_action: AsyncMock,
        mock_execute_action: AsyncMock,
    ) -> None:
        """With block policy, loop waits until resources become available."""
        # Consume all resources
        rate_tracker.consume("block_agent", "llm_calls", 100.0)

        loop = AgentLoop(
            agent_id="block_agent",
            decide_action=mock_decide_action,
            execute_action=mock_execute_action,
            rate_tracker=rate_tracker,
            config=AgentLoopConfig(
                min_loop_delay=0.01,
                resource_check_interval=0.05,
                resource_exhaustion_policy="block",
            ),
        )

        await loop.start()
        await asyncio.sleep(0.02)

        # Should still be running (blocking), not paused
        assert loop.state == AgentState.RUNNING
        # No actions yet since blocked
        mock_execute_action.assert_not_called()

        # Reset resources to unblock
        rate_tracker.reset(agent_id="block_agent", resource="llm_calls")

        await asyncio.sleep(0.1)

        # Should have executed now
        assert mock_execute_action.called

        await loop.stop()

    @pytest.mark.asyncio
    async def test_block_policy_executes_after_resources_available(
        self,
        rate_tracker: RateTracker,
    ) -> None:
        """With block policy, loop continues executing after resources become available."""
        execution_count = 0

        async def counting_decide() -> dict[str, Any]:
            nonlocal execution_count
            execution_count += 1
            return {"action_type": "noop"}

        async def execute(action: dict[str, Any]) -> dict[str, Any]:
            return {"success": True}

        # Consume all resources initially
        rate_tracker.consume("block_exec_agent", "llm_calls", 100.0)

        loop = AgentLoop(
            agent_id="block_exec_agent",
            decide_action=counting_decide,
            execute_action=execute,
            rate_tracker=rate_tracker,
            config=AgentLoopConfig(
                min_loop_delay=0.01,
                resource_check_interval=0.02,
                resource_exhaustion_policy="block",
            ),
        )

        await loop.start()
        await asyncio.sleep(0.03)

        # No executions while blocked
        assert execution_count == 0

        # Reset resources
        rate_tracker.reset(agent_id="block_exec_agent", resource="llm_calls")

        await asyncio.sleep(0.1)

        # Should have executed multiple times now
        assert execution_count > 0

        await loop.stop()

    @pytest.mark.asyncio
    async def test_skip_policy_is_default(
        self,
        rate_tracker: RateTracker,
        mock_decide_action: AsyncMock,
        mock_execute_action: AsyncMock,
    ) -> None:
        """Default policy is 'skip'."""
        # Consume all resources
        rate_tracker.consume("default_policy_agent", "llm_calls", 100.0)

        # Don't specify resource_exhaustion_policy - should default to skip
        loop = AgentLoop(
            agent_id="default_policy_agent",
            decide_action=mock_decide_action,
            execute_action=mock_execute_action,
            rate_tracker=rate_tracker,
            config=AgentLoopConfig(
                min_loop_delay=0.01,
                resource_check_interval=0.02,
            ),
        )

        await loop.start()
        await asyncio.sleep(0.05)

        # With default skip policy, should be paused
        assert loop.state == AgentState.PAUSED

        await loop.stop()

    @pytest.mark.asyncio
    async def test_block_policy_can_be_stopped_while_waiting(
        self,
        rate_tracker: RateTracker,
        mock_decide_action: AsyncMock,
        mock_execute_action: AsyncMock,
    ) -> None:
        """Loop with block policy can be stopped while waiting for resources."""
        # Consume all resources
        rate_tracker.consume("stop_while_block_agent", "llm_calls", 100.0)

        loop = AgentLoop(
            agent_id="stop_while_block_agent",
            decide_action=mock_decide_action,
            execute_action=mock_execute_action,
            rate_tracker=rate_tracker,
            config=AgentLoopConfig(
                min_loop_delay=0.01,
                resource_check_interval=0.5,  # Long interval to ensure we're blocking
                resource_exhaustion_policy="block",
            ),
        )

        await loop.start()
        await asyncio.sleep(0.02)

        # Stop while blocked
        await loop.stop(timeout=0.1)

        assert loop.state == AgentState.STOPPED


# =============================================================================
# AgentLoop Error Handling Tests
# =============================================================================


class TestAgentLoopErrorHandling:
    """Tests for error handling and backoff behavior."""

    @pytest.mark.asyncio
    async def test_error_increments_counter(
        self,
        rate_tracker: RateTracker,
    ) -> None:
        """Errors increment consecutive error counter."""
        mock_decide = AsyncMock(return_value={"action_type": "noop"})
        mock_execute = AsyncMock(return_value={"success": False, "error": "test error"})

        loop = AgentLoop(
            agent_id="error_agent",
            decide_action=mock_decide,
            execute_action=mock_execute,
            rate_tracker=rate_tracker,
            config=AgentLoopConfig(min_loop_delay=0.01, max_consecutive_errors=10),
        )

        await loop.start()
        await asyncio.sleep(0.05)

        assert loop.consecutive_errors > 0

        await loop.stop()

    @pytest.mark.asyncio
    async def test_success_resets_error_counter(
        self,
        rate_tracker: RateTracker,
    ) -> None:
        """Successful action resets error counter."""
        call_count = 0

        async def alternating_execute(action: dict[str, Any]) -> dict[str, Any]:
            nonlocal call_count
            call_count += 1
            # Fail first two, then succeed
            if call_count <= 2:
                return {"success": False}
            return {"success": True}

        mock_decide = AsyncMock(return_value={"action_type": "noop"})

        loop = AgentLoop(
            agent_id="reset_error_agent",
            decide_action=mock_decide,
            execute_action=alternating_execute,
            rate_tracker=rate_tracker,
            config=AgentLoopConfig(min_loop_delay=0.01, max_consecutive_errors=10),
        )

        await loop.start()
        await asyncio.sleep(0.1)

        # After success, errors should be reset
        assert loop.consecutive_errors == 0

        await loop.stop()

    @pytest.mark.asyncio
    async def test_pauses_after_max_errors(
        self,
        rate_tracker: RateTracker,
    ) -> None:
        """Loop pauses after hitting max consecutive errors."""
        mock_decide = AsyncMock(return_value={"action_type": "noop"})
        mock_execute = AsyncMock(return_value={"success": False, "error": "test error"})

        loop = AgentLoop(
            agent_id="max_error_agent",
            decide_action=mock_decide,
            execute_action=mock_execute,
            rate_tracker=rate_tracker,
            config=AgentLoopConfig(min_loop_delay=0.01, max_consecutive_errors=3),
        )

        await loop.start()
        await asyncio.sleep(0.15)

        assert loop.state == AgentState.PAUSED
        assert loop.consecutive_errors >= 3

        await loop.stop()

    @pytest.mark.asyncio
    async def test_exception_in_decide_handled(
        self,
        rate_tracker: RateTracker,
    ) -> None:
        """Exceptions in decide_action are handled gracefully."""
        mock_decide = AsyncMock(side_effect=RuntimeError("decide failed"))
        mock_execute = AsyncMock(return_value={"success": True})

        loop = AgentLoop(
            agent_id="exception_agent",
            decide_action=mock_decide,
            execute_action=mock_execute,
            rate_tracker=rate_tracker,
            config=AgentLoopConfig(min_loop_delay=0.01, max_consecutive_errors=3),
        )

        await loop.start()
        await asyncio.sleep(0.15)

        # Should have hit error limit and paused
        assert loop.state == AgentState.PAUSED

        await loop.stop()


# =============================================================================
# AgentLoop Iteration Tests
# =============================================================================


class TestAgentLoopIteration:
    """Tests for loop iteration behavior."""

    @pytest.mark.asyncio
    async def test_iteration_count_increments(
        self,
        rate_tracker: RateTracker,
        mock_decide_action: AsyncMock,
        mock_execute_action: AsyncMock,
    ) -> None:
        """Iteration count increments with each successful action."""
        loop = AgentLoop(
            agent_id="iter_agent",
            decide_action=mock_decide_action,
            execute_action=mock_execute_action,
            rate_tracker=rate_tracker,
            config=AgentLoopConfig(min_loop_delay=0.01),
        )

        await loop.start()
        await asyncio.sleep(0.1)
        await loop.stop()

        assert loop.iteration_count > 0

    @pytest.mark.asyncio
    async def test_null_action_is_success(
        self,
        rate_tracker: RateTracker,
        mock_execute_action: AsyncMock,
    ) -> None:
        """Returning None from decide_action is treated as success."""
        mock_decide = AsyncMock(return_value=None)

        loop = AgentLoop(
            agent_id="null_action_agent",
            decide_action=mock_decide,
            execute_action=mock_execute_action,
            rate_tracker=rate_tracker,
            config=AgentLoopConfig(min_loop_delay=0.01),
        )

        await loop.start()
        await asyncio.sleep(0.05)

        # Should still be running (not paused from errors)
        assert loop.state == AgentState.RUNNING
        # Execute should not be called for None actions
        mock_execute_action.assert_not_called()
        assert loop.consecutive_errors == 0

        await loop.stop()


# =============================================================================
# AgentLoop Agent Alive Check Tests
# =============================================================================


class TestAgentLoopAliveCheck:
    """Tests for agent alive checking."""

    @pytest.mark.asyncio
    async def test_stops_when_not_alive(
        self,
        rate_tracker: RateTracker,
        mock_decide_action: AsyncMock,
        mock_execute_action: AsyncMock,
    ) -> None:
        """Loop stops when is_alive returns False."""
        alive = True

        def is_alive() -> bool:
            return alive

        loop = AgentLoop(
            agent_id="alive_check_agent",
            decide_action=mock_decide_action,
            execute_action=mock_execute_action,
            rate_tracker=rate_tracker,
            config=AgentLoopConfig(min_loop_delay=0.01),
            is_alive=is_alive,
        )

        await loop.start()
        await asyncio.sleep(0.03)

        assert loop.state == AgentState.RUNNING

        # Set not alive
        alive = False

        await asyncio.sleep(0.05)

        assert loop.state == AgentState.STOPPED


# =============================================================================
# AgentLoopManager Tests
# =============================================================================


class TestAgentLoopManagerInit:
    """Tests for AgentLoopManager initialization."""

    def test_init_empty(self, loop_manager: AgentLoopManager) -> None:
        """Manager starts with no loops."""
        assert loop_manager.loop_count == 0
        assert loop_manager.running_count == 0


class TestAgentLoopManagerCreateLoop:
    """Tests for AgentLoopManager.create_loop()."""

    def test_create_loop(
        self,
        loop_manager: AgentLoopManager,
        mock_decide_action: AsyncMock,
        mock_execute_action: AsyncMock,
    ) -> None:
        """Can create a loop for an agent."""
        loop = loop_manager.create_loop(
            agent_id="agent_1",
            decide_action=mock_decide_action,
            execute_action=mock_execute_action,
        )

        assert loop.agent_id == "agent_1"
        assert loop_manager.loop_count == 1
        assert loop_manager.get_loop("agent_1") is loop

    def test_create_loop_with_config(
        self,
        loop_manager: AgentLoopManager,
        mock_decide_action: AsyncMock,
        mock_execute_action: AsyncMock,
    ) -> None:
        """Can create a loop with custom config."""
        config = AgentLoopConfig(min_loop_delay=0.5)
        loop = loop_manager.create_loop(
            agent_id="agent_2",
            decide_action=mock_decide_action,
            execute_action=mock_execute_action,
            config=config,
        )

        assert loop.config.min_loop_delay == 0.5

    def test_create_duplicate_raises(
        self,
        loop_manager: AgentLoopManager,
        mock_decide_action: AsyncMock,
        mock_execute_action: AsyncMock,
    ) -> None:
        """Creating a duplicate loop raises ValueError."""
        loop_manager.create_loop(
            agent_id="agent_dup",
            decide_action=mock_decide_action,
            execute_action=mock_execute_action,
        )

        with pytest.raises(ValueError, match="Loop already exists"):
            loop_manager.create_loop(
                agent_id="agent_dup",
                decide_action=mock_decide_action,
                execute_action=mock_execute_action,
            )


class TestAgentLoopManagerGetLoop:
    """Tests for AgentLoopManager.get_loop()."""

    def test_get_existing_loop(
        self,
        loop_manager: AgentLoopManager,
        mock_decide_action: AsyncMock,
        mock_execute_action: AsyncMock,
    ) -> None:
        """Can get an existing loop by ID."""
        loop = loop_manager.create_loop(
            agent_id="get_loop_agent",
            decide_action=mock_decide_action,
            execute_action=mock_execute_action,
        )

        retrieved = loop_manager.get_loop("get_loop_agent")
        assert retrieved is loop

    def test_get_nonexistent_loop(self, loop_manager: AgentLoopManager) -> None:
        """Getting nonexistent loop returns None."""
        assert loop_manager.get_loop("nonexistent") is None


class TestAgentLoopManagerRemoveLoop:
    """Tests for AgentLoopManager.remove_loop()."""

    def test_remove_stopped_loop(
        self,
        loop_manager: AgentLoopManager,
        mock_decide_action: AsyncMock,
        mock_execute_action: AsyncMock,
    ) -> None:
        """Can remove a stopped loop."""
        loop_manager.create_loop(
            agent_id="remove_agent",
            decide_action=mock_decide_action,
            execute_action=mock_execute_action,
        )

        result = loop_manager.remove_loop("remove_agent")

        assert result is True
        assert loop_manager.get_loop("remove_agent") is None
        assert loop_manager.loop_count == 0

    def test_remove_nonexistent_loop(self, loop_manager: AgentLoopManager) -> None:
        """Removing nonexistent loop returns False."""
        result = loop_manager.remove_loop("nonexistent")
        assert result is False

    @pytest.mark.asyncio
    async def test_remove_running_loop_raises(
        self,
        loop_manager: AgentLoopManager,
        mock_decide_action: AsyncMock,
        mock_execute_action: AsyncMock,
    ) -> None:
        """Removing a running loop raises ValueError."""
        loop = loop_manager.create_loop(
            agent_id="running_remove_agent",
            decide_action=mock_decide_action,
            execute_action=mock_execute_action,
            config=AgentLoopConfig(min_loop_delay=0.01),
        )

        await loop.start()
        await asyncio.sleep(0.02)

        with pytest.raises(ValueError, match="Cannot remove running loop"):
            loop_manager.remove_loop("running_remove_agent")

        await loop.stop()


class TestAgentLoopManagerStartAll:
    """Tests for AgentLoopManager.start_all()."""

    @pytest.mark.asyncio
    async def test_start_all_starts_all_loops(
        self,
        loop_manager: AgentLoopManager,
        mock_decide_action: AsyncMock,
        mock_execute_action: AsyncMock,
    ) -> None:
        """start_all starts all registered loops."""
        config = AgentLoopConfig(min_loop_delay=0.01)

        for i in range(3):
            loop_manager.create_loop(
                agent_id=f"start_all_agent_{i}",
                decide_action=mock_decide_action,
                execute_action=mock_execute_action,
                config=config,
            )

        await loop_manager.start_all()
        await asyncio.sleep(0.03)

        assert loop_manager.running_count == 3

        await loop_manager.stop_all()


class TestAgentLoopManagerStopAll:
    """Tests for AgentLoopManager.stop_all()."""

    @pytest.mark.asyncio
    async def test_stop_all_stops_all_loops(
        self,
        loop_manager: AgentLoopManager,
        mock_decide_action: AsyncMock,
        mock_execute_action: AsyncMock,
    ) -> None:
        """stop_all stops all registered loops."""
        config = AgentLoopConfig(min_loop_delay=0.01)

        for i in range(3):
            loop_manager.create_loop(
                agent_id=f"stop_all_agent_{i}",
                decide_action=mock_decide_action,
                execute_action=mock_execute_action,
                config=config,
            )

        await loop_manager.start_all()
        await asyncio.sleep(0.03)

        await loop_manager.stop_all()

        assert loop_manager.running_count == 0


class TestAgentLoopManagerGetAllStates:
    """Tests for AgentLoopManager.get_all_states()."""

    @pytest.mark.asyncio
    async def test_get_all_states(
        self,
        loop_manager: AgentLoopManager,
        mock_decide_action: AsyncMock,
        mock_execute_action: AsyncMock,
    ) -> None:
        """get_all_states returns state of all loops."""
        config = AgentLoopConfig(min_loop_delay=0.01)

        loop1 = loop_manager.create_loop(
            agent_id="states_agent_1",
            decide_action=mock_decide_action,
            execute_action=mock_execute_action,
            config=config,
        )
        loop2 = loop_manager.create_loop(
            agent_id="states_agent_2",
            decide_action=mock_decide_action,
            execute_action=mock_execute_action,
            config=config,
        )

        await loop1.start()
        await asyncio.sleep(0.02)

        states = loop_manager.get_all_states()

        assert states["states_agent_1"] == AgentState.RUNNING
        assert states["states_agent_2"] == AgentState.STOPPED

        await loop1.stop()


# =============================================================================
# AgentLoopManager with AgentProtocol Tests
# =============================================================================


class TestAgentLoopManagerWithProtocol:
    """Tests for AgentLoopManager.create_loop_for_agent()."""

    def test_create_loop_for_agent(
        self,
        loop_manager: AgentLoopManager,
    ) -> None:
        """Can create a loop from an agent implementing AgentProtocol."""
        # Create a mock agent
        mock_agent = MagicMock()
        mock_agent.agent_id = "protocol_agent"
        mock_agent.alive = True
        mock_agent.decide_action = AsyncMock(return_value={"action_type": "noop"})
        mock_agent.execute_action = AsyncMock(return_value={"success": True})

        loop = loop_manager.create_loop_for_agent(mock_agent)

        assert loop.agent_id == "protocol_agent"
        assert loop_manager.get_loop("protocol_agent") is loop

    @pytest.mark.asyncio
    async def test_create_loop_for_agent_respects_alive(
        self,
        loop_manager: AgentLoopManager,
    ) -> None:
        """Loop created from agent respects alive property."""
        mock_agent = MagicMock()
        mock_agent.agent_id = "alive_protocol_agent"
        mock_agent.alive = True
        mock_agent.decide_action = AsyncMock(return_value={"action_type": "noop"})
        mock_agent.execute_action = AsyncMock(return_value={"success": True})

        loop = loop_manager.create_loop_for_agent(
            mock_agent,
            config=AgentLoopConfig(min_loop_delay=0.01),
        )

        await loop.start()
        await asyncio.sleep(0.03)

        assert loop.state == AgentState.RUNNING

        # Set agent as not alive
        mock_agent.alive = False

        await asyncio.sleep(0.05)

        assert loop.state == AgentState.STOPPED


# =============================================================================
# Multiple Agents Concurrent Execution Tests
# =============================================================================


class TestMultipleAgentsConcurrent:
    """Tests for multiple agents running concurrently."""

    @pytest.mark.asyncio
    async def test_multiple_agents_run_independently(
        self,
        loop_manager: AgentLoopManager,
    ) -> None:
        """Multiple agents run their loops independently."""
        execution_counts: dict[str, int] = {"agent_a": 0, "agent_b": 0}

        async def decide_a() -> dict[str, Any]:
            execution_counts["agent_a"] += 1
            return {"action_type": "noop"}

        async def decide_b() -> dict[str, Any]:
            execution_counts["agent_b"] += 1
            return {"action_type": "noop"}

        async def execute(action: dict[str, Any]) -> dict[str, Any]:
            return {"success": True}

        config = AgentLoopConfig(min_loop_delay=0.01)

        loop_manager.create_loop(
            agent_id="agent_a",
            decide_action=decide_a,
            execute_action=execute,
            config=config,
        )
        loop_manager.create_loop(
            agent_id="agent_b",
            decide_action=decide_b,
            execute_action=execute,
            config=config,
        )

        await loop_manager.start_all()
        await asyncio.sleep(0.1)
        await loop_manager.stop_all()

        # Both agents should have executed
        assert execution_counts["agent_a"] > 0
        assert execution_counts["agent_b"] > 0

    @pytest.mark.asyncio
    async def test_one_agent_paused_others_continue(
        self,
        rate_tracker: RateTracker,
    ) -> None:
        """When one agent is paused, others continue running."""
        manager = AgentLoopManager(rate_tracker)

        counts = {"agent_1": 0, "agent_2": 0}

        async def decide_1() -> dict[str, Any]:
            counts["agent_1"] += 1
            return {"action_type": "noop"}

        async def decide_2() -> dict[str, Any]:
            counts["agent_2"] += 1
            return {"action_type": "noop"}

        async def execute(action: dict[str, Any]) -> dict[str, Any]:
            return {"success": True}

        config = AgentLoopConfig(min_loop_delay=0.01)

        manager.create_loop(
            agent_id="agent_1",
            decide_action=decide_1,
            execute_action=execute,
            config=config,
        )
        manager.create_loop(
            agent_id="agent_2",
            decide_action=decide_2,
            execute_action=execute,
            config=config,
        )

        # Exhaust resources for agent_1
        rate_tracker.consume("agent_1", "llm_calls", 100.0)

        await manager.start_all()
        await asyncio.sleep(0.1)
        await manager.stop_all()

        # Agent 1 should be paused (no or very few executions)
        # Agent 2 should have many executions
        assert counts["agent_1"] == 0  # Paused, never executed
        assert counts["agent_2"] > 0


# =============================================================================
# Edge Cases and Boundary Conditions
# =============================================================================


class TestEdgeCases:
    """Tests for edge cases and boundary conditions."""

    @pytest.mark.asyncio
    async def test_rapid_start_stop(
        self,
        agent_loop: AgentLoop,
    ) -> None:
        """Rapid start/stop cycles work correctly."""
        for _ in range(5):
            await agent_loop.start()
            await asyncio.sleep(0.01)
            await agent_loop.stop()

            assert agent_loop.state == AgentState.STOPPED

    @pytest.mark.asyncio
    async def test_zero_delay_config(
        self,
        rate_tracker: RateTracker,
        mock_decide_action: AsyncMock,
        mock_execute_action: AsyncMock,
    ) -> None:
        """Zero min_loop_delay is valid."""
        config = AgentLoopConfig(min_loop_delay=0.0, max_loop_delay=0.1)

        loop = AgentLoop(
            agent_id="zero_delay_agent",
            decide_action=mock_decide_action,
            execute_action=mock_execute_action,
            rate_tracker=rate_tracker,
            config=config,
        )

        await loop.start()
        await asyncio.sleep(0.05)

        assert loop.iteration_count > 0

        await loop.stop()

    @pytest.mark.asyncio
    async def test_manager_empty_start_stop(
        self,
        loop_manager: AgentLoopManager,
    ) -> None:
        """start_all/stop_all on empty manager works."""
        await loop_manager.start_all()
        await loop_manager.stop_all()

        assert loop_manager.running_count == 0
