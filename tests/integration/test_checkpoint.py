"""Tests for checkpoint save/load functionality.

Tests the round-trip cycle: save → load → verify state consistency.

Plan #163: Tests for checkpoint completeness including agent state persistence.
"""

import json
import tempfile
from pathlib import Path
from typing import Any, cast
from unittest.mock import MagicMock, patch

import pytest

from src.simulation.checkpoint import (
    save_checkpoint,
    load_checkpoint,
    restore_agent_states,
    CHECKPOINT_VERSION,
)
from src.simulation.types import CheckpointData, BalanceInfo, AgentCheckpointState
from src.agents import Agent


class TestSaveCheckpoint:
    """Tests for save_checkpoint function."""

    def test_creates_file(self) -> None:
        """save_checkpoint creates a JSON file at the specified path."""
        with tempfile.TemporaryDirectory() as tmpdir:
            checkpoint_path = Path(tmpdir) / "test_checkpoint.json"
            config = {"budget": {"checkpoint_file": str(checkpoint_path)}}

            # Create mock world
            world = MagicMock()
            world.event_number = 5
            world.ledger.get_all_balances.return_value = {"agent_a": {"llm_tokens": 100, "scrip": 50}}
            world.artifacts.artifacts = {}

            # Create mock agents with export_state method
            agent = MagicMock(agent_id="agent_a")
            agent.export_state.return_value = {}
            agents: Any = [agent]

            save_checkpoint(world, agents, 0.5, config, "test_reason")

            assert checkpoint_path.exists()
            with open(checkpoint_path) as f:
                data = json.load(f)
            assert isinstance(data, dict)

    def test_checkpoint_structure(self) -> None:
        """save_checkpoint includes all required fields."""
        with tempfile.TemporaryDirectory() as tmpdir:
            checkpoint_path = Path(tmpdir) / "test_checkpoint.json"
            config = {"budget": {"checkpoint_file": str(checkpoint_path)}}

            world = MagicMock()
            world.event_number = 10
            world.ledger.get_all_balances.return_value = {
                "alice": {"llm_tokens": 100, "scrip": 200},
                "bob": {"llm_tokens": 50, "scrip": 75},
            }

            # Mock artifact
            artifact = MagicMock()
            artifact.to_dict.return_value = {
                "id": "test_artifact",
                "type": "data",
                "content": "test content",
                "created_by": "alice",
            }
            world.artifacts.artifacts = {"test_artifact": artifact}

            alice = MagicMock(agent_id="alice")
            alice.export_state.return_value = {}
            bob = MagicMock(agent_id="bob")
            bob.export_state.return_value = {}
            agents: Any = [alice, bob]

            save_checkpoint(world, agents, 1.23, config, "budget_exhausted")

            with open(checkpoint_path) as f:
                data = json.load(f)

            assert data["event_number"] == 10
            assert data["cumulative_api_cost"] == 1.23
            assert data["reason"] == "budget_exhausted"
            assert "alice" in data["balances"]
            assert "bob" in data["balances"]
            assert data["agent_ids"] == ["alice", "bob"]
            assert len(data["artifacts"]) == 1
            assert data["artifacts"][0]["id"] == "test_artifact"

    def test_returns_checkpoint_path(self) -> None:
        """save_checkpoint returns the path to the saved file."""
        with tempfile.TemporaryDirectory() as tmpdir:
            checkpoint_path = Path(tmpdir) / "my_checkpoint.json"
            config = {"budget": {"checkpoint_file": str(checkpoint_path)}}

            world = MagicMock()
            world.event_number = 1
            world.ledger.get_all_balances.return_value = {}
            world.artifacts.artifacts = {}

            result = save_checkpoint(world, [], 0.0, config, "test")

            assert result == str(checkpoint_path)


