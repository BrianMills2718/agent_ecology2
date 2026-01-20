"""Ecosystem health KPI calculations.

Provides computed metrics that indicate overall ecosystem health,
capital flow, and emergence patterns.
"""

from __future__ import annotations

import math
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime
from typing import TYPE_CHECKING

from .models import EmergenceMetrics

if TYPE_CHECKING:
    from .parser import SimulationState


@dataclass
class AgentMetrics:
    """Per-agent computed metrics (Plan #76)."""

    total_actions: int = 0
    last_action_tick: int | None = None
    ticks_since_action: int = 0
    is_frozen: bool = False
    scrip_balance: int = 0
    success_rate: float = 0.0


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
    actions_per_second: float = 0.0  # Time-based metric (Plan #102)
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
    """Count agents that have exhausted their LLM token quota.

    An agent is frozen when llm_tokens_used >= llm_tokens_quota.
    """
    return sum(
        1
        for agent in agents
        if agent.get("llm_tokens_used", 0) >= agent.get("llm_tokens_quota", 0)
    )


def calculate_active_agent_ratio(
    agents: list[dict[str, int | None]],
    current_tick: int,
    threshold_events: int = 5,
) -> float:
    """Calculate ratio of agents that have acted recently.

    An agent is considered active if they have taken an action
    within the last threshold_events events. Note: This is based on
    event count (tick) for backward compatibility - consider migrating
    to time-based thresholds in future.
    """
    if not agents:
        return 0.0

    active_count = 0
    for agent in agents:
        last_action = agent.get("last_action_tick")
        if last_action is not None and (current_tick - last_action) <= threshold_events:
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
        {"llm_tokens_used": agent.llm_tokens_used, "llm_tokens_quota": agent.llm_tokens_quota}
        for agent in agents
    ]
    kpis.frozen_agent_count = count_frozen_agents(agent_dicts_for_frozen)

    # Actions per second (time-based metric)
    total_actions = sum(agent.action_count for agent in agents)
    if elapsed_seconds > 0:
        kpis.actions_per_second = total_actions / elapsed_seconds

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


def compute_agent_metrics(state: SimulationState, agent_id: str) -> AgentMetrics | None:
    """Compute metrics for a specific agent (Plan #76).

    Args:
        state: The current simulation state from the parser.
        agent_id: The ID of the agent to compute metrics for.

    Returns:
        AgentMetrics for the agent, or None if agent not found.
    """
    agent = state.agents.get(agent_id)
    if agent is None:
        return None

    # Calculate ticks since last action
    ticks_since_action = 0
    if agent.last_action_tick is not None:
        ticks_since_action = state.current_tick - agent.last_action_tick

    # Determine if agent is frozen (exhausted LLM tokens)
    is_frozen = agent.llm_tokens_used >= agent.llm_tokens_quota

    # Calculate success rate from action history
    success_rate = 0.0
    total_tracked = agent.action_successes + agent.action_failures
    if total_tracked > 0:
        success_rate = agent.action_successes / total_tracked

    return AgentMetrics(
        total_actions=agent.action_count,
        last_action_tick=agent.last_action_tick,
        ticks_since_action=ticks_since_action,
        is_frozen=is_frozen,
        scrip_balance=agent.scrip,
        success_rate=success_rate,
    )


# Emergence Metrics (Plan #110 Phase 3)


def calculate_coordination_density(
    interactions: list[object], agent_count: int
) -> float:
    """Calculate coordination density: interactions / (n × (n-1)).

    Measures how connected the agent network is. A value of 1.0 means
    every agent has interacted with every other agent at least once.

    Args:
        interactions: List of Interaction objects
        agent_count: Number of agents

    Returns:
        Coordination density between 0.0 and 1.0+
        (can exceed 1.0 if there are many interactions per pair)
    """
    if agent_count < 2:
        return 0.0

    # Count unique agent pairs that have interacted
    interacted_pairs: set[tuple[str, str]] = set()
    for interaction in interactions:
        from_id = getattr(interaction, "from_id", "")
        to_id = getattr(interaction, "to_id", "")
        if from_id and to_id and from_id != to_id:
            # Normalize pair order for bidirectional counting
            pair = tuple(sorted([from_id, to_id]))
            interacted_pairs.add(pair)  # type: ignore[arg-type]

    max_possible_pairs = agent_count * (agent_count - 1) // 2
    if max_possible_pairs == 0:
        return 0.0

    return len(interacted_pairs) / max_possible_pairs


