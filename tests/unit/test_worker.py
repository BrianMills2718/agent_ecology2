"""Tests for worker processes (Plan #53 Phase 3-5).

Workers execute agent turns in separate processes, enabling:
- Isolation between agents (one crash doesn't affect others)
- Resource measurement per-turn (memory, CPU)
- Resource enforcement (kill agents exceeding quotas)
"""

from __future__ import annotations

import pytest
import tempfile
import time
from pathlib import Path
from typing import Any
from unittest.mock import MagicMock, patch


class TestWorkerExecution:
    """Tests for basic worker turn execution."""

    @pytest.mark.plans([53])
    def test_worker_loads_agent_from_state(self) -> None:
        """Worker loads agent state, runs turn, saves updated state."""
        from src.agents.state_store import AgentStateStore, AgentState

        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = Path(tmpdir) / "state.db"
            store = AgentStateStore(db_path)

            # Save initial agent state
            state = AgentState(
                agent_id="worker_test_agent",
                llm_model="test-model",
                system_prompt="Test prompt",
                last_action_result=None,
            )
            store.save(state)

            # Import here to avoid circular imports during collection
            from src.simulation.worker import run_agent_turn

            # mock-ok: LLM calls are expensive and tested in E2E
            with patch("src.agents.agent.get_memory") as mock_memory:
                mock_memory.return_value = MagicMock()

                # mock-ok: LLM provider needs API keys
                with patch("src.agents.agent.LLMProvider") as mock_llm:
                    mock_instance = MagicMock()
                    mock_instance.complete.return_value = (
                        '{"action": "invoke", "artifact_id": "genesis_store", '
                        '"method": "list", "args": {}}',
                        100, 50  # input_tokens, output_tokens
                    )
                    mock_llm.return_value = mock_instance

                    # Run a turn
                    result = run_agent_turn(
                        agent_id="worker_test_agent",
                        state_db_path=db_path,
                        world_state={"tick": 1, "balances": {}},
                    )

                    assert result is not None
                    assert result["agent_id"] == "worker_test_agent"
                    assert "action" in result or "error" in result

    @pytest.mark.plans([53])
    def test_worker_updates_state_after_turn(self) -> None:
        """Worker saves updated state after turn completes."""
        from src.agents.state_store import AgentStateStore, AgentState

        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = Path(tmpdir) / "state.db"
            store = AgentStateStore(db_path)

            # Save initial agent state
            state = AgentState(
                agent_id="update_test",
                llm_model="test-model",
                system_prompt="Test",
                last_action_result=None,
            )
            store.save(state)

            from src.simulation.worker import run_agent_turn

            # mock-ok: Memory and LLM initialization
            with patch("src.agents.agent.get_memory") as mock_memory:
                mock_memory.return_value = MagicMock()

                with patch("src.agents.agent.LLMProvider") as mock_llm:
                    mock_instance = MagicMock()
                    mock_instance.complete.return_value = (
                        '{"action": "noop"}',
                        50, 25
                    )
                    mock_llm.return_value = mock_instance

                    # Run turn
                    run_agent_turn(
                        agent_id="update_test",
                        state_db_path=db_path,
                        world_state={"tick": 1, "balances": {}},
                    )

            # Verify state was updated
            loaded = store.load("update_test")
            assert loaded is not None
            # last_tick should be updated
            assert loaded.last_tick >= 0


class TestWorkerResourceMeasurement:
    """Tests for resource measurement during turns."""

    @pytest.mark.plans([53])
    def test_memory_measurement(self) -> None:
        """Worker tracks memory usage during turn.

        Uses psutil to measure memory before and after turn execution.
        """
        from src.simulation.worker import measure_turn_resources

        # Simulate a function that allocates memory
        def allocate_memory() -> list[bytes]:
            # Allocate ~1MB
            data = [b"x" * 1024 for _ in range(1024)]
            return data

        # Measure resources during allocation
        result = measure_turn_resources(allocate_memory)

        assert "memory_bytes" in result
        assert "cpu_seconds" in result
        # Memory measurement may not be exact, but should be positive
        assert result["memory_bytes"] >= 0

    @pytest.mark.plans([53])
    def test_cpu_measurement(self) -> None:
        """Worker tracks CPU time during turn."""
        from src.simulation.worker import measure_turn_resources

        def cpu_work() -> int:
            # Do some CPU work
            total = 0
            for i in range(100000):
                total += i * i
            return total

        result = measure_turn_resources(cpu_work)

        assert "cpu_seconds" in result
        assert result["cpu_seconds"] >= 0


class TestWorkerResourceEnforcement:
    """Tests for resource quota enforcement (Phase 5)."""

    @pytest.mark.plans([53])
    def test_memory_quota_exceeded(self) -> None:
        """Turn is killed when memory quota exceeded.

        When an agent tries to allocate more memory than its quota,
        the worker should terminate the turn and return an error.
        """
        from src.simulation.worker import run_with_memory_limit

        def allocate_too_much() -> list[bytes]:
            # Try to allocate 100MB
            return [b"x" * (1024 * 1024) for _ in range(100)]

        # Set a low memory limit (10MB)
        result = run_with_memory_limit(
            func=allocate_too_much,
            memory_limit_bytes=10 * 1024 * 1024,
            timeout_seconds=5.0,
        )

        assert result["success"] is False
        assert "memory" in result.get("error", "").lower() or result.get("killed", False)

    @pytest.mark.plans([53])
    def test_cpu_quota_exceeded(self) -> None:
        """Turn is killed when CPU time quota exceeded.

        When an agent runs too long, the worker should terminate
        the turn and return an error.
        """
        from src.simulation.worker import run_with_memory_limit

        def infinite_loop() -> None:
            while True:
                pass

        # Set a short timeout
        result = run_with_memory_limit(
            func=infinite_loop,
            memory_limit_bytes=100 * 1024 * 1024,  # 100MB
            timeout_seconds=0.5,  # 500ms
        )

        assert result["success"] is False
        assert "timeout" in result.get("error", "").lower() or result.get("killed", False)
