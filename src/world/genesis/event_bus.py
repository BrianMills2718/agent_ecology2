"""Genesis Event Bus - GAP-AGENT-009

Provides convenient event subscription API wrapping the kernel trigger system.

This artifact enables agents to easily:
- Subscribe to event types with simple method calls
- List their active subscriptions
- Get available event types
- Unsubscribe from events

The underlying implementation uses trigger artifacts (Plan #169, #180),
but this artifact provides a friendlier API.

Event types emitted by the kernel:
- write_artifact_success: Artifact was written
- edit_artifact_success: Artifact was edited
- delete_artifact_success: Artifact was deleted
- invoke_artifact_success: Artifact method was invoked
- transfer_success: Scrip transfer completed
- scheduled: Scheduled trigger fired (Plan #185)
"""

from __future__ import annotations

from typing import Any, TYPE_CHECKING

from ...config_schema import GenesisConfig
from .base import GenesisArtifact

if TYPE_CHECKING:
    from ..artifacts import ArtifactStore


# Standard event types emitted by the kernel
STANDARD_EVENT_TYPES = [
    "write_artifact_success",
    "edit_artifact_success",
    "delete_artifact_success",
    "invoke_artifact_success",
    "transfer_success",
    "scheduled",
]


class GenesisEventBus(GenesisArtifact):
    """Event subscription service for agents.

    Provides convenient methods to subscribe to kernel events without
    manually creating trigger artifacts.

    Methods:
    - subscribe: Subscribe to an event type
    - unsubscribe: Remove a subscription
    - list_subscriptions: List active subscriptions for an agent
    - list_event_types: Get available event types
    """

    def __init__(
        self,
        artifact_store: "ArtifactStore | None" = None,
        genesis_config: GenesisConfig | None = None,
    ) -> None:
        """Initialize the event bus.

        Args:
            artifact_store: Store for creating/managing trigger artifacts
        """
        super().__init__(
            artifact_id="genesis_event_bus",
            description="Event subscription service for agents (GAP-AGENT-009)",
        )
        self._artifact_store = artifact_store

        # Register methods
        self.register_method(
            name="subscribe",
            handler=self._subscribe,
            cost=1,  # Small cost for creating trigger artifact
            description="Subscribe to an event type with a callback artifact",
        )
        self.register_method(
            name="unsubscribe",
            handler=self._unsubscribe,
            cost=0,
            description="Unsubscribe from an event type",
        )
        self.register_method(
            name="list_subscriptions",
            handler=self._list_subscriptions,
            cost=0,
            description="List active subscriptions for the caller",
        )
        self.register_method(
            name="list_event_types",
            handler=self._list_event_types,
            cost=0,
            description="List available event types",
        )

    def _subscribe(self, args: list[Any], invoker_id: str) -> dict[str, Any]:
        """Subscribe to an event type.

        Args format: [{event_type, callback_artifact, callback_method?, filter?}]
        - event_type: Type of event to subscribe to (e.g., "write_artifact_success")
        - callback_artifact: Artifact to invoke when event occurs (must be owned by caller)
        - callback_method: Method to call on callback artifact (default "run")
        - filter: Additional filter criteria (optional)

        Returns:
            {subscription_id: str, event_type: str}
        """
        if not self._artifact_store:
            return {
                "success": False,
                "error": "Event bus not connected to artifact store",
            }

        if not args or not isinstance(args[0], dict):
            return {
                "success": False,
                "error": "subscribe requires {event_type, callback_artifact}",
            }

        config = args[0]
        event_type = config.get("event_type")
        callback_artifact = config.get("callback_artifact")
        callback_method = config.get("callback_method", "run")
        extra_filter = config.get("filter", {})

        if not event_type:
            return {"success": False, "error": "event_type is required"}
        if not callback_artifact:
            return {"success": False, "error": "callback_artifact is required"}

        # Verify callback artifact exists and is owned by caller
        callback = self._artifact_store.get(callback_artifact)
        if callback is None:
            return {
                "success": False,
                "error": f"Callback artifact '{callback_artifact}' not found",
            }
        if callback.created_by != invoker_id:
            return {
                "success": False,
                "error": f"You must own the callback artifact (owned by {callback.created_by})",
            }

        # Build filter for the trigger
        trigger_filter = {"event_type": event_type, **extra_filter}

        # Create subscription ID
        subscription_id = f"subscription_{invoker_id}_{event_type}_{callback_artifact}"

        # Create trigger artifact
        self._artifact_store.write(
            artifact_id=subscription_id,
            type="trigger",
            content=f"Event subscription: {event_type} -> {callback_artifact}.{callback_method}",
            created_by=invoker_id,
            executable=False,
            metadata={
                "enabled": True,
                "filter": trigger_filter,
                "callback_artifact": callback_artifact,
                "callback_method": callback_method,
                "subscription_source": "genesis_event_bus",
            },
        )

        return {
            "success": True,
            "subscription_id": subscription_id,
            "event_type": event_type,
            "callback_artifact": callback_artifact,
            "callback_method": callback_method,
        }

    def _unsubscribe(self, args: list[Any], invoker_id: str) -> dict[str, Any]:
        """Unsubscribe from an event type.

        Args format: [subscription_id] or [{subscription_id}]
        - subscription_id: ID of the subscription to remove

        Returns:
            {success: bool}
        """
        if not self._artifact_store:
            return {
                "success": False,
                "error": "Event bus not connected to artifact store",
            }

        if not args:
            return {"success": False, "error": "subscription_id is required"}

        subscription_id = args[0]
        if isinstance(subscription_id, dict):
            subscription_id = subscription_id.get("subscription_id")

        if not subscription_id:
            return {"success": False, "error": "subscription_id is required"}

        # Get the subscription artifact
        subscription = self._artifact_store.get(subscription_id)
        if subscription is None:
            return {
                "success": False,
                "error": f"Subscription '{subscription_id}' not found",
            }

        # Verify ownership
        if subscription.created_by != invoker_id:
            return {
                "success": False,
                "error": "You can only unsubscribe from your own subscriptions",
            }

        # Delete the trigger artifact
        self._artifact_store.delete(subscription_id, invoker_id)

        return {"success": True, "unsubscribed": subscription_id}

    def _list_subscriptions(self, args: list[Any], invoker_id: str) -> dict[str, Any]:
        """List active subscriptions for the caller.

        Returns:
            {subscriptions: [{subscription_id, event_type, callback_artifact, callback_method}]}
        """
        if not self._artifact_store:
            return {
                "success": False,
                "error": "Event bus not connected to artifact store",
            }

        subscriptions: list[dict[str, Any]] = []

        for artifact in self._artifact_store.artifacts.values():
            if artifact.type != "trigger":
                continue
            if artifact.deleted:
                continue
            if artifact.created_by != invoker_id:
                continue

            # Check if this is an event bus subscription
            metadata = artifact.metadata or {}
            if metadata.get("subscription_source") != "genesis_event_bus":
                continue

            filter_spec = metadata.get("filter", {})
            subscriptions.append({
                "subscription_id": artifact.id,
                "event_type": filter_spec.get("event_type", "unknown"),
                "callback_artifact": metadata.get("callback_artifact"),
                "callback_method": metadata.get("callback_method", "run"),
                "enabled": metadata.get("enabled", False),
            })

        return {"success": True, "subscriptions": subscriptions, "count": len(subscriptions)}

    def _list_event_types(self, args: list[Any], invoker_id: str) -> dict[str, Any]:
        """List available event types.

        Returns:
            {event_types: [str], descriptions: {type: description}}
        """
        descriptions = {
            "write_artifact_success": "Fired when an artifact is created or updated",
            "edit_artifact_success": "Fired when an artifact is edited (Plan #131)",
            "delete_artifact_success": "Fired when an artifact is deleted",
            "invoke_artifact_success": "Fired when an artifact method is invoked",
            "transfer_success": "Fired when scrip is transferred",
            "scheduled": "Fired for scheduled triggers (Plan #185)",
        }

        return {
            "success": True,
            "event_types": STANDARD_EVENT_TYPES,
            "descriptions": descriptions,
        }

    def get_interface(self) -> dict[str, Any]:
        """Get interface schema (Plan #114)."""
        return {
            "description": self.description,
            "dataType": "service",
            "tools": [
                {
                    "name": "subscribe",
                    "description": self.methods["subscribe"].description,
                    "cost": 1,
                    "inputSchema": {
                        "type": "object",
                        "properties": {
                            "event_type": {
                                "type": "string",
                                "description": "Event type to subscribe to",
                                "enum": STANDARD_EVENT_TYPES,
                            },
                            "callback_artifact": {
                                "type": "string",
                                "description": "Artifact to invoke when event occurs (must be owned by you)",
                            },
                            "callback_method": {
                                "type": "string",
                                "description": "Method to call on callback artifact",
                                "default": "run",
                            },
                            "filter": {
                                "type": "object",
                                "description": "Additional filter criteria for events",
                            },
                        },
                        "required": ["event_type", "callback_artifact"],
                    },
                },
                {
                    "name": "unsubscribe",
                    "description": self.methods["unsubscribe"].description,
                    "cost": 0,
                    "inputSchema": {
                        "type": "object",
                        "properties": {
                            "subscription_id": {
                                "type": "string",
                                "description": "ID of subscription to remove",
                            },
                        },
                        "required": ["subscription_id"],
                    },
                },
                {
                    "name": "list_subscriptions",
                    "description": self.methods["list_subscriptions"].description,
                    "cost": 0,
                    "inputSchema": {"type": "object", "properties": {}},
                },
                {
                    "name": "list_event_types",
                    "description": self.methods["list_event_types"].description,
                    "cost": 0,
                    "inputSchema": {"type": "object", "properties": {}},
                },
            ],
        }
