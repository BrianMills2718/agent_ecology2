"""Metrics engine: State → computed metrics.

Responsible for:
- Computing derived metrics from world state
- Ranking agents by various criteria
- Calculating efficiency and utilization metrics
"""

from __future__ import annotations

import logging
from typing import Any

from ..models_v2.state import WorldState, AgentState
from ..models_v2.metrics import (
    AgentMetrics,
    ResourceMetrics,
    EfficiencyMetrics,
    GlobalMetrics,
)

logger = logging.getLogger(__name__)


class MetricsEngine:
    """Compute metrics from world state.

    Usage:
        engine = MetricsEngine()
        state = tracker.get_state()
        global_metrics = engine.compute_global_metrics(state)
        agent_metrics = engine.compute_agent_metrics(state, "agent_alpha")
    """

    def compute_global_metrics(self, state: WorldState) -> GlobalMetrics:
        """Compute simulation-wide metrics."""
        metrics = GlobalMetrics()

        metrics.elapsed_time = state.simulation_time
        metrics.events_processed = sum(state.event_counts.values())
        metrics.current_sequence = state.sequence

        # Economic metrics
        metrics.total_scrip_circulation = state.total_scrip
        if metrics.total_scrip_circulation == 0:
            # Calculate from agents if not set
            metrics.total_scrip_circulation = sum(
                a.scrip for a in state.agents.values()
            )

        # Count transactions from action events
        metrics.total_transactions = state.event_counts.get("action", 0)

        # Activity metrics
        metrics.total_actions = sum(a.action_count for a in state.agents.values())
        if metrics.elapsed_time > 0:
            metrics.actions_per_second = metrics.total_actions / metrics.elapsed_time

        metrics.active_agent_count = state.active_agents
        if metrics.active_agent_count == 0:
            metrics.active_agent_count = sum(
                1 for a in state.agents.values() if a.status == "active"
            )

        # Artifact metrics
        metrics.total_artifacts = state.total_artifacts
        if metrics.total_artifacts == 0:
            metrics.total_artifacts = len(state.artifacts)

        metrics.executable_artifacts = sum(
            1 for a in state.artifacts.values() if a.executable
        )
        metrics.total_invocations = sum(
            a.invocation_count for a in state.artifacts.values()
        )

        return metrics

    def compute_agent_metrics(
        self, state: WorldState, agent_id: str
    ) -> AgentMetrics | None:
        """Compute metrics for a specific agent."""
        agent = state.get_agent(agent_id)
        if not agent:
            return None

        metrics = AgentMetrics(agent_id=agent_id)

        # Resource metrics
        metrics.resources = self._compute_resource_metrics(agent)

        # Efficiency metrics
        metrics.efficiency = self._compute_efficiency_metrics(agent)
        metrics.efficiency.compute_rates(
            tokens_used=agent.llm_tokens.used,
            budget_spent=agent.llm_budget.used,
        )

        # Rankings (computed across all agents)
        rankings = self._compute_rankings(state)
        metrics.scrip_rank = rankings.get(agent_id, {}).get("scrip_rank")
        metrics.activity_rank = rankings.get(agent_id, {}).get("activity_rank")
        metrics.efficiency_rank = rankings.get(agent_id, {}).get("efficiency_rank")

        return metrics

    def compute_all_agent_metrics(
        self, state: WorldState
    ) -> dict[str, AgentMetrics]:
        """Compute metrics for all agents."""
        rankings = self._compute_rankings(state)

        result = {}
        for agent_id, agent in state.agents.items():
            metrics = AgentMetrics(agent_id=agent_id)
            metrics.resources = self._compute_resource_metrics(agent)
            metrics.efficiency = self._compute_efficiency_metrics(agent)
            metrics.efficiency.compute_rates(
                tokens_used=agent.llm_tokens.used,
                budget_spent=agent.llm_budget.used,
            )

            # Apply rankings
            agent_ranks = rankings.get(agent_id, {})
            metrics.scrip_rank = agent_ranks.get("scrip_rank")
            metrics.activity_rank = agent_ranks.get("activity_rank")
            metrics.efficiency_rank = agent_ranks.get("efficiency_rank")

            result[agent_id] = metrics

        return result

    def _compute_resource_metrics(self, agent: AgentState) -> ResourceMetrics:
        """Compute resource utilization for an agent."""
        metrics = ResourceMetrics()

        # Token metrics
        metrics.tokens_used = agent.llm_tokens.used
        metrics.tokens_quota = agent.llm_tokens.quota

        # Budget metrics
        metrics.budget_spent = agent.llm_budget.used
        metrics.budget_initial = agent.llm_budget.quota

        # Disk metrics
        metrics.disk_used = agent.disk.used
        metrics.disk_quota = agent.disk.quota

        # Compute utilization percentages
        metrics.compute_utilization()

        return metrics

    def _compute_efficiency_metrics(self, agent: AgentState) -> EfficiencyMetrics:
        """Compute efficiency metrics for an agent."""
        metrics = EfficiencyMetrics()

        metrics.total_actions = agent.action_count
        metrics.successful_actions = agent.action_successes
        metrics.failed_actions = agent.action_failures

        # Net scrip would require historical data
        # For now, just use current scrip as a proxy
        metrics.net_scrip_change = agent.scrip

        return metrics

    def _compute_rankings(
        self, state: WorldState
    ) -> dict[str, dict[str, int | None]]:
        """Compute rankings for all agents."""
        agents = list(state.agents.values())
        if not agents:
            return {}

        # Sort by scrip (descending)
        scrip_sorted = sorted(agents, key=lambda a: a.scrip, reverse=True)
        scrip_ranks = {a.agent_id: i + 1 for i, a in enumerate(scrip_sorted)}

        # Sort by activity (action count, descending)
        activity_sorted = sorted(agents, key=lambda a: a.action_count, reverse=True)
        activity_ranks = {a.agent_id: i + 1 for i, a in enumerate(activity_sorted)}

        # Sort by efficiency (success rate, descending)
        def get_success_rate(a: AgentState) -> float:
            if a.action_count == 0:
                return 0.0
            return a.action_successes / a.action_count

        efficiency_sorted = sorted(agents, key=get_success_rate, reverse=True)
        efficiency_ranks = {a.agent_id: i + 1 for i, a in enumerate(efficiency_sorted)}

        # Combine rankings
        result = {}
        for agent in agents:
            result[agent.agent_id] = {
                "scrip_rank": scrip_ranks.get(agent.agent_id),
                "activity_rank": activity_ranks.get(agent.agent_id),
                "efficiency_rank": efficiency_ranks.get(agent.agent_id),
            }

        return result

    def compute_resource_utilization_summary(
        self, state: WorldState
    ) -> dict[str, Any]:
        """Compute overall resource utilization summary."""
        total_tokens_used = sum(a.llm_tokens.used for a in state.agents.values())
        total_tokens_quota = sum(a.llm_tokens.quota for a in state.agents.values())

        total_budget_spent = sum(a.llm_budget.used for a in state.agents.values())
        total_budget_initial = sum(a.llm_budget.quota for a in state.agents.values())

        total_disk_used = sum(a.disk.used for a in state.agents.values())
        total_disk_quota = sum(a.disk.quota for a in state.agents.values())

        return {
            "tokens": {
                "used": total_tokens_used,
                "quota": total_tokens_quota,
                "utilization": (
                    total_tokens_used / total_tokens_quota
                    if total_tokens_quota > 0
                    else None
                ),
            },
            "budget": {
                "spent": total_budget_spent,
                "initial": total_budget_initial,
                "remaining": (
                    total_budget_initial - total_budget_spent
                    if total_budget_initial > 0
                    else None
                ),
            },
            "disk": {
                "used": total_disk_used,
                "quota": total_disk_quota,
                "utilization": (
                    total_disk_used / total_disk_quota if total_disk_quota > 0 else None
                ),
            },
        }
