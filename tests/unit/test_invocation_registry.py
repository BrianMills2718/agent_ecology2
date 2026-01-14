"""Unit tests for InvocationRegistry - Gap #27"""

import pytest
from datetime import datetime

from src.world.invocation_registry import (
    InvocationRecord,
    InvocationRegistry,
    InvocationStats,
)


class TestInvocationRecord:
    """Test InvocationRecord dataclass."""

    def test_create_success_record(self) -> None:
        """Test creating a successful invocation record."""
        record = InvocationRecord(
            tick=42,
            invoker_id="agent_alice",
            artifact_id="contract_foo",
            method="execute",
            success=True,
            duration_ms=15.5,
            timestamp="2026-01-13T10:30:00.015Z",
        )
        assert record.tick == 42
        assert record.invoker_id == "agent_alice"
        assert record.artifact_id == "contract_foo"
        assert record.method == "execute"
        assert record.success is True
        assert record.duration_ms == 15.5
        assert record.error_type is None

    def test_create_failure_record(self) -> None:
        """Test creating a failed invocation record."""
        record = InvocationRecord(
            tick=42,
            invoker_id="agent_alice",
            artifact_id="contract_foo",
            method="execute",
            success=False,
            duration_ms=5000.0,
            error_type="timeout",
            timestamp="2026-01-13T10:30:05.000Z",
        )
        assert record.success is False
        assert record.error_type == "timeout"


