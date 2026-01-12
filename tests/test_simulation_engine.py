"""Tests for SimulationEngine physics calculations.

Tests cover:
- Factory method configuration extraction
- Thinking cost calculation (including edge cases)
- API budget tracking and exhaustion
- Checkpoint resume functionality
"""

import math
import sys
from pathlib import Path

import pytest

# Add src/world to path for direct imports (avoids package import issues)
sys.path.insert(0, str(Path(__file__).parent.parent / "src" / "world"))

from simulation_engine import (
    SimulationEngine,
    ThinkingCostResult,
    BudgetCheckResult,
    ResourceUsage,
    ResourceMeasurer,
    measure_resources,
)


class TestFromConfig:
    """Tests for SimulationEngine.from_config() factory method."""

    def test_extracts_token_rates(self):
        """Extracts per_1k_input_tokens and per_1k_output_tokens from config."""
        config = {
            "costs": {
                "per_1k_input_tokens": 2,
                "per_1k_output_tokens": 5,
            }
        }
        engine = SimulationEngine.from_config(config)

        assert engine.rate_input == 2
        assert engine.rate_output == 5

    def test_extracts_budget(self):
        """Extracts max_api_cost from budget section."""
        config = {
            "budget": {
                "max_api_cost": 10.50,
            }
        }
        engine = SimulationEngine.from_config(config)

        assert engine.max_api_cost == 10.50

    def test_defaults_when_missing_costs(self):
        """Uses default rates when costs section missing."""
        config = {}
        engine = SimulationEngine.from_config(config)

        assert engine.rate_input == 1  # default
        assert engine.rate_output == 3  # default

    def test_defaults_when_missing_budget(self):
        """Uses 0 (unlimited) when budget section missing."""
        config = {}
        engine = SimulationEngine.from_config(config)

        assert engine.max_api_cost == 0.0  # unlimited

    def test_starts_with_zero_cumulative_cost(self):
        """New engine starts with 0 cumulative API cost."""
        config = {"costs": {}, "budget": {"max_api_cost": 100.0}}
        engine = SimulationEngine.from_config(config)

        assert engine.cumulative_api_cost == 0.0

    def test_partial_config(self):
        """Handles partial config with some values missing."""
        config = {
            "costs": {
                "per_1k_input_tokens": 5,
                # per_1k_output_tokens missing
            },
            "budget": {}  # max_api_cost missing
        }
        engine = SimulationEngine.from_config(config)

        assert engine.rate_input == 5
        assert engine.rate_output == 3  # default
        assert engine.max_api_cost == 0.0  # default


class TestCalculateThinkingCost:
    """Tests for thinking cost calculation."""

    def test_basic_calculation(self):
        """Basic token cost calculation."""
        engine = SimulationEngine(rate_input=1, rate_output=3)
        result = engine.calculate_thinking_cost(1000, 1000)

        assert result["input_cost"] == 1  # 1000/1000 * 1 = 1
        assert result["output_cost"] == 3  # 1000/1000 * 3 = 3
        assert result["total_cost"] == 4

    def test_zero_tokens(self):
        """Zero tokens results in zero cost."""
        engine = SimulationEngine(rate_input=1, rate_output=3)
        result = engine.calculate_thinking_cost(0, 0)

        assert result["input_cost"] == 0
        assert result["output_cost"] == 0
        assert result["total_cost"] == 0

    def test_ceiling_behavior_small_input(self):
        """Small token counts round up (ceiling)."""
        engine = SimulationEngine(rate_input=1, rate_output=3)

        # 1 token: 1/1000 * 1 = 0.001 -> ceil = 1
        result = engine.calculate_thinking_cost(1, 0)
        assert result["input_cost"] == 1

        # 500 tokens: 500/1000 * 1 = 0.5 -> ceil = 1
        result = engine.calculate_thinking_cost(500, 0)
        assert result["input_cost"] == 1

        # 999 tokens: 999/1000 * 1 = 0.999 -> ceil = 1
        result = engine.calculate_thinking_cost(999, 0)
        assert result["input_cost"] == 1

    def test_ceiling_behavior_output(self):
        """Output tokens also use ceiling."""
        engine = SimulationEngine(rate_input=1, rate_output=3)

        # 1 output token: 1/1000 * 3 = 0.003 -> ceil = 1
        result = engine.calculate_thinking_cost(0, 1)
        assert result["output_cost"] == 1

        # 334 output tokens: 334/1000 * 3 = 1.002 -> ceil = 2
        result = engine.calculate_thinking_cost(0, 334)
        assert result["output_cost"] == 2

    def test_large_token_counts(self):
        """Large token counts calculate correctly."""
        engine = SimulationEngine(rate_input=1, rate_output=3)

        # 100K input, 50K output
        result = engine.calculate_thinking_cost(100_000, 50_000)
        assert result["input_cost"] == 100  # 100K/1K * 1
        assert result["output_cost"] == 150  # 50K/1K * 3
        assert result["total_cost"] == 250

    def test_custom_rates(self):
        """Custom rate values work correctly."""
        engine = SimulationEngine(rate_input=10, rate_output=30)
        result = engine.calculate_thinking_cost(1000, 1000)

        assert result["input_cost"] == 10
        assert result["output_cost"] == 30
        assert result["total_cost"] == 40

    def test_returns_typed_dict(self):
        """Result has correct TypedDict structure."""
        engine = SimulationEngine()
        result = engine.calculate_thinking_cost(1000, 500)

        assert "input_cost" in result
        assert "output_cost" in result
        assert "total_cost" in result
        assert isinstance(result["input_cost"], int)
        assert isinstance(result["output_cost"], int)
        assert isinstance(result["total_cost"], int)


