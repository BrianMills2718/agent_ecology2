"""Unit tests for the RateTracker class.

Tests rolling window rate limiting functionality including:
- Capacity checking and consumption
- Rolling window expiry
- Async waiting for capacity
- Time estimation
- Multiple agents and resources
"""

from __future__ import annotations

import asyncio
import time
from collections import deque
from typing import TYPE_CHECKING
from unittest.mock import patch

import pytest

from src.world.rate_tracker import RateTracker, UsageRecord


class TestUsageRecord:
    """Tests for the UsageRecord dataclass."""

    def test_usage_record_creation(self) -> None:
        """Verify UsageRecord stores timestamp and amount."""
        record = UsageRecord(timestamp=1000.0, amount=5.0)
        assert record.timestamp == 1000.0
        assert record.amount == 5.0


class TestRateTrackerInit:
    """Tests for RateTracker initialization."""

    def test_default_window(self) -> None:
        """Default window is 60 seconds."""
        tracker = RateTracker()
        assert tracker.window_seconds == 60.0

    def test_custom_window(self) -> None:
        """Can set custom window duration."""
        tracker = RateTracker(window_seconds=120.0)
        assert tracker.window_seconds == 120.0

    def test_empty_on_init(self) -> None:
        """Tracker starts with no usage records or limits."""
        tracker = RateTracker()
        assert tracker._usage == {}
        assert tracker._limits == {}


class TestConfigureLimit:
    """Tests for configure_limit method."""

    def test_configure_limit(self) -> None:
        """Can configure a resource limit."""
        tracker = RateTracker()
        tracker.configure_limit("llm_calls", max_per_window=100.0)

        assert tracker.get_limit("llm_calls") == 100.0

    def test_configure_multiple_limits(self) -> None:
        """Can configure multiple resource limits."""
        tracker = RateTracker()
        tracker.configure_limit("llm_calls", max_per_window=100.0)
        tracker.configure_limit("disk_writes", max_per_window=500.0)

        assert tracker.get_limit("llm_calls") == 100.0
        assert tracker.get_limit("disk_writes") == 500.0

    def test_reconfigure_limit(self) -> None:
        """Can reconfigure an existing limit."""
        tracker = RateTracker()
        tracker.configure_limit("llm_calls", max_per_window=100.0)
        tracker.configure_limit("llm_calls", max_per_window=200.0)

        assert tracker.get_limit("llm_calls") == 200.0

    def test_configure_zero_limit(self) -> None:
        """Can configure a zero limit (nothing allowed)."""
        tracker = RateTracker()
        tracker.configure_limit("llm_calls", max_per_window=0.0)

        assert tracker.get_limit("llm_calls") == 0.0

    def test_configure_negative_limit_raises(self) -> None:
        """Negative limit raises ValueError."""
        tracker = RateTracker()

        with pytest.raises(ValueError, match="non-negative"):
            tracker.configure_limit("llm_calls", max_per_window=-10.0)

    def test_get_limit_unconfigured(self) -> None:
        """Unconfigured resource returns infinity."""
        tracker = RateTracker()
        assert tracker.get_limit("unknown") == float("inf")


class TestInitialCapacity:
    """Tests for initial capacity state."""

    def test_initial_capacity_with_limit(self) -> None:
        """Fresh tracker with configured limit has full capacity."""
        tracker = RateTracker()
        tracker.configure_limit("llm_calls", max_per_window=100.0)

        assert tracker.has_capacity("agent_a", "llm_calls", 1.0)
        assert tracker.has_capacity("agent_a", "llm_calls", 100.0)

    def test_initial_capacity_no_limit(self) -> None:
        """Unconfigured resource has unlimited capacity."""
        tracker = RateTracker()

        assert tracker.has_capacity("agent_a", "unknown", 1000000.0)

    def test_initial_usage_zero(self) -> None:
        """Fresh tracker has zero usage."""
        tracker = RateTracker()
        tracker.configure_limit("llm_calls", max_per_window=100.0)

        assert tracker.get_usage("agent_a", "llm_calls") == 0.0

    def test_initial_remaining_equals_limit(self) -> None:
        """Fresh tracker has remaining equal to limit."""
        tracker = RateTracker()
        tracker.configure_limit("llm_calls", max_per_window=100.0)

        assert tracker.get_remaining("agent_a", "llm_calls") == 100.0