def calculate_specialization_index(
    agent_action_counts: dict[str, dict[str, int]]
) -> float:
    """Calculate specialization index from agent action distributions.

    Higher values indicate agents are more specialized (focused on
    certain action types). Lower values indicate generalist behavior.

    Uses the coefficient of variation (std_dev / mean) of each agent's
    action type distribution, averaged across agents.

    Args:
        agent_action_counts: {agent_id: {action_type: count}}

    Returns:
        Specialization index (0.0 = all generalists, higher = more specialized)
    """
    if not agent_action_counts:
        return 0.0

    specialization_scores: list[float] = []

    for agent_id, action_counts in agent_action_counts.items():
        if not action_counts:
            continue

        counts = list(action_counts.values())
        if len(counts) < 2:
            # If agent only does one action type, they're maximally specialized
            specialization_scores.append(1.0)
            continue

        mean = sum(counts) / len(counts)
        if mean == 0:
            continue

        variance = sum((c - mean) ** 2 for c in counts) / len(counts)
        std_dev = math.sqrt(variance)

        # Coefficient of variation
        cv = std_dev / mean
        specialization_scores.append(cv)

    if not specialization_scores:
        return 0.0

    return sum(specialization_scores) / len(specialization_scores)


def calculate_reuse_ratio(state: SimulationState) -> float:
    """Calculate artifact reuse ratio.

    reuse_ratio = artifacts_used_by_others / total_artifacts

    Measures infrastructure building - higher values indicate agents
    are creating artifacts that others find useful.

    Args:
        state: The simulation state

    Returns:
        Reuse ratio between 0.0 and 1.0
    """
    if not state.artifacts:
        return 0.0

    # Count artifacts that have been invoked by agents other than the owner
    artifacts_used_by_others = 0

    # Build a set of artifact IDs that have been invoked by non-owners
    invoked_by_others: set[str] = set()

    for interaction in state.interactions:
        if interaction.interaction_type in ("artifact_invoke", "genesis_invoke"):
            artifact_id = interaction.artifact_id
            invoker_id = interaction.from_id
            if artifact_id:
                artifact = state.artifacts.get(artifact_id)
                if artifact and artifact.owner_id != invoker_id:
                    invoked_by_others.add(artifact_id)

    artifacts_used_by_others = len(invoked_by_others)

    # Count non-genesis artifacts
    non_genesis_artifacts = sum(
        1 for art in state.artifacts.values()
        if not art.artifact_id.startswith("genesis_")
    )

    if non_genesis_artifacts == 0:
        return 0.0

    return artifacts_used_by_others / non_genesis_artifacts


def calculate_genesis_independence(state: SimulationState) -> float:
    """Calculate genesis independence ratio.

    genesis_independence = non_genesis_ops / total_ops

    Measures ecosystem maturity - higher values indicate agents are
    using each other's artifacts rather than just genesis services.

    Args:
        state: The simulation state

    Returns:
        Genesis independence ratio between 0.0 and 1.0
    """
    genesis_invocations = 0
    non_genesis_invocations = 0

    for interaction in state.interactions:
        if interaction.interaction_type == "genesis_invoke":
            genesis_invocations += 1
        elif interaction.interaction_type == "artifact_invoke":
            artifact_id = interaction.artifact_id
            if artifact_id and artifact_id.startswith("genesis_"):
                genesis_invocations += 1
            else:
                non_genesis_invocations += 1

    total = genesis_invocations + non_genesis_invocations
    if total == 0:
        return 0.0

    return non_genesis_invocations / total


