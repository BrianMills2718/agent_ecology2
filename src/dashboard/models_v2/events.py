"""Event type models per ADR-0020: Event Schema Contract.

All events have a common envelope:
- timestamp: ISO 8601 UTC
- event_type: One of the defined types
- sequence: Monotonic event counter (replaces 'tick' for ordering)

The 'tick' field is retained for backwards compatibility but deprecated.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, Field


class EventEnvelope(BaseModel):
    """Common envelope for all events per ADR-0020."""

    timestamp: str
    event_type: str
    sequence: int = Field(default=0, description="Monotonic event counter")
    # Backwards compatibility - deprecated, use sequence
    tick: int | None = Field(default=None, description="Deprecated: use sequence")

    class Config:
        extra = "allow"  # Allow additional fields for forward compatibility


# Resource Events (ADR-0020 Section 2)


class ResourceConsumedEvent(EventEnvelope):
    """When renewable resources consumed (e.g., LLM tokens).

    Resource type: RENEWABLE (rate-limited, refills over time)
    """

    event_type: Literal["resource_consumed"] = "resource_consumed"
    principal_id: str
    resource: str  # e.g., "llm_tokens"
    amount: float
    balance_after: float
    quota: float
    rate_window_remaining: float | None = None


class ResourceAllocatedEvent(EventEnvelope):
    """When allocatable resources allocated (e.g., disk space).

    Resource type: ALLOCATABLE (quota-based, reclaimable)
    """

    event_type: Literal["resource_allocated"] = "resource_allocated"
    principal_id: str
    resource: str  # e.g., "disk"
    amount: float
    used_after: float
    quota: float


class ResourceSpentEvent(EventEnvelope):
    """When depletable resources spent (e.g., LLM budget).

    Resource type: DEPLETABLE (once spent, gone)
    """

    event_type: Literal["resource_spent"] = "resource_spent"
    principal_id: str
    resource: str  # e.g., "llm_budget"
    amount: float
    balance_after: float


# Action Events (ADR-0020 Section 4)


class ActionResourceUsage(BaseModel):
    """Resource usage within an action."""

    llm_tokens_used: float = 0
    disk_delta: float = 0


class ActionEvent(EventEnvelope):
    """Agent action event with resource context."""

    event_type: Literal["action"] = "action"
    principal_id: str | None = None
    agent_id: str | None = None  # Backwards compatibility
    action_type: str
    target: str | None = None
    success: bool = True
    duration_ms: float | None = None
    resources: ActionResourceUsage | None = None
    # Extended fields from existing parser
    result: Any | None = None
    error: str | None = None
    artifact_id: str | None = None
    content: str | None = None
    method: str | None = None
    args: dict[str, Any] | None = None

    def __init__(self, **data: Any) -> None:
        # Handle agent_id vs principal_id compatibility
        # If only principal_id is provided, copy to agent_id for compatibility
        # If only agent_id is provided, copy to principal_id
        if "principal_id" in data and "agent_id" not in data:
            data["agent_id"] = data["principal_id"]
        elif "agent_id" in data and "principal_id" not in data:
            data["principal_id"] = data["agent_id"]
        super().__init__(**data)


# Agent State Events (ADR-0020 Section 5)


class AgentResourceState(BaseModel):
    """Resource state for an agent."""

    llm_tokens: dict[str, float] | None = None  # {used, quota, rate_remaining}
    llm_budget: dict[str, float] | None = None  # {used, initial}
    disk: dict[str, float] | None = None  # {used, quota}


class AgentStateEvent(EventEnvelope):
    """Emitted when agent state changes materially."""

    event_type: Literal["agent_state"] = "agent_state"
    agent_id: str
    status: Literal["active", "frozen", "terminated"] = "active"
    scrip: float = 0
    resources: AgentResourceState | None = None
    frozen_reason: str | None = None


# Tick Events (Backwards Compatibility)


class TickEvent(EventEnvelope):
    """Tick boundary event (deprecated terminology, use sequence)."""

    event_type: Literal["tick"] = "tick"
    simulation_time: float | None = None
    total_scrip: float | None = None
    total_artifacts: int | None = None
    active_agents: int | None = None


# Thinking Events (Agent Cognitive Activity)


class ThinkingEvent(EventEnvelope):
    """Agent thinking/reasoning event."""

    event_type: Literal["thinking"] = "thinking"
    agent_id: str
    phase: str | None = None  # OODA phase: observe, orient, decide, act
    thinking: str | None = None
    content: str | None = None  # Alternative field name


# Utility Functions


def parse_event(data: dict[str, Any]) -> EventEnvelope:
    """Parse raw event dict into typed event model.

    Unknown event types return a generic EventEnvelope to avoid crashes.
    """
    event_type = data.get("event_type", "")

    event_classes: dict[str, type[EventEnvelope]] = {
        "resource_consumed": ResourceConsumedEvent,
        "resource_allocated": ResourceAllocatedEvent,
        "resource_spent": ResourceSpentEvent,
        "action": ActionEvent,
        "agent_state": AgentStateEvent,
        "tick": TickEvent,
        "thinking": ThinkingEvent,
    }

    event_class = event_classes.get(event_type, EventEnvelope)
    try:
        return event_class(**data)
    except Exception:
        # Fall back to generic envelope for malformed events
        return EventEnvelope(**data)
