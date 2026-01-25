"""State tracker: Events → current state.

Responsible for:
- Building and maintaining world state from events
- Tracking agent and artifact state changes
- Handling event ordering via sequence numbers
"""

from __future__ import annotations

import logging
from typing import Any

from ..models_v2.events import (
    EventEnvelope,
    ResourceConsumedEvent,
    ResourceAllocatedEvent,
    ResourceSpentEvent,
    ActionEvent,
    AgentStateEvent,
    TickEvent,
    ThinkingEvent,
)
from ..models_v2.state import (
    AgentState,
    ArtifactState,
    WorldState,
    ResourceUsage,
    OwnershipRecord,
)

logger = logging.getLogger(__name__)


class StateTracker:
    """Build and maintain world state from event stream.

    Usage:
        tracker = StateTracker()
        for event in parser.parse_file("run.jsonl"):
            tracker.process_event(event)
        state = tracker.get_state()
    """

    def __init__(self) -> None:
        self._state = WorldState()
        self._events_processed: int = 0

    @property
    def events_processed(self) -> int:
        """Total events processed."""
        return self._events_processed

    def get_state(self) -> WorldState:
        """Get current world state."""
        return self._state

    def reset(self) -> None:
        """Reset to empty state."""
        self._state = WorldState()
        self._events_processed = 0

    def process_event(self, event: EventEnvelope) -> None:
        """Process a single event and update state."""
        self._events_processed += 1

        # Track event type counts
        event_type = event.event_type
        self._state.event_counts[event_type] = (
            self._state.event_counts.get(event_type, 0) + 1
        )

        # Update sequence number
        if event.sequence > self._state.sequence:
            self._state.sequence = event.sequence

        # Dispatch to type-specific handlers
        if isinstance(event, ResourceConsumedEvent):
            self._handle_resource_consumed(event)
        elif isinstance(event, ResourceAllocatedEvent):
            self._handle_resource_allocated(event)
        elif isinstance(event, ResourceSpentEvent):
            self._handle_resource_spent(event)
        elif isinstance(event, ActionEvent):
            self._handle_action(event)
        elif isinstance(event, AgentStateEvent):
            self._handle_agent_state(event)
        elif isinstance(event, TickEvent):
            self._handle_tick(event)
        elif isinstance(event, ThinkingEvent):
            self._handle_thinking(event)
        else:
            # Generic event - check for common patterns
            self._handle_generic(event)

    def _handle_resource_consumed(self, event: ResourceConsumedEvent) -> None:
        """Handle renewable resource consumption (e.g., tokens)."""
        agent = self._state.get_or_create_agent(event.principal_id)

        if event.resource == "llm_tokens":
            agent.llm_tokens.used = event.balance_after
            agent.llm_tokens.quota = event.quota
            if event.rate_window_remaining is not None:
                agent.llm_tokens.rate_remaining = event.rate_window_remaining

    def _handle_resource_allocated(self, event: ResourceAllocatedEvent) -> None:
        """Handle allocatable resource changes (e.g., disk)."""
        agent = self._state.get_or_create_agent(event.principal_id)

        if event.resource == "disk":
            agent.disk.used = event.used_after
            agent.disk.quota = event.quota

    def _handle_resource_spent(self, event: ResourceSpentEvent) -> None:
        """Handle depletable resource spending (e.g., budget)."""
        agent = self._state.get_or_create_agent(event.principal_id)

        if event.resource == "llm_budget":
            agent.llm_budget.used += event.amount
            # balance_after is remaining budget
            if agent.llm_budget.quota == 0:
                # First time seeing this agent's budget
                agent.llm_budget.quota = event.balance_after + event.amount

    def _handle_action(self, event: ActionEvent) -> None:
        """Handle agent action events."""
        agent_id = event.principal_id or event.agent_id
        if not agent_id:
            return

        agent = self._state.get_or_create_agent(agent_id)
        agent.action_count += 1
        agent.last_sequence = event.sequence

        if event.success:
            agent.action_successes += 1
        else:
            agent.action_failures += 1

        # Track artifact-related actions
        if event.action_type == "create_artifact" and event.artifact_id:
            self._handle_artifact_created(event)
        elif event.action_type == "invoke" and event.target:
            self._handle_invocation(event)
        elif event.action_type in ("transfer_ownership", "ownership_transfer"):
            self._handle_ownership_transfer(event)

        # Store action in history (limited)
        action_record = {
            "sequence": event.sequence,
            "action_type": event.action_type,
            "target": event.target,
            "success": event.success,
            "timestamp": event.timestamp,
        }
        agent.action_history.append(action_record)
        # Keep last 100 actions
        if len(agent.action_history) > 100:
            agent.action_history = agent.action_history[-100:]

    def _handle_artifact_created(self, event: ActionEvent) -> None:
        """Handle artifact creation."""
        if not event.artifact_id:
            return

        agent_id = event.principal_id or event.agent_id or "unknown"
        artifact_type = "unknown"

        # Try to extract type from event
        if hasattr(event, "artifact_type"):
            artifact_type = getattr(event, "artifact_type")

        artifact = self._state.get_or_create_artifact(
            artifact_id=event.artifact_id,
            artifact_type=artifact_type,
            owner=agent_id,
            created_by=agent_id,
        )
        artifact.created_at = event.timestamp

        # Add to owner's artifacts
        agent = self._state.get_or_create_agent(agent_id)
        if event.artifact_id not in agent.artifacts_owned:
            agent.artifacts_owned.append(event.artifact_id)

        self._state.total_artifacts = len(self._state.artifacts)

    def _handle_invocation(self, event: ActionEvent) -> None:
        """Handle artifact invocation."""
        if not event.target:
            return

        artifact = self._state.artifacts.get(event.target)
        if artifact:
            artifact.invocation_count += 1
            artifact.invocation_history.append(
                {
                    "sequence": event.sequence,
                    "caller": event.principal_id or event.agent_id,
                    "method": event.method,
                    "success": event.success,
                    "timestamp": event.timestamp,
                }
            )
            # Keep last 50 invocations
            if len(artifact.invocation_history) > 50:
                artifact.invocation_history = artifact.invocation_history[-50:]

    def _handle_ownership_transfer(self, event: ActionEvent) -> None:
        """Handle artifact ownership transfer."""
        artifact_id = event.artifact_id or event.target
        if not artifact_id:
            return

        artifact = self._state.artifacts.get(artifact_id)
        if not artifact:
            return

        # Get transfer details from event args
        args = event.args or {}
        from_id = args.get("from_id", artifact.owner)
        to_id = args.get("to_id", args.get("new_owner"))

        if to_id:
            # Update ownership
            old_owner = artifact.owner
            artifact.owner = to_id

            # Record transfer
            artifact.ownership_history.append(
                OwnershipRecord(
                    from_id=old_owner,
                    to_id=to_id,
                    timestamp=event.timestamp,
                    sequence=event.sequence,
                )
            )

            # Update agent artifact lists
            if old_owner in self._state.agents:
                old_agent = self._state.agents[old_owner]
                if artifact_id in old_agent.artifacts_owned:
                    old_agent.artifacts_owned.remove(artifact_id)

            new_agent = self._state.get_or_create_agent(to_id)
            if artifact_id not in new_agent.artifacts_owned:
                new_agent.artifacts_owned.append(artifact_id)

    def _handle_agent_state(self, event: AgentStateEvent) -> None:
        """Handle agent state change events."""
        agent = self._state.get_or_create_agent(event.agent_id)
        agent.status = event.status
        agent.scrip = event.scrip

        if event.resources:
            if event.resources.llm_tokens:
                agent.llm_tokens.used = event.resources.llm_tokens.get("used", 0)
                agent.llm_tokens.quota = event.resources.llm_tokens.get("quota", 0)
                agent.llm_tokens.rate_remaining = event.resources.llm_tokens.get(
                    "rate_remaining"
                )
            if event.resources.llm_budget:
                agent.llm_budget.used = event.resources.llm_budget.get("used", 0)
                agent.llm_budget.quota = event.resources.llm_budget.get("initial", 0)
            if event.resources.disk:
                agent.disk.used = event.resources.disk.get("used", 0)
                agent.disk.quota = event.resources.disk.get("quota", 0)

        # Update active agent count
        self._state.active_agents = sum(
            1 for a in self._state.agents.values() if a.status == "active"
        )

    def _handle_tick(self, event: TickEvent) -> None:
        """Handle tick boundary events."""
        if event.simulation_time is not None:
            self._state.simulation_time = event.simulation_time
        if event.total_scrip is not None:
            self._state.total_scrip = event.total_scrip
        if event.total_artifacts is not None:
            self._state.total_artifacts = event.total_artifacts
        if event.active_agents is not None:
            self._state.active_agents = event.active_agents

    def _handle_thinking(self, event: ThinkingEvent) -> None:
        """Handle agent thinking events."""
        agent = self._state.get_or_create_agent(event.agent_id)

        thinking_record = {
            "sequence": event.sequence,
            "phase": event.phase,
            "content": event.thinking or event.content,
            "timestamp": event.timestamp,
        }
        agent.thinking_history.append(thinking_record)
        # Keep last 50 thinking entries
        if len(agent.thinking_history) > 50:
            agent.thinking_history = agent.thinking_history[-50:]

    def _handle_generic(self, event: EventEnvelope) -> None:
        """Handle untyped events by extracting common patterns."""
        # Try to extract agent_id from event data
        data = event.model_dump()
        agent_id = data.get("agent_id") or data.get("principal_id")

        if agent_id and isinstance(agent_id, str):
            # Ensure agent exists
            self._state.get_or_create_agent(agent_id)

        # Check for scrip changes
        if "scrip" in data and agent_id:
            agent = self._state.agents.get(agent_id)
            if agent:
                agent.scrip = data["scrip"]
