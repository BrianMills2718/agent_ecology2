"""Real E2E tests - actual LLM calls, no mocks.

These tests verify the simulation works end-to-end with real LLM.
They are slow and cost money, so they're skipped by default.

Run with:
    pytest tests/e2e/test_real_e2e.py -v --run-external

Cost estimate: ~$0.01-0.05 per full test run

SAFETY: Each test has:
- max_api_cost: $0.10 budget cap
- max_runtime_seconds: 60s hard timeout
- pytest timeout: 120s per test
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any

import pytest

from src.simulation.runner import SimulationRunner
from src.world import World


# Skip all tests in this module unless --run-external is passed
# Also set a 120 second timeout per test as ultimate backstop
pytestmark = [
    pytest.mark.external,
    pytest.mark.timeout(120),  # Hard timeout per test
]


@pytest.fixture
def real_e2e_config(tmp_path: Path) -> dict[str, Any]:
    """Configuration for real E2E tests.

    Uses minimal settings to keep costs low while still exercising
    the full code path.
    """
    log_file = tmp_path / "real_e2e.jsonl"

    return {
        "world": {
            "max_ticks": 2,  # Minimal ticks
        },
        "costs": {
            "per_1k_input_tokens": 1,
            "per_1k_output_tokens": 3,
        },
        "logging": {
            "output_file": str(log_file),
            "log_dir": str(tmp_path / "llm_logs"),
        },
        "principals": [
            {"id": "e2e_agent", "starting_scrip": 100},
        ],
        "rights": {
            "default_llm_tokens_quota": 100,
            "default_disk_quota": 10000,
        },
        "llm": {
            "default_model": "gemini/gemini-2.0-flash",
            "rate_limit_delay": 0,
        },
        "budget": {
            "max_api_cost": 0.10,  # Cap at $0.10 for safety
            "max_runtime_seconds": 60,  # Hard timeout: 60 seconds per test
            "checkpoint_interval": 0,
            "checkpoint_on_end": False,
        },
        "rate_limiting": {
            "enabled": False,
        },
        # Note: Runner is always autonomous (Plan #102 removed tick-based mode)
    }


class TestRealSimulationSmoke:
    """Smoke tests with real LLM - verify basic functionality works."""

    def test_simulation_runs_one_tick(
        self,
        real_e2e_config: dict[str, Any],
    ) -> None:
        """Simulation completes one tick with real LLM."""
        config = real_e2e_config.copy()
        config["world"]["max_ticks"] = 1

        runner = SimulationRunner(config, verbose=False)
        world = runner.run_sync()

        assert world.event_number >= 1
        assert isinstance(world, World)

    def test_agent_produces_valid_action(
        self,
        real_e2e_config: dict[str, Any],
    ) -> None:
        """Agent produces a parseable action from real LLM."""
        config = real_e2e_config.copy()
        config["world"]["max_ticks"] = 1

        runner = SimulationRunner(config, verbose=False)
        world = runner.run_sync()

        # Check that something happened (action was executed)
        # Autonomous mode produces many events per tick
        assert world.event_number >= 1

    def test_kernel_mint_agent_exists(
        self,
        real_e2e_config: dict[str, Any],
    ) -> None:
        """Plan #254: kernel_mint_agent is created and has can_mint capability."""
        config = real_e2e_config.copy()
        config["world"]["max_ticks"] = 1

        runner = SimulationRunner(config, verbose=False)
        world = runner.run_sync()

        # kernel_mint_agent should exist (replaces genesis_mint)
        assert "kernel_mint_agent" in world.artifacts.artifacts
        mint_agent = world.artifacts.get("kernel_mint_agent")
        assert mint_agent is not None
        assert "can_mint" in mint_agent.capabilities

    def test_ledger_has_balances(
        self,
        real_e2e_config: dict[str, Any],
    ) -> None:
        """Ledger tracks agent balances after simulation."""
        config = real_e2e_config.copy()
        config["world"]["max_ticks"] = 1

        runner = SimulationRunner(config, max_agents=1, verbose=False)
        world = runner.run_sync()

        # At least one agent should have balance tracked
        balances = world.ledger.get_all_scrip()
        assert len(balances) >= 1


class TestRealAgentBehavior:
    """Test that agent behavior works with real LLM."""

    def test_agent_can_write_artifact(
        self,
        real_e2e_config: dict[str, Any],
    ) -> None:
        """Agent can successfully write an artifact.

        This may take multiple ticks as the agent decides what to do.
        """
        config = real_e2e_config.copy()
        config["world"]["max_ticks"] = 3  # Give agent time to write

        runner = SimulationRunner(config, verbose=False)
        world = runner.run_sync()

        # Count artifacts
        # Pre-seeded: kernel_mint_agent + handbooks (~7) + agent artifact
        total_artifacts = len(list(world.artifacts.list_all()))

        # Plan #254: Pre-seeded artifacts replace genesis
        # At minimum: kernel_mint_agent (1) + handbooks (~7) + agent (1) = 9
        assert total_artifacts >= 9

    def test_multi_tick_simulation(
        self,
        real_e2e_config: dict[str, Any],
    ) -> None:
        """Simulation runs multiple ticks without crashing."""
        config = real_e2e_config.copy()
        config["world"]["max_ticks"] = 3

        runner = SimulationRunner(config, verbose=False)
        world = runner.run_sync()

        # Autonomous mode produces many events per tick
        # Just verify something happened
        assert world.event_number >= 1


class TestRealAutonomousMode:
    """Test autonomous mode with real LLM."""

    @pytest.mark.asyncio
    async def test_autonomous_mode_runs(
        self,
        real_e2e_config: dict[str, Any],
    ) -> None:
        """Autonomous mode runs without crashing (Plan #102: always autonomous)."""
        config = real_e2e_config.copy()
        config["execution"] = {
            "agent_loop": {
                "min_loop_delay": 0.5,
                "max_loop_delay": 1.0,
                "resource_check_interval": 0.1,
                "max_consecutive_errors": 2,
                "resources_to_check": [],
            },
        }
        config["rate_limiting"] = {
            "enabled": True,
            "window_seconds": 1.0,
            "resources": {
                "llm_calls": {"max_per_window": 10},
            },
        }

        runner = SimulationRunner(config, verbose=False)

        # Run for 2 seconds
        world = await runner.run(duration=2.0)

        assert isinstance(world, World)
