"""Tests for Plan #169: Kernel Event Triggers.

Tests that agents can register triggers to be invoked when events occur.
"""

import pytest
from typing import Any

from src.world.artifacts import ArtifactStore
from src.world.triggers import TriggerRegistry, TriggerSpec, matches_filter


class TestFilterMatching:
    """Test event filter matching logic."""

    def test_simple_equality(self) -> None:
        """Simple field equality matches."""
        event = {"event_type": "artifact_created", "agent_id": "alice"}
        filter_spec = {"event_type": "artifact_created"}
        assert matches_filter(event, filter_spec) is True

    def test_simple_equality_no_match(self) -> None:
        """Simple field equality fails when different."""
        event = {"event_type": "artifact_updated", "agent_id": "alice"}
        filter_spec = {"event_type": "artifact_created"}
        assert matches_filter(event, filter_spec) is False

    def test_multiple_fields(self) -> None:
        """All fields must match."""
        event = {"event_type": "artifact_created", "agent_id": "alice"}
        filter_spec = {"event_type": "artifact_created", "agent_id": "alice"}
        assert matches_filter(event, filter_spec) is True

    def test_multiple_fields_partial_match(self) -> None:
        """Partial match fails."""
        event = {"event_type": "artifact_created", "agent_id": "bob"}
        filter_spec = {"event_type": "artifact_created", "agent_id": "alice"}
        assert matches_filter(event, filter_spec) is False

    def test_eq_operator(self) -> None:
        """$eq operator matches equality."""
        event = {"event_type": "artifact_created"}
        filter_spec = {"event_type": {"$eq": "artifact_created"}}
        assert matches_filter(event, filter_spec) is True

    def test_ne_operator(self) -> None:
        """$ne operator matches inequality."""
        event = {"event_type": "artifact_updated"}
        filter_spec = {"event_type": {"$ne": "artifact_created"}}
        assert matches_filter(event, filter_spec) is True

    def test_ne_operator_no_match(self) -> None:
        """$ne operator fails when equal."""
        event = {"event_type": "artifact_created"}
        filter_spec = {"event_type": {"$ne": "artifact_created"}}
        assert matches_filter(event, filter_spec) is False

    def test_in_operator(self) -> None:
        """$in operator matches if value in list."""
        event = {"event_type": "artifact_created"}
        filter_spec = {"event_type": {"$in": ["artifact_created", "artifact_updated"]}}
        assert matches_filter(event, filter_spec) is True

    def test_in_operator_no_match(self) -> None:
        """$in operator fails if value not in list."""
        event = {"event_type": "artifact_deleted"}
        filter_spec = {"event_type": {"$in": ["artifact_created", "artifact_updated"]}}
        assert matches_filter(event, filter_spec) is False

    def test_exists_operator_true(self) -> None:
        """$exists true matches if field exists."""
        event = {"event_type": "test", "metadata": {"foo": "bar"}}
        filter_spec = {"metadata": {"$exists": True}}
        assert matches_filter(event, filter_spec) is True

    def test_exists_operator_false(self) -> None:
        """$exists false matches if field missing."""
        event = {"event_type": "test"}
        filter_spec = {"metadata": {"$exists": False}}
        assert matches_filter(event, filter_spec) is True

    def test_nested_field_dot_notation(self) -> None:
        """Dot notation matches nested fields."""
        event = {"event_type": "test", "data": {"category": "oracle"}}
        filter_spec = {"data.category": "oracle"}
        assert matches_filter(event, filter_spec) is True

    def test_nested_field_with_in_operator(self) -> None:
        """Dot notation with $in operator."""
        event = {"data": {"category": "oracle"}}
        filter_spec = {"data.category": {"$in": ["oracle", "tool"]}}
        assert matches_filter(event, filter_spec) is True


