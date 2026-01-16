"""Tests for agent state persistence (Plan #53 Phase 2).

The state store enables process-per-turn model by persisting agent state
between turns. Each turn runs in a worker process that loads state,
runs the agent, and saves updated state.
"""

from __future__ import annotations

import pytest
import sqlite3
import tempfile
import threading
import time
from pathlib import Path
from typing import Any

# Will be implemented in src/agents/state_store.py
# from src.agents.state_store import AgentStateStore, AgentState


class TestAgentStateStore:
    """Tests for AgentStateStore SQLite-backed persistence."""

    @pytest.mark.plans([53])
    def test_save_load_agent_state(self) -> None:
        """Agent state persists correctly across save/load cycle.

        Verifies:
        - Agent ID preserved
        - Config (model, prompt) preserved
        - Turn history preserved
        - Last action result preserved
        """
        from src.agents.state_store import AgentStateStore, AgentState

        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = Path(tmpdir) / "state.db"
            store = AgentStateStore(db_path)

            # Create state to save
            state = AgentState(
                agent_id="test_agent",
                llm_model="gemini/gemini-3-flash",
                system_prompt="You are a helpful agent.",
                action_schema="<action_schema>",
                last_action_result="Successfully transferred 10 scrip",
                turn_history=[
                    {"tick": 1, "action": "invoke", "result": "ok"},
                    {"tick": 2, "action": "transfer", "result": "ok"},
                ],
                rag_enabled=True,
                rag_limit=5,
            )

            # Save and load
            store.save(state)
            loaded = store.load("test_agent")

            # Verify all fields preserved
            assert loaded is not None
            assert loaded.agent_id == "test_agent"
            assert loaded.llm_model == "gemini/gemini-3-flash"
            assert loaded.system_prompt == "You are a helpful agent."
            assert loaded.action_schema == "<action_schema>"
            assert loaded.last_action_result == "Successfully transferred 10 scrip"
            assert loaded.turn_history == [
                {"tick": 1, "action": "invoke", "result": "ok"},
                {"tick": 2, "action": "transfer", "result": "ok"},
            ]
            assert loaded.rag_enabled is True
            assert loaded.rag_limit == 5

    @pytest.mark.plans([53])
    def test_save_updates_existing_state(self) -> None:
        """Saving state for existing agent updates rather than duplicates."""
        from src.agents.state_store import AgentStateStore, AgentState

        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = Path(tmpdir) / "state.db"
            store = AgentStateStore(db_path)

            # Save initial state
            state1 = AgentState(
                agent_id="test_agent",
                llm_model="model1",
                system_prompt="prompt1",
                last_action_result=None,
                turn_history=[],
            )
            store.save(state1)

            # Save updated state
            state2 = AgentState(
                agent_id="test_agent",
                llm_model="model1",
                system_prompt="prompt1",
                last_action_result="new result",
                turn_history=[{"tick": 1, "action": "test"}],
            )
            store.save(state2)

            # Load and verify update applied
            loaded = store.load("test_agent")
            assert loaded is not None
            assert loaded.last_action_result == "new result"
            assert len(loaded.turn_history) == 1

    @pytest.mark.plans([53])
    def test_load_nonexistent_returns_none(self) -> None:
        """Loading non-existent agent returns None."""
        from src.agents.state_store import AgentStateStore

        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = Path(tmpdir) / "state.db"
            store = AgentStateStore(db_path)

            loaded = store.load("nonexistent")
            assert loaded is None

    @pytest.mark.plans([53])
    def test_delete_agent_state(self) -> None:
        """Agent state can be deleted."""
        from src.agents.state_store import AgentStateStore, AgentState

        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = Path(tmpdir) / "state.db"
            store = AgentStateStore(db_path)

            state = AgentState(
                agent_id="test_agent",
                llm_model="model",
                system_prompt="prompt",
            )
            store.save(state)
            assert store.load("test_agent") is not None

            store.delete("test_agent")
            assert store.load("test_agent") is None

    @pytest.mark.plans([53])
    def test_list_all_agents(self) -> None:
        """Can list all agents in the store."""
        from src.agents.state_store import AgentStateStore, AgentState

        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = Path(tmpdir) / "state.db"
            store = AgentStateStore(db_path)

            for name in ["alpha", "beta", "gamma"]:
                state = AgentState(
                    agent_id=name,
                    llm_model="model",
                    system_prompt="prompt",
                )
                store.save(state)

            agents = store.list_agents()
            assert set(agents) == {"alpha", "beta", "gamma"}

    @pytest.mark.plans([53])
    def test_concurrent_access(self) -> None:
        """Multiple workers don't corrupt state with concurrent access.

        SQLite WAL mode should handle concurrent reads and serialized writes.
        """
        from src.agents.state_store import AgentStateStore, AgentState

        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = Path(tmpdir) / "state.db"

            errors: list[Exception] = []
            results: list[int] = []

            def worker(worker_id: int) -> None:
                """Worker that reads, increments counter, and writes."""
                try:
                    store = AgentStateStore(db_path)

                    for _ in range(10):
                        # Load current state
                        state = store.load("counter_agent")
                        if state is None:
                            state = AgentState(
                                agent_id="counter_agent",
                                llm_model="model",
                                system_prompt="prompt",
                                turn_history=[],
                            )

                        # Increment counter in turn_history
                        count = len(state.turn_history)
                        state.turn_history.append({"worker": worker_id, "count": count + 1})

                        # Save
                        store.save(state)
                        time.sleep(0.01)  # Small delay to increase contention

                    results.append(worker_id)
                except Exception as e:
                    errors.append(e)

            # Run 5 workers concurrently
            threads = [threading.Thread(target=worker, args=(i,)) for i in range(5)]
            for t in threads:
                t.start()
            for t in threads:
                t.join()

            # Check no errors
            assert len(errors) == 0, f"Workers had errors: {errors}"
            assert len(results) == 5

            # Verify final state is valid (may have fewer entries due to race conditions,
            # but should not have corruption)
            store = AgentStateStore(db_path)
            final_state = store.load("counter_agent")
            assert final_state is not None
            # Each worker did 10 iterations, but due to read-modify-write races
            # the count will be less than 50. The key is no corruption/crash.
            assert len(final_state.turn_history) > 0


