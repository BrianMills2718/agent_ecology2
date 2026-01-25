"""Tests for dashboard metrics engine.

Required tests per Plan #149:
- test_compute_efficiency_metrics: Calculates agent efficiency
- test_compute_resource_utilization: Calculates resource utilization
"""

import pytest

from src.dashboard.core_v2.metrics_engine import MetricsEngine
from src.dashboard.models_v2.state import (
    WorldState,
    AgentState,
    ArtifactState,
    ResourceUsage,
)


class TestComputeEfficiencyMetrics:
    """Tests for computing efficiency metrics."""

    def test_compute_efficiency_metrics(self) -> None:
        """Calculates agent efficiency correctly."""
        engine = MetricsEngine()

        # Set up world state with an agent
        state = WorldState()
        agent = AgentState(agent_id="agent_alpha")
        agent.action_count = 10
        agent.action_successes = 8
        agent.action_failures = 2
        agent.llm_tokens.used = 1000
        agent.llm_budget.used = 0.10
        state.agents["agent_alpha"] = agent

        metrics = engine.compute_agent_metrics(state, "agent_alpha")

        assert metrics is not None
        assert metrics.efficiency.total_actions == 10
        assert metrics.efficiency.successful_actions == 8
        assert metrics.efficiency.failed_actions == 2
        assert metrics.efficiency.success_rate == 0.8

        # Cost per success
        assert metrics.efficiency.tokens_per_success == 125.0  # 1000 / 8
        assert metrics.efficiency.budget_per_success == 0.0125  # 0.10 / 8

    def test_efficiency_with_no_actions(self) -> None:
        """Handles zero actions gracefully."""
        engine = MetricsEngine()

        state = WorldState()
        agent = AgentState(agent_id="agent_alpha")
        agent.action_count = 0
        state.agents["agent_alpha"] = agent

        metrics = engine.compute_agent_metrics(state, "agent_alpha")

        assert metrics.efficiency.total_actions == 0
        assert metrics.efficiency.success_rate is None  # Not 0

    def test_efficiency_with_no_successes(self) -> None:
        """Handles all failures gracefully."""
        engine = MetricsEngine()

        state = WorldState()
        agent = AgentState(agent_id="agent_alpha")
        agent.action_count = 5
        agent.action_successes = 0
        agent.action_failures = 5
        state.agents["agent_alpha"] = agent

        metrics = engine.compute_agent_metrics(state, "agent_alpha")

        assert metrics.efficiency.success_rate == 0.0
        assert metrics.efficiency.tokens_per_success is None  # Can't compute


class TestComputeResourceUtilization:
    """Tests for computing resource utilization."""

    def test_compute_resource_utilization(self) -> None:
        """Calculates resource utilization correctly."""
        engine = MetricsEngine()

        state = WorldState()
        agent = AgentState(agent_id="agent_alpha")
        agent.llm_tokens = ResourceUsage(used=5000, quota=10000)
        agent.llm_budget = ResourceUsage(used=0.50, quota=1.0)
        agent.disk = ResourceUsage(used=2500, quota=10000)
        state.agents["agent_alpha"] = agent

        metrics = engine.compute_agent_metrics(state, "agent_alpha")

        assert metrics.resources.tokens_used == 5000
        assert metrics.resources.tokens_quota == 10000
        assert metrics.resources.tokens_utilization == 0.5

        assert metrics.resources.budget_spent == 0.50
        assert metrics.resources.budget_initial == 1.0
        assert metrics.resources.budget_remaining == 0.50

        assert metrics.resources.disk_used == 2500
        assert metrics.resources.disk_quota == 10000
        assert metrics.resources.disk_utilization == 0.25

    def test_utilization_with_zero_quota(self) -> None:
        """Handles zero quota (missing data) gracefully."""
        engine = MetricsEngine()

        state = WorldState()
        agent = AgentState(agent_id="agent_alpha")
        # Quotas are 0 (no data)
        agent.llm_tokens = ResourceUsage(used=0, quota=0)
        agent.llm_budget = ResourceUsage(used=0, quota=0)
        agent.disk = ResourceUsage(used=0, quota=0)
        state.agents["agent_alpha"] = agent

        metrics = engine.compute_agent_metrics(state, "agent_alpha")

        # Utilization should be None (no data), not 0 or inf
        assert metrics.resources.tokens_utilization is None
        assert metrics.resources.budget_remaining is None
        assert metrics.resources.disk_utilization is None


