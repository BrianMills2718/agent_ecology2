"""Dashboard API layer.

Routes are organized by entity type:
- routes/agents.py: Agent-related endpoints
- routes/artifacts.py: Artifact-related endpoints
- routes/metrics.py: Metrics and KPI endpoints
- routes/search.py: Search functionality

websocket.py: WebSocket handling for real-time updates
"""

from fastapi import APIRouter

from .routes import agents, artifacts, metrics, search
from .websocket import websocket_endpoint

# Create main API router
api_router = APIRouter()

# Include sub-routers
api_router.include_router(agents.router, prefix="/agents", tags=["agents"])
api_router.include_router(artifacts.router, prefix="/artifacts", tags=["artifacts"])
api_router.include_router(metrics.router, prefix="/metrics", tags=["metrics"])
api_router.include_router(search.router, prefix="/search", tags=["search"])

__all__ = [
    "api_router",
    "websocket_endpoint",
]