def calculate_capital_depth(state: SimulationState) -> int:
    """Calculate capital depth (max dependency chain length).

    Measures how deep the capital structure is - longer chains indicate
    more sophisticated tool-building and composition.

    Args:
        state: The simulation state

    Returns:
        Maximum dependency chain length (0 if no dependencies)
    """
    # Build dependency graph from artifact dependencies
    dependencies: dict[str, set[str]] = defaultdict(set)

    for artifact_id, artifact in state.artifacts.items():
        # Check if artifact has dependency metadata
        if hasattr(artifact, "dependencies") and artifact.dependencies:
            for dep_id in artifact.dependencies:
                dependencies[artifact_id].add(dep_id)

    if not dependencies:
        return 0

    # Calculate max depth using BFS from each node
    def get_depth(artifact_id: str, visited: set[str]) -> int:
        if artifact_id in visited:
            return 0  # Cycle detection
        if artifact_id not in dependencies:
            return 0

        visited.add(artifact_id)
        max_dep_depth = 0
        for dep_id in dependencies[artifact_id]:
            dep_depth = get_depth(dep_id, visited.copy())
            max_dep_depth = max(max_dep_depth, dep_depth)
        return max_dep_depth + 1

    max_depth = 0
    for artifact_id in dependencies:
        depth = get_depth(artifact_id, set())
        max_depth = max(max_depth, depth)

    return max_depth


def calculate_coalition_count(
    interactions: list[object], agent_ids: list[str]
) -> int:
    """Count coalitions (clusters of interacting agents).

    Uses connected components in the interaction graph.

    Args:
        interactions: List of Interaction objects
        agent_ids: List of all agent IDs

    Returns:
        Number of distinct coalitions (clusters)
    """
    if not agent_ids:
        return 0

    # Build adjacency list
    adj: dict[str, set[str]] = {agent_id: set() for agent_id in agent_ids}

    for interaction in interactions:
        from_id = getattr(interaction, "from_id", "")
        to_id = getattr(interaction, "to_id", "")
        if from_id in adj and to_id in adj and from_id != to_id:
            adj[from_id].add(to_id)
            adj[to_id].add(from_id)

    # Find connected components using DFS
    visited: set[str] = set()
    coalition_count = 0

    def dfs(agent_id: str) -> None:
        visited.add(agent_id)
        for neighbor in adj[agent_id]:
            if neighbor not in visited:
                dfs(neighbor)

    for agent_id in agent_ids:
        if agent_id not in visited:
            dfs(agent_id)
            coalition_count += 1

    return coalition_count


def calculate_emergence_metrics(state: SimulationState) -> EmergenceMetrics:
    """Calculate all emergence observability metrics.

    Args:
        state: The simulation state from the parser

    Returns:
        EmergenceMetrics with all computed values
    """
    agents = list(state.agents.values())
    agent_ids = list(state.agents.keys())
    agent_count = len(agents)

    # Build agent action type distributions
    agent_action_counts: dict[str, dict[str, int]] = defaultdict(
        lambda: defaultdict(int)
    )

    # Build action counts from each agent's action history
    for agent_id, agent in state.agents.items():
        for action in agent.actions:
            action_type = getattr(action, "action_type", "")
            if action_type:
                agent_action_counts[agent_id][action_type] += 1

    # Count genesis vs non-genesis invocations
    genesis_invocations = 0
    non_genesis_invocations = 0

    for interaction in state.interactions:
        if interaction.interaction_type == "genesis_invoke":
            genesis_invocations += 1
        elif interaction.interaction_type == "artifact_invoke":
            artifact_id = interaction.artifact_id
            if artifact_id and artifact_id.startswith("genesis_"):
                genesis_invocations += 1
            else:
                non_genesis_invocations += 1

    return EmergenceMetrics(
        # Network metrics
        coordination_density=calculate_coordination_density(
            state.interactions, agent_count
        ),
        coalition_count=calculate_coalition_count(state.interactions, agent_ids),
        # Specialization metrics
        specialization_index=calculate_specialization_index(
            dict(agent_action_counts)
        ),
        # Infrastructure metrics
        reuse_ratio=calculate_reuse_ratio(state),
        genesis_independence=calculate_genesis_independence(state),
        capital_depth=calculate_capital_depth(state),
        # Metadata
        agent_count=agent_count,
        total_interactions=len(state.interactions),
        total_artifacts=len(state.artifacts),
        genesis_invocations=genesis_invocations,
        non_genesis_invocations=non_genesis_invocations,
        # Per-agent specialization data
        agent_specializations=dict(agent_action_counts),
    )
