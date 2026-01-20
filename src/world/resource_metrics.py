"""Resource metrics provider for agent visibility.

Provides read-only aggregation of resource metrics from multiple sources:
- Ledger.resources (llm_budget, etc.)
- Agent.llm.get_usage_stats() (tokens, cost, requests)
- Config (initial allocations)

This is a separate component from ResourceManager (clean separation of concerns):
- ResourceManager: state management (writes + state reads)
- ResourceMetricsProvider: read-only aggregation for visibility

Plan #93: Agent Resource Visibility
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Any, Literal

from pydantic import BaseModel, Field


class ResourceVisibilityConfig(BaseModel):
    """Per-agent visibility configuration."""

    resources: list[str] | None = Field(
        default=None,
        description="Resources to show (None = use system default)",
    )
    detail_level: Literal["minimal", "standard", "verbose"] = Field(
        default="standard",
        description="Detail level: minimal (remaining only), standard (core metrics), verbose (all)",
    )
    see_others: bool = Field(
        default=False,
        description="Whether to see other agents' resources",
    )


@dataclass
class ResourceMetrics:
    """Metrics for a single resource."""

    resource_name: str
    unit: str
    remaining: float

    # Core metrics (standard+ detail level)
    initial: float | None = None
    spent: float | None = None
    percentage: float | None = None

    # LLM-specific metrics (verbose detail level)
    tokens_in: int | None = None
    tokens_out: int | None = None
    total_requests: int | None = None
    avg_cost_per_request: float | None = None
    burn_rate: float | None = None  # units per second


@dataclass
class AgentResourceMetrics:
    """All resource metrics for an agent."""

    agent_id: str
    resources: dict[str, ResourceMetrics] = field(default_factory=dict)
    timestamp: float = field(default_factory=time.time)


class ResourceMetricsProvider:
    """Provides read-only aggregation of resource metrics for visibility.

    Aggregates from multiple sources:
    - Ledger.resources for current balances
    - Agent.llm.get_usage_stats() for token/cost metrics
    - Config for initial allocations

    Respects detail level configuration for progressive disclosure.
    """

    def __init__(
        self,
        initial_allocations: dict[str, float],
        resource_units: dict[str, str],
    ) -> None:
        """Initialize the metrics provider.

        Args:
            initial_allocations: Initial allocation for each resource (e.g., {"llm_budget": 1.0})
            resource_units: Unit of measurement for each resource (e.g., {"llm_budget": "dollars"})
        """
        self.initial_allocations = initial_allocations
        self.resource_units = resource_units

    def validate_config(self, config: ResourceVisibilityConfig) -> None:
        """Validate visibility config, raising error for unknown resources.

        Args:
            config: Visibility configuration to validate

        Raises:
            ValueError: If config references unknown resources
        """
        if config.resources is not None:
            for resource in config.resources:
                if resource not in self.initial_allocations:
                    raise ValueError(
                        f"Unknown resource '{resource}' in visibility config. "
                        f"Known resources: {list(self.initial_allocations.keys())}"
                    )

    def get_agent_metrics(
        self,
        agent_id: str,
        ledger_resources: dict[str, dict[str, float]],
        agents: dict[str, Any],
        start_time: float,
        visibility_config: ResourceVisibilityConfig | None = None,
    ) -> AgentResourceMetrics:
        """Get resource metrics for an agent.

        Args:
            agent_id: ID of the agent to get metrics for
            ledger_resources: Resource balances from ledger (principal -> resource -> amount)
            agents: Dict of agent objects (agent_id -> Agent)
            start_time: Simulation start time for burn rate calculation
            visibility_config: Optional visibility configuration (defaults to verbose)

        Returns:
            AgentResourceMetrics with requested detail level
        """
        config = visibility_config or ResourceVisibilityConfig(detail_level="verbose")
        current_time = time.time()
        elapsed_seconds = max(current_time - start_time, 0.001)  # Avoid division by zero

        # Determine which resources to include
        if config.resources is not None:
            resource_names = config.resources
        else:
            resource_names = list(self.initial_allocations.keys())

        # Get agent's current resources from ledger
        agent_resources = ledger_resources.get(agent_id, {})

        # Get LLM usage stats if agent exists
        llm_stats: dict[str, Any] = {}
        if agent_id in agents:
            agent = agents[agent_id]
            if hasattr(agent, "llm") and hasattr(agent.llm, "get_usage_stats"):
                llm_stats = agent.llm.get_usage_stats()

        # Build metrics for each resource
        metrics: dict[str, ResourceMetrics] = {}
        for resource_name in resource_names:
            if resource_name not in self.initial_allocations:
                continue  # Skip unknown resources

            initial = self.initial_allocations[resource_name]
            remaining = agent_resources.get(resource_name, initial)
            unit = self.resource_units.get(resource_name, "units")

            # Build metrics based on detail level
            resource_metrics = self._build_resource_metrics(
                resource_name=resource_name,
                unit=unit,
                remaining=remaining,
                initial=initial,
                elapsed_seconds=elapsed_seconds,
                llm_stats=llm_stats,
                detail_level=config.detail_level,
            )
            metrics[resource_name] = resource_metrics

        return AgentResourceMetrics(
            agent_id=agent_id,
            resources=metrics,
            timestamp=current_time,
        )

    def _build_resource_metrics(
        self,
        resource_name: str,
        unit: str,
        remaining: float,
        initial: float,
        elapsed_seconds: float,
        llm_stats: dict[str, Any],
        detail_level: str,
    ) -> ResourceMetrics:
        """Build resource metrics based on detail level.

        Detail levels:
        - minimal: remaining only
        - standard: remaining, initial, spent, percentage
        - verbose: all metrics including LLM-specific
        """
        # Always include remaining
        metrics = ResourceMetrics(
            resource_name=resource_name,
            unit=unit,
            remaining=remaining,
        )

        # Standard level: add core metrics
        if detail_level in ("standard", "verbose"):
            metrics.initial = initial
            metrics.spent = initial - remaining
            if initial > 0:
                metrics.percentage = (remaining / initial) * 100
            else:
                metrics.percentage = 100.0

        # Verbose level: add all metrics
        if detail_level == "verbose":
            # Burn rate
            spent = initial - remaining
            if elapsed_seconds > 0:
                metrics.burn_rate = spent / elapsed_seconds

            # LLM-specific metrics (for llm_budget resource)
            if resource_name == "llm_budget" and llm_stats:
                metrics.total_requests = llm_stats.get("requests", 0)

                # Token tracking - LLMProvider tracks total_tokens
                total_tokens = llm_stats.get("total_tokens", 0)
                if total_tokens > 0:
                    # Estimate in/out split (rough: 70% input, 30% output typical)
                    # Better tracking would require per-call breakdown
                    metrics.tokens_in = int(total_tokens * 0.7)
                    metrics.tokens_out = int(total_tokens * 0.3)

                # Average cost per request
                total_cost = llm_stats.get("total_cost", 0.0)
                requests = llm_stats.get("requests", 0)
                if requests > 0:
                    metrics.avg_cost_per_request = total_cost / requests

        return metrics

    def get_all_metrics(
        self,
        ledger_resources: dict[str, dict[str, float]],
        agents: dict[str, Any],
        start_time: float,
        visibility_config: ResourceVisibilityConfig | None = None,
    ) -> dict[str, AgentResourceMetrics]:
        """Get resource metrics for all agents.

        Args:
            ledger_resources: Resource balances from ledger
            agents: Dict of agent objects
            start_time: Simulation start time
            visibility_config: Optional visibility configuration

        Returns:
            Dict mapping agent_id to AgentResourceMetrics
        """
        result: dict[str, AgentResourceMetrics] = {}
        for agent_id in agents:
            result[agent_id] = self.get_agent_metrics(
                agent_id=agent_id,
                ledger_resources=ledger_resources,
                agents=agents,
                start_time=start_time,
                visibility_config=visibility_config,
            )
        return result