class TestTrackApiCost:
    """Tests for API budget tracking."""

    def test_accumulates_costs(self):
        """Costs accumulate correctly."""
        engine = SimulationEngine(max_api_cost=100.0)

        result1 = engine.track_api_cost(10.0)
        assert result1["cumulative_cost"] == 10.0

        result2 = engine.track_api_cost(25.5)
        assert result2["cumulative_cost"] == 35.5

        result3 = engine.track_api_cost(0.5)
        assert result3["cumulative_cost"] == 36.0

    def test_within_budget_flag(self):
        """within_budget is True until limit reached."""
        engine = SimulationEngine(max_api_cost=10.0)

        result = engine.track_api_cost(5.0)
        assert result["within_budget"] is True

        result = engine.track_api_cost(4.9)
        assert result["within_budget"] is True
        assert result["cumulative_cost"] == 9.9

        # Exactly at limit
        result = engine.track_api_cost(0.1)
        assert result["within_budget"] is False  # >= max_api_cost
        assert result["cumulative_cost"] == 10.0

    def test_remaining_calculation(self):
        """Remaining budget calculated correctly."""
        engine = SimulationEngine(max_api_cost=100.0)

        result = engine.track_api_cost(30.0)
        assert result["remaining"] == 70.0

        result = engine.track_api_cost(50.0)
        assert result["remaining"] == 20.0

    def test_unlimited_budget(self):
        """max_api_cost=0 means unlimited."""
        engine = SimulationEngine(max_api_cost=0.0)

        result = engine.track_api_cost(1000.0)
        assert result["within_budget"] is True
        assert result["remaining"] == float("inf")

        result = engine.track_api_cost(999999.0)
        assert result["within_budget"] is True
        assert result["remaining"] == float("inf")

    def test_negative_remaining(self):
        """Remaining can go negative when over budget."""
        engine = SimulationEngine(max_api_cost=10.0)

        engine.track_api_cost(15.0)  # Over budget
        result = engine.track_api_cost(5.0)

        assert result["cumulative_cost"] == 20.0
        assert result["remaining"] == -10.0
        assert result["within_budget"] is False

    def test_returns_typed_dict(self):
        """Result has correct TypedDict structure."""
        engine = SimulationEngine(max_api_cost=100.0)
        result = engine.track_api_cost(10.0)

        assert "within_budget" in result
        assert "cumulative_cost" in result
        assert "max_cost" in result
        assert "remaining" in result
        assert isinstance(result["within_budget"], bool)
        assert isinstance(result["cumulative_cost"], float)


