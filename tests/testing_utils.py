"""Testing utilities for continuous execution.

Provides deterministic time control and async assertion helpers for testing
time-dependent and async code without real delays.

Usage:
    from tests.testing_utils import VirtualClock, wait_for, wait_for_value

    # Deterministic time control
    clock = VirtualClock()
    tracker = RateTracker(window_seconds=60.0, clock=clock)
    tracker.consume("agent", "llm_calls", 50.0)
    clock.advance(61.0)  # Instant, no real delay
    assert tracker.get_remaining("agent", "llm_calls") == 100.0

    # Condition-based assertions
    await wait_for(lambda: loop.state == AgentState.RUNNING)
    await wait_for_value(lambda: counter.value, 10)

See docs/plans/21_continuous_testing.md for design rationale.
"""

from __future__ import annotations

import asyncio
import time
from dataclasses import dataclass, field
from typing import Any, Callable, Protocol, TypeVar

T = TypeVar("T")


class ClockProtocol(Protocol):
    """Protocol for clock implementations.

    Both VirtualClock and RealClock implement this protocol,
    allowing code to accept either for testing or production.
    """

    def time(self) -> float:
        """Get current time in seconds."""
        ...

    async def sleep(self, seconds: float) -> None:
        """Sleep for the given duration."""
        ...


@dataclass
class VirtualClock:
    """Deterministic mock clock for testing.

    Time only advances when advance() is called, making tests
    fast and deterministic. Sleepers wake when their wake time
    is reached via advance().

    Example:
        clock = VirtualClock()
        assert clock.time() == 0.0

        clock.advance(10.0)
        assert clock.time() == 10.0

        # Async sleep responds to advance()
        async def sleeper():
            await clock.sleep(5.0)
            return "done"

        task = asyncio.create_task(sleeper())
        clock.advance(5.0)  # Wakes the sleeper
        result = await task
        assert result == "done"
    """

    _time: float = 0.0
    _waiters: list[tuple[float, asyncio.Event]] = field(default_factory=list)

    def time(self) -> float:
        """Get current virtual time."""
        return self._time

    def advance(self, seconds: float) -> None:
        """Advance virtual time by the given amount.

        Wakes any sleepers whose wake time has been reached.

        Args:
            seconds: Amount to advance (must be non-negative)

        Raises:
            ValueError: If seconds is negative
        """
        if seconds < 0:
            raise ValueError(f"Cannot advance time by negative amount: {seconds}")
        self._time += seconds
        self._wake_expired_waiters()

    def set_time(self, new_time: float) -> None:
        """Set virtual time to specific value.

        Useful for testing specific time scenarios.

        Args:
            new_time: New time value (must be >= current time)

        Raises:
            ValueError: If new_time is less than current time
        """
        if new_time < self._time:
            raise ValueError(
                f"Cannot set time backwards: {new_time} < {self._time}"
            )
        self._time = new_time
        self._wake_expired_waiters()

    def _wake_expired_waiters(self) -> None:
        """Wake any waiters whose time has come."""
        still_waiting: list[tuple[float, asyncio.Event]] = []
        for wake_time, event in self._waiters:
            if wake_time <= self._time:
                event.set()
            else:
                still_waiting.append((wake_time, event))
        self._waiters = still_waiting

    async def sleep(self, seconds: float) -> None:
        """Async sleep that responds to advance().

        The sleep completes when virtual time reaches or exceeds
        the wake time, which happens via advance() calls.

        Args:
            seconds: Duration to sleep (can be 0 for immediate return)
        """
        if seconds <= 0:
            return

        wake_time = self._time + seconds
        event = asyncio.Event()
        self._waiters.append((wake_time, event))

        # Check if already past wake time (in case advance() was called)
        if self._time >= wake_time:
            event.set()

        await event.wait()


@dataclass
class RealClock:
    """Real clock implementation for production use.

    Wraps time.time() and asyncio.sleep() with the ClockProtocol
    interface, allowing the same code to work with either real
    or virtual time.

    Example:
        # In production
        clock = RealClock()
        tracker = RateTracker(clock=clock)

        # In tests
        clock = VirtualClock()
        tracker = RateTracker(clock=clock)
    """

    def time(self) -> float:
        """Get current real time."""
        return time.time()

    async def sleep(self, seconds: float) -> None:
        """Real async sleep."""
        if seconds > 0:
            await asyncio.sleep(seconds)


async def wait_for(
    condition: Callable[[], bool],
    timeout: float = 1.0,
    interval: float = 0.01,
    message: str | None = None,
) -> None:
    """Wait until condition is True or timeout.

    Polls the condition at the given interval until it returns True
    or the timeout is reached.

    Args:
        condition: Callable that returns True when condition is met
        timeout: Maximum seconds to wait (default: 1.0)
        interval: How often to check condition (default: 0.01)
        message: Optional message for timeout error

    Raises:
        TimeoutError: If condition not met within timeout

    Example:
        await wait_for(lambda: loop.state == "running")
        await wait_for(lambda: len(results) > 0, timeout=5.0)
    """
    start = time.time()
    while not condition():
        elapsed = time.time() - start
        if elapsed >= timeout:
            error_msg = message or f"Condition not met within {timeout}s"
            raise TimeoutError(error_msg)
        await asyncio.sleep(interval)


async def wait_for_value(
    getter: Callable[[], T],
    expected: T,
    timeout: float = 1.0,
    interval: float = 0.01,
) -> None:
    """Wait until getter() returns expected value.

    Convenience wrapper around wait_for for value comparisons.

    Args:
        getter: Callable that returns current value
        expected: Value to wait for
        timeout: Maximum seconds to wait (default: 1.0)
        interval: How often to check (default: 0.01)

    Raises:
        TimeoutError: If value not reached within timeout

    Example:
        await wait_for_value(lambda: loop.state, AgentState.RUNNING)
        await wait_for_value(lambda: counter.value, 10)
    """
    def check() -> bool:
        return getter() == expected

    await wait_for(
        check,
        timeout=timeout,
        interval=interval,
        message=f"Value did not become {expected!r} within {timeout}s (got {getter()!r})",
    )


async def wait_for_predicate(
    getter: Callable[[], T],
    predicate: Callable[[T], bool],
    timeout: float = 1.0,
    interval: float = 0.01,
    description: str = "predicate",
) -> T:
    """Wait until predicate(getter()) is True, return final value.

    More flexible than wait_for_value - allows custom predicates.

    Args:
        getter: Callable that returns current value
        predicate: Function that returns True when value is acceptable
        timeout: Maximum seconds to wait (default: 1.0)
        interval: How often to check (default: 0.01)
        description: Description for error message

    Returns:
        The value that satisfied the predicate

    Raises:
        TimeoutError: If predicate not satisfied within timeout

    Example:
        value = await wait_for_predicate(
            lambda: len(items),
            lambda x: x >= 5,
            description="at least 5 items"
        )
    """
    start = time.time()
    while True:
        value = getter()
        if predicate(value):
            return value
        elapsed = time.time() - start
        if elapsed >= timeout:
            raise TimeoutError(
                f"Condition '{description}' not met within {timeout}s (got {value!r})"
            )
        await asyncio.sleep(interval)
