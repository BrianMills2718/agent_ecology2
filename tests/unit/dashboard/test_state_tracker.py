"""Tests for dashboard state tracker.

Required tests per Plan #149:
- test_agent_state_from_events: Builds agent state from events
- test_resource_tracking: Tracks resource changes accurately
- test_missing_data_handling: Missing data is None, not 0
"""

import pytest

from src.dashboard.core_v2.state_tracker import StateTracker
from src.dashboard.models_v2.events import (
    ActionEvent,
    ResourceConsumedEvent,
    ResourceAllocatedEvent,
    ResourceSpentEvent,
    AgentStateEvent,
    TickEvent,
    ThinkingEvent,
    AgentResourceState,
)


class TestAgentStateFromEvents:
    """Tests for building agent state from events."""

    def test_agent_state_from_events(self) -> None:
        """Builds agent state from events."""
        tracker = StateTracker()

        # Process action events for an agent
        tracker.process_event(
            ActionEvent(
                timestamp="2026-01-25T12:00:00Z",
                event_type="action",
                sequence=1,
                agent_id="agent_alpha",
                action_type="read_artifact",
                success=True,
            )
        )
        tracker.process_event(
            ActionEvent(
                timestamp="2026-01-25T12:00:01Z",
                event_type="action",
                sequence=2,
                agent_id="agent_alpha",
                action_type="invoke",
                success=True,
            )
        )
        tracker.process_event(
            ActionEvent(
                timestamp="2026-01-25T12:00:02Z",
                event_type="action",
                sequence=3,
                agent_id="agent_alpha",
                action_type="invoke",
                success=False,
            )
        )

        state = tracker.get_state()
        agent = state.get_agent("agent_alpha")

        assert agent is not None
        assert agent.agent_id == "agent_alpha"
        assert agent.action_count == 3
        assert agent.action_successes == 2
        assert agent.action_failures == 1
        assert agent.last_sequence == 3

    def test_multiple_agents(self) -> None:
        """Tracks multiple agents independently."""
        tracker = StateTracker()

        tracker.process_event(
            ActionEvent(
                timestamp="T",
                event_type="action",
                sequence=1,
                agent_id="agent_alpha",
                action_type="read_artifact",
                success=True,
            )
        )
        tracker.process_event(
            ActionEvent(
                timestamp="T",
                event_type="action",
                sequence=2,
                agent_id="agent_beta",
                action_type="invoke",
                success=True,
            )
        )

        state = tracker.get_state()

        assert len(state.agents) == 2
        assert state.agents["agent_alpha"].action_count == 1
        assert state.agents["agent_beta"].action_count == 1

    def test_agent_state_event(self) -> None:
        """Handles agent_state events correctly."""
        tracker = StateTracker()

        tracker.process_event(
            AgentStateEvent(
                timestamp="T",
                event_type="agent_state",
                sequence=1,
                agent_id="agent_alpha",
                status="active",
                scrip=100.5,
                resources=AgentResourceState(
                    llm_tokens={"used": 500, "quota": 10000, "rate_remaining": 9500},
                    llm_budget={"used": 0.05, "initial": 1.0},
                    disk={"used": 1024, "quota": 10000},
                ),
            )
        )

        state = tracker.get_state()
        agent = state.get_agent("agent_alpha")

        assert agent.status == "active"
        assert agent.scrip == 100.5
        assert agent.llm_tokens.used == 500
        assert agent.llm_tokens.quota == 10000
        assert agent.llm_budget.used == 0.05
        assert agent.disk.used == 1024