class TestLoadCheckpoint:
    """Tests for load_checkpoint function."""

    def test_file_not_found_returns_none(self) -> None:
        """load_checkpoint returns None when file doesn't exist."""
        result = load_checkpoint("/nonexistent/path/checkpoint.json")
        assert result is None

    def test_loads_new_format(self) -> None:
        """load_checkpoint handles new BalanceInfo format."""
        with tempfile.TemporaryDirectory() as tmpdir:
            checkpoint_path = Path(tmpdir) / "checkpoint.json"

            data = {
                "event_number": 25,
                "balances": {
                    "alice": {"llm_tokens": 100, "scrip": 200},
                    "bob": {"llm_tokens": 50, "scrip": 75},
                },
                "cumulative_api_cost": 0.75,
                "artifacts": [],
                "agent_ids": ["alice", "bob"],
                "reason": "test_reason",
            }
            with open(checkpoint_path, "w") as f:
                json.dump(data, f)

            result = load_checkpoint(str(checkpoint_path))

            assert result is not None
            assert result["event_number"] == 25
            assert result["balances"]["alice"]["llm_tokens"] == 100
            assert result["balances"]["alice"]["scrip"] == 200
            assert result["balances"]["bob"]["llm_tokens"] == 50
            assert result["balances"]["bob"]["scrip"] == 75
            assert result["cumulative_api_cost"] == 0.75
            assert result["reason"] == "test_reason"

    def test_loads_legacy_format(self) -> None:
        """load_checkpoint handles legacy int-only balance format."""
        with tempfile.TemporaryDirectory() as tmpdir:
            checkpoint_path = Path(tmpdir) / "checkpoint.json"

            # Legacy format: balances are just integers (scrip only)
            data = {
                "event_number": 10,
                "balances": {
                    "alice": 200,
                    "bob": 75,
                },
                "cumulative_api_cost": 0.5,
                "artifacts": [],
                "agent_ids": ["alice", "bob"],
                "reason": "legacy_checkpoint",
            }
            with open(checkpoint_path, "w") as f:
                json.dump(data, f)

            result = load_checkpoint(str(checkpoint_path))

            assert result is not None
            # Legacy format: compute defaults to 0, scrip is the int value
            assert result["balances"]["alice"]["llm_tokens"] == 0
            assert result["balances"]["alice"]["scrip"] == 200
            assert result["balances"]["bob"]["llm_tokens"] == 0
            assert result["balances"]["bob"]["scrip"] == 75

    def test_loads_artifacts(self) -> None:
        """load_checkpoint preserves artifact data."""
        with tempfile.TemporaryDirectory() as tmpdir:
            checkpoint_path = Path(tmpdir) / "checkpoint.json"

            data = {
                "event_number": 5,
                "balances": {},
                "cumulative_api_cost": 0.0,
                "artifacts": [
                    {"id": "art1", "type": "data", "content": "hello"},
                    {"id": "art2", "type": "executable", "content": "desc", "code": "def run(): pass"},
                ],
                "agent_ids": [],
                "reason": "test",
            }
            with open(checkpoint_path, "w") as f:
                json.dump(data, f)

            result = load_checkpoint(str(checkpoint_path))

            assert result is not None
            assert len(result["artifacts"]) == 2
            assert result["artifacts"][0]["id"] == "art1"
            assert result["artifacts"][1]["id"] == "art2"