class TestGlobalMetrics:
    """Tests for global metrics computation."""

    def test_global_metrics(self) -> None:
        """Computes global metrics correctly."""
        engine = MetricsEngine()

        state = WorldState()
        state.simulation_time = 120.0
        state.sequence = 500
        state.event_counts = {"action": 100, "tick": 10, "thinking": 50}

        # Add agents
        agent1 = AgentState(agent_id="agent_alpha")
        agent1.scrip = 100
        agent1.action_count = 50
        agent1.status = "active"
        state.agents["agent_alpha"] = agent1

        agent2 = AgentState(agent_id="agent_beta")
        agent2.scrip = 200
        agent2.action_count = 50
        agent2.status = "active"
        state.agents["agent_beta"] = agent2

        # Add artifacts
        artifact1 = ArtifactState(
            artifact_id="a1",
            artifact_type="code",
            owner="agent_alpha",
            created_by="agent_alpha",
            executable=True,
            invocation_count=10,
        )
        state.artifacts["a1"] = artifact1

        artifact2 = ArtifactState(
            artifact_id="a2",
            artifact_type="data",
            owner="agent_beta",
            created_by="agent_beta",
            executable=False,
            invocation_count=5,
        )
        state.artifacts["a2"] = artifact2

        metrics = engine.compute_global_metrics(state)

        assert metrics.elapsed_time == 120.0
        assert metrics.current_sequence == 500
        assert metrics.events_processed == 160  # 100 + 10 + 50

        assert metrics.total_scrip_circulation == 300  # 100 + 200
        assert metrics.total_transactions == 100  # action count

        assert metrics.total_actions == 100  # 50 + 50
        assert metrics.actions_per_second == pytest.approx(0.833, rel=0.01)
        assert metrics.active_agent_count == 2

        assert metrics.total_artifacts == 2
        assert metrics.executable_artifacts == 1
        assert metrics.total_invocations == 15


class TestAgentRankings:
    """Tests for agent ranking computation."""

    def test_agent_rankings(self) -> None:
        """Computes agent rankings correctly."""
        engine = MetricsEngine()

        state = WorldState()

        # Agent with most scrip but fewest actions
        agent1 = AgentState(agent_id="rich")
        agent1.scrip = 1000
        agent1.action_count = 10
        agent1.action_successes = 8
        state.agents["rich"] = agent1

        # Agent with medium scrip and actions
        agent2 = AgentState(agent_id="mid")
        agent2.scrip = 500
        agent2.action_count = 50
        agent2.action_successes = 40
        state.agents["mid"] = agent2

        # Agent with least scrip but most actions
        agent3 = AgentState(agent_id="active")
        agent3.scrip = 100
        agent3.action_count = 100
        agent3.action_successes = 90
        state.agents["active"] = agent3

        all_metrics = engine.compute_all_agent_metrics(state)

        # Scrip rankings (descending)
        assert all_metrics["rich"].scrip_rank == 1
        assert all_metrics["mid"].scrip_rank == 2
        assert all_metrics["active"].scrip_rank == 3

        # Activity rankings (descending by action count)
        assert all_metrics["active"].activity_rank == 1
        assert all_metrics["mid"].activity_rank == 2
        assert all_metrics["rich"].activity_rank == 3

        # Efficiency rankings (descending by success rate)
        # active: 90/100 = 0.9
        # mid: 40/50 = 0.8
        # rich: 8/10 = 0.8 (tied, order may vary)
        assert all_metrics["active"].efficiency_rank == 1


class TestResourceUtilizationSummary:
    """Tests for overall resource utilization summary."""

    def test_resource_utilization_summary(self) -> None:
        """Computes resource utilization summary."""
        engine = MetricsEngine()

        state = WorldState()

        agent1 = AgentState(agent_id="a1")
        agent1.llm_tokens = ResourceUsage(used=3000, quota=10000)
        agent1.llm_budget = ResourceUsage(used=0.25, quota=1.0)
        agent1.disk = ResourceUsage(used=1000, quota=5000)
        state.agents["a1"] = agent1

        agent2 = AgentState(agent_id="a2")
        agent2.llm_tokens = ResourceUsage(used=2000, quota=10000)
        agent2.llm_budget = ResourceUsage(used=0.50, quota=1.0)
        agent2.disk = ResourceUsage(used=2000, quota=5000)
        state.agents["a2"] = agent2

        summary = engine.compute_resource_utilization_summary(state)

        assert summary["tokens"]["used"] == 5000  # 3000 + 2000
        assert summary["tokens"]["quota"] == 20000  # 10000 + 10000
        assert summary["tokens"]["utilization"] == 0.25

        assert summary["budget"]["spent"] == 0.75  # 0.25 + 0.50
        assert summary["budget"]["initial"] == 2.0  # 1.0 + 1.0
        assert summary["budget"]["remaining"] == 1.25

        assert summary["disk"]["used"] == 3000  # 1000 + 2000
        assert summary["disk"]["quota"] == 10000  # 5000 + 5000
        assert summary["disk"]["utilization"] == 0.3


class TestNonexistentAgent:
    """Tests for handling nonexistent agents."""

    def test_metrics_for_nonexistent_agent(self) -> None:
        """Returns None for nonexistent agent."""
        engine = MetricsEngine()
        state = WorldState()

        metrics = engine.compute_agent_metrics(state, "nonexistent")
        assert metrics is None