class TestConsume:
    """Tests for consume method."""

    def test_consume_success(self) -> None:
        """Consuming within limit succeeds."""
        tracker = RateTracker()
        tracker.configure_limit("llm_calls", max_per_window=100.0)

        result = tracker.consume("agent_a", "llm_calls", 10.0)

        assert result is True
        assert tracker.get_usage("agent_a", "llm_calls") == 10.0

    def test_consume_reduces_remaining(self) -> None:
        """Consuming reduces remaining capacity."""
        tracker = RateTracker()
        tracker.configure_limit("llm_calls", max_per_window=100.0)

        tracker.consume("agent_a", "llm_calls", 30.0)

        assert tracker.get_remaining("agent_a", "llm_calls") == 70.0

    def test_consume_multiple_times(self) -> None:
        """Multiple consumptions accumulate."""
        tracker = RateTracker()
        tracker.configure_limit("llm_calls", max_per_window=100.0)

        tracker.consume("agent_a", "llm_calls", 20.0)
        tracker.consume("agent_a", "llm_calls", 30.0)
        tracker.consume("agent_a", "llm_calls", 10.0)

        assert tracker.get_usage("agent_a", "llm_calls") == 60.0
        assert tracker.get_remaining("agent_a", "llm_calls") == 40.0

    def test_consume_exact_limit(self) -> None:
        """Can consume exactly up to the limit."""
        tracker = RateTracker()
        tracker.configure_limit("llm_calls", max_per_window=100.0)

        result = tracker.consume("agent_a", "llm_calls", 100.0)

        assert result is True
        assert tracker.get_remaining("agent_a", "llm_calls") == 0.0

    def test_consume_over_limit_fails(self) -> None:
        """Consuming over limit fails."""
        tracker = RateTracker()
        tracker.configure_limit("llm_calls", max_per_window=100.0)

        result = tracker.consume("agent_a", "llm_calls", 101.0)

        assert result is False
        assert tracker.get_usage("agent_a", "llm_calls") == 0.0

    def test_consume_partial_then_exceed_fails(self) -> None:
        """Cannot exceed limit even with multiple consumptions."""
        tracker = RateTracker()
        tracker.configure_limit("llm_calls", max_per_window=100.0)

        tracker.consume("agent_a", "llm_calls", 80.0)
        result = tracker.consume("agent_a", "llm_calls", 30.0)

        assert result is False
        assert tracker.get_usage("agent_a", "llm_calls") == 80.0

    def test_consume_zero_amount(self) -> None:
        """Consuming zero always succeeds."""
        tracker = RateTracker()
        tracker.configure_limit("llm_calls", max_per_window=0.0)

        result = tracker.consume("agent_a", "llm_calls", 0.0)

        assert result is True

    def test_consume_negative_amount_fails(self) -> None:
        """Consuming negative amount fails."""
        tracker = RateTracker()
        tracker.configure_limit("llm_calls", max_per_window=100.0)

        result = tracker.consume("agent_a", "llm_calls", -10.0)

        assert result is False


class TestHasCapacity:
    """Tests for has_capacity method."""

    def test_has_capacity_under_limit(self) -> None:
        """Returns True when under limit."""
        tracker = RateTracker()
        tracker.configure_limit("llm_calls", max_per_window=100.0)

        tracker.consume("agent_a", "llm_calls", 50.0)

        assert tracker.has_capacity("agent_a", "llm_calls", 50.0) is True
        assert tracker.has_capacity("agent_a", "llm_calls", 49.0) is True

    def test_has_capacity_at_limit(self) -> None:
        """Returns False when at limit."""
        tracker = RateTracker()
        tracker.configure_limit("llm_calls", max_per_window=100.0)

        tracker.consume("agent_a", "llm_calls", 100.0)

        assert tracker.has_capacity("agent_a", "llm_calls", 1.0) is False

    def test_has_capacity_over_limit(self) -> None:
        """Returns False when would exceed limit."""
        tracker = RateTracker()
        tracker.configure_limit("llm_calls", max_per_window=100.0)

        tracker.consume("agent_a", "llm_calls", 50.0)

        assert tracker.has_capacity("agent_a", "llm_calls", 51.0) is False

    def test_has_capacity_zero_amount(self) -> None:
        """Zero amount always has capacity."""
        tracker = RateTracker()
        tracker.configure_limit("llm_calls", max_per_window=0.0)

        assert tracker.has_capacity("agent_a", "llm_calls", 0.0) is True

    def test_has_capacity_negative_amount(self) -> None:
        """Negative amount returns False."""
        tracker = RateTracker()
        tracker.configure_limit("llm_calls", max_per_window=100.0)

        assert tracker.has_capacity("agent_a", "llm_calls", -1.0) is False


