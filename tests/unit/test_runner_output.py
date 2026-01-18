"""Unit tests for simulation runner output messaging.

Tests for Plan #73: Fix Simulation Output Messaging
- Verifies mode-appropriate timing output (autonomous vs tick-based)
- Verifies correct LLM terminology (no legacy "compute")
"""

from __future__ import annotations

import io
import sys
from typing import Any
from unittest.mock import patch, MagicMock

import pytest


@pytest.mark.feature("runner_output")
class TestRunnerOutputMode:
    """Test that output shows correct mode information."""

    def _create_mock_runner(
        self,
        use_autonomous_loops: bool = False,
        max_ticks: int = 100,
        max_api_cost: float = 1.0,
        rate_limiting_enabled: bool = False,
    ) -> Any:
        """Create a mock runner for testing output."""
        # mock-ok: Testing output formatting, not actual runner behavior
        runner = MagicMock()
        runner.verbose = True
        runner.use_autonomous_loops = use_autonomous_loops
        runner.config = {
            "rate_limiting": {
                "enabled": rate_limiting_enabled,
                "window_seconds": 60.0,
                "resources": {
                    "llm_tokens": {"max_per_window": 10000},
                },
            },
        }

        # Mock world
        runner.world = MagicMock()
        runner.world.max_ticks = max_ticks
        runner.world.ledger = MagicMock()
        runner.world.ledger.get_all_scrip.return_value = {"alice": 100, "bob": 100}

        # Mock engine
        runner.engine = MagicMock()
        runner.engine.max_api_cost = max_api_cost

        # Mock agents
        runner.agents = [MagicMock(agent_id="alice"), MagicMock(agent_id="bob")]

        return runner

    def test_autonomous_output_no_ticks(self) -> None:
        """Autonomous mode output does NOT show 'Max ticks'."""
        from src.simulation.runner import SimulationRunner

        runner = self._create_mock_runner(use_autonomous_loops=True)

        # Capture stdout
        captured = io.StringIO()
        with patch.object(sys, "stdout", captured):
            # Call the method directly
            SimulationRunner._print_startup_info(runner)

        output = captured.getvalue()

        # Should show autonomous mode
        assert "Autonomous" in output
        assert "agents run independently" in output

        # Should NOT show "Max ticks"
        assert "Max ticks" not in output
        assert "max ticks" not in output

    def test_tick_mode_shows_ticks(self) -> None:
        """Tick-based mode shows 'max ticks' information."""
        from src.simulation.runner import SimulationRunner

        runner = self._create_mock_runner(use_autonomous_loops=False, max_ticks=50)

        # Capture stdout
        captured = io.StringIO()
        with patch.object(sys, "stdout", captured):
            SimulationRunner._print_startup_info(runner)

        output = captured.getvalue()

        # Should show tick mode with max ticks
        assert "Tick-based" in output
        assert "max ticks: 50" in output

        # Should NOT show autonomous mode
        assert "Autonomous" not in output


@pytest.mark.feature("runner_output")
class TestRunnerOutputTerminology:
    """Test that output uses correct LLM terminology."""

    def _create_mock_runner(self) -> Any:
        """Create a mock runner for testing output."""
        # mock-ok: Testing output formatting, not actual runner behavior
        runner = MagicMock()
        runner.verbose = True
        runner.use_autonomous_loops = False
        runner.config = {
            "rate_limiting": {
                "enabled": True,
                "window_seconds": 60.0,
                "resources": {
                    "llm_tokens": {"max_per_window": 5000},
                },
            },
        }

        # Mock world
        runner.world = MagicMock()
        runner.world.max_ticks = 100
        runner.world.ledger = MagicMock()
        runner.world.ledger.get_all_scrip.return_value = {"alice": 100}

        # Mock engine
        runner.engine = MagicMock()
        runner.engine.max_api_cost = 5.0

        # Mock agents
        runner.agents = [MagicMock(agent_id="alice")]

        return runner

    def test_output_uses_llm_terminology(self) -> None:
        """Output uses 'LLM' not legacy 'compute' terminology."""
        from src.simulation.runner import SimulationRunner

        runner = self._create_mock_runner()

        # Capture stdout
        captured = io.StringIO()
        with patch.object(sys, "stdout", captured):
            SimulationRunner._print_startup_info(runner)

        output = captured.getvalue()

        # Should use LLM terminology
        assert "LLM budget" in output
        assert "LLM rate limit" in output

        # Should NOT use legacy "compute" terminology
        assert "compute" not in output.lower()
        assert "Compute" not in output
        assert "Token rates" not in output  # Old format
        assert "compute/1K" not in output

    def test_shows_rate_limit_when_enabled(self) -> None:
        """Rate limit is shown when rate_limiting is enabled."""
        from src.simulation.runner import SimulationRunner

        runner = self._create_mock_runner()

        # Capture stdout
        captured = io.StringIO()
        with patch.object(sys, "stdout", captured):
            SimulationRunner._print_startup_info(runner)

        output = captured.getvalue()

        # Should show rate limit
        assert "LLM rate limit" in output
        assert "5,000" in output  # Formatted with commas
        assert "60" in output  # Window seconds

    def test_hides_rate_limit_when_unlimited(self) -> None:
        """Rate limit is NOT shown when effectively unlimited (>1 billion)."""
        from src.simulation.runner import SimulationRunner

        # mock-ok: Testing output formatting, not actual runner behavior
        runner = MagicMock()
        runner.verbose = True
        runner.use_autonomous_loops = False
        runner.config = {
            "rate_limiting": {
                "enabled": True,
                "window_seconds": 60.0,
                "resources": {
                    "llm_tokens": {"max_per_window": 1_000_000_000},  # Unlimited
                },
            },
        }
        runner.world = MagicMock()
        runner.world.max_ticks = 100
        runner.world.ledger = MagicMock()
        runner.world.ledger.get_all_scrip.return_value = {}
        runner.engine = MagicMock()
        runner.engine.max_api_cost = 0
        runner.agents = []

        # Capture stdout
        captured = io.StringIO()
        with patch.object(sys, "stdout", captured):
            SimulationRunner._print_startup_info(runner)

        output = captured.getvalue()

        # Should NOT show rate limit when unlimited
        assert "LLM rate limit" not in output


@pytest.mark.feature("runner_output")
class TestDatetimeDeprecation:
    """Test that datetime.utcnow() has been replaced."""

    def test_no_utcnow_in_artifacts(self) -> None:
        """src/world/artifacts.py should not use datetime.utcnow()."""
        import src.world.artifacts as artifacts_module
        import inspect

        source = inspect.getsource(artifacts_module)
        assert "utcnow()" not in source

    def test_no_utcnow_in_logger(self) -> None:
        """src/world/logger.py should not use datetime.utcnow()."""
        import src.world.logger as logger_module
        import inspect

        source = inspect.getsource(logger_module)
        assert "utcnow()" not in source

    def test_no_utcnow_in_invocation_registry(self) -> None:
        """src/world/invocation_registry.py should not use datetime.utcnow()."""
        import src.world.invocation_registry as registry_module
        import inspect

        source = inspect.getsource(registry_module)
        assert "utcnow()" not in source

    def test_no_utcnow_in_memory(self) -> None:
        """src/agents/memory.py should not use datetime.utcnow()."""
        import src.agents.memory as memory_module
        import inspect

        source = inspect.getsource(memory_module)
        assert "utcnow()" not in source
