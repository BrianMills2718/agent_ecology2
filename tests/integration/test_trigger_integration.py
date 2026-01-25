"""Tests for Plan #180: Complete Trigger Integration.

Tests that triggers actually fire when events occur in the World.
"""

import tempfile
import pytest
from typing import Any

from src.world.world import World


def make_minimal_config(tmpdir: str) -> dict[str, Any]:
    """Create minimal valid config for testing."""
    return {
        "world": {"max_ticks": 10},
        "costs": {"per_1k_input_tokens": 1, "per_1k_output_tokens": 3},
        "logging": {"output_file": f"{tmpdir}/run.jsonl", "log_dir": tmpdir},
        "scrip": {"starting_amount": 100},
        "llm": {"default_model": "test-model", "rate_limit_delay": 0},
        "budget": {"max_api_cost": 1.0},
        "resources": {
            "stock": {"llm_budget": {"total": 10.0}, "disk": {"total": 50000}},
            "flow": {"compute": {"per_tick": 1000}},
        },
        "genesis": {"artifacts": {"ledger": {"enabled": True}}},
        "principals": [
            {"id": "alice", "starting_scrip": 100},
            {"id": "bob", "starting_scrip": 100},
        ],
    }


@pytest.fixture
def world() -> World:
    """Create a minimal World for testing."""
    with tempfile.TemporaryDirectory() as tmpdir:
        config = make_minimal_config(tmpdir)
        yield World(config)


class TestTriggerIntegration:
    """Test that World integrates with TriggerRegistry."""

    def test_world_has_trigger_registry(self, world: World) -> None:
        """World should have a trigger_registry attribute."""
        assert hasattr(world, "trigger_registry")
        assert world.trigger_registry is not None

    def test_world_has_emit_event_method(self, world: World) -> None:
        """World should have _emit_event method."""
        assert hasattr(world, "_emit_event")
        assert callable(world._emit_event)

    def test_world_has_process_pending_triggers_method(self, world: World) -> None:
        """World should have process_pending_triggers method."""
        assert hasattr(world, "process_pending_triggers")
        assert callable(world.process_pending_triggers)

    def test_world_has_refresh_triggers_method(self, world: World) -> None:
        """World should have refresh_triggers method."""
        assert hasattr(world, "refresh_triggers")
        assert callable(world.refresh_triggers)


class TestTriggerEventEmission:
    """Test that actions emit events for trigger matching."""

    def test_write_action_emits_event(self, world: World) -> None:
        """Write action should emit event and queue matching triggers."""
        # Create handler artifact
        world.artifacts.write(
            artifact_id="my_handler",
            type="executable",
            content="Handler for events",
            created_by="alice",
            executable=True,
            code="def run(event): return {'handled': True}",
        )

        # Create trigger that matches write_artifact events
        trigger_config = {
            "filter": {"event_type": "write_artifact_success"},
            "callback_artifact": "my_handler",
            "callback_method": "run",
            "enabled": True,
        }
        world.artifacts.write(
            artifact_id="my_trigger",
            type="trigger",
            content=str(trigger_config),
            created_by="alice",
            metadata=trigger_config,
        )

        # Refresh triggers so they're active
        world.refresh_triggers()

        # Now write an artifact - this should trigger the event
        from src.world.actions import WriteArtifactIntent
        intent = WriteArtifactIntent(
            principal_id="alice",
            artifact_id="test_artifact",
            artifact_type="data",
            content="Hello world",
        )
        result = world.execute_action(intent)
        assert result.success

        # Check that a trigger invocation was queued
        pending = world.get_pending_trigger_count()
        assert pending == 1

    def test_trigger_invocation_is_processed(self, world: World) -> None:
        """Process pending triggers should execute callback."""
        # Create handler artifact
        world.artifacts.write(
            artifact_id="my_handler",
            type="executable",
            content="Handler for events",
            created_by="alice",
            executable=True,
            code="def run(event): return {'handled': True}",
        )

        # Create trigger
        trigger_config = {
            "filter": {"event_type": "write_artifact_success"},
            "callback_artifact": "my_handler",
            "callback_method": "run",
            "enabled": True,
        }
        world.artifacts.write(
            artifact_id="my_trigger",
            type="trigger",
            content=str(trigger_config),
            created_by="alice",
            metadata=trigger_config,
        )

        world.refresh_triggers()

        # Write artifact to trigger event
        from src.world.actions import WriteArtifactIntent
        intent = WriteArtifactIntent(
            principal_id="alice",
            artifact_id="test_artifact",
            artifact_type="data",
            content="Hello world",
        )
        world.execute_action(intent)

        # Process pending triggers
        results = world.process_pending_triggers()

        # Should have executed one callback
        assert len(results) == 1
        # Pending should be cleared
        assert world.get_pending_trigger_count() == 0


