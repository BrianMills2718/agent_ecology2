"""SimulationEngine - Physics calculations for agent ecology simulation.

Encapsulates all "physics" calculations that were previously scattered in run.py:
- Token-to-compute cost conversion
- API budget tracking
- Resource measurement

This is a pure calculator - it does NOT modify world/ledger state.
run.py remains responsible for orchestration and calling ledger mutations.

Usage:
    from world.simulation_engine import SimulationEngine

    engine = SimulationEngine.from_config(config)
    cost = engine.calculate_thinking_cost(input_tokens, output_tokens)

    # Track API spending
    budget_result = engine.track_api_cost(api_cost)
    if engine.is_budget_exhausted():
        # Save checkpoint and pause

    # Measure resource usage
    with measure_resources() as measurer:
        # do work
        measurer.record_disk_write(1024)
    usage = measurer.get_usage()
"""

from __future__ import annotations

import math
import time
import tracemalloc
from contextlib import contextmanager
from dataclasses import dataclass, field
from typing import Any, Generator, TypedDict


class ThinkingCostResult(TypedDict):
    """Result of calculating thinking cost."""

    input_cost: int
    output_cost: int
    total_cost: int


class BudgetCheckResult(TypedDict):
    """Result of budget check."""

    within_budget: bool
    cumulative_cost: float
    max_cost: float
    remaining: float


@dataclass
class SimulationEngine:
    """
    Physics engine for agent ecology simulation.

    Encapsulates all physics calculations:
    - Token-to-compute cost conversion
    - API budget tracking
    - Thinking affordability checks

    This is a pure calculator - it does not modify world state.
    run.py remains responsible for orchestration and state mutation.

    Attributes:
        rate_input: Compute cost per 1K input tokens (default: 1)
        rate_output: Compute cost per 1K output tokens (default: 3)
        max_api_cost: Maximum API cost in dollars, 0 = unlimited (default: 0)
        cumulative_api_cost: Running total of API costs (default: 0)
    """

    rate_input: int = 1
    rate_output: int = 3
    max_api_cost: float = 0.0
    cumulative_api_cost: float = field(default=0.0)

    @classmethod
    def from_config(cls, config: dict[str, Any]) -> SimulationEngine:
        """
        Factory method to create engine from config dict.

        Extracts relevant values from:
        - config["costs"]["per_1k_input_tokens"]
        - config["costs"]["per_1k_output_tokens"]
        - config["budget"]["max_api_cost"]

        Args:
            config: Configuration dictionary (typically from config.yaml)

        Returns:
            Configured SimulationEngine instance
        """
        costs = config.get("costs", {})
        budget = config.get("budget", {})

        return cls(
            rate_input=costs.get("per_1k_input_tokens", 1),
            rate_output=costs.get("per_1k_output_tokens", 3),
            max_api_cost=budget.get("max_api_cost", 0.0),
            cumulative_api_cost=0.0,
        )

    def calculate_thinking_cost(
        self, input_tokens: int, output_tokens: int
    ) -> ThinkingCostResult:
        """
        Calculate compute cost from token usage.

        Formula:
        - input_cost = ceil((input_tokens / 1000) * rate_input)
        - output_cost = ceil((output_tokens / 1000) * rate_output)

        Args:
            input_tokens: Number of input tokens used
            output_tokens: Number of output tokens generated

        Returns:
            ThinkingCostResult with input_cost, output_cost, total_cost
        """
        input_cost = math.ceil((input_tokens / 1000) * self.rate_input)
        output_cost = math.ceil((output_tokens / 1000) * self.rate_output)

        return {
            "input_cost": input_cost,
            "output_cost": output_cost,
            "total_cost": input_cost + output_cost,
        }

    def track_api_cost(self, api_cost: float) -> BudgetCheckResult:
        """
        Add API cost and check budget constraints.

        Updates cumulative_api_cost and returns budget status.

        Args:
            api_cost: Cost of API call in dollars

        Returns:
            BudgetCheckResult with budget status
        """
        self.cumulative_api_cost += api_cost

        if self.max_api_cost > 0:
            remaining = self.max_api_cost - self.cumulative_api_cost
            within_budget = self.cumulative_api_cost < self.max_api_cost
        else:
            remaining = float("inf")
            within_budget = True

        return {
            "within_budget": within_budget,
            "cumulative_cost": self.cumulative_api_cost,
            "max_cost": self.max_api_cost,
            "remaining": remaining,
        }

    def is_budget_exhausted(self) -> bool:
        """
        Check if API budget has been exhausted.

        Returns:
            True if max_api_cost > 0 and cumulative_api_cost >= max_api_cost
        """
        return self.max_api_cost > 0 and self.cumulative_api_cost >= self.max_api_cost

    def can_afford_thinking(
        self, available_compute: int, input_tokens: int, output_tokens: int
    ) -> tuple[bool, int]:
        """
        Check if agent can afford thinking cost.

        Args:
            available_compute: Agent's current compute balance
            input_tokens: Expected input tokens
            output_tokens: Expected output tokens

        Returns:
            (can_afford, cost): Tuple of whether affordable and the cost amount
        """
        result = self.calculate_thinking_cost(input_tokens, output_tokens)
        return (available_compute >= result["total_cost"], result["total_cost"])

    def reset_budget(self, starting_cost: float = 0.0) -> None:
        """
        Reset cumulative API cost (for checkpoint resume).

        Args:
            starting_cost: Starting cumulative cost (from checkpoint)
        """
        self.cumulative_api_cost = starting_cost

    def get_rates(self) -> tuple[int, int]:
        """
        Get token rates for passing to ledger.deduct_thinking_cost().

        Returns:
            (rate_input, rate_output): Token rates tuple
        """
        return (self.rate_input, self.rate_output)