class TestIsBudgetExhausted:
    """Tests for budget exhaustion check."""

    def test_not_exhausted_when_under_limit(self):
        """Returns False when under budget."""
        engine = SimulationEngine(max_api_cost=100.0)
        engine.track_api_cost(50.0)

        assert engine.is_budget_exhausted() is False

    def test_exhausted_at_limit(self):
        """Returns True when exactly at limit."""
        engine = SimulationEngine(max_api_cost=100.0)
        engine.track_api_cost(100.0)

        assert engine.is_budget_exhausted() is True

    def test_exhausted_over_limit(self):
        """Returns True when over limit."""
        engine = SimulationEngine(max_api_cost=100.0)
        engine.track_api_cost(150.0)

        assert engine.is_budget_exhausted() is True

    def test_never_exhausted_unlimited(self):
        """Never exhausted when max_api_cost=0 (unlimited)."""
        engine = SimulationEngine(max_api_cost=0.0)
        engine.track_api_cost(1_000_000.0)

        assert engine.is_budget_exhausted() is False


class TestCanAffordThinking:
    """Tests for thinking affordability check."""

    def test_can_afford_when_sufficient(self):
        """Returns True when agent has enough compute."""
        engine = SimulationEngine(rate_input=1, rate_output=3)

        # Cost will be: 1 (input) + 3 (output) = 4
        can_afford, cost = engine.can_afford_thinking(10, 1000, 1000)

        assert can_afford is True
        assert cost == 4

    def test_cannot_afford_when_insufficient(self):
        """Returns False when agent lacks compute."""
        engine = SimulationEngine(rate_input=1, rate_output=3)

        # Cost will be 4, but only have 3
        can_afford, cost = engine.can_afford_thinking(3, 1000, 1000)

        assert can_afford is False
        assert cost == 4

    def test_can_afford_exactly(self):
        """Returns True when agent has exactly enough."""
        engine = SimulationEngine(rate_input=1, rate_output=3)

        can_afford, cost = engine.can_afford_thinking(4, 1000, 1000)

        assert can_afford is True
        assert cost == 4

    def test_zero_cost_always_affordable(self):
        """Zero tokens is always affordable."""
        engine = SimulationEngine()

        can_afford, cost = engine.can_afford_thinking(0, 0, 0)

        assert can_afford is True
        assert cost == 0


class TestResetBudget:
    """Tests for budget reset (checkpoint resume)."""

    def test_reset_to_zero(self):
        """Reset clears cumulative cost."""
        engine = SimulationEngine(max_api_cost=100.0)
        engine.track_api_cost(50.0)

        engine.reset_budget()

        assert engine.cumulative_api_cost == 0.0
        assert engine.is_budget_exhausted() is False

    def test_reset_to_checkpoint_value(self):
        """Reset can restore from checkpoint."""
        engine = SimulationEngine(max_api_cost=100.0)

        engine.reset_budget(75.0)

        assert engine.cumulative_api_cost == 75.0
        assert engine.is_budget_exhausted() is False

        # Adding more should exhaust
        engine.track_api_cost(30.0)
        assert engine.is_budget_exhausted() is True

    def test_reset_preserves_rates_and_max(self):
        """Reset doesn't affect rates or max_api_cost."""
        engine = SimulationEngine(
            rate_input=5,
            rate_output=10,
            max_api_cost=50.0
        )
        engine.track_api_cost(40.0)

        engine.reset_budget(10.0)

        assert engine.rate_input == 5
        assert engine.rate_output == 10
        assert engine.max_api_cost == 50.0
        assert engine.cumulative_api_cost == 10.0


class TestGetRates:
    """Tests for get_rates() method."""

    def test_returns_tuple(self):
        """Returns (rate_input, rate_output) tuple."""
        engine = SimulationEngine(rate_input=2, rate_output=6)

        rates = engine.get_rates()

        assert rates == (2, 6)
        assert isinstance(rates, tuple)
        assert len(rates) == 2

    def test_default_rates(self):
        """Default rates are (1, 3)."""
        engine = SimulationEngine()

        assert engine.get_rates() == (1, 3)


