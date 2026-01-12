"""Rolling window rate limiter for resources.

Provides time-based rate limiting independent of simulation ticks.
Tracks usage within a sliding time window and enforces configurable limits.

Usage:
    tracker = RateTracker(window_seconds=60.0)
    tracker.configure_limit("llm_calls", max_per_window=100.0)

    if tracker.has_capacity(agent_id, "llm_calls", amount=1.0):
        tracker.consume(agent_id, "llm_calls", amount=1.0)
        # Make the LLM call

    # Or wait for capacity
    acquired = await tracker.wait_for_capacity(agent_id, "llm_calls", timeout=30.0)

See docs/architecture/gaps/plans/phase1_gap_res_001_rate_tracker.md for design.
"""

from __future__ import annotations

import asyncio
import time
from collections import deque
from dataclasses import dataclass, field
from typing import Any, Deque, Protocol


class ClockProtocol(Protocol):
    """Protocol for clock implementations (VirtualClock or RealClock)."""

    def time(self) -> float:
        """Get current time in seconds."""
        ...

    async def sleep(self, seconds: float) -> None:
        """Sleep for the given duration."""
        ...


@dataclass
class UsageRecord:
    """Single usage event with timestamp."""

    timestamp: float
    amount: float


@dataclass
class RateTracker:
    """Rolling window rate limiter for resources.

    Tracks resource usage within a configurable time window and enforces
    per-agent limits. Usage records older than the window are automatically
    expired.

    Attributes:
        window_seconds: Duration of the rolling window (default: 60.0)
        clock: Optional clock for time operations (for testing with VirtualClock)
    """

    window_seconds: float = 60.0
    clock: Any = None  # ClockProtocol, but Any for dataclass compatibility

    # resource_type -> agent_id -> deque of UsageRecords
    _usage: dict[str, dict[str, Deque[UsageRecord]]] = field(default_factory=dict)
    # resource_type -> max_per_window
    _limits: dict[str, float] = field(default_factory=dict)

    def configure_limit(self, resource: str, max_per_window: float) -> None:
        """Set rate limit for a resource type.

        Args:
            resource: Name of the resource (e.g., "llm_calls", "disk_writes")
            max_per_window: Maximum amount allowed within the rolling window
        """
        if max_per_window < 0:
            raise ValueError(f"max_per_window must be non-negative, got {max_per_window}")
        self._limits[resource] = max_per_window
        if resource not in self._usage:
            self._usage[resource] = {}

    def get_limit(self, resource: str) -> float:
        """Get the configured limit for a resource.

        Args:
            resource: Name of the resource

        Returns:
            The limit, or float('inf') if no limit configured
        """
        return self._limits.get(resource, float("inf"))

    def _clean_old_records(self, resource: str, agent_id: str) -> None:
        """Remove records outside the rolling window.

        Internal method that prunes expired usage records for a specific
        agent and resource combination.
        """
        if resource not in self._usage:
            return
        if agent_id not in self._usage[resource]:
            return

        cutoff = self._get_current_time() - self.window_seconds
        records = self._usage[resource][agent_id]
        while records and records[0].timestamp < cutoff:
            records.popleft()

    def _get_current_time(self) -> float:
        """Get current time. Uses injected clock if available."""
        if self.clock is not None:
            result: float = self.clock.time()
            return result
        return time.time()

    async def _sleep(self, seconds: float) -> None:
        """Async sleep. Uses injected clock if available."""
        if self.clock is not None:
            await self.clock.sleep(seconds)
        else:
            await asyncio.sleep(seconds)

    def get_usage(self, agent_id: str, resource: str) -> float:
        """Get current usage within the rolling window.

        Args:
            agent_id: ID of the agent
            resource: Name of the resource

        Returns:
            Total usage amount within the current window
        """
        self._clean_old_records(resource, agent_id)

        if resource not in self._usage:
            return 0.0
        if agent_id not in self._usage[resource]:
            return 0.0

        return sum(r.amount for r in self._usage[resource][agent_id])

    def get_remaining(self, agent_id: str, resource: str) -> float:
        """Get remaining capacity in current window.

        Args:
            agent_id: ID of the agent
            resource: Name of the resource

        Returns:
            Amount of resource still available in the current window
        """
        limit = self._limits.get(resource, float("inf"))
        usage = self.get_usage(agent_id, resource)
        return max(0.0, limit - usage)

    def has_capacity(
        self, agent_id: str, resource: str, amount: float = 1.0
    ) -> bool:
        """Check if agent has capacity for the requested amount.

        Args:
            agent_id: ID of the agent
            resource: Name of the resource
            amount: Amount to check (default: 1.0)

        Returns:
            True if the agent can use the requested amount
        """
        if amount < 0:
            return False
        if amount == 0:
            return True
        return self.get_remaining(agent_id, resource) >= amount

    def consume(
        self, agent_id: str, resource: str, amount: float = 1.0
    ) -> bool:
        """Consume resource capacity.

        Records the usage if there is sufficient capacity.

        Args:
            agent_id: ID of the agent
            resource: Name of the resource
            amount: Amount to consume (default: 1.0)

        Returns:
            True if successful, False if insufficient capacity
        """
        if amount < 0:
            return False
        if amount == 0:
            return True

        if not self.has_capacity(agent_id, resource, amount):
            return False

        if resource not in self._usage:
            self._usage[resource] = {}
        if agent_id not in self._usage[resource]:
            self._usage[resource][agent_id] = deque()

        self._usage[resource][agent_id].append(
            UsageRecord(timestamp=self._get_current_time(), amount=amount)
        )
        return True

    def time_until_capacity(
        self, agent_id: str, resource: str, amount: float = 1.0
    ) -> float:
        """Estimate seconds until capacity is available.

        Calculates how long until enough old records expire to allow
        the requested amount.

        Args:
            agent_id: ID of the agent
            resource: Name of the resource
            amount: Amount needed (default: 1.0)

        Returns:
            Estimated seconds until capacity available (0.0 if already available)
        """
        if amount <= 0:
            return 0.0

        if self.has_capacity(agent_id, resource, amount):
            return 0.0

        self._clean_old_records(resource, agent_id)

        if resource not in self._usage or agent_id not in self._usage[resource]:
            return 0.0

        records = self._usage[resource][agent_id]
        if not records:
            return 0.0

        # Calculate how much needs to expire
        limit = self._limits.get(resource, float("inf"))
        current_usage = sum(r.amount for r in records)
        needed_to_expire = current_usage - (limit - amount)

        if needed_to_expire <= 0:
            return 0.0

        # Find when enough old records will expire (FIFO order)
        current_time = self._get_current_time()
        accumulated = 0.0
        for record in records:
            accumulated += record.amount
            if accumulated >= needed_to_expire:
                # This record's expiry time
                expiry_time = record.timestamp + self.window_seconds
                return max(0.0, expiry_time - current_time)

        # All records need to expire - return time until last one expires
        return max(0.0, records[-1].timestamp + self.window_seconds - current_time)

    async def wait_for_capacity(
        self,
        agent_id: str,
        resource: str,
        amount: float = 1.0,
        timeout: float | None = None,
        poll_interval: float = 0.1,
    ) -> bool:
        """Wait until capacity is available.

        Blocks asynchronously until the agent has enough capacity for the
        requested amount, or until timeout is reached.

        Args:
            agent_id: ID of the agent
            resource: Name of the resource
            amount: Amount needed (default: 1.0)
            timeout: Maximum seconds to wait (None = wait indefinitely)
            poll_interval: How often to check for capacity (default: 0.1s)

        Returns:
            True if capacity was acquired, False if timeout occurred
        """
        if amount <= 0:
            return True

        start = self._get_current_time()

        while not self.has_capacity(agent_id, resource, amount):
            if timeout is not None and (self._get_current_time() - start) >= timeout:
                return False

            # Calculate intelligent sleep time
            wait_estimate = self.time_until_capacity(agent_id, resource, amount)
            if wait_estimate > 0:
                # Sleep for the estimated time, but cap at poll_interval for responsiveness
                sleep_time = min(wait_estimate, poll_interval)
            else:
                sleep_time = poll_interval

            await self._sleep(sleep_time)

        # Consume the capacity
        return self.consume(agent_id, resource, amount)

    def reset(self, agent_id: str | None = None, resource: str | None = None) -> None:
        """Reset usage records.

        Can reset all records, all records for an agent, all records for a
        resource, or records for a specific agent-resource combination.

        Args:
            agent_id: If provided, only reset records for this agent
            resource: If provided, only reset records for this resource
        """
        if resource is not None and agent_id is not None:
            # Reset specific agent-resource combination
            if resource in self._usage and agent_id in self._usage[resource]:
                self._usage[resource][agent_id].clear()
        elif resource is not None:
            # Reset all agents for this resource
            if resource in self._usage:
                self._usage[resource].clear()
        elif agent_id is not None:
            # Reset all resources for this agent
            for res in self._usage:
                if agent_id in self._usage[res]:
                    self._usage[res][agent_id].clear()
        else:
            # Reset everything
            for res in self._usage:
                self._usage[res].clear()

    def get_all_usage(self) -> dict[str, dict[str, float]]:
        """Get snapshot of all current usage.

        Returns:
            Dict mapping resource -> agent_id -> current usage
            Only includes resources and agents with non-zero usage.
        """
        result: dict[str, dict[str, float]] = {}
        for resource in self._usage:
            resource_usage: dict[str, float] = {}
            for agent_id in self._usage[resource]:
                usage = self.get_usage(agent_id, resource)
                if usage > 0:
                    resource_usage[agent_id] = usage
            # Only include resource if it has any non-zero usage
            if resource_usage:
                result[resource] = resource_usage
        return result
