"""Tests for SimulationRunner.

Tests the core orchestration logic without running full async simulations.
"""

import tempfile
from pathlib import Path
from typing import Any
from unittest.mock import MagicMock, patch, AsyncMock

import pytest
import yaml

from src.simulation.runner import SimulationRunner
from src.simulation.types import CheckpointData


def make_minimal_config(tmpdir: str) -> dict[str, Any]:
    """Create minimal valid config for testing."""
    return {
        "world": {"max_ticks": 10},
        "costs": {"per_1k_input_tokens": 1, "per_1k_output_tokens": 3},
        "logging": {"output_file": f"{tmpdir}/run.jsonl", "log_dir": tmpdir},
        "scrip": {"starting_amount": 100},
        "llm": {"default_model": "test-model", "rate_limit_delay": 0},
        "budget": {"max_api_cost": 1.0},
        "resources": {
            "stock": {"llm_budget": {"total": 10.0}, "disk": {"total": 50000}},
            "flow": {"compute": {"per_tick": 1000}},
        },
        "genesis": {"artifacts": {"ledger": {"enabled": True}}},
    }


class TestSimulationRunnerInit:
    """Tests for SimulationRunner initialization."""

    @patch("src.simulation.runner.load_agents")
    def test_initializes_with_minimal_config(self, mock_load: MagicMock) -> None:
        """SimulationRunner initializes with minimal config."""
        mock_load.return_value = []

        with tempfile.TemporaryDirectory() as tmpdir:
            config = make_minimal_config(tmpdir)
            runner = SimulationRunner(config, verbose=False)

            assert runner.world is not None
            assert runner.config == config
            assert runner.verbose is False
            assert runner.agents == []

    @patch("src.simulation.runner.load_agents")
    def test_loads_agents_from_loader(self, mock_load: MagicMock) -> None:
        """SimulationRunner loads agents via load_agents."""
        mock_load.return_value = [
            {"id": "agent_a", "starting_scrip": 100},
            {"id": "agent_b", "starting_scrip": 200},
        ]

        with tempfile.TemporaryDirectory() as tmpdir:
            config = make_minimal_config(tmpdir)
            runner = SimulationRunner(config, verbose=False)

            assert len(runner.agents) == 2
            assert runner.agents[0].agent_id == "agent_a"
            assert runner.agents[1].agent_id == "agent_b"

    @patch("src.simulation.runner.load_agents")
    def test_respects_max_agents(self, mock_load: MagicMock) -> None:
        """SimulationRunner limits agents to max_agents."""
        mock_load.return_value = [
            {"id": "a1", "starting_scrip": 100},
            {"id": "a2", "starting_scrip": 100},
            {"id": "a3", "starting_scrip": 100},
        ]

        with tempfile.TemporaryDirectory() as tmpdir:
            config = make_minimal_config(tmpdir)
            runner = SimulationRunner(config, max_agents=2, verbose=False)

            assert len(runner.agents) == 2

    @patch("src.simulation.runner.load_agents")
    def test_generates_run_id(self, mock_load: MagicMock) -> None:
        """SimulationRunner generates a run ID."""
        mock_load.return_value = []

        with tempfile.TemporaryDirectory() as tmpdir:
            config = make_minimal_config(tmpdir)
            runner = SimulationRunner(config, verbose=False)

            assert runner.run_id.startswith("run_")
            assert len(runner.run_id) > 10

    @patch("src.simulation.runner.load_agents")
    def test_uses_config_delay(self, mock_load: MagicMock) -> None:
        """SimulationRunner uses delay from config if not overridden."""
        mock_load.return_value = []

        with tempfile.TemporaryDirectory() as tmpdir:
            config = make_minimal_config(tmpdir)
            config["llm"]["rate_limit_delay"] = 5.0
            runner = SimulationRunner(config, verbose=False)

            assert runner.delay == 5.0

    @patch("src.simulation.runner.load_agents")
    def test_delay_override(self, mock_load: MagicMock) -> None:
        """SimulationRunner delay param overrides config."""
        mock_load.return_value = []

        with tempfile.TemporaryDirectory() as tmpdir:
            config = make_minimal_config(tmpdir)
            config["llm"]["rate_limit_delay"] = 5.0
            runner = SimulationRunner(config, delay=1.0, verbose=False)

            assert runner.delay == 1.0


