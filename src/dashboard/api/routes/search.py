"""Search API endpoints."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel

from ...models_v2.state import AgentStateResponse, ArtifactStateResponse, WorldState

router = APIRouter()

# Injected by server
_world_state: WorldState | None = None


def set_dependencies(world_state: WorldState) -> None:
    """Set dependencies for route handlers."""
    global _world_state
    _world_state = world_state


class SearchResult(BaseModel):
    """A single search result."""

    entity_type: str  # "agent" or "artifact"
    entity_id: str
    match_type: str  # "exact", "prefix", "contains"
    score: float  # Relevance score (higher is better)


class SearchResponse(BaseModel):
    """Response for search endpoint."""

    query: str
    results: list[SearchResult]
    agents: list[AgentStateResponse]
    artifacts: list[ArtifactStateResponse]
    total: int


@router.get("", response_model=SearchResponse)
async def search(
    q: str = Query(..., min_length=1, description="Search query"),
    limit: int = Query(20, ge=1, le=100, description="Max results"),
) -> SearchResponse:
    """Search for agents and artifacts by ID.

    Matches:
    - Exact ID matches (highest score)
    - Prefix matches (medium score)
    - Contains matches (lower score)
    """
    if _world_state is None:
        raise HTTPException(status_code=503, detail="State not initialized")

    query = q.lower()
    results: list[SearchResult] = []
    matched_agents: list[AgentStateResponse] = []
    matched_artifacts: list[ArtifactStateResponse] = []

    # Search agents
    for agent_id, agent_state in _world_state.agents.items():
        agent_id_lower = agent_id.lower()
        match_type = None
        score = 0.0

        if agent_id_lower == query:
            match_type = "exact"
            score = 1.0
        elif agent_id_lower.startswith(query):
            match_type = "prefix"
            score = 0.8
        elif query in agent_id_lower:
            match_type = "contains"
            score = 0.5

        if match_type:
            results.append(
                SearchResult(
                    entity_type="agent",
                    entity_id=agent_id,
                    match_type=match_type,
                    score=score,
                )
            )
            matched_agents.append(AgentStateResponse.from_state(agent_state))

    # Search artifacts
    for artifact_id, artifact_state in _world_state.artifacts.items():
        artifact_id_lower = artifact_id.lower()
        match_type = None
        score = 0.0

        if artifact_id_lower == query:
            match_type = "exact"
            score = 1.0
        elif artifact_id_lower.startswith(query):
            match_type = "prefix"
            score = 0.8
        elif query in artifact_id_lower:
            match_type = "contains"
            score = 0.5

        if match_type:
            results.append(
                SearchResult(
                    entity_type="artifact",
                    entity_id=artifact_id,
                    match_type=match_type,
                    score=score,
                )
            )
            matched_artifacts.append(ArtifactStateResponse.from_state(artifact_state))

    # Sort by score (descending), then by ID
    results.sort(key=lambda r: (-r.score, r.entity_id))

    # Apply limit
    results = results[:limit]
    matched_agents = matched_agents[:limit]
    matched_artifacts = matched_artifacts[:limit]

    return SearchResponse(
        query=q,
        results=results,
        agents=matched_agents,
        artifacts=matched_artifacts,
        total=len(results),
    )


@router.get("/agents")
async def search_agents(
    q: str = Query(..., min_length=1),
    limit: int = Query(20, ge=1, le=100),
) -> dict[str, Any]:
    """Search agents only."""
    if _world_state is None:
        raise HTTPException(status_code=503, detail="State not initialized")

    query = q.lower()
    matches = []

    for agent_id, agent_state in _world_state.agents.items():
        if query in agent_id.lower():
            matches.append(AgentStateResponse.from_state(agent_state))

    return {
        "query": q,
        "agents": matches[:limit],
        "total": len(matches),
    }


@router.get("/artifacts")
async def search_artifacts(
    q: str = Query(..., min_length=1),
    limit: int = Query(20, ge=1, le=100),
) -> dict[str, Any]:
    """Search artifacts only."""
    if _world_state is None:
        raise HTTPException(status_code=503, detail="State not initialized")

    query = q.lower()
    matches = []

    for artifact_id, artifact_state in _world_state.artifacts.items():
        if query in artifact_id.lower():
            matches.append(ArtifactStateResponse.from_state(artifact_state))

    return {
        "query": q,
        "artifacts": matches[:limit],
        "total": len(matches),
    }