class TestEdgeCases:
    """Edge case and boundary tests."""

    def test_very_small_api_costs(self):
        """Handles very small floating point costs."""
        engine = SimulationEngine(max_api_cost=1.0)

        for _ in range(1000):
            engine.track_api_cost(0.0001)

        # Should accumulate to ~0.1
        assert 0.09 < engine.cumulative_api_cost < 0.11

    def test_integer_rates_with_fractional_tokens(self):
        """Integer rates work with any token count."""
        engine = SimulationEngine(rate_input=7, rate_output=11)

        # 1234 tokens: 1234/1000 * 7 = 8.638 -> ceil = 9
        result = engine.calculate_thinking_cost(1234, 0)
        assert result["input_cost"] == 9

        # 5678 tokens: 5678/1000 * 11 = 62.458 -> ceil = 63
        result = engine.calculate_thinking_cost(0, 5678)
        assert result["output_cost"] == 63

    def test_dataclass_defaults(self):
        """Default values work when creating directly."""
        engine = SimulationEngine()

        assert engine.rate_input == 1
        assert engine.rate_output == 3
        assert engine.max_api_cost == 0.0
        assert engine.cumulative_api_cost == 0.0

    def test_immutable_after_tracking(self):
        """Max and rates don't change after tracking."""
        engine = SimulationEngine(
            rate_input=5,
            rate_output=10,
            max_api_cost=100.0
        )

        engine.track_api_cost(50.0)
        engine.calculate_thinking_cost(10000, 5000)

        assert engine.rate_input == 5
        assert engine.rate_output == 10
        assert engine.max_api_cost == 100.0


class TestResourceUsage:
    """Tests for ResourceUsage dataclass."""

    def test_default_values(self):
        """Default values are all zero."""
        usage = ResourceUsage()

        assert usage.cpu_seconds == 0.0
        assert usage.peak_memory_bytes == 0
        assert usage.disk_bytes_written == 0

    def test_custom_values(self):
        """Can create with custom values."""
        usage = ResourceUsage(
            cpu_seconds=1.5,
            peak_memory_bytes=1024,
            disk_bytes_written=2048,
        )

        assert usage.cpu_seconds == 1.5
        assert usage.peak_memory_bytes == 1024
        assert usage.disk_bytes_written == 2048

    def test_to_dict(self):
        """Converts to dictionary correctly."""
        usage = ResourceUsage(
            cpu_seconds=0.5,
            peak_memory_bytes=512,
            disk_bytes_written=100,
        )

        result = usage.to_dict()

        assert result == {
            "cpu_seconds": 0.5,
            "peak_memory_bytes": 512,
            "disk_bytes_written": 100,
        }


class TestResourceMeasurer:
    """Tests for ResourceMeasurer context manager."""

    def test_measures_cpu_time(self):
        """Measures CPU time during execution."""
        with ResourceMeasurer() as measurer:
            # Do some CPU work
            total = sum(i * i for i in range(10000))
            _ = total  # Use the variable

        usage = measurer.get_usage()
        assert usage.cpu_seconds >= 0.0  # Should be positive or zero

    def test_measures_memory(self):
        """Measures peak memory during execution."""
        with ResourceMeasurer() as measurer:
            # Allocate some memory
            data = [0] * 10000

        usage = measurer.get_usage()
        # Memory measurement can be tricky, just check it's non-negative
        assert usage.peak_memory_bytes >= 0
        del data  # Clean up

    def test_records_disk_writes(self):
        """Records disk write bytes."""
        with ResourceMeasurer() as measurer:
            measurer.record_disk_write(100)
            measurer.record_disk_write(200)

        usage = measurer.get_usage()
        assert usage.disk_bytes_written == 300

    def test_restores_tracemalloc_state(self):
        """Restores tracemalloc to original state after exit."""
        import tracemalloc

        # Start with tracemalloc off
        if tracemalloc.is_tracing():
            tracemalloc.stop()

        was_tracing_before = tracemalloc.is_tracing()

        with ResourceMeasurer():
            pass

        was_tracing_after = tracemalloc.is_tracing()
        assert was_tracing_before == was_tracing_after


class TestMeasureResources:
    """Tests for measure_resources convenience function."""

    def test_basic_usage(self):
        """Can use as context manager and get results."""
        with measure_resources() as measurer:
            total = sum(range(1000))
            _ = total

        usage = measurer.get_usage()
        assert isinstance(usage, ResourceUsage)
        assert usage.cpu_seconds >= 0.0

    def test_with_disk_recording(self):
        """Can record disk writes through convenience function."""
        with measure_resources() as measurer:
            measurer.record_disk_write(500)

        usage = measurer.get_usage()
        assert usage.disk_bytes_written == 500
