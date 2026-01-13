"""Feature tests for rate_limiting - maps to features/rate_limiting.yaml acceptance criteria.

Each test corresponds to an AC-ID in the feature definition.
"""

from __future__ import annotations

import time
import pytest

from src.world.rate_tracker import RateTracker


class TestRateLimitingFeature:
    """Tests mapping to features/rate_limiting.yaml acceptance criteria."""

    # AC-1: Consume within limit (happy_path)
    def test_ac_1_consume_within_limit(self) -> None:
        """AC-1: Consume within limit.

        Given:
          - Resource 'llm_calls' has limit of 100 per 60-second window
          - Agent has used 50 calls in current window
        When: Agent consumes 10 more calls
        Then:
          - Consume succeeds
          - Usage increases to 60
          - Remaining capacity is 40
        """
        tracker = RateTracker(window_seconds=60.0)
        tracker.configure_limit("llm_calls", max_per_window=100.0)

        # Agent has used 50 calls
        tracker.consume("agent_1", "llm_calls", 50.0)
        assert tracker.get_usage("agent_1", "llm_calls") == 50.0

        # Consume 10 more
        result = tracker.consume("agent_1", "llm_calls", 10.0)

        assert result is True
        assert tracker.get_usage("agent_1", "llm_calls") == 60.0
        assert tracker.get_remaining("agent_1", "llm_calls") == 40.0

    # AC-2: Consume fails when over limit (error_case)
    def test_ac_2_consume_fails_over_limit(self) -> None:
        """AC-2: Consume fails when over limit.

        Given:
          - Resource has limit of 100 per window
          - Agent has used 95 calls
        When: Agent tries to consume 10 calls
        Then:
          - Consume fails (returns False)
          - Usage remains at 95
          - No partial consumption
        """
        tracker = RateTracker(window_seconds=60.0)
        tracker.configure_limit("llm_calls", max_per_window=100.0)

        # Agent has used 95 calls
        tracker.consume("agent_1", "llm_calls", 95.0)

        # Try to consume 10 more (would exceed limit)
        result = tracker.consume("agent_1", "llm_calls", 10.0)

        assert result is False
        assert tracker.get_usage("agent_1", "llm_calls") == 95.0  # Unchanged

    # AC-3: Old records expire after window (happy_path)
    def test_ac_3_old_records_expire(self) -> None:
        """AC-3: Old records expire after window.

        Given:
          - Agent consumed 100 calls 61 seconds ago
          - Window is 60 seconds
        When: Agent checks capacity
        Then:
          - Old records have expired
          - Capacity is fully available (100)
          - Agent can consume again

        Note: This test uses a very short window for fast execution.
        """
        # Use a very short window to test expiration quickly
        tracker = RateTracker(window_seconds=0.1)  # 100ms window
        tracker.configure_limit("llm_calls", max_per_window=100.0)

        # Consume to limit
        tracker.consume("agent_1", "llm_calls", 100.0)
        assert tracker.get_usage("agent_1", "llm_calls") == 100.0
        assert tracker.get_remaining("agent_1", "llm_calls") == 0.0

        # Wait for window to expire
        time.sleep(0.15)  # 150ms - beyond the 100ms window

        # Old records should have expired
        usage = tracker.get_usage("agent_1", "llm_calls")
        assert usage == 0.0  # All records expired

        remaining = tracker.get_remaining("agent_1", "llm_calls")
        assert remaining == 100.0  # Full capacity available

        # Agent can consume again
        result = tracker.consume("agent_1", "llm_calls", 50.0)
        assert result is True

    # AC-4: Wait for capacity with timeout (happy_path)
    @pytest.mark.asyncio
    async def test_ac_4_wait_for_capacity(self) -> None:
        """AC-4: Wait for capacity with timeout.

        Given:
          - Agent is at limit (100/100 used)
          - Records will expire in 5 seconds
        When: Agent calls wait_for_capacity with 10-second timeout
        Then:
          - Waits until records expire
          - Returns True when capacity available
          - Agent can then consume

        Note: This test is simplified to avoid long waits.
        """
        tracker = RateTracker(window_seconds=0.5)  # Short window for testing
        tracker.configure_limit("llm_calls", max_per_window=100.0)

        # Consume to limit
        tracker.consume("agent_1", "llm_calls", 100.0)

        # Wait for capacity (records expire after 0.5s)
        result = await tracker.wait_for_capacity(
            "agent_1", "llm_calls", amount=50.0, timeout=2.0
        )

        assert result is True
        assert tracker.has_capacity("agent_1", "llm_calls", 50.0) is True

    # AC-5: Wait for capacity times out (error_case)
    @pytest.mark.asyncio
    async def test_ac_5_wait_times_out(self) -> None:
        """AC-5: Wait for capacity times out.

        Given:
          - Agent is at limit
          - Records won't expire within timeout period
        When: Agent calls wait_for_capacity with 1-second timeout
        Then:
          - Wait times out
          - Returns False
          - No consumption occurs
        """
        tracker = RateTracker(window_seconds=60.0)  # Long window
        tracker.configure_limit("llm_calls", max_per_window=100.0)

        # Consume to limit
        tracker.consume("agent_1", "llm_calls", 100.0)

        # Wait with short timeout (records won't expire in time)
        result = await tracker.wait_for_capacity(
            "agent_1", "llm_calls", amount=50.0, timeout=0.1  # Very short timeout
        )

        assert result is False
        assert tracker.get_usage("agent_1", "llm_calls") == 100.0  # Unchanged

    # AC-6: Independent limits per agent (happy_path)
    def test_ac_6_independent_limits_per_agent(self) -> None:
        """AC-6: Independent limits per agent.

        Given:
          - Agent A has used 100 calls (at limit)
          - Agent B has used 0 calls
        When: Agent B tries to consume 50 calls
        Then:
          - Agent B succeeds
          - Agent A's limit is independent
          - Each agent tracked separately
        """
        tracker = RateTracker(window_seconds=60.0)
        tracker.configure_limit("llm_calls", max_per_window=100.0)

        # Agent A at limit
        tracker.consume("agent_a", "llm_calls", 100.0)
        assert tracker.get_usage("agent_a", "llm_calls") == 100.0
        assert tracker.has_capacity("agent_a", "llm_calls", 1.0) is False

        # Agent B has full capacity
        assert tracker.get_usage("agent_b", "llm_calls") == 0.0

        # Agent B can consume
        result = tracker.consume("agent_b", "llm_calls", 50.0)

        assert result is True
        assert tracker.get_usage("agent_b", "llm_calls") == 50.0
        assert tracker.get_usage("agent_a", "llm_calls") == 100.0  # Unchanged


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
        # Don't configure a limit

        # Should be able to consume unlimited amounts
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