@dataclass
class ResourceUsage:
    """
    Measured resource usage from action execution.

    Captures CPU time, memory, and disk usage for observability
    and resource accounting.

    Attributes:
        cpu_seconds: CPU time consumed (process-level measurement)
        peak_memory_bytes: Peak memory usage during execution
        disk_bytes_written: Total bytes written to disk
    """

    cpu_seconds: float = 0.0
    peak_memory_bytes: int = 0
    disk_bytes_written: int = 0

    def to_dict(self) -> dict[str, float | int]:
        """Convert to dictionary for serialization."""
        return {
            "cpu_seconds": self.cpu_seconds,
            "peak_memory_bytes": self.peak_memory_bytes,
            "disk_bytes_written": self.disk_bytes_written,
        }


class ResourceMeasurer:
    """
    Context manager for measuring resource usage during execution.

    Measures:
    - CPU time via time.process_time() (process-level, not isolated)
    - Peak memory via tracemalloc
    - Disk writes via explicit recording

    Usage:
        with ResourceMeasurer() as measurer:
            # ... do work ...
            measurer.record_disk_write(1024)
        usage = measurer.get_usage()

    Note: This provides process-level measurement. For true per-action
    isolation, ProcessPoolExecutor would be needed (future enhancement).
    """

    def __init__(self) -> None:
        self._start_cpu: float = 0.0
        self._end_cpu: float = 0.0
        self._start_memory: int = 0
        self._peak_memory: int = 0
        self._disk_bytes: int = 0
        self._tracemalloc_was_running: bool = False

    def __enter__(self) -> "ResourceMeasurer":
        """Start measuring resources."""
        self._start_cpu = time.process_time()

        # Handle tracemalloc state carefully
        self._tracemalloc_was_running = tracemalloc.is_tracing()
        if not self._tracemalloc_was_running:
            tracemalloc.start()

        # Reset peak and get baseline
        tracemalloc.reset_peak()
        current, _ = tracemalloc.get_traced_memory()
        self._start_memory = current

        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: object,
    ) -> None:
        """Stop measuring and capture final values."""
        self._end_cpu = time.process_time()
        _, self._peak_memory = tracemalloc.get_traced_memory()

        # Restore original tracemalloc state
        if not self._tracemalloc_was_running:
            tracemalloc.stop()

    def record_disk_write(self, bytes_written: int) -> None:
        """
        Record bytes written to disk.

        Call this when performing disk writes to track total I/O.

        Args:
            bytes_written: Number of bytes written
        """
        self._disk_bytes += bytes_written

    def get_usage(self) -> ResourceUsage:
        """
        Get the measured resource usage.

        Returns:
            ResourceUsage with cpu_seconds, peak_memory_bytes, disk_bytes_written
        """
        return ResourceUsage(
            cpu_seconds=max(0.0, self._end_cpu - self._start_cpu),
            peak_memory_bytes=max(0, self._peak_memory - self._start_memory),
            disk_bytes_written=self._disk_bytes,
        )


@contextmanager
def measure_resources() -> Generator[ResourceMeasurer, None, None]:
    """
    Convenience function for measuring resource usage.

    Usage:
        with measure_resources() as measurer:
            # ... do work ...
            measurer.record_disk_write(1024)
        usage = measurer.get_usage()

    Yields:
        ResourceMeasurer instance for recording disk writes and getting results
    """
    measurer = ResourceMeasurer()
    with measurer:
        yield measurer


__all__ = [
    "SimulationEngine",
    "ThinkingCostResult",
    "BudgetCheckResult",
    "ResourceUsage",
    "ResourceMeasurer",
    "measure_resources",
]