class TestWindowExpiry:
    """Tests for rolling window expiry behavior."""

    def test_records_expire_after_window(self) -> None:
        """Old records expire and capacity is restored."""
        tracker = RateTracker(window_seconds=1.0)
        tracker.configure_limit("llm_calls", max_per_window=10.0)

        # Consume all capacity
        tracker.consume("agent_a", "llm_calls", 10.0)
        assert tracker.get_remaining("agent_a", "llm_calls") == 0.0

        # Wait for window to expire
        time.sleep(1.1)

        # Capacity should be restored
        assert tracker.get_remaining("agent_a", "llm_calls") == 10.0
        assert tracker.get_usage("agent_a", "llm_calls") == 0.0

    def test_partial_expiry(self) -> None:
        """Records expire individually as they age out."""
        tracker = RateTracker(window_seconds=0.5)
        tracker.configure_limit("llm_calls", max_per_window=10.0)

        # Record first consumption
        tracker.consume("agent_a", "llm_calls", 3.0)

        # Wait a bit, then record second consumption
        time.sleep(0.3)
        tracker.consume("agent_a", "llm_calls", 4.0)

        # Total usage is 7
        assert tracker.get_usage("agent_a", "llm_calls") == 7.0

        # Wait for first record to expire (but not second)
        time.sleep(0.3)

        # First record expired, only second remains
        assert tracker.get_usage("agent_a", "llm_calls") == 4.0
        assert tracker.get_remaining("agent_a", "llm_calls") == 6.0


class TestMultipleAgents:
    """Tests for independent agent tracking."""

    def test_agents_have_independent_limits(self) -> None:
        """Each agent has their own capacity."""
        tracker = RateTracker()
        tracker.configure_limit("llm_calls", max_per_window=100.0)

        tracker.consume("agent_a", "llm_calls", 80.0)
        tracker.consume("agent_b", "llm_calls", 30.0)

        assert tracker.get_usage("agent_a", "llm_calls") == 80.0
        assert tracker.get_usage("agent_b", "llm_calls") == 30.0
        assert tracker.get_remaining("agent_a", "llm_calls") == 20.0
        assert tracker.get_remaining("agent_b", "llm_calls") == 70.0

    def test_one_agent_at_limit_others_unaffected(self) -> None:
        """One agent hitting limit doesn't affect others."""
        tracker = RateTracker()
        tracker.configure_limit("llm_calls", max_per_window=100.0)

        tracker.consume("agent_a", "llm_calls", 100.0)

        assert tracker.has_capacity("agent_a", "llm_calls", 1.0) is False
        assert tracker.has_capacity("agent_b", "llm_calls", 100.0) is True


class TestMultipleResources:
    """Tests for independent resource tracking."""

    def test_resources_tracked_separately(self) -> None:
        """Different resources have independent limits."""
        tracker = RateTracker()
        tracker.configure_limit("llm_calls", max_per_window=100.0)
        tracker.configure_limit("disk_writes", max_per_window=50.0)

        tracker.consume("agent_a", "llm_calls", 80.0)
        tracker.consume("agent_a", "disk_writes", 40.0)

        assert tracker.get_remaining("agent_a", "llm_calls") == 20.0
        assert tracker.get_remaining("agent_a", "disk_writes") == 10.0

    def test_one_resource_at_limit_others_unaffected(self) -> None:
        """Hitting limit on one resource doesn't affect others."""
        tracker = RateTracker()
        tracker.configure_limit("llm_calls", max_per_window=100.0)
        tracker.configure_limit("disk_writes", max_per_window=50.0)

        tracker.consume("agent_a", "llm_calls", 100.0)

        assert tracker.has_capacity("agent_a", "llm_calls", 1.0) is False
        assert tracker.has_capacity("agent_a", "disk_writes", 50.0) is True


