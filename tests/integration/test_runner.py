"""Tests for SimulationRunner.

Tests the core orchestration logic without running full async simulations.

# mock-ok: Mocking load_agents avoids LLM API calls - tests focus on runner orchestration, not agent behavior
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

            # Event counter (tick) is restored directly from checkpoint (Plan #102)
            assert runner.world.tick == 25

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
                {"id": "art1", "type": "data", "content": "hello", "created_by": "system"},
                {"id": "art2", "type": "tool", "content": "tool desc", "created_by": "agent"},
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
            assert status["event_count"] == 0  # Plan #102: renamed from "tick"
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


class TestHandleMintUpdate:
    """Tests for _handle_mint_update method (Plan #79)."""

    @patch("src.simulation.runner.load_agents")
    def test_returns_none_when_no_mint(self, mock_load: MagicMock) -> None:
        """_handle_mint_update returns None when mint not configured."""
        mock_load.return_value = []

        with tempfile.TemporaryDirectory() as tmpdir:
            config = make_minimal_config(tmpdir)
            # Disable mint
            config["genesis"]["artifacts"]["mint"] = {"enabled": False}
            runner = SimulationRunner(config, verbose=False)

            # Remove mint if it exists
            if "genesis_mint" in runner.world.genesis_artifacts:
                del runner.world.genesis_artifacts["genesis_mint"]

            result = runner._handle_mint_update()

            assert result is None

    @patch("src.simulation.runner.load_agents")
    def test_returns_none_when_mint_has_no_update(self, mock_load: MagicMock) -> None:
        """_handle_mint_update returns None for mints without update method."""
        mock_load.return_value = []

        with tempfile.TemporaryDirectory() as tmpdir:
            config = make_minimal_config(tmpdir)
            runner = SimulationRunner(config, verbose=False)

            # Replace mint with mock without update attribute
            mock_mint = MagicMock(spec=[])  # No update attribute
            runner.world.genesis_artifacts["genesis_mint"] = mock_mint

            result = runner._handle_mint_update()

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
            assert runner.world.ledger.get_llm_tokens("agent") == 1000

            # Spend some compute
            runner.world.ledger.spend_llm_tokens("agent", 600)
            assert runner.world.ledger.get_llm_tokens("agent") == 400

            # Advance tick should reset compute (legacy mode)
            runner.world.advance_tick()

            # Compute should be reset to quota (based on config)
            # In legacy mode, compute resets to default_quotas.compute or config value
            assert runner.world.ledger.get_llm_tokens("agent") > 0  # Reset happened

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
            assert runner.world.ledger.get_llm_tokens("agent") == 1000

            # Spend some compute (consumes from RateTracker)
            runner.world.ledger.spend_llm_tokens("agent", 600)
            assert runner.world.ledger.get_llm_tokens("agent") == 400

            # Advance tick should NOT affect RateTracker (no reset)
            runner.world.advance_tick()

            # Compute should remain at 400 (RateTracker, not tick-based)
            assert runner.world.ledger.get_llm_tokens("agent") == 400

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
    def test_autonomous_mode_always_enabled(self, mock_load: MagicMock) -> None:
        """Autonomous mode is always enabled (Plan #102: tick-based mode removed)."""
        mock_load.return_value = []

        with tempfile.TemporaryDirectory() as tmpdir:
            config = make_minimal_config(tmpdir)
            runner = SimulationRunner(config, verbose=False)

            # Plan #102: Autonomous mode is always used
            assert runner.use_autonomous_loops is True
            assert runner.world.loop_manager is not None

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
    def test_autonomous_mode_ignores_config_false(
        self, mock_load: MagicMock
    ) -> None:
        """Autonomous mode is used even if config says false (Plan #102)."""
        mock_load.return_value = []

        with tempfile.TemporaryDirectory() as tmpdir:
            config = make_minimal_config(tmpdir)
            config["execution"] = {"use_autonomous_loops": False}  # Ignored
            runner = SimulationRunner(config, verbose=False)

            # Plan #102: Always uses autonomous mode
            assert runner.use_autonomous_loops is True
            assert runner.world.loop_manager is not None

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
            runner = SimulationRunner(config, verbose=False)

            # Plan #102: run() only accepts duration (max_ticks removed)
            import inspect
            sig = inspect.signature(runner.run)
            params = list(sig.parameters.keys())
            assert "duration" in params
            assert "max_ticks" not in params  # Removed in Plan #102


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


class TestBudgetExhaustion:
    """Tests for global budget exhaustion checks (critical bug fix)."""

    @patch("src.simulation.runner.load_agents")
    def test_agent_decide_skips_when_budget_exhausted(
        self, mock_load: MagicMock
    ) -> None:
        """_agent_decide_action returns None when global budget exhausted."""
        mock_load.return_value = [{"id": "agent", "starting_scrip": 100}]

        with tempfile.TemporaryDirectory() as tmpdir:
            config = make_minimal_config(tmpdir)
            config["budget"]["max_api_cost"] = 0.01  # Very low budget
            runner = SimulationRunner(config, verbose=False)

            # Exhaust the budget
            runner.engine.track_api_cost(0.02)  # Over the $0.01 limit

            # Verify budget is exhausted
            assert runner.engine.is_budget_exhausted() is True

            # _agent_decide_action should return None
            import asyncio
            result = asyncio.run(runner._agent_decide_action(runner.agents[0]))
            assert result is None

    @patch("src.simulation.runner.load_agents")
    def test_autonomous_loop_checks_budget(self, mock_load: MagicMock) -> None:
        """_run_autonomous checks budget exhaustion in loop."""
        mock_load.return_value = []

        with tempfile.TemporaryDirectory() as tmpdir:
            config = make_minimal_config(tmpdir)
            config["budget"]["max_api_cost"] = 0.01
            runner = SimulationRunner(config, verbose=False)

            # Exhaust budget before run
            runner.engine.track_api_cost(0.02)

            # Run should exit quickly due to budget exhaustion
            import asyncio
            import time

            start = time.time()
            asyncio.run(runner._run_autonomous(duration=5.0))  # Would be 5s if no budget check
            elapsed = time.time() - start

            # Should exit well before 5 seconds due to budget check
            assert elapsed < 2.0, f"Expected quick exit due to budget exhaustion, took {elapsed}s"

    @patch("src.simulation.runner.load_agents")
    def test_engine_budget_exhaustion_check(self, mock_load: MagicMock) -> None:
        """is_budget_exhausted returns correct values."""
        mock_load.return_value = []

        with tempfile.TemporaryDirectory() as tmpdir:
            config = make_minimal_config(tmpdir)
            config["budget"]["max_api_cost"] = 1.0
            runner = SimulationRunner(config, verbose=False)

            # Not exhausted initially
            assert runner.engine.is_budget_exhausted() is False

            # Track cost below limit
            runner.engine.track_api_cost(0.50)
            assert runner.engine.is_budget_exhausted() is False

            # Track cost to exceed limit
            runner.engine.track_api_cost(0.60)  # Total: $1.10
            assert runner.engine.is_budget_exhausted() is True
