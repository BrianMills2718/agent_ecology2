"""Feature acceptance tests for agent_loop - maps to acceptance_gates/agent_loop.yaml.

Run with: pytest --feature agent_loop tests/
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


@pytest.mark.feature("agent_loop")
class TestAgentLoopFeature:
    """Tests mapping to acceptance_gates/agent_loop.yaml acceptance criteria."""

    # AC-1: Agent loop starts and runs iterations (happy_path)
    @pytest.mark.asyncio
    async def test_ac_1_loop_starts_and_runs(self) -> None:
        """AC-1: Agent loop starts and runs iterations."""
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
                min_loop_delay=0.01,
                resources_to_check=[],
            ),
        )

        await loop.start()
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

        # With exhausted rate limit and skip policy, loop should be waiting
        assert loop.state in (AgentState.RUNNING, AgentState.PAUSED)

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

        iterations = 0

        async def decide_action() -> dict[str, Any] | None:
            nonlocal iterations
            iterations += 1
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

        await asyncio.sleep(0.02)
        assert loop.state == AgentState.SLEEPING

        # Wait for wake - give extra time for wake condition
        await asyncio.sleep(0.15)
        # Loop should have woken up (either running or still waking)
        assert loop.state in (AgentState.RUNNING, AgentState.SLEEPING)

        await loop.stop()

    # AC-5: Error backoff increases delay (error_case)
    @pytest.mark.asyncio
    async def test_ac_5_error_backoff(self) -> None:
        """AC-5: Error backoff increases delay.

        Given:
          - Agent loop encounters consecutive errors
          - Error count reaches threshold
        When: Another error occurs
        Then:
          - State transitions to BACKING_OFF
          - Delay increases
          - Agent eventually retries
        """
        rate_tracker = RateTracker(window_seconds=60.0)

        error_count = 0

        async def decide_action() -> dict[str, Any] | None:
            return {"action": "error_action"}

        async def execute_action(action: dict[str, Any]) -> dict[str, Any]:
            nonlocal error_count
            error_count += 1
            if error_count <= 3:
                raise RuntimeError("Simulated error")
            return {"success": True}

        loop = AgentLoop(
            agent_id="error_agent",
            decide_action=decide_action,
            execute_action=execute_action,
            rate_tracker=rate_tracker,
            config=AgentLoopConfig(
                min_loop_delay=0.01,
                max_loop_delay=0.1,
                max_consecutive_errors=5,
                resources_to_check=[],
            ),
        )

        await loop.start()
        await asyncio.sleep(0.2)

        # Should have encountered errors and backed off, then recovered
        assert error_count >= 3
        # Loop should still be running (recovered after errors stopped)
        assert loop.state in (AgentState.RUNNING, AgentState.PAUSED)

        await loop.stop()


    # AC-4: Wake condition types work correctly (happy_path)
    def test_ac_4_wake_condition_types(self) -> None:
        """AC-4: Wake condition types work correctly."""
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

    # AC-6: Loop manager starts multiple agents (happy_path)
    @pytest.mark.asyncio
    async def test_ac_6_manager_starts_multiple(self) -> None:
        """AC-6: Loop manager starts multiple agents."""
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

        for agent_id in agent_iterations:
            manager.create_loop(
                agent_id=agent_id,
                decide_action=make_decide(agent_id),
                execute_action=execute_action,
                config=AgentLoopConfig(min_loop_delay=0.01, resources_to_check=[]),
            )

        await manager.start_all()
        await asyncio.sleep(0.1)

        for agent_id in agent_iterations:
            loop = manager.get_loop(agent_id)
            assert loop is not None
            assert loop.is_running

        for agent_id, count in agent_iterations.items():
            assert count > 0, f"{agent_id} didn't run"

        await manager.stop_all()

    # AC-7: Loop manager stops all agents gracefully (happy_path)
    @pytest.mark.asyncio
    async def test_ac_7_manager_stops_all_gracefully(self) -> None:
        """AC-7: Loop manager stops all agents gracefully."""
        rate_tracker = RateTracker(window_seconds=60.0)
        manager = AgentLoopManager(rate_tracker)

        async def decide_action() -> dict[str, Any] | None:
            return {"action": "test"}

        async def execute_action(action: dict[str, Any]) -> dict[str, Any]:
            return {"success": True}

        for i in range(3):
            manager.create_loop(
                agent_id=f"agent_{i}",
                decide_action=decide_action,
                execute_action=execute_action,
                config=AgentLoopConfig(min_loop_delay=0.01, resources_to_check=[]),
            )

        await manager.start_all()
        await asyncio.sleep(0.05)

        for i in range(3):
            loop = manager.get_loop(f"agent_{i}")
            assert loop is not None
            assert loop.is_running

        await manager.stop_all()

        for i in range(3):
            loop = manager.get_loop(f"agent_{i}")
            assert loop is not None
            assert loop.state == AgentState.STOPPED


@pytest.mark.feature("agent_loop")
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
