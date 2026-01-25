"""Agent-related API endpoints."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from ...models_v2.state import AgentStateResponse, WorldState
from ...models_v2.metrics import AgentMetricsResponse
from ...core_v2.metrics_engine import MetricsEngine

router = APIRouter()

# These will be injected by the server
_world_state: WorldState | None = None
_metrics_engine: MetricsEngine | None = None


def set_dependencies(world_state: WorldState, metrics_engine: MetricsEngine) -> None:
    """Set dependencies for route handlers."""
    global _world_state, _metrics_engine
    _world_state = world_state
    _metrics_engine = metrics_engine


class AgentListResponse(BaseModel):
    """Response for agent list endpoint."""

    agents: list[AgentStateResponse]
    total: int


class AgentDetailResponse(BaseModel):
    """Response for agent detail endpoint."""

    agent: AgentStateResponse
    metrics: AgentMetricsResponse | None = None
    action_history: list[dict[str, Any]] = []
    thinking_history: list[dict[str, Any]] = []


@router.get("", response_model=AgentListResponse)
async def list_agents() -> AgentListResponse:
    """List all agents with summary state."""
    if _world_state is None:
        raise HTTPException(status_code=503, detail="State not initialized")

    agents = [
        AgentStateResponse.from_state(state)
        for state in _world_state.agents.values()
    ]

    return AgentListResponse(agents=agents, total=len(agents))


@router.get("/{agent_id}", response_model=AgentDetailResponse)
async def get_agent(agent_id: str) -> AgentDetailResponse:
    """Get detailed agent state and metrics."""
    if _world_state is None:
        raise HTTPException(status_code=503, detail="State not initialized")

    agent_state = _world_state.get_agent(agent_id)
    if agent_state is None:
        raise HTTPException(status_code=404, detail=f"Agent not found: {agent_id}")

    # Get metrics if engine available
    metrics = None
    if _metrics_engine is not None:
        agent_metrics = _metrics_engine.compute_agent_metrics(_world_state, agent_id)
        if agent_metrics:
            metrics = AgentMetricsResponse.from_metrics(agent_metrics)

    return AgentDetailResponse(
        agent=AgentStateResponse.from_state(agent_state),
        metrics=metrics,
        action_history=agent_state.action_history[-50:],  # Last 50
        thinking_history=agent_state.thinking_history[-20:],  # Last 20
    )


@router.get("/{agent_id}/actions")
async def get_agent_actions(
    agent_id: str, limit: int = 50, offset: int = 0
) -> dict[str, Any]:
    """Get agent action history with pagination."""
    if _world_state is None:
        raise HTTPException(status_code=503, detail="State not initialized")

    agent_state = _world_state.get_agent(agent_id)
    if agent_state is None:
        raise HTTPException(status_code=404, detail=f"Agent not found: {agent_id}")

    history = agent_state.action_history
    total = len(history)
    actions = history[offset : offset + limit]

    return {
        "agent_id": agent_id,
        "actions": actions,
        "total": total,
        "offset": offset,
        "limit": limit,
    }


@router.get("/{agent_id}/thinking")
async def get_agent_thinking(
    agent_id: str, limit: int = 20, offset: int = 0
) -> dict[str, Any]:
    """Get agent thinking history with pagination."""
    if _world_state is None:
        raise HTTPException(status_code=503, detail="State not initialized")

    agent_state = _world_state.get_agent(agent_id)
    if agent_state is None:
        raise HTTPException(status_code=404, detail=f"Agent not found: {agent_id}")

    history = agent_state.thinking_history
    total = len(history)
    thinking = history[offset : offset + limit]

    return {
        "agent_id": agent_id,
        "thinking": thinking,
        "total": total,
        "offset": offset,
        "limit": limit,
    }
