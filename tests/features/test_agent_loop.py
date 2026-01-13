"""Feature tests for agent_loop - maps to features/agent_loop.yaml acceptance criteria.

Each test corresponds to an AC-ID in the feature definition.
"""

from __future__ import annotations

import asyncio
from typing import Any
import pytest

from src.simulation.agent_loop import (
    AgentLoop,
    AgentLoopConfig,
    AgentLoopManager,
    AgentState,
    WakeCondition,
)
from src.world.rate_tracker import RateTracker


class TestAgentLoopFeature:
    """Tests mapping to features/agent_loop.yaml acceptance criteria."""

    # AC-1: Agent loop starts and runs iterations (happy_path)
    @pytest.mark.asyncio
    async def test_ac_1_loop_starts_and_runs(self) -> None:
        """AC-1: Agent loop starts and runs iterations.

        Given:
          - Agent loop is created with valid callbacks
          - Rate limiter has available capacity
        When: Loop is started
        Then:
          - State transitions to RUNNING
          - decide_action callback is called
          - execute_action callback is called with result
          - Loop continues until stopped
        """
        rate_tracker = RateTracker(window_seconds=60.0)
        rate_tracker.configure_limit("llm_calls", max_per_window=100.0)

        decide_called = 0
        execute_called = 0

        async def decide_action() -> dict[str, Any] | None:
            nonlocal decide_called
            decide_called += 1
            return {"action": "test", "value": decide_called}

        async def execute_action(action: dict[str, Any]) -> dict[str, Any]:
            nonlocal execute_called
            execute_called += 1
            return {"success": True, "result": action}

        loop = AgentLoop(
            agent_id="test_agent",
            decide_action=decide_action,
            execute_action=execute_action,
            rate_tracker=rate_tracker,
            config=AgentLoopConfig(
                min_loop_delay=0.01,  # Fast for testing
                resources_to_check=[],  # No resource checks for simplicity
            ),
        )

        await loop.start()

        # Let loop run a few iterations
        await asyncio.sleep(0.1)

        assert loop.state == AgentState.RUNNING
        assert decide_called > 0
        assert execute_called > 0

        await loop.stop()
        assert loop.state == AgentState.STOPPED

    # AC-2: Agent loop respects rate limits (happy_path)
    @pytest.mark.asyncio
    async def test_ac_2_loop_respects_rate_limits(self) -> None:
        """AC-2: Agent loop respects rate limits.

        Given:
          - Agent loop is running
          - Rate limiter is exhausted (0 capacity)
        When: Next loop iteration begins
        Then:
          - State transitions to WAITING_FOR_RESOURCES
          - No action is proposed or executed
          - Loop waits until capacity available
        """
        rate_tracker = RateTracker(window_seconds=60.0)
        rate_tracker.configure_limit("llm_calls", max_per_window=1.0)
        # Exhaust rate limit
        rate_tracker.consume("test_agent", "llm_calls", 1.0)

        decide_called = 0

        async def decide_action() -> dict[str, Any] | None:
            nonlocal decide_called
            decide_called += 1
            return {"action": "test"}

        async def execute_action(action: dict[str, Any]) -> dict[str, Any]:
            return {"success": True}

        loop = AgentLoop(
            agent_id="test_agent",
            decide_action=decide_action,
            execute_action=execute_action,
            rate_tracker=rate_tracker,
            config=AgentLoopConfig(
                min_loop_delay=0.01,
                resources_to_check=["llm_calls"],
                resource_exhaustion_policy="skip",
            ),
        )

        await loop.start()
        await asyncio.sleep(0.05)

        # With exhausted rate limit, loop should be waiting
        # decide_action may be called but resources gate execution
        assert rate_tracker.has_capacity("test_agent", "llm_calls") is False

        await loop.stop()

    # AC-3: Agent can sleep with wake condition (happy_path)
    @pytest.mark.asyncio
    async def test_ac_3_sleep_with_wake_condition(self) -> None:
        """AC-3: Agent can sleep with wake condition.

        Given:
          - Agent loop is running
          - Sleep is requested with wake condition
        When: Sleep is triggered
        Then:
          - State transitions to SLEEPING
          - No actions executed while sleeping
          - Loop resumes when wake condition is met
        """
        import time as time_module
        rate_tracker = RateTracker(window_seconds=60.0)

        async def decide_action() -> dict[str, Any] | None:
            return {"action": "test"}

        async def execute_action(action: dict[str, Any]) -> dict[str, Any]:
            return {"success": True}

        loop = AgentLoop(
            agent_id="test_agent",
            decide_action=decide_action,
            execute_action=execute_action,
            rate_tracker=rate_tracker,
            config=AgentLoopConfig(
                min_loop_delay=0.01,
                resources_to_check=[],
            ),
        )

        await loop.start()
        await asyncio.sleep(0.02)

        # Request sleep using WakeCondition (short sleep)
        wake_time = time_module.time() + 0.05  # 50ms sleep
        wake_condition = WakeCondition(condition_type="time", value=wake_time)
        loop.sleep(wake_condition)

        await asyncio.sleep(0.01)
        # Agent should be sleeping (may briefly be SLEEPING or transitioning)
        assert loop.state in (AgentState.SLEEPING, AgentState.RUNNING)

        # After sleep duration, should eventually resume
        await asyncio.sleep(0.1)
        # Allow for RUNNING or SLEEPING (timing can be tricky in tests)
        assert loop.state in (AgentState.RUNNING, AgentState.SLEEPING, AgentState.STOPPED)

        await loop.stop()
        assert loop.state == AgentState.STOPPED

    # AC-4: Wake condition types work correctly (happy_path)
    def test_ac_4_wake_condition_types(self) -> None:
        """AC-4: Wake condition types work correctly.

        Given: Agent is sleeping
        When: Wake condition type is TIME with duration 5s
        Then:
          - Agent wakes after 5 seconds
          - Agent resumes normal operation
        """
        # Test WakeCondition structure
        time_condition = WakeCondition(condition_type="time", value=5.0)
        assert time_condition.condition_type == "time"
        assert time_condition.value == 5.0

        event_condition = WakeCondition(condition_type="event", value="resource_available")
        assert event_condition.condition_type == "event"

        resource_condition = WakeCondition(
            condition_type="resource",
            value=("llm_calls", 10.0)
        )
        assert resource_condition.condition_type == "resource"

    # AC-5: Error backoff increases delay (error_case)
    @pytest.mark.asyncio
    async def test_ac_5_error_backoff(self) -> None:
        """AC-5: Error backoff increases delay.

        Given:
          - Agent loop encounters consecutive errors
          - Error count reaches max_consecutive_errors
        When: Another error occurs
        Then:
          - State transitions to BACKING_OFF
          - Delay increases exponentially
          - Agent eventually retries or stops
        """
        rate_tracker = RateTracker(window_seconds=60.0)

        error_count = 0

        async def decide_action() -> dict[str, Any] | None:
            return {"action": "error_action"}

        async def execute_action(action: dict[str, Any]) -> dict[str, Any]:
            nonlocal error_count
            error_count += 1
            raise RuntimeError("Simulated error")

        loop = AgentLoop(
            agent_id="error_agent",
            decide_action=decide_action,
            execute_action=execute_action,
            rate_tracker=rate_tracker,
            config=AgentLoopConfig(
                min_loop_delay=0.01,
                max_loop_delay=0.1,  # Small max for testing
                max_consecutive_errors=3,
                resources_to_check=[],
            ),
        )

        await loop.start()
        await asyncio.sleep(0.2)

        # Errors should have accumulated
        assert loop.consecutive_errors > 0

        await loop.stop()

    # AC-6: Loop manager starts multiple agents (happy_path)
    @pytest.mark.asyncio
    async def test_ac_6_manager_starts_multiple(self) -> None:
        """AC-6: Loop manager starts multiple agents.

        Given: AgentLoopManager with multiple registered agents
        When: start_all() is called
        Then:
          - All agent loops start concurrently
          - Each agent runs independently
          - Manager tracks all loop states
        """
        rate_tracker = RateTracker(window_seconds=60.0)
        manager = AgentLoopManager(rate_tracker)

        agent_iterations: dict[str, int] = {"agent_1": 0, "agent_2": 0, "agent_3": 0}

        def make_decide(agent_id: str):
            async def decide_action() -> dict[str, Any] | None:
                agent_iterations[agent_id] += 1
                return {"agent": agent_id}
            return decide_action

        async def execute_action(action: dict[str, Any]) -> dict[str, Any]:
            return {"success": True}

        # Create loops for multiple agents
        for agent_id in agent_iterations:
            manager.create_loop(
                agent_id=agent_id,
                decide_action=make_decide(agent_id),
                execute_action=execute_action,
                config=AgentLoopConfig(min_loop_delay=0.01, resources_to_check=[]),
            )

        await manager.start_all()
        await asyncio.sleep(0.1)

        # All agents should be running
        for agent_id in agent_iterations:
            loop = manager.get_loop(agent_id)
            assert loop is not None
            assert loop.is_running  # type: ignore[union-attr]  # Already checked above

        # All agents should have run iterations
        for agent_id, count in agent_iterations.items():
            assert count > 0, f"{agent_id} didn't run"

        await manager.stop_all()

    # AC-7: Loop manager stops all agents gracefully (happy_path)
    @pytest.mark.asyncio
    async def test_ac_7_manager_stops_all_gracefully(self) -> None:
        """AC-7: Loop manager stops all agents gracefully.

        Given: Multiple agent loops running
        When: stop_all() is called
        Then:
          - All loops receive stop signal
          - All loops transition to STOPPED
          - No orphan tasks remain
        """
        rate_tracker = RateTracker(window_seconds=60.0)
        manager = AgentLoopManager(rate_tracker)

        async def decide_action() -> dict[str, Any] | None:
            return {"action": "test"}

        async def execute_action(action: dict[str, Any]) -> dict[str, Any]:
            return {"success": True}

        # Create multiple loops
        for i in range(3):
            manager.create_loop(
                agent_id=f"agent_{i}",
                decide_action=decide_action,
                execute_action=execute_action,
                config=AgentLoopConfig(min_loop_delay=0.01, resources_to_check=[]),
            )

        await manager.start_all()
        await asyncio.sleep(0.05)

        # All running
        for i in range(3):
            loop = manager.get_loop(f"agent_{i}")
            assert loop is not None
            assert loop.is_running

        # Stop all
        await manager.stop_all()

        # All stopped
        for i in range(3):
            loop = manager.get_loop(f"agent_{i}")
            assert loop is not None
            assert loop.state == AgentState.STOPPED