class TestCheckpointRestore:
    """Tests for checkpoint restoration."""

    @patch("src.simulation.runner.load_agents")
    def test_restores_tick_from_checkpoint(self, mock_load: MagicMock) -> None:
        """SimulationRunner restores tick from checkpoint."""
        mock_load.return_value = [{"id": "agent", "starting_scrip": 100}]

        checkpoint: CheckpointData = {
            "tick": 25,
            "balances": {"agent": {"compute": 50, "scrip": 150}},
            "cumulative_api_cost": 0.5,
            "artifacts": [],
            "agent_ids": ["agent"],
            "reason": "test",
        }

        with tempfile.TemporaryDirectory() as tmpdir:
            config = make_minimal_config(tmpdir)
            runner = SimulationRunner(config, checkpoint=checkpoint, verbose=False)

            # Tick is restored to checkpoint.tick - 1 (because advance_tick increments)
            assert runner.world.tick == 24

    @patch("src.simulation.runner.load_agents")
    def test_restores_api_cost_from_checkpoint(self, mock_load: MagicMock) -> None:
        """SimulationRunner restores API cost from checkpoint."""
        mock_load.return_value = []

        checkpoint: CheckpointData = {
            "tick": 10,
            "balances": {},
            "cumulative_api_cost": 0.75,
            "artifacts": [],
            "agent_ids": [],
            "reason": "test",
        }

        with tempfile.TemporaryDirectory() as tmpdir:
            config = make_minimal_config(tmpdir)
            runner = SimulationRunner(config, checkpoint=checkpoint, verbose=False)

            assert runner.engine.cumulative_api_cost == 0.75

    @patch("src.simulation.runner.load_agents")
    def test_restores_artifacts_from_checkpoint(self, mock_load: MagicMock) -> None:
        """SimulationRunner restores artifacts from checkpoint."""
        mock_load.return_value = []

        checkpoint: CheckpointData = {
            "tick": 5,
            "balances": {},
            "cumulative_api_cost": 0.0,
            "artifacts": [
                {"id": "art1", "type": "data", "content": "hello", "owner_id": "system"},
                {"id": "art2", "type": "tool", "content": "tool desc", "owner_id": "agent"},
            ],
            "agent_ids": [],
            "reason": "test",
        }

        with tempfile.TemporaryDirectory() as tmpdir:
            config = make_minimal_config(tmpdir)
            runner = SimulationRunner(config, checkpoint=checkpoint, verbose=False)

            # Artifacts restored (genesis artifacts + checkpoint artifacts)
            assert runner.world.artifacts.get("art1") is not None
            assert runner.world.artifacts.get("art2") is not None


class TestCheckForNewPrincipals:
    """Tests for _check_for_new_principals."""

    @patch("src.simulation.runner.load_agents")
    def test_detects_spawned_principals(self, mock_load: MagicMock) -> None:
        """_check_for_new_principals creates agents for new principals."""
        mock_load.return_value = [{"id": "original", "starting_scrip": 100}]

        with tempfile.TemporaryDirectory() as tmpdir:
            config = make_minimal_config(tmpdir)
            runner = SimulationRunner(config, verbose=False)

            # Manually add a principal to ledger
            runner.world.ledger.create_principal("spawned_1", 50, 100)

            new_agents = runner._check_for_new_principals()

            assert len(new_agents) == 1
            assert new_agents[0].agent_id == "spawned_1"

    @patch("src.simulation.runner.load_agents")
    def test_ignores_existing_agents(self, mock_load: MagicMock) -> None:
        """_check_for_new_principals doesn't duplicate existing agents."""
        mock_load.return_value = [
            {"id": "existing_a", "starting_scrip": 100},
            {"id": "existing_b", "starting_scrip": 100},
        ]

        with tempfile.TemporaryDirectory() as tmpdir:
            config = make_minimal_config(tmpdir)
            runner = SimulationRunner(config, verbose=False)

            # No new principals
            new_agents = runner._check_for_new_principals()

            assert len(new_agents) == 0

    @patch("src.simulation.runner.load_agents")
    def test_multiple_spawned_principals(self, mock_load: MagicMock) -> None:
        """_check_for_new_principals handles multiple spawned principals."""
        mock_load.return_value = [{"id": "original", "starting_scrip": 100}]

        with tempfile.TemporaryDirectory() as tmpdir:
            config = make_minimal_config(tmpdir)
            runner = SimulationRunner(config, verbose=False)

            # Add multiple principals
            runner.world.ledger.create_principal("new_1", 50, 100)
            runner.world.ledger.create_principal("new_2", 50, 100)
            runner.world.ledger.create_principal("new_3", 50, 100)

            new_agents = runner._check_for_new_principals()

            assert len(new_agents) == 3
            agent_ids = {a.agent_id for a in new_agents}
            assert agent_ids == {"new_1", "new_2", "new_3"}


