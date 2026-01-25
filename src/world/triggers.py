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

from collections import defaultdict
from dataclasses import dataclass, field
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
        fire_at_event: Optional event number to fire at (Plan #185)
        fire_after_events: Optional delay in events from registration (Plan #185)
        registered_at_event: Event number when trigger was registered (Plan #185)
    """

    trigger_id: str
    owner: str
    filter: dict[str, Any]
    callback_artifact: str
    callback_method: str = "run"
    # Plan #185: Time-based scheduling
    fire_at_event: int | None = None
    fire_after_events: int | None = None
    registered_at_event: int | None = None

    @property
    def is_scheduled(self) -> bool:
        """Check if this is a scheduled trigger (not event-based)."""
        return self.fire_at_event is not None or self.fire_after_events is not None

    def get_fire_event(self) -> int | None:
        """Get the absolute event number this trigger should fire at.

        Returns:
            Event number to fire at, or None if not scheduled
        """
        if self.fire_at_event is not None:
            return self.fire_at_event
        if self.fire_after_events is not None and self.registered_at_event is not None:
            return self.registered_at_event + self.fire_after_events
        return None


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

    Plan #185 adds time-based scheduling:
    - Triggers can specify fire_at_event or fire_after_events
    - Scheduled triggers are tracked separately and fired at the right event
    - Scheduled triggers don't use event filters - they fire at specific times

    Attributes:
        active_triggers: List of currently active TriggerSpec objects (event-based)
        scheduled_triggers: Dict of event_number -> list of TriggerSpec (time-based)
    """

    def __init__(self, artifact_store: "ArtifactStore") -> None:
        """Initialize trigger registry.

        Args:
            artifact_store: Store to scan for trigger artifacts
        """
        self._artifact_store = artifact_store
        self.active_triggers: list[TriggerSpec] = []
        self._pending_invocations: list[dict[str, Any]] = []
        # Plan #185: Scheduled triggers indexed by fire event number
        self._scheduled_triggers: dict[int, list[TriggerSpec]] = defaultdict(list)
        self._current_event_number: int = 0

    def set_current_event_number(self, event_number: int) -> None:
        """Update the current event number for scheduling.

        Args:
            event_number: Current event number in simulation
        """
        self._current_event_number = event_number

    def refresh(self) -> None:
        """Scan trigger artifacts and update active trigger cache.

        Validates triggers:
        - Must be enabled
        - Must have valid filter and callback
        - Trigger owner must own the callback artifact (spam prevention)

        Plan #185: Also rebuilds scheduled trigger index for time-based triggers.
        """
        self.active_triggers = []
        self._scheduled_triggers.clear()

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
            callback_artifact = metadata.get("callback_artifact")
            callback_method = metadata.get("callback_method", "run")

            if not callback_artifact:
                continue

            # Spam prevention: trigger owner must own callback artifact
            callback = self._artifact_store.get(callback_artifact)
            if callback is None:
                continue
            if callback.created_by != artifact.created_by:
                # Cannot trigger artifacts you don't own
                continue

            # Plan #185: Check for scheduling fields
            fire_at_event = metadata.get("fire_at_event")
            fire_after_events = metadata.get("fire_after_events")
            registered_at_event = metadata.get("registered_at_event")

            # Build trigger spec
            trigger_spec = TriggerSpec(
                trigger_id=artifact.id,
                owner=artifact.created_by,
                filter=metadata.get("filter", {}),
                callback_artifact=callback_artifact,
                callback_method=callback_method,
                fire_at_event=fire_at_event,
                fire_after_events=fire_after_events,
                registered_at_event=registered_at_event,
            )

            # Plan #185: Separate scheduled vs event-based triggers
            if trigger_spec.is_scheduled:
                fire_event = trigger_spec.get_fire_event()
                if fire_event is not None and fire_event >= self._current_event_number:
                    # Only schedule if not already past
                    self._scheduled_triggers[fire_event].append(trigger_spec)
            else:
                # Event-based trigger - requires filter
                if not metadata.get("filter"):
                    continue
                self.active_triggers.append(trigger_spec)

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

    # Plan #185: Scheduled trigger methods

    def schedule_trigger(
        self,
        trigger_spec: TriggerSpec,
        at_event: int | None = None,
        after_events: int | None = None,
    ) -> bool:
        """Schedule a trigger to fire at a specific event number.

        Args:
            trigger_spec: The trigger specification
            at_event: Absolute event number to fire at
            after_events: Number of events from now to fire

        Returns:
            True if scheduled successfully
        """
        if at_event is not None:
            fire_at = at_event
        elif after_events is not None:
            fire_at = self._current_event_number + after_events
        else:
            return False

        if fire_at < self._current_event_number:
            # Can't schedule in the past
            return False

        # Update trigger spec
        trigger_spec.fire_at_event = fire_at
        trigger_spec.registered_at_event = self._current_event_number

        self._scheduled_triggers[fire_at].append(trigger_spec)
        return True

    def get_scheduled_triggers(self, event_number: int) -> list[TriggerSpec]:
        """Get triggers scheduled to fire at a specific event number.

        Args:
            event_number: The event number to check

        Returns:
            List of TriggerSpec objects scheduled for that event
        """
        return list(self._scheduled_triggers.get(event_number, []))

    def fire_scheduled_triggers(self, event_number: int) -> int:
        """Fire all triggers scheduled for a specific event number.

        Queues invocations for all triggers scheduled at this event.
        Removes fired triggers from the schedule.

        Args:
            event_number: Current event number

        Returns:
            Number of triggers fired
        """
        scheduled = self._scheduled_triggers.pop(event_number, [])
        for trigger in scheduled:
            # Create a synthetic "scheduled" event for the trigger
            event = {
                "event_type": "scheduled",
                "event_number": event_number,
                "trigger_id": trigger.trigger_id,
                "scheduled_at": trigger.registered_at_event,
            }
            self._pending_invocations.append(
                {
                    "trigger_id": trigger.trigger_id,
                    "callback_artifact": trigger.callback_artifact,
                    "callback_method": trigger.callback_method,
                    "event": event,
                    "owner": trigger.owner,
                }
            )
        return len(scheduled)

    def cancel_scheduled_trigger(self, trigger_id: str) -> bool:
        """Cancel a scheduled trigger before it fires.

        Args:
            trigger_id: ID of the trigger to cancel

        Returns:
            True if found and cancelled
        """
        for event_num, triggers in list(self._scheduled_triggers.items()):
            for i, trigger in enumerate(triggers):
                if trigger.trigger_id == trigger_id:
                    triggers.pop(i)
                    if not triggers:
                        del self._scheduled_triggers[event_num]
                    return True
        return False

    def get_scheduled_count(self) -> int:
        """Get total number of scheduled triggers.

        Returns:
            Number of triggers currently scheduled
        """
        return sum(len(triggers) for triggers in self._scheduled_triggers.values())