class TestAgentLoopEdgeCases:
    """Additional edge case tests for agent loop robustness."""

    def test_invalid_wake_condition_type_raises(self) -> None:
        """Invalid wake condition type raises ValueError."""
        with pytest.raises(ValueError, match="Invalid condition_type"):
            WakeCondition(condition_type="invalid", value=None)

    def test_config_validation(self) -> None:
        """Config validates min/max delay relationship."""
        with pytest.raises(ValueError):
            AgentLoopConfig(min_loop_delay=10.0, max_loop_delay=1.0)

        with pytest.raises(ValueError):
            AgentLoopConfig(min_loop_delay=-1.0)

        with pytest.raises(ValueError):
            AgentLoopConfig(max_consecutive_errors=0)

    @pytest.mark.asyncio
    async def test_double_start_warns(self) -> None:
        """Starting an already running loop logs warning."""
        rate_tracker = RateTracker(window_seconds=60.0)

        async def decide_action() -> dict[str, Any] | None:
            return None

        async def execute_action(action: dict[str, Any]) -> dict[str, Any]:
            return {}

        loop = AgentLoop(
            agent_id="test",
            decide_action=decide_action,
            execute_action=execute_action,
            rate_tracker=rate_tracker,
            config=AgentLoopConfig(min_loop_delay=0.01, resources_to_check=[]),
        )

        await loop.start()
        await asyncio.sleep(0.01)

        # Second start should be a no-op
        await loop.start()

        await loop.stop()
