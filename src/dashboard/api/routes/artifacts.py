"""Artifact-related API endpoints."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from ...models_v2.state import ArtifactStateResponse, WorldState

router = APIRouter()

# Injected by server
_world_state: WorldState | None = None


def set_dependencies(world_state: WorldState) -> None:
    """Set dependencies for route handlers."""
    global _world_state
    _world_state = world_state


class ArtifactListResponse(BaseModel):
    """Response for artifact list endpoint."""

    artifacts: list[ArtifactStateResponse]
    total: int


class ArtifactDetailResponse(BaseModel):
    """Response for artifact detail endpoint."""

    artifact: ArtifactStateResponse
    content: str | None = None
    invocation_history: list[dict[str, Any]] = []
    ownership_history: list[dict[str, Any]] = []


@router.get("", response_model=ArtifactListResponse)
async def list_artifacts(
    artifact_type: str | None = None,
    owner: str | None = None,
    executable: bool | None = None,
) -> ArtifactListResponse:
    """List artifacts with optional filtering."""
    if _world_state is None:
        raise HTTPException(status_code=503, detail="State not initialized")

    artifacts = []
    for state in _world_state.artifacts.values():
        # Apply filters
        if artifact_type and state.artifact_type != artifact_type:
            continue
        if owner and state.owner != owner:
            continue
        if executable is not None and state.executable != executable:
            continue

        artifacts.append(ArtifactStateResponse.from_state(state))

    return ArtifactListResponse(artifacts=artifacts, total=len(artifacts))


@router.get("/{artifact_id}", response_model=ArtifactDetailResponse)
async def get_artifact(artifact_id: str) -> ArtifactDetailResponse:
    """Get detailed artifact state."""
    if _world_state is None:
        raise HTTPException(status_code=503, detail="State not initialized")

    artifact_state = _world_state.get_artifact(artifact_id)
    if artifact_state is None:
        raise HTTPException(
            status_code=404, detail=f"Artifact not found: {artifact_id}"
        )

    # Convert ownership history to dicts
    ownership_history = [
        {
            "from_id": record.from_id,
            "to_id": record.to_id,
            "timestamp": record.timestamp,
            "sequence": record.sequence,
        }
        for record in artifact_state.ownership_history
    ]

    return ArtifactDetailResponse(
        artifact=ArtifactStateResponse.from_state(artifact_state),
        content=artifact_state.content,
        invocation_history=artifact_state.invocation_history[-50:],
        ownership_history=ownership_history[-20:],
    )


@router.get("/{artifact_id}/invocations")
async def get_artifact_invocations(
    artifact_id: str, limit: int = 50, offset: int = 0
) -> dict[str, Any]:
    """Get artifact invocation history with pagination."""
    if _world_state is None:
        raise HTTPException(status_code=503, detail="State not initialized")

    artifact_state = _world_state.get_artifact(artifact_id)
    if artifact_state is None:
        raise HTTPException(
            status_code=404, detail=f"Artifact not found: {artifact_id}"
        )

    history = artifact_state.invocation_history
    total = len(history)
    invocations = history[offset : offset + limit]

    return {
        "artifact_id": artifact_id,
        "invocations": invocations,
        "total": total,
        "offset": offset,
        "limit": limit,
    }


@router.get("/by-owner/{owner_id}")
async def get_artifacts_by_owner(owner_id: str) -> ArtifactListResponse:
    """Get all artifacts owned by a specific principal."""
    if _world_state is None:
        raise HTTPException(status_code=503, detail="State not initialized")

    artifacts = [
        ArtifactStateResponse.from_state(state)
        for state in _world_state.artifacts.values()
        if state.owner == owner_id
    ]

    return ArtifactListResponse(artifacts=artifacts, total=len(artifacts))