class TestTimeUntilCapacity:
    """Tests for time_until_capacity estimation."""

    def test_time_until_capacity_has_capacity(self) -> None:
        """Returns 0 when capacity is available."""
        tracker = RateTracker()
        tracker.configure_limit("llm_calls", max_per_window=100.0)

        assert tracker.time_until_capacity("agent_a", "llm_calls", 50.0) == 0.0

    def test_time_until_capacity_zero_amount(self) -> None:
        """Returns 0 for zero amount."""
        tracker = RateTracker()
        tracker.configure_limit("llm_calls", max_per_window=0.0)

        assert tracker.time_until_capacity("agent_a", "llm_calls", 0.0) == 0.0

    def test_time_until_capacity_negative_amount(self) -> None:
        """Returns 0 for negative amount."""
        tracker = RateTracker()
        tracker.configure_limit("llm_calls", max_per_window=100.0)

        assert tracker.time_until_capacity("agent_a", "llm_calls", -10.0) == 0.0

    def test_time_until_capacity_at_limit(self) -> None:
        """Returns positive time when at limit."""
        tracker = RateTracker(window_seconds=60.0)
        tracker.configure_limit("llm_calls", max_per_window=10.0)

        tracker.consume("agent_a", "llm_calls", 10.0)

        wait_time = tracker.time_until_capacity("agent_a", "llm_calls", 1.0)

        # Should be close to 60 seconds (window duration)
        assert 55.0 <= wait_time <= 60.0

    def test_time_until_capacity_estimates_correctly(self) -> None:
        """Time estimate is accurate based on record timestamps."""
        tracker = RateTracker(window_seconds=1.0)
        tracker.configure_limit("llm_calls", max_per_window=10.0)

        # Consume capacity
        tracker.consume("agent_a", "llm_calls", 10.0)

        # Check estimate immediately
        wait_time = tracker.time_until_capacity("agent_a", "llm_calls", 1.0)
        assert 0.9 <= wait_time <= 1.0

        # Wait a bit
        time.sleep(0.5)

        # Estimate should have decreased
        wait_time = tracker.time_until_capacity("agent_a", "llm_calls", 1.0)
        assert 0.4 <= wait_time <= 0.6


class TestWaitForCapacity:
    """Tests for async wait_for_capacity method."""

    @pytest.mark.asyncio
    async def test_wait_immediate_capacity(self) -> None:
        """Returns True immediately if capacity available."""
        tracker = RateTracker()
        tracker.configure_limit("llm_calls", max_per_window=100.0)

        result = await tracker.wait_for_capacity("agent_a", "llm_calls", 50.0)

        assert result is True
        # Should have consumed the capacity
        assert tracker.get_usage("agent_a", "llm_calls") == 50.0

    @pytest.mark.asyncio
    async def test_wait_zero_amount(self) -> None:
        """Zero amount returns True immediately."""
        tracker = RateTracker()
        tracker.configure_limit("llm_calls", max_per_window=0.0)

        result = await tracker.wait_for_capacity("agent_a", "llm_calls", 0.0)

        assert result is True

    @pytest.mark.asyncio
    async def test_wait_blocks_then_succeeds(self) -> None:
        """Waits for capacity to become available."""
        tracker = RateTracker(window_seconds=0.3)
        tracker.configure_limit("llm_calls", max_per_window=10.0)

        # Consume all capacity
        tracker.consume("agent_a", "llm_calls", 10.0)

        start = time.time()
        result = await tracker.wait_for_capacity(
            "agent_a", "llm_calls", 5.0, poll_interval=0.05
        )
        elapsed = time.time() - start

        assert result is True
        # Should have waited approximately window_seconds
        assert 0.25 <= elapsed <= 0.5

    @pytest.mark.asyncio
    async def test_wait_timeout(self) -> None:
        """Returns False on timeout."""
        tracker = RateTracker(window_seconds=10.0)  # Long window
        tracker.configure_limit("llm_calls", max_per_window=10.0)

        # Consume all capacity
        tracker.consume("agent_a", "llm_calls", 10.0)

        start = time.time()
        result = await tracker.wait_for_capacity(
            "agent_a", "llm_calls", 5.0, timeout=0.2
        )
        elapsed = time.time() - start

        assert result is False
        # Should have timed out around 0.2 seconds
        assert 0.15 <= elapsed <= 0.35
        # Should not have consumed capacity
        assert tracker.get_usage("agent_a", "llm_calls") == 10.0


