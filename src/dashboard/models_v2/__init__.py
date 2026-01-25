"""Dashboard data models.

Structured into:
- events.py: Event type models (Pydantic) per ADR-0020
- state.py: Agent/artifact/world state models
- metrics.py: Computed metric models
"""

from .events import (
    EventEnvelope,
    ResourceConsumedEvent,
    ResourceAllocatedEvent,
    ResourceSpentEvent,
    ActionEvent,
    AgentStateEvent,
    TickEvent,
    ThinkingEvent,
    parse_event,
)
from .state import (
    AgentState,
    ArtifactState,
    WorldState,
)
from .metrics import (
    AgentMetrics,
    ResourceMetrics,
    EfficiencyMetrics,
)

__all__ = [
    # Events
    "EventEnvelope",
    "ResourceConsumedEvent",
    "ResourceAllocatedEvent",
    "ResourceSpentEvent",
    "ActionEvent",
    "AgentStateEvent",
    "TickEvent",
    "ThinkingEvent",
    "parse_event",
    # State
    "AgentState",
    "ArtifactState",
    "WorldState",
    # Metrics
    "AgentMetrics",
    "ResourceMetrics",
    "EfficiencyMetrics",
]
