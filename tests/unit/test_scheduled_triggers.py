"""Tests for Plan #185: Time-Based Scheduling for Triggers.

These tests verify:
1. TriggerSpec scheduling fields work correctly
2. TriggerRegistry schedules and fires triggers at correct events
3. Scheduled triggers can be cancelled
4. World integration fires scheduled triggers on event increment
"""

import pytest
from unittest.mock import MagicMock

from src.world.triggers import TriggerSpec, TriggerRegistry


class TestTriggerSpecScheduling:
    """Test TriggerSpec scheduling fields and methods."""

    def test_is_scheduled_with_fire_at_event(self) -> None:
        """Trigger with fire_at_event is scheduled."""
        spec = TriggerSpec(
            trigger_id="t1",
            owner="agent1",
            filter={},
            callback_artifact="cb1",
            fire_at_event=100,
        )
        assert spec.is_scheduled is True

    def test_is_scheduled_with_fire_after_events(self) -> None:
        """Trigger with fire_after_events is scheduled."""
        spec = TriggerSpec(
            trigger_id="t1",
            owner="agent1",
            filter={},
            callback_artifact="cb1",
            fire_after_events=50,
            registered_at_event=10,
        )
        assert spec.is_scheduled is True

    def test_is_scheduled_event_based(self) -> None:
        """Trigger without scheduling fields is event-based."""
        spec = TriggerSpec(
            trigger_id="t1",
            owner="agent1",
            filter={"event_type": "artifact_created"},
            callback_artifact="cb1",
        )
        assert spec.is_scheduled is False

    def test_get_fire_event_absolute(self) -> None:
        """get_fire_event returns fire_at_event when set."""
        spec = TriggerSpec(
            trigger_id="t1",
            owner="agent1",
            filter={},
            callback_artifact="cb1",
            fire_at_event=100,
        )
        assert spec.get_fire_event() == 100

    def test_get_fire_event_relative(self) -> None:
        """get_fire_event calculates from fire_after_events."""
        spec = TriggerSpec(
            trigger_id="t1",
            owner="agent1",
            filter={},
            callback_artifact="cb1",
            fire_after_events=50,
            registered_at_event=10,
        )
        assert spec.get_fire_event() == 60  # 10 + 50

    def test_get_fire_event_none_for_event_based(self) -> None:
        """get_fire_event returns None for event-based triggers."""
        spec = TriggerSpec(
            trigger_id="t1",
            owner="agent1",
            filter={"event_type": "test"},
            callback_artifact="cb1",
        )
        assert spec.get_fire_event() is None


class TestTriggerRegistryScheduling:
    """Test TriggerRegistry scheduled trigger management."""

    @pytest.fixture
    def mock_store(self) -> MagicMock:
        """Create a mock artifact store."""
        store = MagicMock()
        store.artifacts = {}
        store.get = lambda aid: store.artifacts.get(aid)
        return store

    @pytest.fixture
    def registry(self, mock_store: MagicMock) -> TriggerRegistry:
        """Create a trigger registry with mock store."""
        return TriggerRegistry(mock_store)

    def test_set_current_event_number(self, registry: TriggerRegistry) -> None:
        """Registry tracks current event number."""
        registry.set_current_event_number(42)
        assert registry._current_event_number == 42

    def test_schedule_trigger_absolute(self, registry: TriggerRegistry) -> None:
        """Schedule trigger at absolute event number."""
        registry.set_current_event_number(10)
        spec = TriggerSpec(
            trigger_id="t1",
            owner="agent1",
            filter={},
            callback_artifact="cb1",
        )
        result = registry.schedule_trigger(spec, at_event=50)
        assert result is True
        assert registry.get_scheduled_count() == 1
        assert len(registry.get_scheduled_triggers(50)) == 1

    def test_schedule_trigger_relative(self, registry: TriggerRegistry) -> None:
        """Schedule trigger with relative delay."""
        registry.set_current_event_number(10)
        spec = TriggerSpec(
            trigger_id="t1",
            owner="agent1",
            filter={},
            callback_artifact="cb1",
        )
        result = registry.schedule_trigger(spec, after_events=30)
        assert result is True
        assert len(registry.get_scheduled_triggers(40)) == 1  # 10 + 30

    def test_schedule_trigger_past_fails(self, registry: TriggerRegistry) -> None:
        """Cannot schedule trigger in the past."""
        registry.set_current_event_number(100)
        spec = TriggerSpec(
            trigger_id="t1",
            owner="agent1",
            filter={},
            callback_artifact="cb1",
        )
        result = registry.schedule_trigger(spec, at_event=50)
        assert result is False
        assert registry.get_scheduled_count() == 0

    def test_fire_scheduled_triggers(self, registry: TriggerRegistry) -> None:
        """Firing scheduled triggers queues invocations."""
        registry.set_current_event_number(10)
        spec = TriggerSpec(
            trigger_id="t1",
            owner="agent1",
            filter={},
            callback_artifact="cb1",
            callback_method="on_schedule",
        )
        registry.schedule_trigger(spec, at_event=20)

        # Fire at event 20
        count = registry.fire_scheduled_triggers(20)
        assert count == 1

        # Check invocation was queued
        pending = registry.get_pending_invocations()
        assert len(pending) == 1
        assert pending[0]["trigger_id"] == "t1"
        assert pending[0]["callback_artifact"] == "cb1"
        assert pending[0]["callback_method"] == "on_schedule"
        assert pending[0]["event"]["event_type"] == "scheduled"

    def test_fire_removes_from_schedule(self, registry: TriggerRegistry) -> None:
        """Fired triggers are removed from schedule."""
        registry.set_current_event_number(10)
        spec = TriggerSpec(
            trigger_id="t1",
            owner="agent1",
            filter={},
            callback_artifact="cb1",
        )
        registry.schedule_trigger(spec, at_event=20)
        assert registry.get_scheduled_count() == 1

        registry.fire_scheduled_triggers(20)
        assert registry.get_scheduled_count() == 0

    def test_fire_multiple_same_event(self, registry: TriggerRegistry) -> None:
        """Multiple triggers at same event all fire."""
        registry.set_current_event_number(10)
        for i in range(3):
            spec = TriggerSpec(
                trigger_id=f"t{i}",
                owner="agent1",
                filter={},
                callback_artifact=f"cb{i}",
            )
            registry.schedule_trigger(spec, at_event=20)

        count = registry.fire_scheduled_triggers(20)
        assert count == 3
        assert len(registry.get_pending_invocations()) == 3

    def test_cancel_scheduled_trigger(self, registry: TriggerRegistry) -> None:
        """Cancel removes trigger from schedule."""
        registry.set_current_event_number(10)
        spec = TriggerSpec(
            trigger_id="t1",
            owner="agent1",
            filter={},
            callback_artifact="cb1",
        )
        registry.schedule_trigger(spec, at_event=50)
        assert registry.get_scheduled_count() == 1

        result = registry.cancel_scheduled_trigger("t1")
        assert result is True
        assert registry.get_scheduled_count() == 0

    def test_cancel_nonexistent_trigger(self, registry: TriggerRegistry) -> None:
        """Cancelling nonexistent trigger returns False."""
        result = registry.cancel_scheduled_trigger("nonexistent")
        assert result is False


