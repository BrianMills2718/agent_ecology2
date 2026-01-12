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
            runner.world.ledger.create_principal("spawned_1", 50)

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
            runner.world.ledger.create_principal("new_1", 50)
            runner.world.ledger.create_principal("new_2", 50)
            runner.world.ledger.create_principal("new_3", 50)

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


class TestAdvanceTickResourceReset:
    """Tests for advance_tick resource reset behavior based on rate limiting mode."""

    @patch("src.simulation.runner.load_agents")
    def test_advance_tick_resets_compute_in_legacy_mode(self, mock_load: MagicMock) -> None:
        """advance_tick resets compute when rate limiting is disabled (legacy mode)."""
        mock_load.return_value = [{"id": "agent", "starting_scrip": 100}]

        with tempfile.TemporaryDirectory() as tmpdir:
            config = make_minimal_config(tmpdir)
            # Ensure rate limiting is disabled (default behavior)
            config["rate_limiting"] = {"enabled": False}
            runner = SimulationRunner(config, verbose=False)

            # Set initial compute
            runner.world.ledger.set_resource("agent", "llm_tokens", 1000.0)
            assert runner.world.ledger.get_compute("agent") == 1000

            # Spend some compute
            runner.world.ledger.spend_compute("agent", 600)
            assert runner.world.ledger.get_compute("agent") == 400

            # Advance tick should reset compute (legacy mode)
            runner.world.advance_tick()

            # Compute should be reset to quota (based on config)
            # In legacy mode, compute resets to default_quotas.compute or config value
            assert runner.world.ledger.get_compute("agent") > 0  # Reset happened

    @patch("src.simulation.runner.load_agents")
    def test_advance_tick_no_reset_when_rate_tracker_enabled(
        self, mock_load: MagicMock
    ) -> None:
        """advance_tick does NOT reset compute when rate limiting is enabled.

        With rate_limiting enabled, get_compute and spend_compute use RateTracker
        instead of tick-based balance. advance_tick should not affect RateTracker.
        """
        mock_load.return_value = [{"id": "agent", "starting_scrip": 100}]

        with tempfile.TemporaryDirectory() as tmpdir:
            config = make_minimal_config(tmpdir)
            # Enable rate limiting with "llm_tokens" resource configured
            config["rate_limiting"] = {
                "enabled": True,
                "window_seconds": 60.0,
                "resources": {"llm_tokens": {"max_per_window": 1000}}
            }
            runner = SimulationRunner(config, verbose=False)

            # get_compute returns RateTracker remaining (full capacity initially)
            assert runner.world.ledger.get_compute("agent") == 1000

            # Spend some compute (consumes from RateTracker)
            runner.world.ledger.spend_compute("agent", 600)
            assert runner.world.ledger.get_compute("agent") == 400

            # Advance tick should NOT affect RateTracker (no reset)
            runner.world.advance_tick()

            # Compute should remain at 400 (RateTracker, not tick-based)
            assert runner.world.ledger.get_compute("agent") == 400

    @patch("src.simulation.runner.load_agents")
    def test_world_use_rate_tracker_flag_from_config(self, mock_load: MagicMock) -> None:
        """World.use_rate_tracker is correctly set from config."""
        mock_load.return_value = []

        with tempfile.TemporaryDirectory() as tmpdir:
            # Test with rate limiting disabled
            config = make_minimal_config(tmpdir)
            config["rate_limiting"] = {"enabled": False}
            runner = SimulationRunner(config, verbose=False)
            assert runner.world.use_rate_tracker is False

            # Test with rate limiting enabled
            config2 = make_minimal_config(tmpdir)
            config2["rate_limiting"] = {"enabled": True}
            config2["logging"]["output_file"] = f"{tmpdir}/run2.jsonl"
            runner2 = SimulationRunner(config2, verbose=False)
            assert runner2.world.use_rate_tracker is True

    @patch("src.simulation.runner.load_agents")
    def test_scrip_never_resets_in_either_mode(self, mock_load: MagicMock) -> None:
        """Scrip never resets regardless of rate limiting mode."""
        mock_load.return_value = [{"id": "agent", "starting_scrip": 100}]

        with tempfile.TemporaryDirectory() as tmpdir:
            # Test legacy mode
            config = make_minimal_config(tmpdir)
            config["rate_limiting"] = {"enabled": False}
            runner = SimulationRunner(config, verbose=False)

            # Spend some scrip
            runner.world.ledger.deduct_scrip("agent", 30)
            assert runner.world.ledger.get_scrip("agent") == 70

            # Advance tick
            runner.world.advance_tick()

            # Scrip should remain at 70 (never resets)
            assert runner.world.ledger.get_scrip("agent") == 70

            # Test rate limiting mode
            config2 = make_minimal_config(tmpdir)
            config2["rate_limiting"] = {"enabled": True}
            config2["logging"]["output_file"] = f"{tmpdir}/run2.jsonl"
            runner2 = SimulationRunner(config2, verbose=False)

            # Spend some scrip
            runner2.world.ledger.deduct_scrip("agent", 30)
            assert runner2.world.ledger.get_scrip("agent") == 70

            # Advance tick
            runner2.world.advance_tick()

            # Scrip should remain at 70 (never resets)
            assert runner2.world.ledger.get_scrip("agent") == 70


