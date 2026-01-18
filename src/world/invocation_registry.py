"""Invocation Registry - Track invocation history for observability (Gap #27)

This module provides:
1. InvocationRecord - Data class for a single invocation
2. InvocationStats - Aggregated statistics for an artifact
3. InvocationRegistry - In-memory registry tracking all invocations

The registry is read-only for external consumers - it observes but doesn't
affect invocation behavior. This enables emergent reputation without
prescribing how reputation should be computed.

Key design decisions:
- Observability only: We track, not enforce
- In-memory registry: Events persist to log, registry is per-session
- No reputation algorithm: Agents decide what stats matter to them
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any


@dataclass
class InvocationRecord:
    """Record of a single artifact invocation.

    Attributes:
        tick: Simulation tick when invocation occurred
        invoker_id: Principal ID of the caller
        artifact_id: ID of the artifact being invoked
        method: Method name being called (for genesis artifacts)
        success: Whether the invocation succeeded
        duration_ms: Execution time in milliseconds
        error_type: Type of error if failed (timeout, validation, execution, etc.)
        timestamp: ISO timestamp of invocation
    """
    tick: int
    invoker_id: str
    artifact_id: str
    method: str
    success: bool
    duration_ms: float
    error_type: str | None = None
    timestamp: str = ""

    def __post_init__(self) -> None:
        """Set timestamp if not provided."""
        if not self.timestamp:
            self.timestamp = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for API responses."""
        return {
            "tick": self.tick,
            "invoker_id": self.invoker_id,
            "artifact_id": self.artifact_id,
            "method": self.method,
            "success": self.success,
            "duration_ms": self.duration_ms,
            "error_type": self.error_type,
            "timestamp": self.timestamp,
        }


@dataclass
class InvocationStats:
    """Aggregated invocation statistics for an artifact.

    Attributes:
        total_invocations: Total number of invocations
        successful: Number of successful invocations
        failed: Number of failed invocations
        success_rate: Ratio of successful to total (0.0-1.0)
        avg_duration_ms: Average execution time in milliseconds
        failure_types: Count of each failure type
    """
    total_invocations: int = 0
    successful: int = 0
    failed: int = 0
    success_rate: float = 0.0
    avg_duration_ms: float = 0.0
    failure_types: dict[str, int] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for API responses."""
        return {
            "total_invocations": self.total_invocations,
            "successful": self.successful,
            "failed": self.failed,
            "success_rate": self.success_rate,
            "avg_duration_ms": self.avg_duration_ms,
            "failure_types": self.failure_types,
        }


class InvocationRegistry:
    """In-memory registry tracking invocation history.

    Provides queryable access to invocation records and statistics.
    Records are stored in memory - events are also logged to the
    event stream for persistence.

    Usage:
        registry = InvocationRegistry()
        registry.record_invocation(record)
        stats = registry.get_artifact_stats("my_artifact")
    """

    _records: list[InvocationRecord]

    def __init__(self) -> None:
        """Initialize an empty registry."""
        self._records = []

    def record_invocation(self, record: InvocationRecord) -> None:
        """Add an invocation record to the registry.

        Args:
            record: The invocation record to store
        """
        self._records.append(record)

    def get_artifact_stats(self, artifact_id: str) -> InvocationStats:
        """Get aggregated statistics for an artifact.

        Args:
            artifact_id: The artifact to get stats for

        Returns:
            InvocationStats with success rate, duration, failure types, etc.
        """
        relevant = [r for r in self._records if r.artifact_id == artifact_id]

        if not relevant:
            return InvocationStats()

        successful = sum(1 for r in relevant if r.success)
        failed = len(relevant) - successful
        total = len(relevant)

        # Calculate average duration
        total_duration = sum(r.duration_ms for r in relevant)
        avg_duration = total_duration / total if total > 0 else 0.0

        # Count failure types
        failure_types: dict[str, int] = {}
        for r in relevant:
            if not r.success and r.error_type:
                failure_types[r.error_type] = failure_types.get(r.error_type, 0) + 1

        return InvocationStats(
            total_invocations=total,
            successful=successful,
            failed=failed,
            success_rate=successful / total if total > 0 else 0.0,
            avg_duration_ms=avg_duration,
            failure_types=failure_types,
        )

    def get_invoker_history(
        self,
        invoker_id: str,
        limit: int = 100,
    ) -> list[InvocationRecord]:
        """Get recent invocations by a specific invoker.

        Args:
            invoker_id: The invoker to get history for
            limit: Maximum number of records to return

        Returns:
            List of invocation records, most recent first
        """
        relevant = [r for r in self._records if r.invoker_id == invoker_id]
        # Return most recent first, limited
        return relevant[-limit:][::-1] if relevant else []

    def get_all_invocations(
        self,
        artifact_id: str | None = None,
        invoker_id: str | None = None,
        success: bool | None = None,
        limit: int = 100,
    ) -> list[InvocationRecord]:
        """Get filtered invocation records.

        Args:
            artifact_id: Filter by artifact (optional)
            invoker_id: Filter by invoker (optional)
            success: Filter by success status (optional)
            limit: Maximum number of records to return

        Returns:
            List of matching invocation records
        """
        results = self._records

        if artifact_id is not None:
            results = [r for r in results if r.artifact_id == artifact_id]

        if invoker_id is not None:
            results = [r for r in results if r.invoker_id == invoker_id]

        if success is not None:
            results = [r for r in results if r.success == success]

        return results[-limit:] if results else []

    def clear(self) -> None:
        """Clear all invocation records.

        Useful for testing or resetting state between simulation runs.
        """
        self._records = []

    def count(self) -> int:
        """Get total number of recorded invocations."""
        return len(self._records)
