"""E2E smoke tests - verify basic simulation functionality.

These tests ensure the simulation runs without errors in
autonomous mode. Uses mocked LLM calls.

Plan #109: Updated for autonomous-only execution (tick mode removed in Plan #102).

Run with:
    pytest tests/e2e/test_smoke.py -v
"""

from __future__ import annotations

from typing import Any
from unittest.mock import MagicMock

import pytest

from src.simulation.runner import SimulationRunner
from src.world import World

# Default test duration in seconds (short for fast tests)
TEST_DURATION = 0.5


class TestSimulationSmoke:
    """Smoke tests for simulation execution."""

    def test_simulation_starts(
        self,
        mock_llm: MagicMock,
        e2e_config: dict[str, Any],
    ) -> None:
        """Simulation runner can be instantiated."""
        runner = SimulationRunner(e2e_config, verbose=False)
        assert runner is not None
        assert runner.world is not None

    def test_simulation_completes(
        self,
        mock_llm: MagicMock,
        e2e_config: dict[str, Any],
    ) -> None:
        """Simulation completes without error."""
        runner = SimulationRunner(e2e_config, verbose=False)
        world = runner.run_sync(duration=TEST_DURATION)

        # Verify simulation completed
        assert isinstance(world, World)

    def test_simulation_creates_artifacts(
        self,
        mock_llm: MagicMock,
        e2e_config: dict[str, Any],
    ) -> None:
        """Simulation has genesis artifacts."""
        runner = SimulationRunner(e2e_config, verbose=False)
        world = runner.run_sync(duration=TEST_DURATION)

        # Genesis artifacts should exist (stored in genesis_artifacts dict)
        assert len(world.genesis_artifacts) > 0

        # Check for expected genesis artifacts
        assert "genesis_ledger" in world.genesis_artifacts

    def test_simulation_tracks_balances(
        self,
        mock_llm: MagicMock,
        e2e_config: dict[str, Any],
    ) -> None:
        """Simulation tracks agent balances."""
        # Use max_agents=1 to limit to single agent for predictable test
        runner = SimulationRunner(e2e_config, max_agents=1, verbose=False)
        world = runner.run_sync(duration=TEST_DURATION)

        # At least one agent should have balance tracked
        balances = world.ledger.get_all_scrip()
        assert len(balances) >= 1

        # First agent should have non-negative balance
        first_agent_balance = list(balances.values())[0]
        assert first_agent_balance >= 0


class TestAutonomousModeSmoke:
    """Smoke tests for autonomous execution mode."""

    @pytest.mark.asyncio
    async def test_autonomous_mode_starts(
        self,
        mock_llm: MagicMock,
        e2e_autonomous_config: dict[str, Any],
    ) -> None:
        """Autonomous mode simulation can start."""
        runner = SimulationRunner(e2e_autonomous_config, verbose=False)
        assert runner.use_autonomous_loops is True

    @pytest.mark.asyncio
    async def test_autonomous_mode_runs_briefly(
        self,
        mock_llm: MagicMock,
        e2e_autonomous_config: dict[str, Any],
    ) -> None:
        """Autonomous mode runs for a short duration without error."""
        runner = SimulationRunner(e2e_autonomous_config, verbose=False)

        # Run for 0.5 seconds (very short)
        world = await runner.run(duration=0.5)

        assert isinstance(world, World)
        # In autonomous mode, tick may stay at 0 (ticks aren't used)
        # Just verify no crash


class TestIntegrationSmoke:
    """Integration smoke tests."""

    def test_world_state_summary(
        self,
        mock_llm: MagicMock,
        e2e_config: dict[str, Any],
    ) -> None:
        """World state summary can be retrieved."""
        runner = SimulationRunner(e2e_config, verbose=False)
        runner.run_sync(duration=TEST_DURATION)

        state = runner.world.get_state_summary()

        assert "tick" in state  # Still present for backward compat
        assert "balances" in state
        assert "artifacts" in state

    def test_no_unhandled_exceptions(
        self,
        mock_llm: MagicMock,
        e2e_config: dict[str, Any],
    ) -> None:
        """Simulation completes without unhandled exceptions.

        This is the most basic sanity check - the simulation
        should run to completion without crashing.
        """
        runner = SimulationRunner(e2e_config, verbose=False)

        # This should not raise
        world = runner.run_sync(duration=TEST_DURATION)

        # Verify we got a valid result
        assert world is not None
        assert isinstance(world, World)