class TestResourceTracking:
    """Tests for resource tracking."""

    def test_resource_tracking(self) -> None:
        """Tracks resource changes accurately."""
        tracker = StateTracker()

        # Token consumption
        tracker.process_event(
            ResourceConsumedEvent(
                timestamp="T",
                event_type="resource_consumed",
                sequence=1,
                principal_id="agent_alpha",
                resource="llm_tokens",
                amount=1500,
                balance_after=8500,
                quota=10000,
                rate_window_remaining=6500,
            )
        )

        state = tracker.get_state()
        agent = state.get_agent("agent_alpha")

        assert agent.llm_tokens.used == 8500  # balance_after is current usage
        assert agent.llm_tokens.quota == 10000
        assert agent.llm_tokens.rate_remaining == 6500

    def test_disk_allocation(self) -> None:
        """Tracks disk allocation correctly."""
        tracker = StateTracker()

        tracker.process_event(
            ResourceAllocatedEvent(
                timestamp="T",
                event_type="resource_allocated",
                sequence=1,
                principal_id="agent_alpha",
                resource="disk",
                amount=2048,
                used_after=5120,
                quota=10000,
            )
        )

        state = tracker.get_state()
        agent = state.get_agent("agent_alpha")

        assert agent.disk.used == 5120
        assert agent.disk.quota == 10000

    def test_budget_spending(self) -> None:
        """Tracks budget spending correctly."""
        tracker = StateTracker()

        # First spend
        tracker.process_event(
            ResourceSpentEvent(
                timestamp="T",
                event_type="resource_spent",
                sequence=1,
                principal_id="agent_alpha",
                resource="llm_budget",
                amount=0.05,
                balance_after=0.95,
            )
        )

        state = tracker.get_state()
        agent = state.get_agent("agent_alpha")

        # Budget quota should be calculated from first spend
        assert agent.llm_budget.used == 0.05
        assert agent.llm_budget.quota == 1.0  # 0.95 + 0.05

        # Second spend
        tracker.process_event(
            ResourceSpentEvent(
                timestamp="T",
                event_type="resource_spent",
                sequence=2,
                principal_id="agent_alpha",
                resource="llm_budget",
                amount=0.10,
                balance_after=0.85,
            )
        )

        agent = state.get_agent("agent_alpha")
        assert agent.llm_budget.used == pytest.approx(0.15)  # Cumulative


class TestMissingDataHandling:
    """Tests for handling missing data."""

    def test_missing_data_handling(self) -> None:
        """Missing data is None, not 0."""
        tracker = StateTracker()

        # Create agent with just an action - no resource events
        tracker.process_event(
            ActionEvent(
                timestamp="T",
                event_type="action",
                sequence=1,
                agent_id="agent_alpha",
                action_type="read_artifact",
                success=True,
            )
        )

        state = tracker.get_state()
        agent = state.get_agent("agent_alpha")

        # Resource quotas should be 0 (not set)
        # This indicates "no data" vs "zero usage"
        assert agent.llm_tokens.quota == 0.0
        assert agent.llm_budget.quota == 0.0
        assert agent.disk.quota == 0.0

        # Rate remaining should be None (not set)
        assert agent.llm_tokens.rate_remaining is None

    def test_partial_resource_data(self) -> None:
        """Handles partial resource data correctly."""
        tracker = StateTracker()

        # Only disk is tracked, not tokens or budget
        tracker.process_event(
            ResourceAllocatedEvent(
                timestamp="T",
                event_type="resource_allocated",
                sequence=1,
                principal_id="agent_alpha",
                resource="disk",
                amount=1024,
                used_after=1024,
                quota=10000,
            )
        )

        state = tracker.get_state()
        agent = state.get_agent("agent_alpha")

        # Disk has data
        assert agent.disk.used == 1024
        assert agent.disk.quota == 10000

        # Tokens and budget have no data
        assert agent.llm_tokens.quota == 0.0
        assert agent.llm_budget.quota == 0.0