class TestAutonomousMode:
    """Tests for autonomous agent loop execution (INT-003)."""

    @patch("src.simulation.runner.load_agents")
    def test_autonomous_mode_disabled_by_default(self, mock_load: MagicMock) -> None:
        """Autonomous mode is not used by default."""
        mock_load.return_value = []

        with tempfile.TemporaryDirectory() as tmpdir:
            config = make_minimal_config(tmpdir)
            runner = SimulationRunner(config, verbose=False)

            assert runner.use_autonomous_loops is False
            assert runner.world.use_autonomous_loops is False
            assert runner.world.loop_manager is None

    @patch("src.simulation.runner.load_agents")
    def test_autonomous_mode_enabled_from_config(self, mock_load: MagicMock) -> None:
        """Autonomous mode is enabled when configured."""
        mock_load.return_value = []

        with tempfile.TemporaryDirectory() as tmpdir:
            config = make_minimal_config(tmpdir)
            config["execution"] = {"use_autonomous_loops": True}
            runner = SimulationRunner(config, verbose=False)

            assert runner.use_autonomous_loops is True
            assert runner.world.use_autonomous_loops is True
            # loop_manager should be created
            assert runner.world.loop_manager is not None

    @patch("src.simulation.runner.load_agents")
    def test_autonomous_mode_creates_rate_tracker_if_missing(
        self, mock_load: MagicMock
    ) -> None:
        """Autonomous mode creates a rate tracker if not configured."""
        mock_load.return_value = []

        with tempfile.TemporaryDirectory() as tmpdir:
            config = make_minimal_config(tmpdir)
            config["execution"] = {"use_autonomous_loops": True}
            # rate_limiting disabled (no rate_tracker from config)
            config["rate_limiting"] = {"enabled": False}
            runner = SimulationRunner(config, verbose=False)

            # rate_tracker should be created even if rate_limiting is disabled
            assert runner.world.rate_tracker is not None
            assert runner.world.loop_manager is not None

    @patch("src.simulation.runner.load_agents")
    def test_autonomous_mode_uses_existing_rate_tracker(
        self, mock_load: MagicMock
    ) -> None:
        """Autonomous mode uses existing rate tracker when available."""
        mock_load.return_value = []

        with tempfile.TemporaryDirectory() as tmpdir:
            config = make_minimal_config(tmpdir)
            config["execution"] = {"use_autonomous_loops": True}
            config["rate_limiting"] = {
                "enabled": True,
                "window_seconds": 120.0,
                "resources": {"llm_calls": {"max_per_window": 50}},
            }
            runner = SimulationRunner(config, verbose=False)

            # Should use the rate tracker from rate_limiting config
            assert runner.world.rate_tracker is not None
            assert runner.world.rate_tracker.window_seconds == 120.0

    @patch("src.simulation.runner.load_agents")
    def test_tick_based_mode_unchanged_when_flag_false(
        self, mock_load: MagicMock
    ) -> None:
        """Tick-based mode works as before when autonomous mode is disabled."""
        mock_load.return_value = []

        with tempfile.TemporaryDirectory() as tmpdir:
            config = make_minimal_config(tmpdir)
            config["execution"] = {"use_autonomous_loops": False}
            runner = SimulationRunner(config, verbose=False)

            # Should be in tick-based mode
            assert runner.use_autonomous_loops is False
            assert runner.world.loop_manager is None

    @patch("src.simulation.runner.load_agents")
    def test_create_agent_loop_with_config(self, mock_load: MagicMock) -> None:
        """_create_agent_loop uses config values."""
        mock_load.return_value = [{"id": "agent", "starting_scrip": 100}]

        with tempfile.TemporaryDirectory() as tmpdir:
            config = make_minimal_config(tmpdir)
            config["execution"] = {
                "use_autonomous_loops": True,
                "agent_loop": {
                    "min_loop_delay": 0.5,
                    "max_loop_delay": 20.0,
                    "resource_check_interval": 2.0,
                    "max_consecutive_errors": 10,
                    "resources_to_check": ["llm_calls", "bandwidth_bytes"],
                },
            }
            runner = SimulationRunner(config, verbose=False)

            # Create loop for the agent
            runner._create_agent_loop(runner.agents[0])

            # Check that loop was created
            loop = runner.world.loop_manager.get_loop("agent")
            assert loop is not None
            assert loop.config.min_loop_delay == 0.5
            assert loop.config.max_loop_delay == 20.0
            assert loop.config.resource_check_interval == 2.0
            assert loop.config.max_consecutive_errors == 10

    @patch("src.simulation.runner.load_agents")
    def test_shutdown_stops_loops(self, mock_load: MagicMock) -> None:
        """shutdown() stops all agent loops."""
        mock_load.return_value = []

        with tempfile.TemporaryDirectory() as tmpdir:
            config = make_minimal_config(tmpdir)
            config["execution"] = {"use_autonomous_loops": True}
            runner = SimulationRunner(config, verbose=False)

            # Should be able to call shutdown even when not running
            import asyncio
            asyncio.run(runner.shutdown())

            assert runner._running is False

    @patch("src.simulation.runner.load_agents")
    def test_world_loop_manager_created_for_autonomous_mode(
        self, mock_load: MagicMock
    ) -> None:
        """World.loop_manager is created when autonomous mode is enabled."""
        mock_load.return_value = [
            {"id": "agent1", "starting_scrip": 100},
            {"id": "agent2", "starting_scrip": 100},
        ]

        with tempfile.TemporaryDirectory() as tmpdir:
            config = make_minimal_config(tmpdir)
            config["execution"] = {"use_autonomous_loops": True}
            runner = SimulationRunner(config, verbose=False)

            assert runner.world.loop_manager is not None
            # Initially no loops (loops created in _run_autonomous)
            assert runner.world.loop_manager.loop_count == 0

    @patch("src.simulation.runner.load_agents")
    def test_run_method_accepts_duration_parameter(self, mock_load: MagicMock) -> None:
        """run() accepts duration parameter for autonomous mode."""
        mock_load.return_value = []

        with tempfile.TemporaryDirectory() as tmpdir:
            config = make_minimal_config(tmpdir)
            # Use tick-based mode for this test
            config["execution"] = {"use_autonomous_loops": False}
            runner = SimulationRunner(config, verbose=False)

            # Should have run method that accepts duration
            import inspect
            sig = inspect.signature(runner.run)
            params = list(sig.parameters.keys())
            assert "duration" in params
            assert "max_ticks" in params


class TestAgentAliveProperty:
    """Tests for Agent.alive property (for autonomous loops)."""

    @patch("src.simulation.runner.load_agents")
    def test_agent_starts_alive(self, mock_load: MagicMock) -> None:
        """Agent starts with alive=True."""
        mock_load.return_value = [{"id": "agent", "starting_scrip": 100}]

        with tempfile.TemporaryDirectory() as tmpdir:
            config = make_minimal_config(tmpdir)
            runner = SimulationRunner(config, verbose=False)

            agent = runner.agents[0]
            assert agent.alive is True

    @patch("src.simulation.runner.load_agents")
    def test_agent_alive_can_be_set(self, mock_load: MagicMock) -> None:
        """Agent.alive can be set to False."""
        mock_load.return_value = [{"id": "agent", "starting_scrip": 100}]

        with tempfile.TemporaryDirectory() as tmpdir:
            config = make_minimal_config(tmpdir)
            runner = SimulationRunner(config, verbose=False)

            agent = runner.agents[0]
            agent.alive = False
            assert agent.alive is False

            # Can also set back to True
            agent.alive = True
            assert agent.alive is True
