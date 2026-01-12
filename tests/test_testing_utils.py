"""Tests for testing utilities (VirtualClock, wait_for, etc).

These tests verify the testing infrastructure works correctly,
enabling deterministic async testing throughout the codebase.
"""

from __future__ import annotations

import asyncio
import time

import pytest

from tests.testing_utils import (
    VirtualClock,
    RealClock,
    wait_for,
    wait_for_value,
    wait_for_predicate,
)
from src.world.rate_tracker import RateTracker


# =============================================================================
# VirtualClock Tests
# =============================================================================


class TestVirtualClockBasics:
    """Basic VirtualClock functionality."""

    def test_virtual_clock_initial_time(self) -> None:
        """Clock starts at 0."""
        clock = VirtualClock()
        assert clock.time() == 0.0

    def test_virtual_clock_advance(self) -> None:
        """advance() increases time."""
        clock = VirtualClock()
        clock.advance(10.0)
        assert clock.time() == 10.0

        clock.advance(5.0)
        assert clock.time() == 15.0

    def test_virtual_clock_advance_negative_raises(self) -> None:
        """Cannot advance by negative amount."""
        clock = VirtualClock()
        with pytest.raises(ValueError, match="negative"):
            clock.advance(-1.0)

    def test_virtual_clock_set_time(self) -> None:
        """set_time() sets specific time value."""
        clock = VirtualClock()
        clock.set_time(100.0)
        assert clock.time() == 100.0

    def test_virtual_clock_set_time_backwards_raises(self) -> None:
        """Cannot set time backwards."""
        clock = VirtualClock()
        clock.advance(50.0)
        with pytest.raises(ValueError, match="backwards"):
            clock.set_time(25.0)


class TestVirtualClockSleep:
    """VirtualClock async sleep functionality."""

    @pytest.mark.asyncio
    async def test_virtual_clock_sleep_zero(self) -> None:
        """Sleep(0) returns immediately."""
        clock = VirtualClock()
        await clock.sleep(0)
        assert clock.time() == 0.0

    @pytest.mark.asyncio
    async def test_virtual_clock_sleep_negative(self) -> None:
        """Sleep with negative value returns immediately."""
        clock = VirtualClock()
        await clock.sleep(-1.0)
        assert clock.time() == 0.0

    @pytest.mark.asyncio
    async def test_virtual_clock_sleep_wakes_on_advance(self) -> None:
        """Sleeper wakes when time advances past wake time."""
        clock = VirtualClock()
        woke_up = False

        async def sleeper() -> None:
            nonlocal woke_up
            await clock.sleep(5.0)
            woke_up = True

        task = asyncio.create_task(sleeper())

        # Give the task a chance to start
        await asyncio.sleep(0)

        assert not woke_up
        clock.advance(5.0)

        # Give the task a chance to complete
        await asyncio.sleep(0)
        await task

        assert woke_up

    @pytest.mark.asyncio
    async def test_virtual_clock_multiple_sleepers(self) -> None:
        """Multiple sleepers wake at correct times."""
        clock = VirtualClock()
        wake_order: list[str] = []

        async def sleeper(name: str, duration: float) -> None:
            await clock.sleep(duration)
            wake_order.append(name)

        task1 = asyncio.create_task(sleeper("short", 2.0))
        task2 = asyncio.create_task(sleeper("long", 5.0))
        task3 = asyncio.create_task(sleeper("medium", 3.0))

        await asyncio.sleep(0)  # Let tasks start

        clock.advance(2.5)
        await asyncio.sleep(0)  # Let short wake

        clock.advance(1.0)  # Total: 3.5
        await asyncio.sleep(0)  # Let medium wake

        clock.advance(2.0)  # Total: 5.5
        await asyncio.sleep(0)  # Let long wake

        await asyncio.gather(task1, task2, task3)

        assert wake_order == ["short", "medium", "long"]

    @pytest.mark.asyncio
    async def test_virtual_clock_sleep_with_concurrent_advance(self) -> None:
        """Sleep completes when advance is called concurrently."""
        clock = VirtualClock()
        completed = False

        async def sleeper() -> None:
            nonlocal completed
            await clock.sleep(10.0)
            completed = True

        async def advancer() -> None:
            await asyncio.sleep(0)  # Yield to let sleeper start
            clock.advance(10.0)

        # Run both concurrently
        await asyncio.gather(sleeper(), advancer())
        assert completed


# =============================================================================
# RealClock Tests
# =============================================================================


class TestRealClock:
    """RealClock basic functionality."""

    def test_real_clock_time(self) -> None:
        """RealClock.time() returns current time."""
        clock = RealClock()
        before = time.time()
        clock_time = clock.time()
        after = time.time()

        assert before <= clock_time <= after

    @pytest.mark.asyncio
    async def test_real_clock_sleep(self) -> None:
        """RealClock.sleep() actually sleeps."""
        clock = RealClock()
        start = time.time()
        await clock.sleep(0.05)
        elapsed = time.time() - start

        assert elapsed >= 0.04  # Allow some tolerance