class TestAgentSerialization:
    """Tests for Agent.to_state() and Agent.from_state() methods."""

    @pytest.mark.plans([53])
    def test_agent_to_state(self) -> None:
        """Agent can serialize its state."""
        from unittest.mock import patch, MagicMock
        from src.agents.agent import Agent
        from src.agents.state_store import AgentState

        # mock-ok: Memory initialization requires external API (Mem0/Qdrant)
        with patch("src.agents.agent.get_memory") as mock_get_memory:
            mock_memory = MagicMock()
            mock_get_memory.return_value = mock_memory

            agent = Agent(
                agent_id="test_agent",
                llm_model="gemini/gemini-3-flash",
                system_prompt="You are helpful.",
                action_schema="<schema>",
            )
            agent.last_action_result = "Previous result"

            state = agent.to_state()

            assert isinstance(state, AgentState)
            assert state.agent_id == "test_agent"
            assert state.llm_model == "gemini/gemini-3-flash"
            assert state.system_prompt == "You are helpful."
            assert state.last_action_result == "Previous result"

    @pytest.mark.plans([53])
    def test_agent_from_state(self) -> None:
        """Agent can be reconstructed from saved state."""
        from unittest.mock import patch, MagicMock
        from src.agents.agent import Agent
        from src.agents.state_store import AgentState

        state = AgentState(
            agent_id="restored_agent",
            llm_model="gemini/gemini-3-flash",
            system_prompt="Restored prompt",
            action_schema="<schema>",
            last_action_result="Previous action",
            turn_history=[{"tick": 1}],
            rag_enabled=True,
            rag_limit=3,
        )

        # mock-ok: Memory initialization requires external API (Mem0/Qdrant)
        with patch("src.agents.agent.get_memory") as mock_get_memory:
            mock_memory = MagicMock()
            mock_get_memory.return_value = mock_memory

            agent = Agent.from_state(state)

            assert agent.agent_id == "restored_agent"
            assert agent._llm_model == "gemini/gemini-3-flash"
            assert agent._system_prompt == "Restored prompt"
            assert agent.last_action_result == "Previous action"

    @pytest.mark.plans([53])
    def test_round_trip_preserves_state(self) -> None:
        """Agent -> state -> Agent preserves all relevant state."""
        from unittest.mock import patch, MagicMock
        from src.agents.agent import Agent
        from src.agents.state_store import AgentStateStore
        import tempfile
        from pathlib import Path

        # mock-ok: Memory initialization requires external API (Mem0/Qdrant)
        with patch("src.agents.agent.get_memory") as mock_get_memory:
            mock_memory = MagicMock()
            mock_get_memory.return_value = mock_memory

            with tempfile.TemporaryDirectory() as tmpdir:
                db_path = Path(tmpdir) / "state.db"
                store = AgentStateStore(db_path)

                # Create and configure agent
                original = Agent(
                    agent_id="roundtrip_agent",
                    llm_model="test-model",
                    system_prompt="Test prompt",
                )
                original.last_action_result = "Test result"

                # Save state
                state = original.to_state()
                store.save(state)

                # Load and reconstruct
                loaded_state = store.load("roundtrip_agent")
                assert loaded_state is not None
                restored = Agent.from_state(loaded_state)

                # Verify
                assert restored.agent_id == original.agent_id
                assert restored._llm_model == original._llm_model
                assert restored._system_prompt == original._system_prompt
                assert restored.last_action_result == original.last_action_result