class TestCheckpointRoundTrip:
    """Tests for save → load → verify cycle."""

    def test_basic_round_trip(self) -> None:
        """Basic checkpoint round trip preserves event_number, cost, and reason."""
        with tempfile.TemporaryDirectory() as tmpdir:
            checkpoint_path = Path(tmpdir) / "checkpoint.json"
            config = {"budget": {"checkpoint_file": str(checkpoint_path)}}

            world = MagicMock()
            world.event_number = 42
            world.ledger.get_all_balances.return_value = {}
            world.artifacts.artifacts = {}

            save_checkpoint(world, [], 1.234, config, "budget_pause")
            loaded = load_checkpoint(str(checkpoint_path))

            assert loaded is not None
            assert loaded["event_number"] == 42
            assert loaded["cumulative_api_cost"] == 1.234
            assert loaded["reason"] == "budget_pause"

    def test_balances_round_trip(self) -> None:
        """Balances survive round trip with compute and scrip."""
        with tempfile.TemporaryDirectory() as tmpdir:
            checkpoint_path = Path(tmpdir) / "checkpoint.json"
            config = {"budget": {"checkpoint_file": str(checkpoint_path)}}

            world = MagicMock()
            world.event_number = 1
            world.ledger.get_all_balances.return_value = {
                "alice": {"llm_tokens": 100, "scrip": 500},
                "bob": {"llm_tokens": 75, "scrip": 250},
                "charlie": {"llm_tokens": 0, "scrip": 1000},
            }
            world.artifacts.artifacts = {}

            alice = MagicMock(agent_id="alice")
            alice.export_state.return_value = {}
            bob = MagicMock(agent_id="bob")
            bob.export_state.return_value = {}
            charlie = MagicMock(agent_id="charlie")
            charlie.export_state.return_value = {}
            agents: Any = [alice, bob, charlie]

            save_checkpoint(world, agents, 0.0, config, "test")
            loaded = load_checkpoint(str(checkpoint_path))

            assert loaded is not None
            assert loaded["balances"]["alice"]["llm_tokens"] == 100
            assert loaded["balances"]["alice"]["scrip"] == 500
            assert loaded["balances"]["bob"]["llm_tokens"] == 75
            assert loaded["balances"]["bob"]["scrip"] == 250
            assert loaded["balances"]["charlie"]["llm_tokens"] == 0
            assert loaded["balances"]["charlie"]["scrip"] == 1000

    def test_artifacts_round_trip(self) -> None:
        """Artifacts survive round trip with all fields."""
        with tempfile.TemporaryDirectory() as tmpdir:
            checkpoint_path = Path(tmpdir) / "checkpoint.json"
            config = {"budget": {"checkpoint_file": str(checkpoint_path)}}

            world = MagicMock()
            world.event_number = 1
            world.ledger.get_all_balances.return_value = {}

            # Create mock artifacts
            artifact1 = MagicMock()
            artifact1.to_dict.return_value = {
                "id": "data_artifact",
                "type": "data",
                "content": "some data content",
                "created_by": "alice",
            }
            artifact2 = MagicMock()
            artifact2.to_dict.return_value = {
                "id": "exec_artifact",
                "type": "executable",
                "content": "A useful tool",
                "created_by": "bob",
                "executable": True,
                "price": 10,
                "code": "def run(x): return x * 2",
            }
            world.artifacts.artifacts = {
                "data_artifact": artifact1,
                "exec_artifact": artifact2,
            }

            save_checkpoint(world, [], 0.0, config, "test")
            loaded = load_checkpoint(str(checkpoint_path))

            assert loaded is not None
            assert len(loaded["artifacts"]) == 2

            # Find artifacts by id
            artifacts_by_id = {a["id"]: a for a in loaded["artifacts"]}

            assert "data_artifact" in artifacts_by_id
            assert artifacts_by_id["data_artifact"]["content"] == "some data content"

            assert "exec_artifact" in artifacts_by_id
            assert artifacts_by_id["exec_artifact"]["executable"] is True
            assert artifacts_by_id["exec_artifact"]["price"] == 10
            assert "def run(x)" in artifacts_by_id["exec_artifact"]["code"]

    def test_agent_ids_round_trip(self) -> None:
        """Agent IDs survive round trip in order."""
        with tempfile.TemporaryDirectory() as tmpdir:
            checkpoint_path = Path(tmpdir) / "checkpoint.json"
            config = {"budget": {"checkpoint_file": str(checkpoint_path)}}

            world = MagicMock()
            world.event_number = 1
            world.ledger.get_all_balances.return_value = {}
            world.artifacts.artifacts = {}

            first = MagicMock(agent_id="first")
            first.export_state.return_value = {}
            second = MagicMock(agent_id="second")
            second.export_state.return_value = {}
            third = MagicMock(agent_id="third")
            third.export_state.return_value = {}
            agents: Any = [first, second, third]

            save_checkpoint(world, agents, 0.0, config, "test")
            loaded = load_checkpoint(str(checkpoint_path))

            assert loaded is not None
            assert loaded["agent_ids"] == ["first", "second", "third"]

    def test_empty_state_round_trip(self) -> None:
        """Empty state (no agents, no artifacts) survives round trip."""
        with tempfile.TemporaryDirectory() as tmpdir:
            checkpoint_path = Path(tmpdir) / "checkpoint.json"
            config = {"budget": {"checkpoint_file": str(checkpoint_path)}}

            world = MagicMock()
            world.event_number = 0
            world.ledger.get_all_balances.return_value = {}
            world.artifacts.artifacts = {}

            save_checkpoint(world, [], 0.0, config, "empty_test")
            loaded = load_checkpoint(str(checkpoint_path))

            assert loaded is not None
            assert loaded["event_number"] == 0
            assert loaded["balances"] == {}
            assert loaded["artifacts"] == []
            assert loaded["agent_ids"] == []
            assert loaded["cumulative_api_cost"] == 0.0


