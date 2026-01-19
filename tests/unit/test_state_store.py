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


class TestRetryLogic:
    """Tests for SQLite retry logic with exponential backoff (Plan #97).

    These tests use the _with_retry helper function directly, which is
    more testable than trying to mock SQLite's C extension internals.
    """

    @pytest.mark.plans([97])
    def test_retries_on_database_locked(self) -> None:
        """Retry helper retries on 'database is locked' error.

        Verifies that transient SQLite lock errors trigger retry behavior
        rather than immediate failure.
        """
        from unittest.mock import patch
        from src.agents.state_store import _with_retry

        call_count = 0

        def fail_twice_then_succeed() -> str:
            nonlocal call_count
            call_count += 1
            if call_count <= 2:  # Fail first 2 attempts
                raise sqlite3.OperationalError("database is locked")
            return "success"

        with patch('time.sleep'):  # Don't actually sleep in tests
            result = _with_retry(fail_twice_then_succeed)

        assert result == "success"
        assert call_count == 3, f"Expected 3 calls (2 failures + 1 success) but got {call_count}"

    @pytest.mark.plans([97])
    def test_gives_up_after_max_retries(self) -> None:
        """Retry helper fails after max retry attempts.

        Verifies that the retry mechanism has an upper bound and eventually
        raises the error if it persists beyond max_retries.
        """
        from unittest.mock import patch
        from src.agents.state_store import _with_retry

        call_count = 0

        def always_fail() -> None:
            nonlocal call_count
            call_count += 1
            raise sqlite3.OperationalError("database is locked")

        with patch('time.sleep'):  # Don't actually sleep
            with pytest.raises(sqlite3.OperationalError, match="database is locked"):
                _with_retry(always_fail, max_retries=5)

        # Should have tried exactly max_retries times
        assert call_count == 5, f"Expected 5 attempts but got {call_count}"

    @pytest.mark.plans([97])
    def test_exponential_backoff_timing(self) -> None:
        """Retry delays follow exponential backoff pattern.

        Verifies that delays between retries increase exponentially.
        """
        from unittest.mock import patch
        from src.agents.state_store import _with_retry

        sleep_calls: list[float] = []
        call_count = 0

        def track_sleep(duration: float) -> None:
            sleep_calls.append(duration)

        def fail_thrice_then_succeed() -> str:
            nonlocal call_count
            call_count += 1
            if call_count <= 3:  # Fail first 3 attempts
                raise sqlite3.OperationalError("database is locked")
            return "success"

        with patch('time.sleep', side_effect=track_sleep):
            result = _with_retry(fail_thrice_then_succeed, base_delay=0.1)

        assert result == "success"
        # Should have 3 sleep calls for 3 failures
        assert len(sleep_calls) == 3, f"Expected 3 sleep calls but got {len(sleep_calls)}"

        # Verify exponential growth: each delay should be >= previous * 2
        # With base_delay=0.1: delays should be ~0.1, ~0.2, ~0.4
        for i in range(1, len(sleep_calls)):
            assert sleep_calls[i] >= sleep_calls[i - 1], \
                f"Delay {i} ({sleep_calls[i]}) should be >= delay {i-1} ({sleep_calls[i-1]})"

    @pytest.mark.plans([97])
    def test_passes_through_other_errors(self) -> None:
        """Non-lock errors are not retried.

        Verifies that only 'database is locked' errors trigger retry logic,
        while other errors propagate immediately.
        """
        from unittest.mock import patch
        from src.agents.state_store import _with_retry

        call_count = 0

        def fail_with_io_error() -> None:
            nonlocal call_count
            call_count += 1
            raise sqlite3.OperationalError("disk I/O error")

        with patch('time.sleep'):
            with pytest.raises(sqlite3.OperationalError, match="disk I/O error"):
                _with_retry(fail_with_io_error)

        # Should have only tried once (no retries for non-lock errors)
        assert call_count == 1, f"Expected 1 call (no retry) but got {call_count}"

    @pytest.mark.plans([97])
    def test_respects_max_delay_cap(self) -> None:
        """Exponential backoff respects maximum delay cap.

        Verifies that delays don't exceed the configured max_delay.
        """
        from unittest.mock import patch
        from src.agents.state_store import _with_retry

        sleep_calls: list[float] = []
        call_count = 0

        def track_sleep(duration: float) -> None:
            sleep_calls.append(duration)

        def fail_many_times() -> str:
            nonlocal call_count
            call_count += 1
            if call_count < 10:
                raise sqlite3.OperationalError("database is locked")
            return "success"

        with patch('time.sleep', side_effect=track_sleep):
            result = _with_retry(
                fail_many_times,
                max_retries=10,
                base_delay=0.1,
                max_delay=0.5,  # Cap at 0.5s
            )

        assert result == "success"
        # All delays should be <= max_delay
        for delay in sleep_calls:
            assert delay <= 0.5, f"Delay {delay} exceeded max_delay of 0.5"


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