class TestReset:
    """Tests for reset method."""

    def test_reset_all(self) -> None:
        """Reset all clears everything."""
        tracker = RateTracker()
        tracker.configure_limit("llm_calls", max_per_window=100.0)
        tracker.configure_limit("disk_writes", max_per_window=50.0)

        tracker.consume("agent_a", "llm_calls", 50.0)
        tracker.consume("agent_b", "disk_writes", 30.0)

        tracker.reset()

        assert tracker.get_usage("agent_a", "llm_calls") == 0.0
        assert tracker.get_usage("agent_b", "disk_writes") == 0.0

    def test_reset_agent(self) -> None:
        """Reset specific agent."""
        tracker = RateTracker()
        tracker.configure_limit("llm_calls", max_per_window=100.0)

        tracker.consume("agent_a", "llm_calls", 50.0)
        tracker.consume("agent_b", "llm_calls", 30.0)

        tracker.reset(agent_id="agent_a")

        assert tracker.get_usage("agent_a", "llm_calls") == 0.0
        assert tracker.get_usage("agent_b", "llm_calls") == 30.0

    def test_reset_resource(self) -> None:
        """Reset specific resource."""
        tracker = RateTracker()
        tracker.configure_limit("llm_calls", max_per_window=100.0)
        tracker.configure_limit("disk_writes", max_per_window=50.0)

        tracker.consume("agent_a", "llm_calls", 50.0)
        tracker.consume("agent_a", "disk_writes", 30.0)

        tracker.reset(resource="llm_calls")

        assert tracker.get_usage("agent_a", "llm_calls") == 0.0
        assert tracker.get_usage("agent_a", "disk_writes") == 30.0

    def test_reset_agent_resource(self) -> None:
        """Reset specific agent-resource combination."""
        tracker = RateTracker()
        tracker.configure_limit("llm_calls", max_per_window=100.0)

        tracker.consume("agent_a", "llm_calls", 50.0)
        tracker.consume("agent_b", "llm_calls", 30.0)

        tracker.reset(agent_id="agent_a", resource="llm_calls")

        assert tracker.get_usage("agent_a", "llm_calls") == 0.0
        assert tracker.get_usage("agent_b", "llm_calls") == 30.0


class TestGetAllUsage:
    """Tests for get_all_usage method."""

    def test_get_all_usage_empty(self) -> None:
        """Returns empty dict when no usage."""
        tracker = RateTracker()
        tracker.configure_limit("llm_calls", max_per_window=100.0)

        assert tracker.get_all_usage() == {}

    def test_get_all_usage_single_agent(self) -> None:
        """Returns usage for single agent."""
        tracker = RateTracker()
        tracker.configure_limit("llm_calls", max_per_window=100.0)

        tracker.consume("agent_a", "llm_calls", 50.0)

        usage = tracker.get_all_usage()
        assert usage == {"llm_calls": {"agent_a": 50.0}}

    def test_get_all_usage_multiple(self) -> None:
        """Returns usage for multiple agents and resources."""
        tracker = RateTracker()
        tracker.configure_limit("llm_calls", max_per_window=100.0)
        tracker.configure_limit("disk_writes", max_per_window=50.0)

        tracker.consume("agent_a", "llm_calls", 50.0)
        tracker.consume("agent_b", "llm_calls", 30.0)
        tracker.consume("agent_a", "disk_writes", 20.0)

        usage = tracker.get_all_usage()
        assert usage == {
            "llm_calls": {"agent_a": 50.0, "agent_b": 30.0},
            "disk_writes": {"agent_a": 20.0},
        }


class TestEdgeCases:
    """Tests for edge cases and boundary conditions."""

    def test_very_small_amounts(self) -> None:
        """Handles very small amounts correctly."""
        tracker = RateTracker()
        tracker.configure_limit("resource", max_per_window=1.0)

        for _ in range(100):
            tracker.consume("agent_a", "resource", 0.01)

        # Allow for floating point accumulation errors
        # (100 * 0.01 may not equal exactly 1.0 due to binary representation)
        usage = tracker.get_usage("agent_a", "resource")
        assert 0.99 <= usage <= 1.01

    def test_very_large_amounts(self) -> None:
        """Handles very large amounts correctly."""
        tracker = RateTracker()
        tracker.configure_limit("resource", max_per_window=1e12)

        tracker.consume("agent_a", "resource", 1e11)

        assert tracker.get_remaining("agent_a", "resource") == 9e11

    def test_concurrent_consume_simulation(self) -> None:
        """Simulates concurrent consumption (single-threaded)."""
        tracker = RateTracker()
        tracker.configure_limit("resource", max_per_window=100.0)

        # Simulate rapid sequential consumption
        for i in range(100):
            tracker.consume("agent_a", "resource", 1.0)

        assert tracker.get_usage("agent_a", "resource") == 100.0
        assert tracker.has_capacity("agent_a", "resource", 1.0) is False

    def test_many_agents(self) -> None:
        """Handles many agents efficiently."""
        tracker = RateTracker()
        tracker.configure_limit("resource", max_per_window=10.0)

        for i in range(1000):
            tracker.consume(f"agent_{i}", "resource", 5.0)

        # Spot check a few agents
        assert tracker.get_usage("agent_0", "resource") == 5.0
        assert tracker.get_usage("agent_500", "resource") == 5.0
        assert tracker.get_usage("agent_999", "resource") == 5.0
