"""Feature acceptance tests for rate_limiting - maps to acceptance_gates/rate_limiting.yaml.

Run with: pytest --feature rate_limiting tests/
"""

from __future__ import annotations

import time
import pytest

from src.world.rate_tracker import RateTracker


@pytest.mark.feature("rate_limiting")
class TestRateLimitingFeature:
    """Tests mapping to acceptance_gates/rate_limiting.yaml acceptance criteria."""

    # AC-1: Consume within limit (happy_path)
    def test_ac_1_consume_within_limit(self) -> None:
        """AC-1: Consume within limit."""
        tracker = RateTracker(window_seconds=60.0)
        tracker.configure_limit("llm_calls", max_per_window=100.0)

        tracker.consume("agent_1", "llm_calls", 50.0)
        assert tracker.get_usage("agent_1", "llm_calls") == 50.0

        result = tracker.consume("agent_1", "llm_calls", 10.0)

        assert result is True
        assert tracker.get_usage("agent_1", "llm_calls") == 60.0
        assert tracker.get_remaining("agent_1", "llm_calls") == 40.0

    # AC-2: Consume fails when over limit (error_case)
    def test_ac_2_consume_fails_over_limit(self) -> None:
        """AC-2: Consume fails when over limit."""
        tracker = RateTracker(window_seconds=60.0)
        tracker.configure_limit("llm_calls", max_per_window=100.0)

        tracker.consume("agent_1", "llm_calls", 95.0)
        result = tracker.consume("agent_1", "llm_calls", 10.0)

        assert result is False
        assert tracker.get_usage("agent_1", "llm_calls") == 95.0

    # AC-3: Old records expire after window (happy_path)
    def test_ac_3_old_records_expire(self) -> None:
        """AC-3: Old records expire after window."""
        tracker = RateTracker(window_seconds=0.1)
        tracker.configure_limit("llm_calls", max_per_window=100.0)

        tracker.consume("agent_1", "llm_calls", 100.0)
        assert tracker.get_usage("agent_1", "llm_calls") == 100.0

        time.sleep(0.15)

        usage = tracker.get_usage("agent_1", "llm_calls")
        assert usage == 0.0

        result = tracker.consume("agent_1", "llm_calls", 50.0)
        assert result is True

    # AC-4: Wait for capacity with timeout (happy_path)
    @pytest.mark.asyncio
    async def test_ac_4_wait_for_capacity(self) -> None:
        """AC-4: Wait for capacity with timeout."""
        tracker = RateTracker(window_seconds=0.5)
        tracker.configure_limit("llm_calls", max_per_window=100.0)

        tracker.consume("agent_1", "llm_calls", 100.0)

        result = await tracker.wait_for_capacity(
            "agent_1", "llm_calls", amount=50.0, timeout=2.0
        )

        assert result is True
        assert tracker.has_capacity("agent_1", "llm_calls", 50.0) is True

    # AC-5: Wait for capacity times out (error_case)
    @pytest.mark.asyncio
    async def test_ac_5_wait_times_out(self) -> None:
        """AC-5: Wait for capacity times out."""
        tracker = RateTracker(window_seconds=60.0)
        tracker.configure_limit("llm_calls", max_per_window=100.0)

        tracker.consume("agent_1", "llm_calls", 100.0)

        result = await tracker.wait_for_capacity(
            "agent_1", "llm_calls", amount=50.0, timeout=0.1
        )

        assert result is False
        assert tracker.get_usage("agent_1", "llm_calls") == 100.0

    # AC-6: Independent limits per agent (happy_path)
    def test_ac_6_independent_limits_per_agent(self) -> None:
        """AC-6: Independent limits per agent."""
        tracker = RateTracker(window_seconds=60.0)
        tracker.configure_limit("llm_calls", max_per_window=100.0)

        tracker.consume("agent_a", "llm_calls", 100.0)
        assert tracker.has_capacity("agent_a", "llm_calls", 1.0) is False

        result = tracker.consume("agent_b", "llm_calls", 50.0)

        assert result is True
        assert tracker.get_usage("agent_b", "llm_calls") == 50.0
        assert tracker.get_usage("agent_a", "llm_calls") == 100.0


@pytest.mark.feature("rate_limiting")
class TestRateLimitingEdgeCases:
    """Additional edge case tests for rate limiting robustness."""

    def test_zero_amount_consume_succeeds(self) -> None:
        """Zero amount consumption always succeeds."""
        tracker = RateTracker(window_seconds=60.0)
        tracker.configure_limit("resource", max_per_window=100.0)

        result = tracker.consume("agent", "resource", 0.0)

        assert result is True
        assert tracker.get_usage("agent", "resource") == 0.0

    def test_negative_amount_fails(self) -> None:
        """Negative amount consumption fails."""
        tracker = RateTracker(window_seconds=60.0)
        tracker.configure_limit("resource", max_per_window=100.0)

        result = tracker.consume("agent", "resource", -10.0)

        assert result is False

    def test_unconfigured_resource_unlimited(self) -> None:
        """Unconfigured resources have unlimited capacity."""
        tracker = RateTracker(window_seconds=60.0)

        result = tracker.consume("agent", "unconfigured", 1000000.0)

        assert result is True
        assert tracker.get_limit("unconfigured") == float("inf")

    def test_exact_limit_consumption(self) -> None:
        """Can consume exactly up to the limit."""
        tracker = RateTracker(window_seconds=60.0)
        tracker.configure_limit("resource", max_per_window=100.0)

        # Consume exactly 100
        result = tracker.consume("agent", "resource", 100.0)

        assert result is True
        assert tracker.get_usage("agent", "resource") == 100.0
        assert tracker.get_remaining("agent", "resource") == 0.0
        assert tracker.has_capacity("agent", "resource", 0.01) is False