class TestCheckpointEdgeCases:
    """Tests for edge cases and error conditions."""

    def test_default_checkpoint_path(self) -> None:
        """Uses default checkpoint.json when not specified in config."""
        with tempfile.TemporaryDirectory() as tmpdir:
            import os
            original_dir = os.getcwd()
            try:
                os.chdir(tmpdir)
                config: dict = {}  # No budget.checkpoint_file

                world = MagicMock()
                world.event_number = 1
                world.ledger.get_all_balances.return_value = {}
                world.artifacts.artifacts = {}

                result = save_checkpoint(world, [], 0.0, config, "test")

                assert result == "checkpoint.json"
                assert Path("checkpoint.json").exists()
            finally:
                os.chdir(original_dir)

    def test_overwrites_existing_checkpoint(self) -> None:
        """save_checkpoint overwrites existing checkpoint file."""
        with tempfile.TemporaryDirectory() as tmpdir:
            checkpoint_path = Path(tmpdir) / "checkpoint.json"
            config = {"budget": {"checkpoint_file": str(checkpoint_path)}}

            # Write initial checkpoint
            with open(checkpoint_path, "w") as f:
                json.dump({"old": "data"}, f)

            world = MagicMock()
            world.event_number = 99
            world.ledger.get_all_balances.return_value = {}
            world.artifacts.artifacts = {}

            save_checkpoint(world, [], 0.0, config, "new_reason")
            loaded = load_checkpoint(str(checkpoint_path))

            assert loaded is not None
            assert loaded["event_number"] == 99
            assert loaded["reason"] == "new_reason"
            assert "old" not in loaded  # type: ignore[operator]

    def test_high_precision_cost(self) -> None:
        """Cumulative API cost preserves decimal precision."""
        with tempfile.TemporaryDirectory() as tmpdir:
            checkpoint_path = Path(tmpdir) / "checkpoint.json"
            config = {"budget": {"checkpoint_file": str(checkpoint_path)}}

            world = MagicMock()
            world.event_number = 1
            world.ledger.get_all_balances.return_value = {}
            world.artifacts.artifacts = {}

            precise_cost = 0.123456789
            save_checkpoint(world, [], precise_cost, config, "test")
            loaded = load_checkpoint(str(checkpoint_path))

            assert loaded is not None
            # JSON preserves float precision reasonably well
            assert abs(loaded["cumulative_api_cost"] - precise_cost) < 1e-10