class TestPauseResume:
    """Tests for pause/resume functionality."""

    @patch("src.simulation.runner.load_agents")
    def test_starts_unpaused(self, mock_load: MagicMock) -> None:
        """SimulationRunner starts in unpaused state."""
        mock_load.return_value = []

        with tempfile.TemporaryDirectory() as tmpdir:
            config = make_minimal_config(tmpdir)
            runner = SimulationRunner(config, verbose=False)

            assert runner.is_paused is False

    @patch("src.simulation.runner.load_agents")
    def test_pause_sets_paused_flag(self, mock_load: MagicMock) -> None:
        """pause() sets is_paused to True."""
        mock_load.return_value = []

        with tempfile.TemporaryDirectory() as tmpdir:
            config = make_minimal_config(tmpdir)
            runner = SimulationRunner(config, verbose=False)

            runner.pause()

            assert runner.is_paused is True

    @patch("src.simulation.runner.load_agents")
    def test_resume_clears_paused_flag(self, mock_load: MagicMock) -> None:
        """resume() sets is_paused to False."""
        mock_load.return_value = []

        with tempfile.TemporaryDirectory() as tmpdir:
            config = make_minimal_config(tmpdir)
            runner = SimulationRunner(config, verbose=False)

            runner.pause()
            runner.resume()

            assert runner.is_paused is False

    @patch("src.simulation.runner.load_agents")
    def test_starts_not_running(self, mock_load: MagicMock) -> None:
        """SimulationRunner starts in non-running state."""
        mock_load.return_value = []

        with tempfile.TemporaryDirectory() as tmpdir:
            config = make_minimal_config(tmpdir)
            runner = SimulationRunner(config, verbose=False)

            assert runner.is_running is False


class TestGetStatus:
    """Tests for get_status method."""

    @patch("src.simulation.runner.load_agents")
    def test_returns_status_dict(self, mock_load: MagicMock) -> None:
        """get_status returns correct status information."""
        mock_load.return_value = [
            {"id": "a1", "starting_scrip": 100},
            {"id": "a2", "starting_scrip": 100},
        ]

        with tempfile.TemporaryDirectory() as tmpdir:
            config = make_minimal_config(tmpdir)
            runner = SimulationRunner(config, verbose=False)

            status = runner.get_status()

            assert status["running"] is False
            assert status["paused"] is False
            assert status["tick"] == 0
            assert status["max_ticks"] == 10
            assert status["agent_count"] == 2
            assert "api_cost" in status
            assert "max_api_cost" in status

    @patch("src.simulation.runner.load_agents")
    def test_status_reflects_pause(self, mock_load: MagicMock) -> None:
        """get_status reflects paused state."""
        mock_load.return_value = []

        with tempfile.TemporaryDirectory() as tmpdir:
            config = make_minimal_config(tmpdir)
            runner = SimulationRunner(config, verbose=False)

            runner.pause()
            status = runner.get_status()

            assert status["paused"] is True


class TestActiveRunner:
    """Tests for class-level active runner tracking."""

    @patch("src.simulation.runner.load_agents")
    def test_get_active_returns_none_initially(self, mock_load: MagicMock) -> None:
        """get_active returns None when no simulation is running."""
        # Clear any existing active runner
        SimulationRunner._active_runner = None

        result = SimulationRunner.get_active()

        assert result is None