class TestTriggerRefresh:
    """Test trigger refresh on artifact changes."""

    def test_creating_trigger_artifact_refreshes_registry(self, world: World) -> None:
        """Creating a trigger artifact should refresh the registry."""
        # Create handler first
        world.artifacts.write(
            artifact_id="my_handler",
            type="executable",
            content="Handler",
            created_by="alice",
            executable=True,
            code="def run(event): return {}",
        )

        # Initially no triggers
        world.refresh_triggers()
        assert len(world.trigger_registry.active_triggers) == 0

        # Create trigger via world action (not direct write)
        trigger_config = {
            "filter": {"event_type": "test"},
            "callback_artifact": "my_handler",
            "callback_method": "run",
            "enabled": True,
        }
        from src.world.actions import WriteArtifactIntent
        intent = WriteArtifactIntent(
            principal_id="alice",
            artifact_id="my_trigger",
            artifact_type="trigger",
            content=str(trigger_config),
            metadata=trigger_config,
        )
        result = world.execute_action(intent)
        assert result.success

        # Trigger registry should have been refreshed automatically
        assert len(world.trigger_registry.active_triggers) == 1


class TestTriggerFilters:
    """Test that trigger filters match the right events."""

    def test_trigger_does_not_fire_on_non_matching_event(self, world: World) -> None:
        """Trigger should not fire on non-matching events."""
        # Create handler
        world.artifacts.write(
            artifact_id="my_handler",
            type="executable",
            content="Handler",
            created_by="alice",
            executable=True,
            code="def run(event): return {}",
        )

        # Trigger only for artifact_deleted events
        trigger_config = {
            "filter": {"event_type": "delete_artifact_success"},  # Only delete events
            "callback_artifact": "my_handler",
            "callback_method": "run",
            "enabled": True,
        }
        world.artifacts.write(
            artifact_id="my_trigger",
            type="trigger",
            content=str(trigger_config),
            created_by="alice",
            metadata=trigger_config,
        )
        world.refresh_triggers()

        # Write action should NOT trigger (filter is for delete)
        from src.world.actions import WriteArtifactIntent
        intent = WriteArtifactIntent(
            principal_id="alice",
            artifact_id="test_artifact",
            artifact_type="data",
            content="Hello",
        )
        world.execute_action(intent)

        # No triggers should be queued
        assert world.get_pending_trigger_count() == 0

    def test_trigger_with_nested_filter(self, world: World) -> None:
        """Trigger with nested filter using dot notation."""
        # Create handler
        world.artifacts.write(
            artifact_id="my_handler",
            type="executable",
            content="Handler",
            created_by="bob",
            executable=True,
            code="def run(event): return {}",
        )

        # Trigger for specific artifact type
        trigger_config = {
            "filter": {
                "event_type": "write_artifact_success",
                "intent.artifact_type": "message",  # Nested filter
            },
            "callback_artifact": "my_handler",
            "callback_method": "run",
            "enabled": True,
        }
        world.artifacts.write(
            artifact_id="my_trigger",
            type="trigger",
            content=str(trigger_config),
            created_by="bob",
            metadata=trigger_config,
        )
        world.refresh_triggers()

        # Write a "message" type artifact
        from src.world.actions import WriteArtifactIntent
        intent = WriteArtifactIntent(
            principal_id="bob",
            artifact_id="msg_001",
            artifact_type="message",
            content="Hello Alice!",
        )
        world.execute_action(intent)

        # Should have triggered
        assert world.get_pending_trigger_count() == 1

        # Clear and test non-matching type
        world.trigger_registry.clear_pending_invocations()

        intent2 = WriteArtifactIntent(
            principal_id="bob",
            artifact_id="data_001",
            artifact_type="data",  # Different type
            content="Some data",
        )
        world.execute_action(intent2)

        # Should NOT have triggered
        assert world.get_pending_trigger_count() == 0