@pytest.mark.plans([163])
class TestCheckpointVersion:
    """Tests for checkpoint versioning (Plan #163)."""

    def test_saves_version_number(self) -> None:
        """Checkpoint file includes version field."""
        with tempfile.TemporaryDirectory() as tmpdir:
            checkpoint_path = Path(tmpdir) / "checkpoint.json"
            config = {"budget": {"checkpoint_file": str(checkpoint_path)}}

            world = MagicMock()
            world.event_number = 1
            world.ledger.get_all_balances.return_value = {}
            world.artifacts.artifacts = {}

            save_checkpoint(world, [], 0.0, config, "test")

            with open(checkpoint_path) as f:
                data = json.load(f)

            assert "version" in data
            assert data["version"] == CHECKPOINT_VERSION

    def test_loads_v1_format(self) -> None:
        """Can load v1 checkpoint without version field."""
        with tempfile.TemporaryDirectory() as tmpdir:
            checkpoint_path = Path(tmpdir) / "checkpoint.json"

            # v1 format: no version, no agent_states
            data = {
                "event_number": 10,
                "balances": {"alice": {"llm_tokens": 100, "scrip": 200}},
                "cumulative_api_cost": 0.5,
                "artifacts": [],
                "agent_ids": ["alice"],
                "reason": "v1_test",
            }
            with open(checkpoint_path, "w") as f:
                json.dump(data, f)

            loaded = load_checkpoint(str(checkpoint_path))

            assert loaded is not None
            assert loaded["event_number"] == 10
            assert loaded["version"] == 2  # Migrated to v2
            assert "agent_states" in loaded
            # Empty state for alice (migrated)
            assert "alice" in loaded["agent_states"]

    def test_v1_migration_creates_empty_agent_states(self) -> None:
        """Migration from v1 creates empty agent_states dict."""
        with tempfile.TemporaryDirectory() as tmpdir:
            checkpoint_path = Path(tmpdir) / "checkpoint.json"

            data = {
                "event_number": 5,
                "balances": {},
                "cumulative_api_cost": 0.0,
                "artifacts": [],
                "agent_ids": ["agent_a", "agent_b"],
                "reason": "migration_test",
            }
            with open(checkpoint_path, "w") as f:
                json.dump(data, f)

            loaded = load_checkpoint(str(checkpoint_path))

            assert loaded is not None
            assert loaded["agent_states"]["agent_a"] == {}
            assert loaded["agent_states"]["agent_b"] == {}


