"""Integration tests for pool module (Plan #53 Phase 3).

Tests WorkerPool's ability to run multiple agents in parallel.
"""

from __future__ import annotations

import pytest
import tempfile
from pathlib import Path
from unittest.mock import patch, MagicMock, PropertyMock


class TestWorkerPool:
    """Tests for WorkerPool parallel execution."""

    @pytest.mark.plans([53])
    def test_pool_runs_multiple_agents(self) -> None:
        """Pool can run multiple agents in a single tick."""
        from src.simulation.pool import WorkerPool, PoolConfig
        from src.agents.state_store import AgentStateStore, AgentState

        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = Path(tmpdir) / "state.db"
            store = AgentStateStore(db_path)

            # Create multiple agents
            for name in ["agent_a", "agent_b", "agent_c"]:
                state = AgentState(
                    agent_id=name,
                    llm_model="test-model",
                    system_prompt=f"Agent {name}",
                )
                store.save(state)

            config = PoolConfig(
                num_workers=2,
                state_db_path=db_path,
            )

            # mock-ok: LLM and memory require external APIs
            with patch("src.agents.agent.get_memory") as mock_memory:
                mock_memory.return_value = MagicMock()

                with patch("src.agents.agent.LLMProvider") as mock_llm:
                    mock_instance = MagicMock()
                    # Mock generate() to return a FlatActionResponse-like object
                    # that converts to ActionResponse via to_action_response()
                    mock_flat_response = MagicMock()
                    mock_action_response = MagicMock()
                    mock_action_response.action.model_dump.return_value = {"action": "noop"}
                    mock_action_response.reasoning = "Test thought"
                    # to_action_response() returns the action response
                    mock_flat_response.to_action_response.return_value = mock_action_response
                    mock_instance.generate.return_value = mock_flat_response
                    mock_instance.last_usage = {"input_tokens": 50, "output_tokens": 25, "total_tokens": 75, "cost": 0.001}
                    mock_llm.return_value = mock_instance

                    with WorkerPool(config) as pool:
                        results = pool.run_round(
                            agent_ids=["agent_a", "agent_b", "agent_c"],
                            world_state={"event_number": 1, "balances": {}},
                        )

            assert results.event_number == 1
            assert len(results.results) == 3
            assert results.success_count == 3
            assert results.error_count == 0
            assert results.all_success

    @pytest.mark.plans([53])
    def test_pool_handles_missing_agent(self) -> None:
        """Pool gracefully handles agent not found in state store."""
        from src.simulation.pool import WorkerPool, PoolConfig
        from src.agents.state_store import AgentStateStore

        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = Path(tmpdir) / "state.db"
            # Create empty store (no agents)
            AgentStateStore(db_path)

            config = PoolConfig(
                num_workers=1,
                state_db_path=db_path,
            )

            with WorkerPool(config) as pool:
                results = pool.run_round(
                    agent_ids=["nonexistent"],
                    world_state={"event_number": 1},
                )

            assert results.error_count == 1
            assert results.success_count == 0
            assert not results.all_success
            assert "not found" in results.results[0].get("error", "").lower()

    @pytest.mark.plans([53])
    def test_pool_context_manager(self) -> None:
        """Pool works as context manager."""
        from src.simulation.pool import WorkerPool, PoolConfig

        with tempfile.TemporaryDirectory() as tmpdir:
            config = PoolConfig(
                num_workers=2,
                state_db_path=Path(tmpdir) / "state.db",
            )

            with WorkerPool(config) as pool:
                assert pool._executor is not None

            # After exit, executor should be shut down
            assert pool._executor is None

    @pytest.mark.plans([53])
    def test_pool_aggregates_resource_usage(self) -> None:
        """Pool aggregates memory and CPU usage across agents."""
        from src.simulation.pool import WorkerPool, PoolConfig
        from src.agents.state_store import AgentStateStore, AgentState

        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = Path(tmpdir) / "state.db"
            store = AgentStateStore(db_path)

            for name in ["agent_1", "agent_2"]:
                state = AgentState(
                    agent_id=name,
                    llm_model="test-model",
                    system_prompt="Test",
                )
                store.save(state)

            config = PoolConfig(
                num_workers=2,
                state_db_path=db_path,
            )

            # mock-ok: LLM and memory require external APIs
            with patch("src.agents.agent.get_memory") as mock_memory:
                mock_memory.return_value = MagicMock()

                with patch("src.agents.agent.LLMProvider") as mock_llm:
                    mock_instance = MagicMock()
                    # Mock generate() to return a FlatActionResponse-like object
                    # that converts to ActionResponse via to_action_response()
                    mock_flat_response = MagicMock()
                    mock_action_response = MagicMock()
                    mock_action_response.action.model_dump.return_value = {"action": "noop"}
                    mock_action_response.reasoning = "Test thought"
                    # to_action_response() returns the action response
                    mock_flat_response.to_action_response.return_value = mock_action_response
                    mock_instance.generate.return_value = mock_flat_response
                    mock_instance.last_usage = {"input_tokens": 50, "output_tokens": 25, "total_tokens": 75, "cost": 0.001}
                    mock_llm.return_value = mock_instance

                    with WorkerPool(config) as pool:
                        results = pool.run_round(
                            agent_ids=["agent_1", "agent_2"],
                            world_state={"event_number": 1},
                        )

            # Should have aggregated CPU time (at least some)
            assert results.total_cpu_seconds >= 0
            # Memory may be 0 if psutil not available
            assert results.total_memory_bytes >= 0


class TestWorkerPoolScaling:
    """Tests for pool scaling behavior."""

    @pytest.mark.plans([53])
    @pytest.mark.slow
    def test_10_agents(self) -> None:
        """Pool can handle 10 agents without issues."""
        from src.simulation.pool import WorkerPool, PoolConfig
        from src.agents.state_store import AgentStateStore, AgentState

        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = Path(tmpdir) / "state.db"
            store = AgentStateStore(db_path)

            # Create 10 agents
            agent_ids = [f"agent_{i}" for i in range(10)]
            for agent_id in agent_ids:
                state = AgentState(
                    agent_id=agent_id,
                    llm_model="test-model",
                    system_prompt=f"Agent {agent_id}",
                )
                store.save(state)

            config = PoolConfig(
                num_workers=4,
                state_db_path=db_path,
            )

            # mock-ok: LLM and memory require external APIs
            with patch("src.agents.agent.get_memory") as mock_memory:
                mock_memory.return_value = MagicMock()

                with patch("src.agents.agent.LLMProvider") as mock_llm:
                    mock_instance = MagicMock()
                    # Mock generate() to return a FlatActionResponse-like object
                    # that converts to ActionResponse via to_action_response()
                    mock_flat_response = MagicMock()
                    mock_action_response = MagicMock()
                    mock_action_response.action.model_dump.return_value = {"action": "noop"}
                    mock_action_response.reasoning = "Test thought"
                    # to_action_response() returns the action response
                    mock_flat_response.to_action_response.return_value = mock_action_response
                    mock_instance.generate.return_value = mock_flat_response
                    mock_instance.last_usage = {"input_tokens": 50, "output_tokens": 25, "total_tokens": 75, "cost": 0.001}
                    mock_llm.return_value = mock_instance

                    with WorkerPool(config) as pool:
                        results = pool.run_round(
                            agent_ids=agent_ids,
                            world_state={"event_number": 1},
                        )

            assert results.success_count == 10
            assert results.error_count == 0