# =============================================================================
# wait_for Tests
# =============================================================================


class TestWaitFor:
    """wait_for() async helper tests."""

    @pytest.mark.asyncio
    async def test_wait_for_immediate_true(self) -> None:
        """Returns immediately if condition already true."""
        start = time.time()
        await wait_for(lambda: True, timeout=1.0)
        elapsed = time.time() - start

        assert elapsed < 0.1

    @pytest.mark.asyncio
    async def test_wait_for_becomes_true(self) -> None:
        """Waits until condition becomes true."""
        value = False

        async def set_true() -> None:
            nonlocal value
            await asyncio.sleep(0.05)
            value = True

        task = asyncio.create_task(set_true())
        await wait_for(lambda: value, timeout=1.0)
        await task

        assert value is True

    @pytest.mark.asyncio
    async def test_wait_for_timeout(self) -> None:
        """Raises TimeoutError on timeout."""
        with pytest.raises(TimeoutError):
            await wait_for(lambda: False, timeout=0.05)

    @pytest.mark.asyncio
    async def test_wait_for_custom_message(self) -> None:
        """Custom message appears in TimeoutError."""
        with pytest.raises(TimeoutError, match="custom error"):
            await wait_for(lambda: False, timeout=0.01, message="custom error")


class TestWaitForValue:
    """wait_for_value() async helper tests."""

    @pytest.mark.asyncio
    async def test_wait_for_value_immediate_match(self) -> None:
        """Returns immediately if value matches."""
        value = 42
        start = time.time()
        await wait_for_value(lambda: value, 42, timeout=1.0)
        elapsed = time.time() - start

        assert elapsed < 0.1

    @pytest.mark.asyncio
    async def test_wait_for_value_becomes_match(self) -> None:
        """Waits until value matches."""
        counter = [0]

        async def increment() -> None:
            for _ in range(10):
                await asyncio.sleep(0.01)
                counter[0] += 1

        task = asyncio.create_task(increment())
        await wait_for_value(lambda: counter[0], 10, timeout=1.0)
        await task

        assert counter[0] == 10

    @pytest.mark.asyncio
    async def test_wait_for_value_timeout(self) -> None:
        """Raises TimeoutError with current value in message."""
        with pytest.raises(TimeoutError, match="got 0"):
            await wait_for_value(lambda: 0, 100, timeout=0.01)


class TestWaitForPredicate:
    """wait_for_predicate() async helper tests."""

    @pytest.mark.asyncio
    async def test_wait_for_predicate_immediate(self) -> None:
        """Returns value immediately if predicate satisfied."""
        result = await wait_for_predicate(
            lambda: 10,
            lambda x: x > 5,
            timeout=1.0,
        )
        assert result == 10

    @pytest.mark.asyncio
    async def test_wait_for_predicate_becomes_true(self) -> None:
        """Waits until predicate is satisfied."""
        counter = [0]

        async def increment() -> None:
            for _ in range(10):
                await asyncio.sleep(0.01)
                counter[0] += 1

        task = asyncio.create_task(increment())
        result = await wait_for_predicate(
            lambda: counter[0],
            lambda x: x >= 5,
            timeout=1.0,
            description="counter >= 5",
        )
        await task

        assert result >= 5

    @pytest.mark.asyncio
    async def test_wait_for_predicate_timeout(self) -> None:
        """Raises TimeoutError with description."""
        with pytest.raises(TimeoutError, match="at least 100"):
            await wait_for_predicate(
                lambda: 5,
                lambda x: x >= 100,
                timeout=0.01,
                description="at least 100",
            )


# =============================================================================
# RateTracker with VirtualClock Tests
# =============================================================================


