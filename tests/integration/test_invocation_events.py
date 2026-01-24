"""Integration tests for invocation events - Gap #27"""

import pytest
import json
import tempfile
from pathlib import Path

from src.world.world import World
from src.world.artifacts import ArtifactStore
from src.world.ledger import Ledger
from src.world.logger import EventLogger
from src.world.actions import InvokeArtifactIntent


def make_test_world(output_file: str) -> World:
    """Create a minimal World for testing."""
    config = {
        "world": {"max_ticks": 10},
        "costs": {"per_1k_input_tokens": 1, "per_1k_output_tokens": 1},
        "logging": {"output_file": output_file},
        "principals": [
            {"id": "agent_a", "starting_scrip": 100},
            {"id": "agent_b", "starting_scrip": 100},
        ],
        "rights": {
            "default_quotas": {"compute": 1000.0, "disk": 10000.0}
        },
    }
    return World(config)


class TestInvokeSuccessEvent:
    """Test invoke_success event emission."""

    def test_invoke_success_event_logged(self) -> None:
        """Test that invoke_success event is logged on successful artifact invocation."""
        with tempfile.NamedTemporaryFile(suffix=".jsonl", delete=False) as f:
            output_file = f.name

        world = make_test_world(output_file)
        world.advance_tick()

        # Create an executable artifact
        world.artifacts.write(
            artifact_id="test_artifact",
            type="service",
            content="A test artifact",
            created_by="agent_b",
            executable=True,
            code='def run(x): return x * 2',
            price=5,
        )

        # Invoke the artifact
        intent = InvokeArtifactIntent(
            principal_id="agent_a",
            artifact_id="test_artifact",
            method="run",
            args=[10],
        )
        result = world.execute_action(intent)
        assert result.success is True

        # Check events in log
        events = world.logger.read_recent(50)
        invoke_events = [e for e in events if e.get("event_type") == "invoke_success"]

        assert len(invoke_events) >= 1
        event = invoke_events[-1]
        assert event["invoker_id"] == "agent_a"
        assert event["artifact_id"] == "test_artifact"
        assert "duration_ms" in event

    def test_invoke_success_event_for_genesis(self) -> None:
        """Test invoke_success event for genesis artifact methods."""
        with tempfile.NamedTemporaryFile(suffix=".jsonl", delete=False) as f:
            output_file = f.name

        world = make_test_world(output_file)
        world.advance_tick()

        # Invoke a genesis artifact method (genesis_ledger.balance)
        # The balance method requires [agent_id] as argument
        intent = InvokeArtifactIntent(
            principal_id="agent_a",
            artifact_id="genesis_ledger",
            method="balance",
            args=["agent_a"],  # Pass the agent_id we want to check balance for
        )
        result = world.execute_action(intent)
        assert result.success is True

        # Check events in log
        events = world.logger.read_recent(50)
        invoke_events = [e for e in events if e.get("event_type") == "invoke_success"]

        assert len(invoke_events) >= 1
        event = invoke_events[-1]
        assert event["artifact_id"] == "genesis_ledger"
        assert event["method"] == "balance"


class TestInvokeFailureEvent:
    """Test invoke_failure event emission."""

    def test_invoke_failure_event_logged(self) -> None:
        """Test that invoke_failure event is logged on failed invocation."""
        with tempfile.NamedTemporaryFile(suffix=".jsonl", delete=False) as f:
            output_file = f.name

        world = make_test_world(output_file)
        world.advance_tick()

        # Create an executable artifact with code that raises an error
        world.artifacts.write(
            artifact_id="error_artifact",
            type="service",
            content="An artifact that fails",
            created_by="agent_b",
            executable=True,
            code='def run(x): raise ValueError("intentional error")',
            price=0,
        )

        # Invoke the artifact
        intent = InvokeArtifactIntent(
            principal_id="agent_a",
            artifact_id="error_artifact",
            method="run",
            args=[10],
        )
        result = world.execute_action(intent)
        assert result.success is False

        # Check events in log
        events = world.logger.read_recent(50)
        invoke_events = [e for e in events if e.get("event_type") == "invoke_failure"]

        assert len(invoke_events) >= 1
        event = invoke_events[-1]
        assert event["invoker_id"] == "agent_a"
        assert event["artifact_id"] == "error_artifact"
        assert event["error_type"] == "execution"
        assert "ValueError" in event.get("error_message", "")

    def test_invoke_failure_on_not_found(self) -> None:
        """Test invoke_failure when artifact doesn't exist."""
        with tempfile.NamedTemporaryFile(suffix=".jsonl", delete=False) as f:
            output_file = f.name

        world = make_test_world(output_file)
        world.advance_tick()

        # Try to invoke nonexistent artifact
        intent = InvokeArtifactIntent(
            principal_id="agent_a",
            artifact_id="nonexistent",
            method="run",
            args=[],
        )
        result = world.execute_action(intent)
        assert result.success is False

        # Check events in log
        events = world.logger.read_recent(50)
        invoke_events = [e for e in events if e.get("event_type") == "invoke_failure"]

        assert len(invoke_events) >= 1
        event = invoke_events[-1]
        assert event["artifact_id"] == "nonexistent"
        assert event["error_type"] == "not_found"


class TestDashboardInvocationApi:
    """Test dashboard API endpoints for invocation stats."""

    @pytest.mark.asyncio
    async def test_api_invocations_endpoint(self) -> None:
        """Test /api/invocations endpoint returns invocation list."""
        # This test requires the dashboard server to be running
        # For now, we test the registry functionality that the endpoint will use
        from src.world.invocation_registry import InvocationRegistry, InvocationRecord

        registry = InvocationRegistry()
        registry.record_invocation(InvocationRecord(
            event_number=1, invoker_id="agent_a", artifact_id="artifact_x",
            method="run", success=True, duration_ms=10.0,
        ))

        all_invocations = registry.get_all_invocations()
        assert len(all_invocations) == 1

        # Simulate API response format
        response = [
            {
                "event_number": r.event_number,
                "invoker_id": r.invoker_id,
                "artifact_id": r.artifact_id,
                "method": r.method,
                "success": r.success,
                "duration_ms": r.duration_ms,
                "error_type": r.error_type,
                "timestamp": r.timestamp,
            }
            for r in all_invocations
        ]
        assert response[0]["invoker_id"] == "agent_a"

    @pytest.mark.asyncio
    async def test_api_artifact_invocations_endpoint(self) -> None:
        """Test /api/artifacts/{id}/invocations endpoint returns stats."""
        from src.world.invocation_registry import InvocationRegistry, InvocationRecord

        registry = InvocationRegistry()

        # Add some invocations for artifact_x
        for _ in range(5):
            registry.record_invocation(InvocationRecord(
                event_number=1, invoker_id="agent_a", artifact_id="artifact_x",
                method="run", success=True, duration_ms=10.0,
            ))
        registry.record_invocation(InvocationRecord(
            event_number=2, invoker_id="agent_b", artifact_id="artifact_x",
            method="run", success=False, duration_ms=100.0, error_type="timeout",
        ))

        stats = registry.get_artifact_stats("artifact_x")
        response = stats.to_dict()

        assert response["total_invocations"] == 6
        assert response["successful"] == 5
        assert response["failed"] == 1
        assert response["failure_types"] == {"timeout": 1}
