"""Metrics and KPI API endpoints."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from ...models_v2.state import WorldState
from ...models_v2.metrics import GlobalMetricsResponse, AgentMetricsResponse
from ...core_v2.metrics_engine import MetricsEngine

router = APIRouter()

# Injected by server
_world_state: WorldState | None = None
_metrics_engine: MetricsEngine | None = None


def set_dependencies(world_state: WorldState, metrics_engine: MetricsEngine) -> None:
    """Set dependencies for route handlers."""
    global _world_state, _metrics_engine
    _world_state = world_state
    _metrics_engine = metrics_engine


class ResourceSummaryResponse(BaseModel):
    """Resource utilization summary."""

    tokens: dict[str, Any]
    budget: dict[str, Any]
    disk: dict[str, Any]


class LeaderboardEntry(BaseModel):
    """Entry in a leaderboard."""

    agent_id: str
    value: float
    rank: int


class LeaderboardResponse(BaseModel):
    """Response for leaderboard endpoints."""

    category: str
    entries: list[LeaderboardEntry]


@router.get("/global", response_model=GlobalMetricsResponse)
async def get_global_metrics() -> GlobalMetricsResponse:
    """Get simulation-wide metrics."""
    if _world_state is None or _metrics_engine is None:
        raise HTTPException(status_code=503, detail="State not initialized")

    metrics = _metrics_engine.compute_global_metrics(_world_state)
    return GlobalMetricsResponse.from_metrics(metrics)


@router.get("/resources", response_model=ResourceSummaryResponse)
async def get_resource_summary() -> ResourceSummaryResponse:
    """Get overall resource utilization summary."""
    if _world_state is None or _metrics_engine is None:
        raise HTTPException(status_code=503, detail="State not initialized")

    summary = _metrics_engine.compute_resource_utilization_summary(_world_state)
    return ResourceSummaryResponse(
        tokens=summary["tokens"],
        budget=summary["budget"],
        disk=summary["disk"],
    )


@router.get("/agents", response_model=dict[str, AgentMetricsResponse])
async def get_all_agent_metrics() -> dict[str, AgentMetricsResponse]:
    """Get metrics for all agents."""
    if _world_state is None or _metrics_engine is None:
        raise HTTPException(status_code=503, detail="State not initialized")

    all_metrics = _metrics_engine.compute_all_agent_metrics(_world_state)
    return {
        agent_id: AgentMetricsResponse.from_metrics(metrics)
        for agent_id, metrics in all_metrics.items()
    }


@router.get("/leaderboard/scrip", response_model=LeaderboardResponse)
async def get_scrip_leaderboard(limit: int = 10) -> LeaderboardResponse:
    """Get agents ranked by scrip balance."""
    if _world_state is None:
        raise HTTPException(status_code=503, detail="State not initialized")

    agents = list(_world_state.agents.values())
    sorted_agents = sorted(agents, key=lambda a: a.scrip, reverse=True)[:limit]

    entries = [
        LeaderboardEntry(agent_id=a.agent_id, value=a.scrip, rank=i + 1)
        for i, a in enumerate(sorted_agents)
    ]

    return LeaderboardResponse(category="scrip", entries=entries)


@router.get("/leaderboard/activity", response_model=LeaderboardResponse)
async def get_activity_leaderboard(limit: int = 10) -> LeaderboardResponse:
    """Get agents ranked by action count."""
    if _world_state is None:
        raise HTTPException(status_code=503, detail="State not initialized")

    agents = list(_world_state.agents.values())
    sorted_agents = sorted(agents, key=lambda a: a.action_count, reverse=True)[:limit]

    entries = [
        LeaderboardEntry(agent_id=a.agent_id, value=float(a.action_count), rank=i + 1)
        for i, a in enumerate(sorted_agents)
    ]

    return LeaderboardResponse(category="activity", entries=entries)


@router.get("/leaderboard/efficiency", response_model=LeaderboardResponse)
async def get_efficiency_leaderboard(limit: int = 10) -> LeaderboardResponse:
    """Get agents ranked by success rate."""
    if _world_state is None:
        raise HTTPException(status_code=503, detail="State not initialized")

    agents = list(_world_state.agents.values())

    def get_success_rate(a: Any) -> float:
        if a.action_count == 0:
            return 0.0
        return a.action_successes / a.action_count

    sorted_agents = sorted(agents, key=get_success_rate, reverse=True)[:limit]

    entries = [
        LeaderboardEntry(agent_id=a.agent_id, value=get_success_rate(a), rank=i + 1)
        for i, a in enumerate(sorted_agents)
    ]

    return LeaderboardResponse(category="efficiency", entries=entries)


@router.get("/kpis")
async def get_kpis() -> dict[str, Any]:
    """Get key performance indicators."""
    if _world_state is None or _metrics_engine is None:
        raise HTTPException(status_code=503, detail="State not initialized")

    global_metrics = _metrics_engine.compute_global_metrics(_world_state)
    resource_summary = _metrics_engine.compute_resource_utilization_summary(_world_state)

    return {
        "simulation": {
            "elapsed_time": global_metrics.elapsed_time,
            "events_processed": global_metrics.events_processed,
            "current_sequence": global_metrics.current_sequence,
        },
        "economy": {
            "total_scrip": global_metrics.total_scrip_circulation,
            "total_transactions": global_metrics.total_transactions,
        },
        "agents": {
            "active_count": global_metrics.active_agent_count,
            "total_actions": global_metrics.total_actions,
            "actions_per_second": global_metrics.actions_per_second,
        },
        "artifacts": {
            "total": global_metrics.total_artifacts,
            "executable": global_metrics.executable_artifacts,
            "total_invocations": global_metrics.total_invocations,
        },
        "resources": resource_summary,
    }
