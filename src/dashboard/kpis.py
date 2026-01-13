"""Ecosystem health KPI calculations.

Provides computed metrics that indicate overall ecosystem health,
capital flow, and emergence patterns.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .parser import SimulationState


@dataclass
class EcosystemKPIs:
    """Computed ecosystem health metrics."""

    # Capital metrics
    total_scrip: int = 0
    scrip_velocity: float = 0.0
    gini_coefficient: float = 0.0
    median_scrip: int = 0

    # Activity metrics
    active_agent_ratio: float = 0.0
    frozen_agent_count: int = 0
    actions_per_tick: float = 0.0
    thinking_cost_rate: float = 0.0

    # Market metrics
    escrow_volume: int = 0
    escrow_active_listings: int = 0
    mint_scrip_rate: float = 0.0
    artifact_creation_rate: float = 0.0

    # Resource metrics
    llm_budget_remaining: float = 0.0
    llm_budget_burn_rate: float = 0.0

    # Emergence metrics
    agent_spawn_rate: float = 0.0
    coordination_events: int = 0
    artifact_diversity: int = 0

    # Trends (last N ticks)
    scrip_velocity_trend: list[float] = field(default_factory=list)
    activity_trend: list[float] = field(default_factory=list)


def calculate_gini_coefficient(balances: list[int]) -> float:
    """Calculate Gini coefficient from scrip balances.

    The Gini coefficient measures wealth inequality:
    - 0 = perfect equality (everyone has same amount)
    - 1 = perfect inequality (one person has everything)

    Uses the formula: G = (2 * sum(i * y_i) / (n * sum(y_i))) - (n + 1) / n
    where y_i are sorted values and i is the rank (1-indexed).
    """
    if not balances:
        return 0.0

    n = len(balances)
    if n == 1:
        return 0.0

    # Sort balances
    sorted_balances = sorted(balances)
    total = sum(sorted_balances)

    if total == 0:
        return 0.0

    # Calculate using the standard formula
    # G = (2 * sum((i+1) * y_i)) / (n * total) - (n + 1) / n
    weighted_sum = sum((i + 1) * y for i, y in enumerate(sorted_balances))
    gini = (2 * weighted_sum) / (n * total) - (n + 1) / n

    return max(0.0, min(1.0, gini))  # Clamp to [0, 1]


def calculate_scrip_velocity(
    total_transfers: int, total_scrip: int, elapsed_seconds: float
) -> float:
    """Calculate scrip velocity (transfers per scrip per second).

    Velocity = total_transfers / total_scrip / elapsed_time

    Higher velocity indicates more economic activity.
    """
    if total_scrip <= 0 or elapsed_seconds <= 0:
        return 0.0

    return total_transfers / total_scrip / elapsed_seconds


def count_frozen_agents(agents: list[dict[str, float]]) -> int:
    """Count agents that have exhausted their compute quota.

    An agent is frozen when compute_used >= compute_quota.
    """
    return sum(
        1
        for agent in agents
        if agent.get("compute_used", 0) >= agent.get("compute_quota", 0)
    )


def calculate_active_agent_ratio(
    agents: list[dict[str, int | None]],
    current_tick: int,
    threshold_ticks: int = 5,
) -> float:
    """Calculate ratio of agents that have acted recently.

    An agent is considered active if they have taken an action
    within the last threshold_ticks ticks.
    """
    if not agents:
        return 0.0

    active_count = 0
    for agent in agents:
        last_action = agent.get("last_action_tick")
        if last_action is not None and (current_tick - last_action) <= threshold_ticks:
            active_count += 1

    return active_count / len(agents)


def calculate_median_scrip(balances: list[int]) -> int:
    """Calculate median scrip balance.

    For odd count, returns middle value.
    For even count, returns floor of average of middle two.
    """
    if not balances:
        return 0

    sorted_balances = sorted(balances)
    n = len(sorted_balances)

    if n % 2 == 1:
        return sorted_balances[n // 2]
    else:
        mid = n // 2
        return (sorted_balances[mid - 1] + sorted_balances[mid]) // 2


def calculate_kpis(state: SimulationState) -> EcosystemKPIs:
    """Calculate all ecosystem KPIs from simulation state.

    Args:
        state: The current simulation state from the parser.

    Returns:
        EcosystemKPIs with all computed metrics.
    """
    kpis = EcosystemKPIs()

    # Get agent data
    agents = list(state.agents.values())
    if not agents:
        return kpis

    # Capital metrics
    scrip_balances = [agent.scrip for agent in agents]
    kpis.total_scrip = sum(scrip_balances)
    kpis.median_scrip = calculate_median_scrip(scrip_balances)
    kpis.gini_coefficient = calculate_gini_coefficient(scrip_balances)

    # Calculate elapsed time
    elapsed_seconds = 0.0
    if state.start_time:
        try:
            start = datetime.fromisoformat(state.start_time)
            elapsed_seconds = (datetime.now() - start).total_seconds()
        except (ValueError, TypeError):
            pass

    # Scrip velocity from transfers
    total_transfers = sum(t.amount for t in state.ledger_transfers)
    kpis.scrip_velocity = calculate_scrip_velocity(
        total_transfers, kpis.total_scrip, elapsed_seconds
    )

    # Activity metrics
    agent_dicts_for_active = [
        {"last_action_tick": agent.last_action_tick}
        for agent in agents
    ]
    kpis.active_agent_ratio = calculate_active_agent_ratio(
        agent_dicts_for_active, state.current_tick
    )

    agent_dicts_for_frozen = [
        {"compute_used": agent.compute_used, "compute_quota": agent.compute_quota}
        for agent in agents
    ]
    kpis.frozen_agent_count = count_frozen_agents(agent_dicts_for_frozen)

    # Actions per tick
    if state.current_tick > 0:
        total_actions = sum(agent.action_count for agent in agents)
        kpis.actions_per_tick = total_actions / state.current_tick

    # Thinking cost rate (cost per second)
    total_thinking_cost = sum(
        t.thinking_cost
        for agent in agents
        for t in agent.thinking_history
    )
    if elapsed_seconds > 0:
        kpis.thinking_cost_rate = total_thinking_cost / elapsed_seconds

    # Market metrics
    kpis.escrow_active_listings = len(state.escrow_listings)
    kpis.escrow_volume = sum(trade.get("price", 0) for trade in state.escrow_trades)

    # Mint scrip rate
    if elapsed_seconds > 0:
        kpis.mint_scrip_rate = state.total_scrip_minted / elapsed_seconds

    # Artifact creation rate
    if state.current_tick > 0:
        kpis.artifact_creation_rate = len(state.artifacts) / state.current_tick

    # Resource metrics
    kpis.llm_budget_remaining = state.api_cost_limit - state.api_cost_spent
    if elapsed_seconds > 0:
        kpis.llm_budget_burn_rate = state.api_cost_spent / elapsed_seconds

    # Emergence metrics
    if elapsed_seconds > 0:
        kpis.agent_spawn_rate = len(state.ledger_spawns) / elapsed_seconds

    # Coordination events (artifact invocations between different agents)
    kpis.coordination_events = sum(
        1
        for interaction in state.interactions
        if interaction.interaction_type == "artifact_invoke"
    )

    # Artifact diversity (unique artifact types)
    artifact_types = set(art.artifact_type for art in state.artifacts.values())
    kpis.artifact_diversity = len(artifact_types)

    # Calculate trends from tick summaries (last 10 ticks)
    recent_summaries = state.tick_summaries[-10:]
    if recent_summaries:
        # Activity trend
        kpis.activity_trend = [
            float(s.action_count) for s in recent_summaries
        ]

        # Scrip velocity trend requires per-tick calculation
        # For simplicity, use scrip transferred per tick as proxy
        kpis.scrip_velocity_trend = [
            float(s.total_scrip_transferred) for s in recent_summaries
        ]

    return kpis