class TestInvocationRegistry:
    """Test InvocationRegistry core functionality."""

    def test_record_invocation(self) -> None:
        """Test that invocations are recorded correctly."""
        registry = InvocationRegistry()
        record = InvocationRecord(
            tick=1,
            invoker_id="agent_a",
            artifact_id="artifact_x",
            method="run",
            success=True,
            duration_ms=10.0,
        )
        registry.record_invocation(record)

        # Should be retrievable
        history = registry.get_invoker_history("agent_a")
        assert len(history) == 1
        assert history[0].artifact_id == "artifact_x"

    def test_get_artifact_stats(self) -> None:
        """Test stats calculation for an artifact."""
        registry = InvocationRegistry()

        # Add some invocations
        for i in range(8):
            registry.record_invocation(InvocationRecord(
                tick=i,
                invoker_id="agent_a",
                artifact_id="artifact_x",
                method="run",
                success=True,
                duration_ms=10.0 + i,
            ))

        # Add 2 failures
        registry.record_invocation(InvocationRecord(
            tick=8,
            invoker_id="agent_a",
            artifact_id="artifact_x",
            method="run",
            success=False,
            duration_ms=5000.0,
            error_type="timeout",
        ))
        registry.record_invocation(InvocationRecord(
            tick=9,
            invoker_id="agent_b",
            artifact_id="artifact_x",
            method="run",
            success=False,
            duration_ms=100.0,
            error_type="validation",
        ))

        stats = registry.get_artifact_stats("artifact_x")
        assert stats.total_invocations == 10
        assert stats.successful == 8
        assert stats.failed == 2
        assert stats.success_rate == 0.8

    def test_success_rate_calculation(self) -> None:
        """Test that success rate is calculated correctly."""
        registry = InvocationRegistry()

        # 3 successes, 1 failure = 75% success rate
        for success in [True, True, True, False]:
            registry.record_invocation(InvocationRecord(
                tick=0,
                invoker_id="agent_a",
                artifact_id="artifact_x",
                method="run",
                success=success,
                duration_ms=10.0,
                error_type=None if success else "execution",
            ))

        stats = registry.get_artifact_stats("artifact_x")
        assert stats.success_rate == 0.75

    def test_success_rate_no_invocations(self) -> None:
        """Test success rate when no invocations exist."""
        registry = InvocationRegistry()
        stats = registry.get_artifact_stats("nonexistent")
        assert stats.success_rate == 0.0
        assert stats.total_invocations == 0

    def test_filter_by_invoker(self) -> None:
        """Test filtering invocations by invoker."""
        registry = InvocationRegistry()

        # Add invocations from different invokers
        registry.record_invocation(InvocationRecord(
            tick=1, invoker_id="agent_a", artifact_id="artifact_x",
            method="run", success=True, duration_ms=10.0,
        ))
        registry.record_invocation(InvocationRecord(
            tick=2, invoker_id="agent_b", artifact_id="artifact_x",
            method="run", success=True, duration_ms=10.0,
        ))
        registry.record_invocation(InvocationRecord(
            tick=3, invoker_id="agent_a", artifact_id="artifact_y",
            method="run", success=True, duration_ms=10.0,
        ))

        # Filter by agent_a
        history = registry.get_invoker_history("agent_a")
        assert len(history) == 2
        assert all(r.invoker_id == "agent_a" for r in history)

        # Filter by agent_b
        history_b = registry.get_invoker_history("agent_b")
        assert len(history_b) == 1

    def test_failure_type_counts(self) -> None:
        """Test that failure types are categorized correctly."""
        registry = InvocationRegistry()

        # Add failures with different error types
        registry.record_invocation(InvocationRecord(
            tick=1, invoker_id="agent_a", artifact_id="artifact_x",
            method="run", success=False, duration_ms=5000.0,
            error_type="timeout",
        ))
        registry.record_invocation(InvocationRecord(
            tick=2, invoker_id="agent_a", artifact_id="artifact_x",
            method="run", success=False, duration_ms=5.0,
            error_type="validation",
        ))
        registry.record_invocation(InvocationRecord(
            tick=3, invoker_id="agent_a", artifact_id="artifact_x",
            method="run", success=False, duration_ms=5000.0,
            error_type="timeout",
        ))
        registry.record_invocation(InvocationRecord(
            tick=4, invoker_id="agent_a", artifact_id="artifact_x",
            method="run", success=True, duration_ms=10.0,
        ))

        stats = registry.get_artifact_stats("artifact_x")
        assert stats.failure_types == {"timeout": 2, "validation": 1}

    def test_avg_duration_calculation(self) -> None:
        """Test average duration calculation."""
        registry = InvocationRegistry()

        # Add invocations with known durations: 10, 20, 30 ms = avg 20ms
        for duration in [10.0, 20.0, 30.0]:
            registry.record_invocation(InvocationRecord(
                tick=0, invoker_id="agent_a", artifact_id="artifact_x",
                method="run", success=True, duration_ms=duration,
            ))

        stats = registry.get_artifact_stats("artifact_x")
        assert stats.avg_duration_ms == 20.0

    def test_history_limit(self) -> None:
        """Test that history respects limit parameter."""
        registry = InvocationRegistry()

        # Add 10 invocations
        for i in range(10):
            registry.record_invocation(InvocationRecord(
                tick=i, invoker_id="agent_a", artifact_id="artifact_x",
                method="run", success=True, duration_ms=10.0,
            ))

        # Get with limit
        history = registry.get_invoker_history("agent_a", limit=5)
        assert len(history) == 5

    def test_get_all_invocations(self) -> None:
        """Test getting all invocations with filters."""
        registry = InvocationRegistry()

        # Add various invocations
        registry.record_invocation(InvocationRecord(
            tick=1, invoker_id="agent_a", artifact_id="artifact_x",
            method="run", success=True, duration_ms=10.0,
        ))
        registry.record_invocation(InvocationRecord(
            tick=2, invoker_id="agent_b", artifact_id="artifact_y",
            method="run", success=False, duration_ms=100.0,
            error_type="execution",
        ))

        # Get all
        all_records = registry.get_all_invocations()
        assert len(all_records) == 2

        # Filter by artifact
        x_records = registry.get_all_invocations(artifact_id="artifact_x")
        assert len(x_records) == 1
        assert x_records[0].artifact_id == "artifact_x"

        # Filter by success
        failed = registry.get_all_invocations(success=False)
        assert len(failed) == 1
        assert failed[0].success is False

    def test_clear_registry(self) -> None:
        """Test clearing the registry."""
        registry = InvocationRegistry()

        # Add some invocations
        registry.record_invocation(InvocationRecord(
            tick=1, invoker_id="agent_a", artifact_id="artifact_x",
            method="run", success=True, duration_ms=10.0,
        ))

        # Clear
        registry.clear()

        # Should be empty
        assert len(registry.get_all_invocations()) == 0
        stats = registry.get_artifact_stats("artifact_x")
        assert stats.total_invocations == 0


class TestInvocationStats:
    """Test InvocationStats dataclass."""

    def test_stats_to_dict(self) -> None:
        """Test converting stats to dict for API response."""
        stats = InvocationStats(
            total_invocations=100,
            successful=95,
            failed=5,
            success_rate=0.95,
            avg_duration_ms=12.5,
            failure_types={"timeout": 3, "validation": 2},
        )

        d = stats.to_dict()
        assert d["total_invocations"] == 100
        assert d["successful"] == 95
        assert d["failed"] == 5
        assert d["success_rate"] == 0.95
        assert d["avg_duration_ms"] == 12.5
        assert d["failure_types"] == {"timeout": 3, "validation": 2}
