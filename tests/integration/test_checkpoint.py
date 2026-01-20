"""Tests for checkpoint save/load functionality.

Tests the round-trip cycle: save → load → verify state consistency.
"""

import json
import tempfile
from pathlib import Path
from typing import Any, cast
from unittest.mock import MagicMock, patch

import pytest

from src.simulation.checkpoint import save_checkpoint, load_checkpoint
from src.simulation.types import CheckpointData, BalanceInfo


class TestSaveCheckpoint:
    """Tests for save_checkpoint function."""

    def test_creates_file(self) -> None:
        """save_checkpoint creates a JSON file at the specified path."""
        with tempfile.TemporaryDirectory() as tmpdir:
            checkpoint_path = Path(tmpdir) / "test_checkpoint.json"
            config = {"budget": {"checkpoint_file": str(checkpoint_path)}}

            # Create mock world
            world = MagicMock()
            world.tick = 5
            world.ledger.get_all_balances.return_value = {"agent_a": {"compute": 100, "scrip": 50}}
            world.artifacts.artifacts = {}

            # Create mock agents
            agents: Any = [MagicMock(agent_id="agent_a")]

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
            world.tick = 10
            world.ledger.get_all_balances.return_value = {
                "alice": {"compute": 100, "scrip": 200},
                "bob": {"compute": 50, "scrip": 75},
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

            agents: Any = [
                MagicMock(agent_id="alice"),
                MagicMock(agent_id="bob"),
            ]

            save_checkpoint(world, agents, 1.23, config, "budget_exhausted")

            with open(checkpoint_path) as f:
                data = json.load(f)

            assert data["tick"] == 10
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
            world.tick = 1
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
                "tick": 25,
                "balances": {
                    "alice": {"compute": 100, "scrip": 200},
                    "bob": {"compute": 50, "scrip": 75},
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
            assert result["tick"] == 25
            assert result["balances"]["alice"]["compute"] == 100
            assert result["balances"]["alice"]["scrip"] == 200
            assert result["balances"]["bob"]["compute"] == 50
            assert result["balances"]["bob"]["scrip"] == 75
            assert result["cumulative_api_cost"] == 0.75
            assert result["reason"] == "test_reason"

    def test_loads_legacy_format(self) -> None:
        """load_checkpoint handles legacy int-only balance format."""
        with tempfile.TemporaryDirectory() as tmpdir:
            checkpoint_path = Path(tmpdir) / "checkpoint.json"

            # Legacy format: balances are just integers (scrip only)
            data = {
                "tick": 10,
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
            assert result["balances"]["alice"]["compute"] == 0
            assert result["balances"]["alice"]["scrip"] == 200
            assert result["balances"]["bob"]["compute"] == 0
            assert result["balances"]["bob"]["scrip"] == 75

    def test_loads_artifacts(self) -> None:
        """load_checkpoint preserves artifact data."""
        with tempfile.TemporaryDirectory() as tmpdir:
            checkpoint_path = Path(tmpdir) / "checkpoint.json"

            data = {
                "tick": 5,
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
        """Basic checkpoint round trip preserves tick, cost, and reason."""
        with tempfile.TemporaryDirectory() as tmpdir:
            checkpoint_path = Path(tmpdir) / "checkpoint.json"
            config = {"budget": {"checkpoint_file": str(checkpoint_path)}}

            world = MagicMock()
            world.tick = 42
            world.ledger.get_all_balances.return_value = {}
            world.artifacts.artifacts = {}

            save_checkpoint(world, [], 1.234, config, "budget_pause")
            loaded = load_checkpoint(str(checkpoint_path))

            assert loaded is not None
            assert loaded["tick"] == 42
            assert loaded["cumulative_api_cost"] == 1.234
            assert loaded["reason"] == "budget_pause"

    def test_balances_round_trip(self) -> None:
        """Balances survive round trip with compute and scrip."""
        with tempfile.TemporaryDirectory() as tmpdir:
            checkpoint_path = Path(tmpdir) / "checkpoint.json"
            config = {"budget": {"checkpoint_file": str(checkpoint_path)}}

            world = MagicMock()
            world.tick = 1
            world.ledger.get_all_balances.return_value = {
                "alice": {"compute": 100, "scrip": 500},
                "bob": {"compute": 75, "scrip": 250},
                "charlie": {"compute": 0, "scrip": 1000},
            }
            world.artifacts.artifacts = {}

            agents: Any = [
                MagicMock(agent_id="alice"),
                MagicMock(agent_id="bob"),
                MagicMock(agent_id="charlie"),
            ]

            save_checkpoint(world, agents, 0.0, config, "test")
            loaded = load_checkpoint(str(checkpoint_path))

            assert loaded is not None
            assert loaded["balances"]["alice"]["compute"] == 100
            assert loaded["balances"]["alice"]["scrip"] == 500
            assert loaded["balances"]["bob"]["compute"] == 75
            assert loaded["balances"]["bob"]["scrip"] == 250
            assert loaded["balances"]["charlie"]["compute"] == 0
            assert loaded["balances"]["charlie"]["scrip"] == 1000

    def test_artifacts_round_trip(self) -> None:
        """Artifacts survive round trip with all fields."""
        with tempfile.TemporaryDirectory() as tmpdir:
            checkpoint_path = Path(tmpdir) / "checkpoint.json"
            config = {"budget": {"checkpoint_file": str(checkpoint_path)}}

            world = MagicMock()
            world.tick = 1
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
            world.tick = 1
            world.ledger.get_all_balances.return_value = {}
            world.artifacts.artifacts = {}

            agents: Any = [
                MagicMock(agent_id="first"),
                MagicMock(agent_id="second"),
                MagicMock(agent_id="third"),
            ]

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
            world.tick = 0
            world.ledger.get_all_balances.return_value = {}
            world.artifacts.artifacts = {}

            save_checkpoint(world, [], 0.0, config, "empty_test")
            loaded = load_checkpoint(str(checkpoint_path))

            assert loaded is not None
            assert loaded["tick"] == 0
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
                world.tick = 1
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
            world.tick = 99
            world.ledger.get_all_balances.return_value = {}
            world.artifacts.artifacts = {}

            save_checkpoint(world, [], 0.0, config, "new_reason")
            loaded = load_checkpoint(str(checkpoint_path))

            assert loaded is not None
            assert loaded["tick"] == 99
            assert loaded["reason"] == "new_reason"
            assert "old" not in loaded  # type: ignore[operator]

    def test_high_precision_cost(self) -> None:
        """Cumulative API cost preserves decimal precision."""
        with tempfile.TemporaryDirectory() as tmpdir:
            checkpoint_path = Path(tmpdir) / "checkpoint.json"
            config = {"budget": {"checkpoint_file": str(checkpoint_path)}}

            world = MagicMock()
            world.tick = 1
            world.ledger.get_all_balances.return_value = {}
            world.artifacts.artifacts = {}

            precise_cost = 0.123456789
            save_checkpoint(world, [], precise_cost, config, "test")
            loaded = load_checkpoint(str(checkpoint_path))

            assert loaded is not None
            # JSON preserves float precision reasonably well
            assert abs(loaded["cumulative_api_cost"] - precise_cost) < 1e-10