@pytest.mark.plans([163])
class TestCheckpointAgentState:
    """Tests for agent state persistence in checkpoints (Plan #163)."""

    def _create_mock_agent(self, agent_id: str) -> MagicMock:
        """Create a mock agent with export_state method."""
        agent = MagicMock()
        agent.agent_id = agent_id
        agent.export_state.return_value = {
            "working_memory": {"goal": "test goal"},
            "action_history": ["action1", "action2"],
            "failure_history": ["failure1"],
            "actions_taken": 5,
            "successful_actions": 3,
            "failed_actions": 2,
            "revenue_earned": 100.0,
            "artifacts_completed": 2,
            "starting_balance": 50.0,
            "last_action_result": "SUCCESS: test",
        }
        return agent

    def test_saves_agent_states(self) -> None:
        """Checkpoint includes agent_states dict."""
        with tempfile.TemporaryDirectory() as tmpdir:
            checkpoint_path = Path(tmpdir) / "checkpoint.json"
            config = {"budget": {"checkpoint_file": str(checkpoint_path)}}

            world = MagicMock()
            world.event_number = 10
            world.ledger.get_all_balances.return_value = {"alice": {"llm_tokens": 100, "scrip": 200}}
            world.artifacts.artifacts = {}

            agent = self._create_mock_agent("alice")

            save_checkpoint(world, [agent], 0.5, config, "test")

            with open(checkpoint_path) as f:
                data = json.load(f)

            assert "agent_states" in data
            assert "alice" in data["agent_states"]
            state = data["agent_states"]["alice"]
            assert state["working_memory"] == {"goal": "test goal"}
            assert state["action_history"] == ["action1", "action2"]
            assert state["actions_taken"] == 5

    def test_agent_state_roundtrip(self) -> None:
        """Agent state survives save/load cycle."""
        with tempfile.TemporaryDirectory() as tmpdir:
            checkpoint_path = Path(tmpdir) / "checkpoint.json"
            config = {"budget": {"checkpoint_file": str(checkpoint_path)}}

            world = MagicMock()
            world.event_number = 1
            world.ledger.get_all_balances.return_value = {}
            world.artifacts.artifacts = {}

            agent = self._create_mock_agent("test_agent")

            save_checkpoint(world, [agent], 0.0, config, "test")
            loaded = load_checkpoint(str(checkpoint_path))

            assert loaded is not None
            state = loaded["agent_states"]["test_agent"]
            assert state["working_memory"] == {"goal": "test goal"}
            assert state["action_history"] == ["action1", "action2"]
            assert state["failure_history"] == ["failure1"]
            assert state["actions_taken"] == 5
            assert state["successful_actions"] == 3
            assert state["failed_actions"] == 2
            assert state["revenue_earned"] == 100.0
            assert state["artifacts_completed"] == 2
            assert state["starting_balance"] == 50.0
            assert state["last_action_result"] == "SUCCESS: test"

    def test_multiple_agents_state_roundtrip(self) -> None:
        """Multiple agents' states survive round trip."""
        with tempfile.TemporaryDirectory() as tmpdir:
            checkpoint_path = Path(tmpdir) / "checkpoint.json"
            config = {"budget": {"checkpoint_file": str(checkpoint_path)}}

            world = MagicMock()
            world.event_number = 1
            world.ledger.get_all_balances.return_value = {}
            world.artifacts.artifacts = {}

            agent1 = self._create_mock_agent("alice")
            agent1.export_state.return_value = {"actions_taken": 10}

            agent2 = self._create_mock_agent("bob")
            agent2.export_state.return_value = {"actions_taken": 20}

            save_checkpoint(world, [agent1, agent2], 0.0, config, "test")
            loaded = load_checkpoint(str(checkpoint_path))

            assert loaded is not None
            assert loaded["agent_states"]["alice"]["actions_taken"] == 10
            assert loaded["agent_states"]["bob"]["actions_taken"] == 20


@pytest.mark.plans([163])
class TestCheckpointAtomicWrite:
    """Tests for atomic write functionality (Plan #163)."""

    def test_creates_then_renames(self) -> None:
        """Save creates temp file then renames to final path."""
        with tempfile.TemporaryDirectory() as tmpdir:
            checkpoint_path = Path(tmpdir) / "checkpoint.json"
            temp_path = Path(tmpdir) / "checkpoint.json.tmp"
            config = {"budget": {"checkpoint_file": str(checkpoint_path)}}

            world = MagicMock()
            world.event_number = 1
            world.ledger.get_all_balances.return_value = {}
            world.artifacts.artifacts = {}

            save_checkpoint(world, [], 0.0, config, "test")

            # Final file should exist
            assert checkpoint_path.exists()
            # Temp file should NOT exist (was renamed)
            assert not temp_path.exists()

    def test_no_temp_file_remains_on_success(self) -> None:
        """After successful save, no .tmp file remains."""
        with tempfile.TemporaryDirectory() as tmpdir:
            checkpoint_path = Path(tmpdir) / "test_checkpoint.json"
            config = {"budget": {"checkpoint_file": str(checkpoint_path)}}

            world = MagicMock()
            world.event_number = 42
            world.ledger.get_all_balances.return_value = {}
            world.artifacts.artifacts = {}

            save_checkpoint(world, [], 0.0, config, "atomic_test")

            # List all files in directory
            files = list(Path(tmpdir).iterdir())
            assert len(files) == 1
            assert files[0].name == "test_checkpoint.json"


