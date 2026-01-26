"""Unit tests for genesis_event_bus (GAP-AGENT-009)."""

from __future__ import annotations

import pytest
from unittest.mock import MagicMock, PropertyMock


class TestGenesisEventBusSubscribe:
    """Tests for subscribe functionality."""

    def test_subscribe_creates_trigger_artifact(self) -> None:
        """Subscribe creates a trigger artifact."""
        from src.world.genesis.event_bus import GenesisEventBus

        # mock-ok: Testing subscription logic without real artifact store
        mock_store = MagicMock()
        mock_callback = MagicMock()
        mock_callback.created_by = "test_agent"
        mock_store.get.return_value = mock_callback

        event_bus = GenesisEventBus(artifact_store=mock_store)
        result = event_bus._subscribe(
            [{
                "event_type": "write_artifact_success",
                "callback_artifact": "my_handler",
            }],
            "test_agent"
        )

        assert result["success"] is True
        assert "subscription_id" in result
        assert result["event_type"] == "write_artifact_success"
        mock_store.write.assert_called_once()

    def test_subscribe_requires_owned_callback(self) -> None:
        """Subscribe fails if callback not owned by caller."""
        from src.world.genesis.event_bus import GenesisEventBus

        # mock-ok: Testing ownership validation
        mock_store = MagicMock()
        mock_callback = MagicMock()
        mock_callback.created_by = "other_agent"  # Different owner
        mock_store.get.return_value = mock_callback

        event_bus = GenesisEventBus(artifact_store=mock_store)
        result = event_bus._subscribe(
            [{
                "event_type": "write_artifact_success",
                "callback_artifact": "their_handler",
            }],
            "test_agent"
        )

        assert result["success"] is False
        assert "must own" in result["error"]

    def test_subscribe_with_extra_filter(self) -> None:
        """Subscribe with additional filter criteria."""
        from src.world.genesis.event_bus import GenesisEventBus

        # mock-ok: Testing filter handling
        mock_store = MagicMock()
        mock_callback = MagicMock()
        mock_callback.created_by = "test_agent"
        mock_store.get.return_value = mock_callback

        event_bus = GenesisEventBus(artifact_store=mock_store)
        result = event_bus._subscribe(
            [{
                "event_type": "invoke_artifact_success",
                "callback_artifact": "my_handler",
                "filter": {"data.artifact_id": "specific_artifact"},
            }],
            "test_agent"
        )

        assert result["success"] is True
        # Verify filter was included in trigger metadata
        call_kwargs = mock_store.write.call_args.kwargs
        metadata = call_kwargs["metadata"]
        assert metadata["filter"]["event_type"] == "invoke_artifact_success"
        assert metadata["filter"]["data.artifact_id"] == "specific_artifact"

    def test_subscribe_requires_event_type(self) -> None:
        """Subscribe fails without event_type."""
        from src.world.genesis.event_bus import GenesisEventBus

        mock_store = MagicMock()
        event_bus = GenesisEventBus(artifact_store=mock_store)

        result = event_bus._subscribe(
            [{"callback_artifact": "my_handler"}],
            "test_agent"
        )

        assert result["success"] is False
        assert "event_type is required" in result["error"]


class TestGenesisEventBusUnsubscribe:
    """Tests for unsubscribe functionality."""

    def test_unsubscribe_deletes_trigger(self) -> None:
        """Unsubscribe deletes the trigger artifact."""
        from src.world.genesis.event_bus import GenesisEventBus

        # mock-ok: Testing unsubscribe deletion
        mock_store = MagicMock()
        mock_subscription = MagicMock()
        mock_subscription.created_by = "test_agent"
        mock_store.get.return_value = mock_subscription

        event_bus = GenesisEventBus(artifact_store=mock_store)
        result = event_bus._unsubscribe(["sub_123"], "test_agent")

        assert result["success"] is True
        assert result["unsubscribed"] == "sub_123"
        mock_store.delete.assert_called_once_with("sub_123", "test_agent")

    def test_unsubscribe_requires_ownership(self) -> None:
        """Unsubscribe fails if not owned by caller."""
        from src.world.genesis.event_bus import GenesisEventBus

        # mock-ok: Testing ownership check
        mock_store = MagicMock()
        mock_subscription = MagicMock()
        mock_subscription.created_by = "other_agent"
        mock_store.get.return_value = mock_subscription

        event_bus = GenesisEventBus(artifact_store=mock_store)
        result = event_bus._unsubscribe(["sub_123"], "test_agent")

        assert result["success"] is False
        assert "your own subscriptions" in result["error"]

    def test_unsubscribe_dict_format(self) -> None:
        """Unsubscribe accepts dict format."""
        from src.world.genesis.event_bus import GenesisEventBus

        # mock-ok: Testing argument parsing
        mock_store = MagicMock()
        mock_subscription = MagicMock()
        mock_subscription.created_by = "test_agent"
        mock_store.get.return_value = mock_subscription

        event_bus = GenesisEventBus(artifact_store=mock_store)
        result = event_bus._unsubscribe(
            [{"subscription_id": "sub_456"}],
            "test_agent"
        )

        assert result["success"] is True
        mock_store.delete.assert_called_once_with("sub_456", "test_agent")


