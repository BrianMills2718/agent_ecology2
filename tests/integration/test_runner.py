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
    def test_no_legacy_agents_loaded(self, mock_load: MagicMock) -> None:
        """SimulationRunner no longer loads legacy agents (Plan #299).

        Legacy agent loading has been disabled. Agents are now artifact-based
        and loaded via genesis. The load_agents function is not called.
        """
        # mock_load won't be called because legacy loading is disabled
        mock_load.return_value = [
            {"id": "agent_a", "starting_scrip": 100},
            {"id": "agent_b", "starting_scrip": 200},
        ]

        with tempfile.TemporaryDirectory() as tmpdir:
            config = make_minimal_config(tmpdir)
            runner = SimulationRunner(config, verbose=False)

            # No legacy agents loaded - artifact-based agents are discovered
            # by ArtifactLoopManager.discover_loops() during run()
            assert len(runner.agents) == 0
            mock_load.assert_not_called()

    @patch("src.simulation.runner.load_agents")
    def test_max_agents_param_exists(self, mock_load: MagicMock) -> None:
        """SimulationRunner accepts max_agents parameter (legacy compat)."""
        mock_load.return_value = []

        with tempfile.TemporaryDirectory() as tmpdir:
            config = make_minimal_config(tmpdir)
            # Parameter is accepted but has no effect on artifact-based agents
            runner = SimulationRunner(config, max_agents=2, verbose=False)

            # No legacy agents loaded
            assert len(runner.agents) == 0

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
    def test_restores_event_number_from_checkpoint(self, mock_load: MagicMock) -> None:
        """SimulationRunner restores event_number from checkpoint."""
        mock_load.return_value = [{"id": "agent", "starting_scrip": 100}]

        checkpoint: CheckpointData = {
            "event_number": 25,
            "balances": {"agent": {"compute": 50, "scrip": 150}},
            "cumulative_api_cost": 0.5,
            "artifacts": [],
            "agent_ids": ["agent"],
            "reason": "test",
        }

        with tempfile.TemporaryDirectory() as tmpdir:
            config = make_minimal_config(tmpdir)
            runner = SimulationRunner(config, checkpoint=checkpoint, verbose=False)

            # Event counter is restored directly from checkpoint (Plan #102)
            assert runner.world.event_number == 25

    @patch("src.simulation.runner.load_agents")
    def test_restores_api_cost_from_checkpoint(self, mock_load: MagicMock) -> None:
        """SimulationRunner restores API cost from checkpoint."""
        mock_load.return_value = []

        checkpoint: CheckpointData = {
            "event_number": 10,
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
            "event_number": 5,
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
        # Plan #299: Legacy agent loading disabled - mock won't be called
        mock_load.return_value = []

        with tempfile.TemporaryDirectory() as tmpdir:
            config = make_minimal_config(tmpdir)
            runner = SimulationRunner(config, verbose=False)

            status = runner.get_status()

            assert status["running"] is False
            assert status["paused"] is False
            assert status["event_count"] == 0  # Plan #102: renamed from "tick"
            # Plan #299: No legacy agents - artifact loops discovered at runtime
            assert status["agent_count"] == 0
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
    """Tests for _create_agents method (Plan #299: legacy loading disabled)."""

    @patch("src.simulation.runner.load_agents")
    def test_no_legacy_agents_created(self, mock_load: MagicMock) -> None:
        """_create_agents returns empty list (Plan #299: legacy loading disabled)."""
        # Mock is set but won't be called
        mock_load.return_value = [
            {"id": "alice", "starting_scrip": 100},
            {"id": "bob", "starting_scrip": 200},
        ]

        with tempfile.TemporaryDirectory() as tmpdir:
            config = make_minimal_config(tmpdir)
            runner = SimulationRunner(config, verbose=False)

            # No legacy agents created - artifact loops discovered at runtime
            assert len(runner.agents) == 0
            mock_load.assert_not_called()

    @patch("src.simulation.runner.load_agents")
    def test_agent_configs_empty(self, mock_load: MagicMock) -> None:
        """agent_configs is always empty (Plan #299: legacy loading disabled)."""
        mock_load.return_value = [{"id": "agent", "starting_scrip": 100}]

        with tempfile.TemporaryDirectory() as tmpdir:
            config = make_minimal_config(tmpdir)
            runner = SimulationRunner(config, verbose=False)

            assert len(runner.agent_configs) == 0


class TestPrincipalConfig:
    """Tests for principal config building (Plan #299: from genesis, not legacy agents)."""

    @patch("src.simulation.runner.load_agents")
    def test_no_principals_from_legacy_agents(self, mock_load: MagicMock) -> None:
        """SimulationRunner no longer builds principals from legacy agents."""
        # Mock is set but won't be called
        mock_load.return_value = [
            {"id": "alice", "starting_scrip": 150},
            {"id": "bob", "starting_scrip": 75},
        ]

        with tempfile.TemporaryDirectory() as tmpdir:
            config = make_minimal_config(tmpdir)
            runner = SimulationRunner(config, verbose=False)

            # Legacy agents don't create principals - genesis loader creates them
            # These IDs won't exist in ledger from legacy loading
            assert not runner.world.ledger.principal_exists("alice")
            assert not runner.world.ledger.principal_exists("bob")

    @patch("src.simulation.runner.load_agents")
    def test_genesis_principals_exist(self, mock_load: MagicMock) -> None:
        """Genesis loader creates principals, not legacy agent loading."""
        mock_load.return_value = []

        with tempfile.TemporaryDirectory() as tmpdir:
            config = make_minimal_config(tmpdir)
            runner = SimulationRunner(config, verbose=False)

            # Genesis creates kernel_mint_agent principal
            assert runner.world.ledger.principal_exists("kernel_mint_agent")


class TestRateTrackerResourceBehavior:
    """Tests for RateTracker-based resource behavior (Plan #247: legacy tick mode removed)."""

    @patch("src.simulation.runner.load_agents")
    def test_rate_tracker_always_created(self, mock_load: MagicMock) -> None:
        """RateTracker is always created regardless of config (Plan #247)."""
        mock_load.return_value = []

        with tempfile.TemporaryDirectory() as tmpdir:
            config = make_minimal_config(tmpdir)
            runner = SimulationRunner(config, verbose=False)
            assert runner.world.rate_tracker is not None
            assert runner.world.ledger.rate_tracker is not None

    @patch("src.simulation.runner.load_agents")
    def test_scrip_never_resets(self, mock_load: MagicMock) -> None:
        """Scrip never resets on advance_tick."""
        mock_load.return_value = []

        with tempfile.TemporaryDirectory() as tmpdir:
            config = make_minimal_config(tmpdir)
            runner = SimulationRunner(config, verbose=False)

            # Create a test principal directly (Plan #299: no legacy agent loading)
            runner.world.ledger.create_principal("test_agent", starting_scrip=100)

            # Spend some scrip
            runner.world.ledger.deduct_scrip("test_agent", 30)
            assert runner.world.ledger.get_scrip("test_agent") == 70

            # Advance tick
            runner.world.advance_tick()

            # Scrip should remain at 70 (never resets)
            assert runner.world.ledger.get_scrip("test_agent") == 70


class TestAutonomousMode:
    """Tests for autonomous agent loop execution (INT-003)."""

    @patch("src.simulation.runner.load_agents")
    def test_autonomous_mode_always_enabled(self, mock_load: MagicMock) -> None:
        """Autonomous mode is always enabled (Plan #102: tick-based mode removed)."""
        mock_load.return_value = []

        with tempfile.TemporaryDirectory() as tmpdir:
            config = make_minimal_config(tmpdir)
            runner = SimulationRunner(config, verbose=False)

            # Plan #102: Autonomous mode is always used, loop_manager always created
            assert runner.world.loop_manager is not None

    @patch("src.simulation.runner.load_agents")
    def test_rate_tracker_always_created(
        self, mock_load: MagicMock
    ) -> None:
        """RateTracker is always created (Plan #247)."""
        mock_load.return_value = []

        with tempfile.TemporaryDirectory() as tmpdir:
            config = make_minimal_config(tmpdir)
            runner = SimulationRunner(config, verbose=False)

            # Plan #247: RateTracker is always created
            assert runner.world.rate_tracker is not None
            assert runner.world.loop_manager is not None

    @patch("src.simulation.runner.load_agents")
    def test_rate_tracker_uses_config_values(
        self, mock_load: MagicMock
    ) -> None:
        """RateTracker uses config values when provided."""
        mock_load.return_value = []

        with tempfile.TemporaryDirectory() as tmpdir:
            config = make_minimal_config(tmpdir)
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
    def test_loop_manager_config_propagates(self, mock_load: MagicMock) -> None:
        """Loop manager config is set from execution config (Plan #299: no legacy agents)."""
        mock_load.return_value = []

        with tempfile.TemporaryDirectory() as tmpdir:
            config = make_minimal_config(tmpdir)
            config["execution"] = {
                "agent_loop": {
                    "min_loop_delay": 0.5,
                    "max_loop_delay": 20.0,
                    "resource_check_interval": 2.0,
                    "max_consecutive_errors": 10,
                    "resources_to_check": ["llm_calls", "bandwidth_bytes"],
                },
            }
            runner = SimulationRunner(config, verbose=False)

            # Config is stored but loops aren't created until runtime
            # (artifact loops discovered via ArtifactLoopManager.discover_loops())
            assert runner.world.loop_manager is not None
            # No legacy loops created
            assert runner.world.loop_manager.loop_count == 0

    @patch("src.simulation.runner.load_agents")
    def test_shutdown_stops_loops(self, mock_load: MagicMock) -> None:
        """shutdown() stops all agent loops."""
        mock_load.return_value = []

        with tempfile.TemporaryDirectory() as tmpdir:
            config = make_minimal_config(tmpdir)
            runner = SimulationRunner(config, verbose=False)

            # Should be able to call shutdown even when not running
            import asyncio
            asyncio.run(runner.shutdown())

            assert runner._running is False

    @patch("src.simulation.runner.load_agents")
    def test_world_loop_manager_always_created(
        self, mock_load: MagicMock
    ) -> None:
        """World.loop_manager is always created (Plan #102)."""
        mock_load.return_value = [
            {"id": "agent1", "starting_scrip": 100},
            {"id": "agent2", "starting_scrip": 100},
        ]

        with tempfile.TemporaryDirectory() as tmpdir:
            config = make_minimal_config(tmpdir)
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
    """Tests for Agent.alive property (Plan #299: legacy agents removed)."""

    @patch("src.simulation.runner.load_agents")
    def test_no_legacy_agents(self, mock_load: MagicMock) -> None:
        """No legacy agents are created (Plan #299)."""
        mock_load.return_value = []

        with tempfile.TemporaryDirectory() as tmpdir:
            config = make_minimal_config(tmpdir)
            runner = SimulationRunner(config, verbose=False)

            # No legacy agents - artifact loops handle agent behavior
            assert len(runner.agents) == 0

    @patch("src.simulation.runner.load_agents")
    def test_artifact_loops_discovered_at_runtime(self, mock_load: MagicMock) -> None:
        """Artifact loops are discovered during run(), not at init."""
        mock_load.return_value = []

        with tempfile.TemporaryDirectory() as tmpdir:
            config = make_minimal_config(tmpdir)
            runner = SimulationRunner(config, verbose=False)

            # ArtifactLoopManager exists but hasn't discovered loops yet
            assert runner.artifact_loop_manager is not None
            # Loops are discovered during _run_autonomous()
            assert runner.artifact_loop_manager.loop_count == 0


class TestBudgetExhaustion:
    """Tests for global budget exhaustion checks (critical bug fix)."""

    @patch("src.simulation.runner.load_agents")
    def test_budget_exhausted_flag(self, mock_load: MagicMock) -> None:
        """engine.is_budget_exhausted() returns True when budget exceeded."""
        mock_load.return_value = []

        with tempfile.TemporaryDirectory() as tmpdir:
            config = make_minimal_config(tmpdir)
            config["budget"]["max_api_cost"] = 0.01  # Very low budget
            runner = SimulationRunner(config, verbose=False)

            # Initially not exhausted
            assert runner.engine.is_budget_exhausted() is False

            # Exhaust the budget
            runner.engine.track_api_cost(0.02)  # Over the $0.01 limit

            # Verify budget is exhausted
            assert runner.engine.is_budget_exhausted() is True

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


class TestRuntimeTimeout:
    """Tests for runtime timeout backstop."""

    @patch("src.simulation.runner.load_agents")
    def test_runtime_timeout_config_loaded(self, mock_load: MagicMock) -> None:
        """max_runtime_seconds is loaded from config."""
        mock_load.return_value = []

        with tempfile.TemporaryDirectory() as tmpdir:
            config = make_minimal_config(tmpdir)
            config["budget"]["max_runtime_seconds"] = 1800  # 30 minutes
            runner = SimulationRunner(config, verbose=False)

            assert runner.max_runtime_seconds == 1800

    @patch("src.simulation.runner.load_agents")
    def test_runtime_timeout_default(self, mock_load: MagicMock) -> None:
        """max_runtime_seconds defaults to 3600 (1 hour) if not specified."""
        mock_load.return_value = []

        with tempfile.TemporaryDirectory() as tmpdir:
            config = make_minimal_config(tmpdir)
            del config["budget"]  # Remove budget config entirely
            runner = SimulationRunner(config, verbose=False)

            # Default should be 3600 (1 hour)
            assert runner.max_runtime_seconds == 3600

    @patch("src.simulation.runner.load_agents")
    def test_is_runtime_exceeded_before_start(self, mock_load: MagicMock) -> None:
        """is_runtime_exceeded returns False before run starts."""
        mock_load.return_value = []

        with tempfile.TemporaryDirectory() as tmpdir:
            config = make_minimal_config(tmpdir)
            config["budget"]["max_runtime_seconds"] = 10
            runner = SimulationRunner(config, verbose=False)

            # Before run(), _run_start_time is None
            assert runner._run_start_time is None
            assert runner.is_runtime_exceeded() is False

    @patch("src.simulation.runner.load_agents")
    def test_is_runtime_exceeded_unlimited(self, mock_load: MagicMock) -> None:
        """is_runtime_exceeded returns False when max_runtime_seconds is 0."""
        mock_load.return_value = []

        with tempfile.TemporaryDirectory() as tmpdir:
            config = make_minimal_config(tmpdir)
            config["budget"]["max_runtime_seconds"] = 0  # Unlimited
            runner = SimulationRunner(config, verbose=False)

            # Even if we fake a start time far in the past, should return False for unlimited
            import time
            runner._run_start_time = time.time() - 10000  # 10000 seconds ago
            assert runner.is_runtime_exceeded() is False

    @patch("src.simulation.runner.load_agents")
    def test_autonomous_loop_checks_runtime(self, mock_load: MagicMock) -> None:
        """_run_autonomous exits when runtime exceeded."""
        mock_load.return_value = []

        with tempfile.TemporaryDirectory() as tmpdir:
            config = make_minimal_config(tmpdir)
            config["budget"]["max_runtime_seconds"] = 1  # 1 second timeout
            config["budget"]["max_api_cost"] = 1000  # High budget so it doesn't trigger
            runner = SimulationRunner(config, verbose=False)

            import asyncio
            import time

            start = time.time()
            # Run with long duration - should exit early due to runtime timeout
            asyncio.run(runner.run(duration=10.0))
            elapsed = time.time() - start

            # Should exit after ~1-2 seconds (runtime timeout), not 10 seconds
            assert elapsed < 5.0, f"Expected exit due to runtime timeout, took {elapsed}s"

    @patch("src.simulation.runner.load_agents")
    def test_status_includes_runtime_limit(self, mock_load: MagicMock) -> None:
        """get_status includes max_runtime_seconds."""
        mock_load.return_value = []

        with tempfile.TemporaryDirectory() as tmpdir:
            config = make_minimal_config(tmpdir)
            config["budget"]["max_runtime_seconds"] = 7200
            runner = SimulationRunner(config, verbose=False)

            status = runner.get_status()
            assert "max_runtime_seconds" in status
            assert status["max_runtime_seconds"] == 7200


class TestCostCallbackWiring:
    """Tests for cost callback wiring (Plan #153)."""

    @patch("src.simulation.runner.load_agents")
    def test_mint_auction_cost_callbacks_wired(self, mock_load: MagicMock) -> None:
        """Kernel mint auction has cost callbacks wired."""
        mock_load.return_value = []

        with tempfile.TemporaryDirectory() as tmpdir:
            config = make_minimal_config(tmpdir)
            runner = SimulationRunner(config, verbose=False)

            # Check mint auction has callbacks set
            assert runner.world.mint_auction._is_budget_exhausted is not None
            assert runner.world.mint_auction._track_api_cost is not None

    @patch("src.simulation.runner.load_agents")
    def test_mint_auction_callback_tracks_cost(self, mock_load: MagicMock) -> None:
        """Mint auction cost callback updates engine cumulative cost."""
        mock_load.return_value = []

        with tempfile.TemporaryDirectory() as tmpdir:
            config = make_minimal_config(tmpdir)
            runner = SimulationRunner(config, verbose=False)

            initial_cost = runner.engine.cumulative_api_cost

            # Manually trigger cost callback (simulating what scorer does)
            runner.world.mint_auction._track_api_cost(0.05)

            assert runner.engine.cumulative_api_cost == initial_cost + 0.05

    @patch("src.simulation.runner.load_agents")
    def test_budget_exhausted_callback_returns_engine_state(
        self, mock_load: MagicMock
    ) -> None:
        """Budget exhausted callback returns engine's budget state."""
        mock_load.return_value = []

        with tempfile.TemporaryDirectory() as tmpdir:
            config = make_minimal_config(tmpdir)
            config["budget"]["max_api_cost"] = 0.10  # Low budget
            runner = SimulationRunner(config, verbose=False)

            # Initially budget not exhausted
            assert runner.world.mint_auction._is_budget_exhausted() is False

            # Exhaust budget
            runner.engine.track_api_cost(0.15)

            # Now callback should return True
            assert runner.world.mint_auction._is_budget_exhausted() is True