@pytest.mark.plans([163])
class TestRestoreAgentStates:
    """Tests for restore_agent_states helper function (Plan #163)."""

    def test_restores_state_to_matching_agents(self) -> None:
        """restore_agent_states calls restore_state on matching agents."""
        # Create mock agents
        agent1 = MagicMock()
        agent1.agent_id = "alice"
        agent2 = MagicMock()
        agent2.agent_id = "bob"

        checkpoint: CheckpointData = {
            "version": 2,
            "event_number": 10,
            "balances": {},
            "cumulative_api_cost": 0.0,
            "artifacts": [],
            "agent_ids": ["alice", "bob"],
            "reason": "test",
            "agent_states": {
                "alice": {"actions_taken": 5},  # type: ignore[dict-item]
                "bob": {"actions_taken": 10},  # type: ignore[dict-item]
            },
        }

        restore_agent_states([agent1, agent2], checkpoint)

        agent1.restore_state.assert_called_once_with({"actions_taken": 5})
        agent2.restore_state.assert_called_once_with({"actions_taken": 10})

    def test_skips_agents_without_state(self) -> None:
        """Agents not in checkpoint don't get restore_state called."""
        agent = MagicMock()
        agent.agent_id = "new_agent"

        checkpoint: CheckpointData = {
            "version": 2,
            "event_number": 10,
            "balances": {},
            "cumulative_api_cost": 0.0,
            "artifacts": [],
            "agent_ids": [],
            "reason": "test",
            "agent_states": {},
        }

        restore_agent_states([agent], checkpoint)

        agent.restore_state.assert_not_called()

    def test_handles_missing_agent_states_key(self) -> None:
        """Handles checkpoint without agent_states gracefully."""
        agent = MagicMock()
        agent.agent_id = "alice"

        # Simulate v1 checkpoint that was partially migrated
        checkpoint: CheckpointData = {
            "version": 2,
            "event_number": 10,
            "balances": {},
            "cumulative_api_cost": 0.0,
            "artifacts": [],
            "agent_ids": ["alice"],
            "reason": "test",
        }  # type: ignore[typeddict-item]

        # Should not raise
        restore_agent_states([agent], checkpoint)