class TestGenesisEventBusListSubscriptions:
    """Tests for list_subscriptions functionality."""

    def test_list_subscriptions_returns_own_only(self) -> None:
        """List subscriptions returns only caller's subscriptions."""
        from src.world.genesis.event_bus import GenesisEventBus

        # mock-ok: Testing subscription filtering
        mock_store = MagicMock()

        # Create mock artifacts
        my_sub = MagicMock()
        my_sub.type = "trigger"
        my_sub.deleted = False
        my_sub.created_by = "test_agent"
        my_sub.id = "my_sub"
        my_sub.metadata = {
            "subscription_source": "genesis_event_bus",
            "filter": {"event_type": "write_artifact_success"},
            "callback_artifact": "handler",
            "callback_method": "run",
            "enabled": True,
        }

        other_sub = MagicMock()
        other_sub.type = "trigger"
        other_sub.deleted = False
        other_sub.created_by = "other_agent"
        other_sub.id = "other_sub"
        other_sub.metadata = {
            "subscription_source": "genesis_event_bus",
            "filter": {"event_type": "invoke_artifact_success"},
            "callback_artifact": "other_handler",
            "enabled": True,
        }

        mock_store.artifacts = {"my_sub": my_sub, "other_sub": other_sub}

        event_bus = GenesisEventBus(artifact_store=mock_store)
        result = event_bus._list_subscriptions([], "test_agent")

        assert result["success"] is True
        assert result["count"] == 1
        assert len(result["subscriptions"]) == 1
        assert result["subscriptions"][0]["subscription_id"] == "my_sub"

    def test_list_subscriptions_excludes_manual_triggers(self) -> None:
        """List subscriptions excludes triggers not created by event_bus."""
        from src.world.genesis.event_bus import GenesisEventBus

        # mock-ok: Testing source filtering
        mock_store = MagicMock()

        manual_trigger = MagicMock()
        manual_trigger.type = "trigger"
        manual_trigger.deleted = False
        manual_trigger.created_by = "test_agent"
        manual_trigger.id = "manual_trigger"
        manual_trigger.metadata = {
            # No subscription_source - manual trigger
            "filter": {"event_type": "write_artifact_success"},
            "callback_artifact": "handler",
            "enabled": True,
        }

        mock_store.artifacts = {"manual_trigger": manual_trigger}

        event_bus = GenesisEventBus(artifact_store=mock_store)
        result = event_bus._list_subscriptions([], "test_agent")

        assert result["success"] is True
        assert result["count"] == 0


class TestGenesisEventBusListEventTypes:
    """Tests for list_event_types functionality."""

    def test_list_event_types_returns_standard_types(self) -> None:
        """List event types returns all standard types."""
        from src.world.genesis.event_bus import GenesisEventBus, STANDARD_EVENT_TYPES

        event_bus = GenesisEventBus()
        result = event_bus._list_event_types([], "test_agent")

        assert result["success"] is True
        assert result["event_types"] == STANDARD_EVENT_TYPES
        assert "descriptions" in result
        assert "write_artifact_success" in result["descriptions"]


class TestGenesisEventBusInterface:
    """Tests for interface schema."""

    def test_interface_has_all_methods(self) -> None:
        """Interface includes all public methods."""
        from src.world.genesis.event_bus import GenesisEventBus

        event_bus = GenesisEventBus()
        interface = event_bus.get_interface()

        assert "tools" in interface
        tool_names = [t["name"] for t in interface["tools"]]

        assert "subscribe" in tool_names
        assert "unsubscribe" in tool_names
        assert "list_subscriptions" in tool_names
        assert "list_event_types" in tool_names

    def test_subscribe_has_event_type_enum(self) -> None:
        """Subscribe method documents valid event types."""
        from src.world.genesis.event_bus import GenesisEventBus, STANDARD_EVENT_TYPES

        event_bus = GenesisEventBus()
        interface = event_bus.get_interface()

        subscribe_tool = next(t for t in interface["tools"] if t["name"] == "subscribe")
        event_type_schema = subscribe_tool["inputSchema"]["properties"]["event_type"]

        assert "enum" in event_type_schema
        assert event_type_schema["enum"] == STANDARD_EVENT_TYPES