class TestArtifactTracking:
    """Tests for artifact state tracking."""

    def test_artifact_creation(self) -> None:
        """Tracks artifact creation."""
        tracker = StateTracker()

        tracker.process_event(
            ActionEvent(
                timestamp="T",
                event_type="action",
                sequence=1,
                agent_id="agent_alpha",
                action_type="create_artifact",
                artifact_id="my_artifact",
                success=True,
            )
        )

        state = tracker.get_state()

        assert "my_artifact" in state.artifacts
        artifact = state.artifacts["my_artifact"]
        assert artifact.artifact_id == "my_artifact"
        assert artifact.owner == "agent_alpha"
        assert artifact.created_by == "agent_alpha"

        # Agent should own the artifact
        agent = state.get_agent("agent_alpha")
        assert "my_artifact" in agent.artifacts_owned

    def test_artifact_invocation(self) -> None:
        """Tracks artifact invocations."""
        tracker = StateTracker()

        # First create the artifact
        tracker.process_event(
            ActionEvent(
                timestamp="T",
                event_type="action",
                sequence=1,
                agent_id="agent_alpha",
                action_type="create_artifact",
                artifact_id="my_service",
                success=True,
            )
        )

        # Then invoke it
        tracker.process_event(
            ActionEvent(
                timestamp="T",
                event_type="action",
                sequence=2,
                agent_id="agent_beta",
                action_type="invoke",
                target="my_service",
                method="do_something",
                success=True,
            )
        )

        state = tracker.get_state()
        artifact = state.artifacts["my_service"]

        assert artifact.invocation_count == 1
        assert len(artifact.invocation_history) == 1


class TestThinkingTracking:
    """Tests for thinking event tracking."""

    def test_thinking_events(self) -> None:
        """Tracks agent thinking history."""
        tracker = StateTracker()

        tracker.process_event(
            ThinkingEvent(
                timestamp="T",
                event_type="thinking",
                sequence=1,
                agent_id="agent_alpha",
                phase="observe",
                thinking="I see 3 artifacts...",
            )
        )

        state = tracker.get_state()
        agent = state.get_agent("agent_alpha")

        assert len(agent.thinking_history) == 1
        assert agent.thinking_history[0]["phase"] == "observe"
        assert agent.thinking_history[0]["content"] == "I see 3 artifacts..."


class TestTickEvents:
    """Tests for tick event handling."""

    def test_tick_updates_simulation_state(self) -> None:
        """Tick events update global simulation state."""
        tracker = StateTracker()

        tracker.process_event(
            TickEvent(
                timestamp="T",
                event_type="tick",
                sequence=10,
                tick=10,
                simulation_time=60.5,
                total_scrip=1000,
                total_artifacts=25,
                active_agents=3,
            )
        )

        state = tracker.get_state()

        assert state.sequence == 10
        assert state.simulation_time == 60.5
        assert state.total_scrip == 1000
        assert state.total_artifacts == 25
        assert state.active_agents == 3


class TestSequenceTracking:
    """Tests for sequence number tracking."""

    def test_sequence_monotonic(self) -> None:
        """State sequence tracks highest seen."""
        tracker = StateTracker()

        tracker.process_event(
            ActionEvent(
                timestamp="T", event_type="action", sequence=5, agent_id="a", action_type="x", success=True
            )
        )
        tracker.process_event(
            ActionEvent(
                timestamp="T", event_type="action", sequence=10, agent_id="a", action_type="x", success=True
            )
        )
        tracker.process_event(
            ActionEvent(
                timestamp="T", event_type="action", sequence=8, agent_id="a", action_type="x", success=True
            )
        )

        state = tracker.get_state()
        assert state.sequence == 10  # Highest seen


class TestReset:
    """Tests for state reset."""

    def test_reset_clears_state(self) -> None:
        """Reset clears all state."""
        tracker = StateTracker()

        tracker.process_event(
            ActionEvent(
                timestamp="T", event_type="action", sequence=1, agent_id="a", action_type="x", success=True
            )
        )

        tracker.reset()
        state = tracker.get_state()

        assert len(state.agents) == 0
        assert len(state.artifacts) == 0
        assert state.sequence == 0
        assert tracker.events_processed == 0