class TestCreateAgents:
    """Tests for _create_agents method."""

    @patch("src.simulation.runner.load_agents")
    def test_creates_agents_with_correct_ids(self, mock_load: MagicMock) -> None:
        """_create_agents creates agents with correct IDs."""
        mock_load.return_value = [
            {"id": "alice", "starting_scrip": 100},
            {"id": "bob", "starting_scrip": 200},
        ]

        with tempfile.TemporaryDirectory() as tmpdir:
            config = make_minimal_config(tmpdir)
            runner = SimulationRunner(config, verbose=False)

            assert runner.agents[0].agent_id == "alice"
            assert runner.agents[1].agent_id == "bob"

    @patch("src.simulation.runner.load_agents")
    def test_agents_get_run_id(self, mock_load: MagicMock) -> None:
        """Created agents receive the runner's run_id."""
        mock_load.return_value = [{"id": "agent", "starting_scrip": 100}]

        with tempfile.TemporaryDirectory() as tmpdir:
            config = make_minimal_config(tmpdir)
            runner = SimulationRunner(config, verbose=False)

            # Agent should have same run_id as runner
            assert runner.agents[0].run_id == runner.run_id

    @patch("src.simulation.runner.load_agents")
    def test_uses_default_model_when_not_specified(self, mock_load: MagicMock) -> None:
        """_create_agents uses default model when agent config lacks llm_model."""
        mock_load.return_value = [{"id": "agent", "starting_scrip": 100}]  # No llm_model

        with tempfile.TemporaryDirectory() as tmpdir:
            config = make_minimal_config(tmpdir)
            config["llm"]["default_model"] = "my-custom-model"
            runner = SimulationRunner(config, verbose=False)

            assert runner.agents[0].llm_model == "my-custom-model"


class TestHandleOracleTick:
    """Tests for _handle_oracle_tick method."""

    @patch("src.simulation.runner.load_agents")
    def test_returns_none_when_no_oracle(self, mock_load: MagicMock) -> None:
        """_handle_oracle_tick returns None when oracle not configured."""
        mock_load.return_value = []

        with tempfile.TemporaryDirectory() as tmpdir:
            config = make_minimal_config(tmpdir)
            # Disable oracle
            config["genesis"]["artifacts"]["oracle"] = {"enabled": False}
            runner = SimulationRunner(config, verbose=False)

            # Remove oracle if it exists
            if "genesis_oracle" in runner.world.genesis_artifacts:
                del runner.world.genesis_artifacts["genesis_oracle"]

            result = runner._handle_oracle_tick()

            assert result is None

    @patch("src.simulation.runner.load_agents")
    def test_returns_none_when_oracle_has_no_on_tick(self, mock_load: MagicMock) -> None:
        """_handle_oracle_tick returns None for oracles without on_tick."""
        mock_load.return_value = []

        with tempfile.TemporaryDirectory() as tmpdir:
            config = make_minimal_config(tmpdir)
            runner = SimulationRunner(config, verbose=False)

            # Replace oracle with mock without on_tick
            mock_oracle = MagicMock(spec=[])  # No on_tick attribute
            runner.world.genesis_artifacts["genesis_oracle"] = mock_oracle

            result = runner._handle_oracle_tick()

            assert result is None


class TestPrincipalConfig:
    """Tests for principal config building."""

    @patch("src.simulation.runner.load_agents")
    def test_builds_principals_from_agents(self, mock_load: MagicMock) -> None:
        """SimulationRunner builds principals list for World init."""
        mock_load.return_value = [
            {"id": "alice", "starting_scrip": 150},
            {"id": "bob", "starting_scrip": 75},
        ]

        with tempfile.TemporaryDirectory() as tmpdir:
            config = make_minimal_config(tmpdir)
            runner = SimulationRunner(config, verbose=False)

            # Verify principals were created in ledger
            assert runner.world.ledger.get_scrip("alice") == 150
            assert runner.world.ledger.get_scrip("bob") == 75

    @patch("src.simulation.runner.load_agents")
    def test_uses_default_scrip_when_not_specified(self, mock_load: MagicMock) -> None:
        """SimulationRunner uses default starting_amount when not in agent config."""
        mock_load.return_value = [{"id": "agent"}]  # No starting_scrip

        with tempfile.TemporaryDirectory() as tmpdir:
            config = make_minimal_config(tmpdir)
            config["scrip"]["starting_amount"] = 500
            runner = SimulationRunner(config, verbose=False)

            assert runner.world.ledger.get_scrip("agent") == 500