class TestRateTrackerWithVirtualClock:
    """RateTracker integration with VirtualClock."""

    def test_rate_tracker_with_virtual_clock(self) -> None:
        """RateTracker uses injected clock for time."""
        clock = VirtualClock()
        tracker = RateTracker(window_seconds=60.0, clock=clock)
        tracker.configure_limit("llm_calls", max_per_window=100.0)

        # Consume at t=0
        tracker.consume("agent", "llm_calls", 50.0)
        assert tracker.get_remaining("agent", "llm_calls") == 50.0

        # Advance but still in window
        clock.advance(30.0)
        assert tracker.get_remaining("agent", "llm_calls") == 50.0

    def test_rate_tracker_window_expiry_virtual(self) -> None:
        """Window expires correctly with virtual clock."""
        clock = VirtualClock()
        tracker = RateTracker(window_seconds=60.0, clock=clock)
        tracker.configure_limit("llm_calls", max_per_window=100.0)

        # Consume at t=0
        tracker.consume("agent", "llm_calls", 50.0)
        assert tracker.get_usage("agent", "llm_calls") == 50.0

        # Advance past window
        clock.advance(61.0)

        # Usage should be expired
        assert tracker.get_usage("agent", "llm_calls") == 0.0
        assert tracker.get_remaining("agent", "llm_calls") == 100.0

    def test_rate_tracker_multiple_consumes_with_clock(self) -> None:
        """Multiple consumes at different times expire correctly."""
        clock = VirtualClock()
        tracker = RateTracker(window_seconds=60.0, clock=clock)
        tracker.configure_limit("llm_calls", max_per_window=100.0)

        # Consume 30 at t=0
        tracker.consume("agent", "llm_calls", 30.0)

        # Consume 30 at t=30
        clock.advance(30.0)
        tracker.consume("agent", "llm_calls", 30.0)

        # At t=30, both are in window
        assert tracker.get_usage("agent", "llm_calls") == 60.0

        # At t=65, first consume expired, second still valid
        clock.advance(35.0)
        assert tracker.get_usage("agent", "llm_calls") == 30.0

        # At t=95, both expired
        clock.advance(30.0)
        assert tracker.get_usage("agent", "llm_calls") == 0.0

    def test_rate_tracker_time_until_capacity_with_clock(self) -> None:
        """time_until_capacity uses virtual clock."""
        clock = VirtualClock()
        tracker = RateTracker(window_seconds=60.0, clock=clock)
        tracker.configure_limit("llm_calls", max_per_window=100.0)

        # Exhaust capacity at t=0
        tracker.consume("agent", "llm_calls", 100.0)

        # Should need to wait ~60 seconds for first record to expire
        wait_time = tracker.time_until_capacity("agent", "llm_calls", 10.0)
        assert 59.0 <= wait_time <= 60.0

        # Advance 30 seconds
        clock.advance(30.0)

        # Should now need ~30 seconds
        wait_time = tracker.time_until_capacity("agent", "llm_calls", 10.0)
        assert 29.0 <= wait_time <= 30.0

    @pytest.mark.asyncio
    async def test_rate_tracker_wait_for_capacity_with_clock(self) -> None:
        """wait_for_capacity works with virtual clock."""
        clock = VirtualClock()
        tracker = RateTracker(window_seconds=10.0, clock=clock)
        tracker.configure_limit("llm_calls", max_per_window=10.0)

        # Exhaust capacity at t=0
        tracker.consume("agent", "llm_calls", 10.0)

        # Start waiting for capacity
        result_container: list[bool] = []

        async def wait_and_store() -> None:
            result = await tracker.wait_for_capacity(
                "agent", "llm_calls", 5.0, timeout=20.0
            )
            result_container.append(result)

        task = asyncio.create_task(wait_and_store())
        await asyncio.sleep(0)  # Let task start

        # Should not have capacity yet
        assert len(result_container) == 0

        # Advance past window
        clock.advance(11.0)
        await asyncio.sleep(0)  # Let task wake

        await task

        # Should have acquired capacity
        assert result_container == [True]

    @pytest.mark.asyncio
    async def test_rate_tracker_wait_timeout_with_clock(self) -> None:
        """wait_for_capacity timeout works with virtual clock."""
        clock = VirtualClock()
        tracker = RateTracker(window_seconds=60.0, clock=clock)
        tracker.configure_limit("llm_calls", max_per_window=10.0)

        # Exhaust capacity
        tracker.consume("agent", "llm_calls", 10.0)

        # Start waiting with short timeout
        result_container: list[bool] = []

        async def wait_and_store() -> None:
            result = await tracker.wait_for_capacity(
                "agent", "llm_calls", 5.0, timeout=5.0, poll_interval=1.0
            )
            result_container.append(result)

        task = asyncio.create_task(wait_and_store())
        await asyncio.sleep(0)

        # Advance past timeout but not past window
        clock.advance(6.0)
        await asyncio.sleep(0)

        await task

        # Should have timed out (returned False)
        assert result_container == [False]


class TestRateTrackerWithoutClock:
    """RateTracker still works without clock (backwards compatibility)."""

    def test_rate_tracker_default_uses_real_time(self) -> None:
        """RateTracker without clock uses real time."""
        tracker = RateTracker(window_seconds=60.0)
        tracker.configure_limit("llm_calls", max_per_window=100.0)

        before = time.time()
        tracker.consume("agent", "llm_calls", 50.0)
        after = time.time()

        # Check internal timestamp is in expected range
        records = tracker._usage["llm_calls"]["agent"]
        assert len(records) == 1
        assert before <= records[0].timestamp <= after
