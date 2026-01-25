"""Kernel Event Triggers - Plan #169

Enables agents to register triggers: "when event matching X occurs, invoke artifact Y."

Design:
- Triggers are stored as artifacts with type="trigger"
- TriggerRegistry scans trigger artifacts and caches active ones
- Events are matched using filter operators ($eq, $ne, $in, $exists)
- Matching invocations are queued (not synchronous) to prevent loops
- Spam prevention: can only trigger artifacts you own
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, TYPE_CHECKING

if TYPE_CHECKING:
    from .artifacts import ArtifactStore


@dataclass
class TriggerSpec:
    """Specification for an active trigger.

    Attributes:
        trigger_id: ID of the trigger artifact
        owner: Who created the trigger
        filter: Event filter dictionary
        callback_artifact: Artifact to invoke when triggered
        callback_method: Method to call (default "run")
    """

    trigger_id: str
    owner: str
    filter: dict[str, Any]
    callback_artifact: str
    callback_method: str = "run"


def _get_nested_value(data: dict[str, Any], path: str) -> Any:
    """Get a value from nested dict using dot notation.

    Args:
        data: Dictionary to search
        path: Dot-separated path (e.g., "data.category")

    Returns:
        Value at path, or None if not found
    """
    keys = path.split(".")
    value: Any = data
    for key in keys:
        if isinstance(value, dict) and key in value:
            value = value[key]
        else:
            return None
    return value


def _match_operator(event_value: Any, filter_value: Any) -> bool:
    """Match a single filter value against an event value.

    Supports operators: $eq, $ne, $in, $exists
    Plain values are treated as $eq.

    Args:
        event_value: Value from the event
        filter_value: Filter specification (value or {$op: value})

    Returns:
        True if matches
    """
    # Plain value = equality check
    if not isinstance(filter_value, dict):
        return event_value == filter_value

    # Operator-based matching
    for op, op_value in filter_value.items():
        if op == "$eq":
            if event_value != op_value:
                return False
        elif op == "$ne":
            if event_value == op_value:
                return False
        elif op == "$in":
            if not isinstance(op_value, list):
                return False
            if event_value not in op_value:
                return False
        elif op == "$exists":
            exists = event_value is not None
            if op_value and not exists:
                return False
            if not op_value and exists:
                return False
        else:
            # Unknown operator - fail closed
            return False

    return True


def matches_filter(event: dict[str, Any], filter_spec: dict[str, Any]) -> bool:
    """Check if an event matches a filter specification.

    Filter supports:
    - Simple equality: {"event_type": "artifact_created"}
    - Operators: {"event_type": {"$in": ["a", "b"]}}
    - Dot notation for nested fields: {"data.category": "oracle"}

    All filter conditions must match (AND logic).

    Args:
        event: The event dictionary
        filter_spec: Filter specification

    Returns:
        True if event matches all filter conditions
    """
    for field, expected in filter_spec.items():
        # Get value using dot notation
        actual = _get_nested_value(event, field)

        # Match against expected (handles operators)
        if not _match_operator(actual, expected):
            return False

    return True


class TriggerRegistry:
    """Registry for managing event triggers.

    Scans trigger artifacts and caches active ones. Provides methods
    to find matching triggers for events and queue invocations.

    Attributes:
        active_triggers: List of currently active TriggerSpec objects
    """

    def __init__(self, artifact_store: "ArtifactStore") -> None:
        """Initialize trigger registry.

        Args:
            artifact_store: Store to scan for trigger artifacts
        """
        self._artifact_store = artifact_store
        self.active_triggers: list[TriggerSpec] = []
        self._pending_invocations: list[dict[str, Any]] = []

    def refresh(self) -> None:
        """Scan trigger artifacts and update active trigger cache.

        Validates triggers:
        - Must be enabled
        - Must have valid filter and callback
        - Trigger owner must own the callback artifact (spam prevention)
        """
        self.active_triggers = []

        # Scan all artifacts of type "trigger"
        for artifact in self._artifact_store.artifacts.values():
            if artifact.type != "trigger":
                continue
            if artifact.deleted:
                continue

            # Get trigger config from metadata
            metadata = artifact.metadata
            if not metadata:
                continue

            # Check if enabled
            if not metadata.get("enabled", False):
                continue

            # Get required fields
            filter_spec = metadata.get("filter")
            callback_artifact = metadata.get("callback_artifact")
            callback_method = metadata.get("callback_method", "run")

            if not filter_spec or not callback_artifact:
                continue

            # Spam prevention: trigger owner must own callback artifact
            callback = self._artifact_store.get(callback_artifact)
            if callback is None:
                continue
            if callback.created_by != artifact.created_by:
                # Cannot trigger artifacts you don't own
                continue

            # Valid trigger - add to active list
            self.active_triggers.append(
                TriggerSpec(
                    trigger_id=artifact.id,
                    owner=artifact.created_by,
                    filter=filter_spec,
                    callback_artifact=callback_artifact,
                    callback_method=callback_method,
                )
            )

    def get_matching_triggers(self, event: dict[str, Any]) -> list[TriggerSpec]:
        """Get all triggers that match an event.

        Args:
            event: Event dictionary

        Returns:
            List of matching TriggerSpec objects
        """
        return [t for t in self.active_triggers if matches_filter(event, t.filter)]

    def queue_matching_invocations(self, event: dict[str, Any]) -> int:
        """Queue invocations for all triggers matching an event.

        Invocations are queued (not executed immediately) to prevent
        trigger loops and maintain async behavior.

        Args:
            event: Event dictionary

        Returns:
            Number of invocations queued
        """
        matching = self.get_matching_triggers(event)
        for trigger in matching:
            self._pending_invocations.append(
                {
                    "trigger_id": trigger.trigger_id,
                    "callback_artifact": trigger.callback_artifact,
                    "callback_method": trigger.callback_method,
                    "event": event,
                    "owner": trigger.owner,
                }
            )
        return len(matching)

    def get_pending_invocations(self) -> list[dict[str, Any]]:
        """Get list of pending trigger invocations.

        Returns:
            List of pending invocation dicts with callback_artifact, event, etc.
        """
        return list(self._pending_invocations)

    def clear_pending_invocations(self) -> None:
        """Clear all pending invocations."""
        self._pending_invocations.clear()
