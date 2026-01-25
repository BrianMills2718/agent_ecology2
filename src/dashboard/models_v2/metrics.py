"""Computed metric models.

Metrics are derived from state, not stored directly.
These models define the structure for metric computations.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from pydantic import BaseModel


@dataclass
class ResourceMetrics:
    """Resource utilization metrics for a principal."""

    # Token metrics (renewable)
    tokens_used: float = 0.0
    tokens_quota: float = 0.0
    tokens_utilization: float | None = None  # None if no quota

    # Budget metrics (depletable)
    budget_spent: float = 0.0
    budget_initial: float = 0.0
    budget_remaining: float | None = None  # None if no initial budget

    # Disk metrics (allocatable)
    disk_used: float = 0.0
    disk_quota: float = 0.0
    disk_utilization: float | None = None  # None if no quota

    def compute_utilization(self) -> None:
        """Compute utilization percentages."""
        if self.tokens_quota > 0:
            self.tokens_utilization = self.tokens_used / self.tokens_quota
        if self.budget_initial > 0:
            self.budget_remaining = self.budget_initial - self.budget_spent
        if self.disk_quota > 0:
            self.disk_utilization = self.disk_used / self.disk_quota


@dataclass
class EfficiencyMetrics:
    """Agent efficiency metrics."""

    # Action efficiency
    total_actions: int = 0
    successful_actions: int = 0
    failed_actions: int = 0
    success_rate: float | None = None  # None if no actions

    # Economic efficiency
    scrip_earned: float = 0.0
    scrip_spent: float = 0.0
    net_scrip_change: float = 0.0

    # Resource efficiency (cost per successful action)
    tokens_per_success: float | None = None
    budget_per_success: float | None = None

    def compute_rates(self, tokens_used: float = 0, budget_spent: float = 0) -> None:
        """Compute efficiency rates."""
        if self.total_actions > 0:
            self.success_rate = self.successful_actions / self.total_actions

        if self.successful_actions > 0:
            if tokens_used > 0:
                self.tokens_per_success = tokens_used / self.successful_actions
            if budget_spent > 0:
                self.budget_per_success = budget_spent / self.successful_actions


@dataclass
class AgentMetrics:
    """Complete metrics for an agent."""

    agent_id: str
    resources: ResourceMetrics = field(default_factory=ResourceMetrics)
    efficiency: EfficiencyMetrics = field(default_factory=EfficiencyMetrics)

    # Ranking metrics
    scrip_rank: int | None = None
    activity_rank: int | None = None
    efficiency_rank: int | None = None


@dataclass
class GlobalMetrics:
    """Simulation-wide metrics."""

    # Time metrics
    elapsed_time: float = 0.0
    events_processed: int = 0
    current_sequence: int = 0

    # Economic metrics
    total_scrip_circulation: float = 0.0
    total_transactions: int = 0
    average_transaction_size: float = 0.0

    # Activity metrics
    total_actions: int = 0
    actions_per_second: float = 0.0
    active_agent_count: int = 0

    # Artifact metrics
    total_artifacts: int = 0
    executable_artifacts: int = 0
    total_invocations: int = 0


# Pydantic versions for API responses


class ResourceMetricsResponse(BaseModel):
    """Resource metrics for API responses."""

    tokens_used: float = 0.0
    tokens_quota: float = 0.0
    tokens_utilization: float | None = None
    budget_spent: float = 0.0
    budget_initial: float = 0.0
    budget_remaining: float | None = None
    disk_used: float = 0.0
    disk_quota: float = 0.0
    disk_utilization: float | None = None

    @classmethod
    def from_metrics(cls, metrics: ResourceMetrics) -> "ResourceMetricsResponse":
        """Create from internal metrics."""
        return cls(
            tokens_used=metrics.tokens_used,
            tokens_quota=metrics.tokens_quota,
            tokens_utilization=metrics.tokens_utilization,
            budget_spent=metrics.budget_spent,
            budget_initial=metrics.budget_initial,
            budget_remaining=metrics.budget_remaining,
            disk_used=metrics.disk_used,
            disk_quota=metrics.disk_quota,
            disk_utilization=metrics.disk_utilization,
        )


class EfficiencyMetricsResponse(BaseModel):
    """Efficiency metrics for API responses."""

    total_actions: int = 0
    successful_actions: int = 0
    failed_actions: int = 0
    success_rate: float | None = None
    tokens_per_success: float | None = None
    budget_per_success: float | None = None

    @classmethod
    def from_metrics(cls, metrics: EfficiencyMetrics) -> "EfficiencyMetricsResponse":
        """Create from internal metrics."""
        return cls(
            total_actions=metrics.total_actions,
            successful_actions=metrics.successful_actions,
            failed_actions=metrics.failed_actions,
            success_rate=metrics.success_rate,
            tokens_per_success=metrics.tokens_per_success,
            budget_per_success=metrics.budget_per_success,
        )


class AgentMetricsResponse(BaseModel):
    """Agent metrics for API responses."""

    agent_id: str
    resources: ResourceMetricsResponse
    efficiency: EfficiencyMetricsResponse
    scrip_rank: int | None = None
    activity_rank: int | None = None

    @classmethod
    def from_metrics(cls, metrics: AgentMetrics) -> "AgentMetricsResponse":
        """Create from internal metrics."""
        return cls(
            agent_id=metrics.agent_id,
            resources=ResourceMetricsResponse.from_metrics(metrics.resources),
            efficiency=EfficiencyMetricsResponse.from_metrics(metrics.efficiency),
            scrip_rank=metrics.scrip_rank,
            activity_rank=metrics.activity_rank,
        )


class GlobalMetricsResponse(BaseModel):
    """Global metrics for API responses."""

    elapsed_time: float = 0.0
    events_processed: int = 0
    current_sequence: int = 0
    total_scrip_circulation: float = 0.0
    total_transactions: int = 0
    active_agent_count: int = 0
    total_artifacts: int = 0
    executable_artifacts: int = 0
    total_invocations: int = 0

    @classmethod
    def from_metrics(cls, metrics: GlobalMetrics) -> "GlobalMetricsResponse":
        """Create from internal metrics."""
        return cls(
            elapsed_time=metrics.elapsed_time,
            events_processed=metrics.events_processed,
            current_sequence=metrics.current_sequence,
            total_scrip_circulation=metrics.total_scrip_circulation,
            total_transactions=metrics.total_transactions,
            active_agent_count=metrics.active_agent_count,
            total_artifacts=metrics.total_artifacts,
            executable_artifacts=metrics.executable_artifacts,
            total_invocations=metrics.total_invocations,
        )