class TestTriggerRegistryRefreshScheduled:
    """Test refresh() handling of scheduled trigger artifacts."""

    @pytest.fixture
    def mock_artifact(self) -> MagicMock:
        """Create a mock artifact."""
        artifact = MagicMock()
        artifact.id = "trigger1"
        artifact.type = "trigger"
        artifact.deleted = False
        artifact.created_by = "agent1"
        artifact.metadata = {}  # Will be set per-test
        return artifact

    @pytest.fixture
    def mock_callback(self) -> MagicMock:
        """Create a mock callback artifact."""
        callback = MagicMock()
        callback.id = "callback1"
        callback.created_by = "agent1"  # Same owner
        # ADR-0028: triggers check writer/principal from state
        callback.state = {"writer": "agent1"}
        return callback

    @pytest.fixture
    def mock_store(
        self, mock_artifact: MagicMock, mock_callback: MagicMock
    ) -> MagicMock:
        """Create store with trigger and callback."""
        store = MagicMock()
        store.artifacts = {"trigger1": mock_artifact, "callback1": mock_callback}
        store.get = lambda aid: store.artifacts.get(aid)
        return store

    def test_refresh_scheduled_trigger(
        self,
        mock_store: MagicMock,
        mock_artifact: MagicMock,
    ) -> None:
        """Refresh picks up scheduled trigger from artifact."""
        mock_artifact.metadata = {
            "enabled": True,
            "callback_artifact": "callback1",
            "fire_at_event": 100,
        }
        mock_artifact.state = {"writer": "agent1"}

        registry = TriggerRegistry(mock_store)
        registry.set_current_event_number(50)
        registry.refresh()

        # Should be in scheduled, not active
        assert len(registry.active_triggers) == 0
        assert registry.get_scheduled_count() == 1
        assert len(registry.get_scheduled_triggers(100)) == 1

    def test_refresh_event_based_trigger(
        self,
        mock_store: MagicMock,
        mock_artifact: MagicMock,
    ) -> None:
        """Refresh picks up event-based trigger."""
        mock_artifact.metadata = {
            "enabled": True,
            "callback_artifact": "callback1",
            "filter": {"event_type": "artifact_created"},
        }
        mock_artifact.state = {"writer": "agent1"}

        registry = TriggerRegistry(mock_store)
        registry.refresh()

        # Should be in active, not scheduled
        assert len(registry.active_triggers) == 1
        assert registry.get_scheduled_count() == 0

    def test_refresh_ignores_past_scheduled(
        self,
        mock_store: MagicMock,
        mock_artifact: MagicMock,
    ) -> None:
        """Refresh ignores scheduled triggers in the past."""
        mock_artifact.metadata = {
            "enabled": True,
            "callback_artifact": "callback1",
            "fire_at_event": 50,
        }
        mock_artifact.state = {"writer": "agent1"}

        registry = TriggerRegistry(mock_store)
        registry.set_current_event_number(100)  # Past event 50
        registry.refresh()

        # Should not be scheduled (already past)
        assert registry.get_scheduled_count() == 0


class TestWorldScheduledTriggerIntegration:
    """Test World integration with scheduled triggers."""

    def test_increment_event_fires_scheduled(self) -> None:
        """Incrementing event counter fires scheduled triggers."""
        # This is an integration test that requires World
        # Using mock to avoid full World setup
        from src.world.triggers import TriggerRegistry

        mock_store = MagicMock()
        mock_store.artifacts = {}
        mock_store.get = lambda aid: None

        registry = TriggerRegistry(mock_store)
        registry.set_current_event_number(9)

        # Schedule for event 10
        spec = TriggerSpec(
            trigger_id="t1",
            owner="agent1",
            filter={},
            callback_artifact="cb1",
        )
        registry.schedule_trigger(spec, at_event=10)

        # Simulate what increment_event_counter does
        registry.set_current_event_number(10)
        fired = registry.fire_scheduled_triggers(10)

        assert fired == 1
        assert len(registry.get_pending_invocations()) == 1