@pytest.mark.plans([163])
class TestAgentExportRestoreState:
    """Tests for Agent.export_state() and restore_state() methods."""

    @pytest.fixture
    def agent(self) -> Agent:
        """Create a real agent instance for testing."""
        return Agent(
            agent_id="test_agent",
            llm_model="test-model",
            system_prompt="Test prompt",
        )

    def test_export_state_returns_dict(self, agent: Agent) -> None:
        """export_state returns a dictionary."""
        state = agent.export_state()
        assert isinstance(state, dict)

    def test_export_state_includes_action_history(self, agent: Agent) -> None:
        """export_state includes action_history."""
        agent.action_history = ["action1", "action2"]
        state = agent.export_state()
        assert state["action_history"] == ["action1", "action2"]

    def test_export_state_includes_failure_history(self, agent: Agent) -> None:
        """export_state includes failure_history."""
        agent.failure_history = ["fail1", "fail2"]
        state = agent.export_state()
        assert state["failure_history"] == ["fail1", "fail2"]

    def test_export_state_includes_metrics(self, agent: Agent) -> None:
        """export_state includes opportunity cost metrics."""
        agent.actions_taken = 10
        agent.successful_actions = 7
        agent.failed_actions = 3
        agent.revenue_earned = 150.5
        agent.artifacts_completed = 4
        agent._starting_balance = 100.0

        state = agent.export_state()

        assert state["actions_taken"] == 10
        assert state["successful_actions"] == 7
        assert state["failed_actions"] == 3
        assert state["revenue_earned"] == 150.5
        assert state["artifacts_completed"] == 4
        assert state["starting_balance"] == 100.0

    def test_export_state_includes_last_action_result(self, agent: Agent) -> None:
        """export_state includes last_action_result."""
        agent.last_action_result = "SUCCESS: Created artifact"
        state = agent.export_state()
        assert state["last_action_result"] == "SUCCESS: Created artifact"

    def test_restore_state_sets_action_history(self, agent: Agent) -> None:
        """restore_state sets action_history."""
        state = {"action_history": ["a1", "a2", "a3"]}
        agent.restore_state(state)
        assert agent.action_history == ["a1", "a2", "a3"]

    def test_restore_state_sets_failure_history(self, agent: Agent) -> None:
        """restore_state sets failure_history."""
        state = {"failure_history": ["f1", "f2"]}
        agent.restore_state(state)
        assert agent.failure_history == ["f1", "f2"]

    def test_restore_state_sets_metrics(self, agent: Agent) -> None:
        """restore_state sets opportunity cost metrics."""
        state = {
            "actions_taken": 20,
            "successful_actions": 15,
            "failed_actions": 5,
            "revenue_earned": 200.0,
            "artifacts_completed": 8,
            "starting_balance": 75.0,
        }
        agent.restore_state(state)

        assert agent.actions_taken == 20
        assert agent.successful_actions == 15
        assert agent.failed_actions == 5
        assert agent.revenue_earned == 200.0
        assert agent.artifacts_completed == 8
        assert agent._starting_balance == 75.0

    def test_restore_state_sets_last_action_result(self, agent: Agent) -> None:
        """restore_state sets last_action_result."""
        state = {"last_action_result": "FAILED: Insufficient funds"}
        agent.restore_state(state)
        assert agent.last_action_result == "FAILED: Insufficient funds"

    def test_roundtrip_preserves_state(self, agent: Agent) -> None:
        """export_state -> restore_state preserves all state."""
        # Set up agent state
        agent.action_history = ["hist1", "hist2"]
        agent.failure_history = ["fail1"]
        agent.actions_taken = 15
        agent.successful_actions = 12
        agent.failed_actions = 3
        agent.revenue_earned = 500.0
        agent.artifacts_completed = 5
        agent._starting_balance = 200.0
        agent.last_action_result = "SUCCESS: Test"
        agent._working_memory = {"key": "value"}

        # Export state
        exported = agent.export_state()

        # Create new agent and restore
        new_agent = Agent(
            agent_id="test_agent_2",
            llm_model="test-model",
        )
        new_agent.restore_state(exported)

        # Verify all state was preserved
        assert new_agent.action_history == ["hist1", "hist2"]
        assert new_agent.failure_history == ["fail1"]
        assert new_agent.actions_taken == 15
        assert new_agent.successful_actions == 12
        assert new_agent.failed_actions == 3
        assert new_agent.revenue_earned == 500.0
        assert new_agent.artifacts_completed == 5
        assert new_agent._starting_balance == 200.0
        assert new_agent.last_action_result == "SUCCESS: Test"
        assert new_agent._working_memory == {"key": "value"}

    def test_restore_handles_empty_state(self, agent: Agent) -> None:
        """restore_state handles empty state dict gracefully."""
        # Set some state first
        agent.actions_taken = 10

        # Restore empty state - should set defaults
        agent.restore_state({})

        assert agent.actions_taken == 0
        assert agent.action_history == []
        assert agent.failure_history == []

    def test_restore_handles_partial_state(self, agent: Agent) -> None:
        """restore_state handles partial state dict."""
        state = {
            "actions_taken": 5,
            # Missing other fields
        }
        agent.restore_state(state)

        assert agent.actions_taken == 5
        assert agent.successful_actions == 0  # Defaults
        assert agent.action_history == []  # Defaults