class TestTriggerRegistry:
    """Test TriggerRegistry for managing triggers."""

    @pytest.fixture
    def artifact_store(self) -> ArtifactStore:
        """Create a fresh artifact store."""
        return ArtifactStore()

    @pytest.fixture
    def registry(self, artifact_store: ArtifactStore) -> TriggerRegistry:
        """Create trigger registry with artifact store."""
        return TriggerRegistry(artifact_store)

    def test_register_trigger(
        self,
        artifact_store: ArtifactStore,
        registry: TriggerRegistry,
    ) -> None:
        """Can register a trigger artifact."""
        # Create handler artifact first
        artifact_store.write(
            artifact_id="my_handler",
            type="executable",
            content="Handler for events",
            created_by="alice",
            executable=True,
            code="def run(event): return {'handled': True}",
        )

        # Create trigger
        trigger_content = {
            "filter": {"event_type": "artifact_created"},
            "callback_artifact": "my_handler",
            "callback_method": "run",
            "enabled": True,
        }
        artifact_store.write(
            artifact_id="my_trigger",
            type="trigger",
            content=str(trigger_content),
            created_by="alice",
            metadata=trigger_content,  # Store structured data in metadata
        )

        # Refresh registry
        registry.refresh()

        assert len(registry.active_triggers) == 1
        assert registry.active_triggers[0].callback_artifact == "my_handler"

    def test_disabled_trigger_not_active(
        self,
        artifact_store: ArtifactStore,
        registry: TriggerRegistry,
    ) -> None:
        """Disabled triggers are not included in active list."""
        artifact_store.write(
            artifact_id="my_handler",
            type="executable",
            content="Handler",
            created_by="alice",
            executable=True,
            code="def run(event): pass",
        )

        trigger_content = {
            "filter": {"event_type": "artifact_created"},
            "callback_artifact": "my_handler",
            "callback_method": "run",
            "enabled": False,  # Disabled
        }
        artifact_store.write(
            artifact_id="my_trigger",
            type="trigger",
            content=str(trigger_content),
            created_by="alice",
            metadata=trigger_content,
        )

        registry.refresh()
        assert len(registry.active_triggers) == 0

    def test_spam_prevention(
        self,
        artifact_store: ArtifactStore,
        registry: TriggerRegistry,
    ) -> None:
        """Cannot create trigger for artifact you don't own."""
        # Alice creates handler
        artifact_store.write(
            artifact_id="alices_handler",
            type="executable",
            content="Handler",
            created_by="alice",
            executable=True,
            code="def run(event): pass",
        )

        # Bob tries to create trigger for Alice's handler
        trigger_content = {
            "filter": {"event_type": "artifact_created"},
            "callback_artifact": "alices_handler",
            "callback_method": "run",
            "enabled": True,
        }
        artifact_store.write(
            artifact_id="bobs_trigger",
            type="trigger",
            content=str(trigger_content),
            created_by="bob",  # Different owner!
            metadata=trigger_content,
        )

        registry.refresh()
        # Trigger should be rejected (spam prevention)
        assert len(registry.active_triggers) == 0

    def test_match_event(
        self,
        artifact_store: ArtifactStore,
        registry: TriggerRegistry,
    ) -> None:
        """Registry returns matching triggers for event."""
        artifact_store.write(
            artifact_id="handler_1",
            type="executable",
            content="Handler",
            created_by="alice",
            executable=True,
            code="def run(event): pass",
        )
        artifact_store.write(
            artifact_id="handler_2",
            type="executable",
            content="Handler",
            created_by="bob",
            executable=True,
            code="def run(event): pass",
        )

        # Trigger for artifact_created
        t1 = {
            "filter": {"event_type": "artifact_created"},
            "callback_artifact": "handler_1",
            "callback_method": "run",
            "enabled": True,
        }
        artifact_store.write(
            artifact_id="trigger_1",
            type="trigger",
            content=str(t1),
            created_by="alice",
            metadata=t1,
        )

        # Trigger for artifact_updated
        t2 = {
            "filter": {"event_type": "artifact_updated"},
            "callback_artifact": "handler_2",
            "callback_method": "run",
            "enabled": True,
        }
        artifact_store.write(
            artifact_id="trigger_2",
            type="trigger",
            content=str(t2),
            created_by="bob",
            metadata=t2,
        )

        registry.refresh()

        # Only trigger_1 should match
        event = {"event_type": "artifact_created", "artifact_id": "test"}
        matches = registry.get_matching_triggers(event)
        assert len(matches) == 1
        assert matches[0].callback_artifact == "handler_1"


class TestTriggerInvocationQueue:
    """Test queued trigger invocations."""

    @pytest.fixture
    def artifact_store(self) -> ArtifactStore:
        """Create a fresh artifact store."""
        return ArtifactStore()

    @pytest.fixture
    def registry(self, artifact_store: ArtifactStore) -> TriggerRegistry:
        """Create trigger registry with artifact store."""
        return TriggerRegistry(artifact_store)

    def test_queue_invocation(
        self,
        artifact_store: ArtifactStore,
        registry: TriggerRegistry,
    ) -> None:
        """Can queue trigger invocations."""
        artifact_store.write(
            artifact_id="my_handler",
            type="executable",
            content="Handler",
            created_by="alice",
            executable=True,
            code="def run(event): return {'handled': True}",
        )

        t = {
            "filter": {"event_type": "test"},
            "callback_artifact": "my_handler",
            "callback_method": "run",
            "enabled": True,
        }
        artifact_store.write(
            artifact_id="my_trigger",
            type="trigger",
            content=str(t),
            created_by="alice",
            metadata=t,
        )

        registry.refresh()

        # Queue an invocation
        event = {"event_type": "test", "data": "hello"}
        registry.queue_matching_invocations(event)

        # Check pending invocations
        pending = registry.get_pending_invocations()
        assert len(pending) == 1
        assert pending[0]["callback_artifact"] == "my_handler"
        assert pending[0]["event"] == event

    def test_clear_pending(
        self,
        artifact_store: ArtifactStore,
        registry: TriggerRegistry,
    ) -> None:
        """Can clear pending invocations."""
        artifact_store.write(
            artifact_id="my_handler",
            type="executable",
            content="Handler",
            created_by="alice",
            executable=True,
            code="def run(event): pass",
        )

        t = {
            "filter": {"event_type": "test"},
            "callback_artifact": "my_handler",
            "callback_method": "run",
            "enabled": True,
        }
        artifact_store.write(
            artifact_id="my_trigger",
            type="trigger",
            content=str(t),
            created_by="alice",
            metadata=t,
        )

        registry.refresh()
        registry.queue_matching_invocations({"event_type": "test"})
        assert len(registry.get_pending_invocations()) == 1

        registry.clear_pending_invocations()
        assert len(registry.get_pending_invocations()) == 0
