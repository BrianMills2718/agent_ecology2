"""FastAPI server for the agent ecology dashboard."""

from __future__ import annotations

import asyncio
import json
from pathlib import Path
from typing import Any

from contextlib import asynccontextmanager
from typing import AsyncGenerator

from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Query, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse
from fastapi.middleware.cors import CORSMiddleware

from .parser import JSONLParser
from .kpis import calculate_kpis, EcosystemKPIs
from .auditor import assess_health, AuditorThresholds, HealthReport

# Import simulation runner for control (may not be available)
try:
    from simulation import SimulationRunner
    HAS_SIMULATION = True
except ImportError:
    HAS_SIMULATION = False
    SimulationRunner = None
from .watcher import PollingWatcher
from .models import (
    SimulationState as SimulationStateModel,
    AgentSummary,
    AgentDetail,
    ArtifactInfo,
    RawEvent,
    SimulationProgress,
    GenesisActivitySummary,
    ResourceChartData,
    EconomicFlowData,
    ConfigInfo,
    EventFilter,
    EcosystemKPIsResponse,
)

# Default paths
DEFAULT_JSONL_PATH = "run.jsonl"
DEFAULT_STATIC_DIR = Path(__file__).parent / "static"
DEFAULT_CONFIG_PATH = "config/config.yaml"


class ConnectionManager:
    """Manages WebSocket connections for real-time updates."""

    def __init__(self) -> None:
        self.active_connections: list[WebSocket] = []

    async def connect(self, websocket: WebSocket) -> None:
        """Accept and store a new WebSocket connection."""
        await websocket.accept()
        self.active_connections.append(websocket)

    def disconnect(self, websocket: WebSocket) -> None:
        """Remove a WebSocket connection."""
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)

    async def broadcast(self, message: dict[str, Any]) -> None:
        """Broadcast a message to all connected clients."""
        disconnected: list[WebSocket] = []
        for connection in self.active_connections:
            try:
                await connection.send_json(message)
            except Exception:
                disconnected.append(connection)

        # Clean up disconnected clients
        for conn in disconnected:
            self.disconnect(conn)

    @property
    def connection_count(self) -> int:
        """Get the number of active connections."""
        return len(self.active_connections)


class DashboardApp:
    """Dashboard application state and configuration."""

    def __init__(
        self,
        jsonl_path: str | Path = DEFAULT_JSONL_PATH,
        static_dir: str | Path = DEFAULT_STATIC_DIR,
        config_path: str | Path = DEFAULT_CONFIG_PATH,
    ) -> None:
        self.jsonl_path = Path(jsonl_path)
        self.static_dir = Path(static_dir)
        self.config_path = Path(config_path)

        self.parser = JSONLParser(self.jsonl_path)
        self.watcher = PollingWatcher(self.jsonl_path, poll_interval=0.5)
        self.connection_manager = ConnectionManager()

        # Initial parse
        if self.jsonl_path.exists():
            self.parser.parse_full()

    async def on_file_change(self) -> None:
        """Handle file change events."""
        new_events = self.parser.get_new_events()
        if new_events:
            # Broadcast new events to all connected clients
            for event in new_events:
                await self.connection_manager.broadcast({
                    "type": "event",
                    "data": event.model_dump(),
                })

            # Also broadcast updated state summary
            await self.connection_manager.broadcast({
                "type": "state_update",
                "data": {
                    "progress": self.parser.get_progress().model_dump(),
                    "agent_count": len(self.parser.state.agents),
                    "artifact_count": len(self.parser.state.artifacts),
                },
            })

    async def start(self) -> None:
        """Start the file watcher."""
        self.watcher.add_callback(self.on_file_change)
        await self.watcher.start()

    def stop(self) -> None:
        """Stop the file watcher."""
        self.watcher.stop()

    def get_config(self) -> dict[str, Any]:
        """Load and return config file."""
        if not self.config_path.exists():
            return {}
        try:
            import yaml
            with open(self.config_path) as f:
                return yaml.safe_load(f) or {}
        except Exception:
            return {}


def create_app(
    jsonl_path: str | Path = DEFAULT_JSONL_PATH,
    static_dir: str | Path = DEFAULT_STATIC_DIR,
    config_path: str | Path = DEFAULT_CONFIG_PATH,
) -> FastAPI:
    """Create and configure the FastAPI application."""

    app = FastAPI(
        title="Agent Ecology Dashboard",
        description="Real-time visibility into the agent ecology simulation",
        version="1.0.0",
    )

    # CORS middleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Dashboard app state
    dashboard = DashboardApp(jsonl_path, static_dir, config_path)

    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
        """Lifespan context manager for startup/shutdown."""
        await dashboard.start()
        yield
        dashboard.stop()

    # Attach lifespan to app
    app.router.lifespan_context = lifespan

    # Static files
    if dashboard.static_dir.exists():
        app.mount("/static", StaticFiles(directory=str(dashboard.static_dir)), name="static")

    # Routes

    @app.get("/", response_class=HTMLResponse, response_model=None)
    async def index() -> HTMLResponse:
        """Serve the main dashboard page."""
        index_path = dashboard.static_dir / "index.html"
        if index_path.exists():
            with open(index_path) as f:
                return HTMLResponse(content=f.read())
        return HTMLResponse("<h1>Dashboard static files not found</h1>")

    @app.get("/api/state")
    async def get_state() -> dict[str, Any]:
        """Get complete simulation state."""
        dashboard.parser.parse_incremental()
        return {
            "progress": dashboard.parser.get_progress().model_dump(),
            "agents": [a.model_dump() for a in dashboard.parser.get_all_agent_summaries()],
            "artifacts": [a.model_dump() for a in dashboard.parser.get_all_artifacts()],
            "genesis": dashboard.parser.get_genesis_activity().model_dump(),
            "recent_events": [
                e.model_dump() for e in dashboard.parser.state.all_events[-50:]
            ],
        }

    @app.get("/api/progress")
    async def get_progress() -> dict[str, Any]:
        """Get simulation progress only."""
        dashboard.parser.parse_incremental()
        return dashboard.parser.get_progress().model_dump()

    @app.get("/api/agents")
    async def get_agents() -> list[dict[str, Any]]:
        """Get all agent summaries."""
        dashboard.parser.parse_incremental()
        return [a.model_dump() for a in dashboard.parser.get_all_agent_summaries()]

    @app.get("/api/agents/{agent_id}")
    async def get_agent(agent_id: str) -> dict[str, Any]:
        """Get detailed info for a single agent."""
        dashboard.parser.parse_incremental()
        detail = dashboard.parser.get_agent_detail(agent_id)
        if detail:
            return detail.model_dump()
        return {"error": f"Agent {agent_id} not found"}

    @app.get("/api/artifacts")
    async def get_artifacts() -> list[dict[str, Any]]:
        """Get all artifacts."""
        dashboard.parser.parse_incremental()
        return [a.model_dump() for a in dashboard.parser.get_all_artifacts()]

    @app.get("/api/events")
    async def get_events(
        event_types: str | None = Query(None, description="Comma-separated event types"),
        agent_id: str | None = Query(None),
        artifact_id: str | None = Query(None),
        tick_min: int | None = Query(None),
        tick_max: int | None = Query(None),
        limit: int = Query(100, ge=1, le=1000),
        offset: int = Query(0, ge=0),
    ) -> list[dict[str, Any]]:
        """Get filtered events."""
        dashboard.parser.parse_incremental()

        types_list = event_types.split(",") if event_types else None
        events = dashboard.parser.filter_events(
            event_types=types_list,
            agent_id=agent_id,
            artifact_id=artifact_id,
            tick_min=tick_min,
            tick_max=tick_max,
            limit=limit,
            offset=offset,
        )
        return [e.model_dump() for e in events]

    @app.get("/api/genesis")
    async def get_genesis() -> dict[str, Any]:
        """Get genesis artifact activity summary."""
        dashboard.parser.parse_incremental()
        return dashboard.parser.get_genesis_activity().model_dump()

    @app.get("/api/charts/compute")
    async def get_compute_chart() -> dict[str, Any]:
        """Get compute utilization chart data."""
        dashboard.parser.parse_incremental()
        return dashboard.parser.get_compute_chart_data().model_dump()

    @app.get("/api/charts/scrip")
    async def get_scrip_chart() -> dict[str, Any]:
        """Get scrip balance chart data."""
        dashboard.parser.parse_incremental()
        return dashboard.parser.get_scrip_chart_data().model_dump()

    @app.get("/api/charts/flow")
    async def get_flow_chart() -> dict[str, Any]:
        """Get economic flow visualization data."""
        dashboard.parser.parse_incremental()
        return dashboard.parser.get_economic_flow_data().model_dump()

    @app.get("/api/kpis")
    async def get_kpis() -> dict[str, Any]:
        """Get ecosystem health KPIs.

        Returns computed metrics indicating overall ecosystem health,
        capital flow, and emergence patterns.
        """
        dashboard.parser.parse_incremental()
        kpis = calculate_kpis(dashboard.parser.state)

        # Convert dataclass to dict for response
        return {
            "total_scrip": kpis.total_scrip,
            "scrip_velocity": kpis.scrip_velocity,
            "gini_coefficient": kpis.gini_coefficient,
            "median_scrip": kpis.median_scrip,
            "active_agent_ratio": kpis.active_agent_ratio,
            "frozen_agent_count": kpis.frozen_agent_count,
            "actions_per_tick": kpis.actions_per_tick,
            "thinking_cost_rate": kpis.thinking_cost_rate,
            "escrow_volume": kpis.escrow_volume,
            "escrow_active_listings": kpis.escrow_active_listings,
            "mint_scrip_rate": kpis.mint_scrip_rate,
            "artifact_creation_rate": kpis.artifact_creation_rate,
            "llm_budget_remaining": kpis.llm_budget_remaining,
            "llm_budget_burn_rate": kpis.llm_budget_burn_rate,
            "agent_spawn_rate": kpis.agent_spawn_rate,
            "coordination_events": kpis.coordination_events,
            "artifact_diversity": kpis.artifact_diversity,
            "scrip_velocity_trend": kpis.scrip_velocity_trend,
            "activity_trend": kpis.activity_trend,
        }

    # Store previous KPIs for trend calculation
    _prev_kpis: EcosystemKPIs | None = None

    @app.get("/api/health")
    async def get_health() -> dict[str, Any]:
        """Get ecosystem health report.

        Returns health assessment based on KPIs with threshold-based
        status (healthy/warning/critical), concerns, and trends.
        """
        nonlocal _prev_kpis

        dashboard.parser.parse_incremental()
        kpis = calculate_kpis(dashboard.parser.state)

        # Get default thresholds (could be made configurable via config.yaml)
        thresholds = AuditorThresholds()

        # Count total agents for ratio calculations
        total_agents = len(dashboard.parser.state.agents)

        report = assess_health(kpis, _prev_kpis, thresholds, total_agents=max(1, total_agents))

        # Update previous KPIs for next trend calculation
        _prev_kpis = kpis

        return {
            "timestamp": report.timestamp,
            "overall_status": report.overall_status,
            "health_score": report.health_score,
            "trend": report.trend,
            "concerns": [
                {
                    "metric": c.metric,
                    "value": c.value,
                    "threshold": c.threshold,
                    "severity": c.severity,
                    "message": c.message,
                }
                for c in report.concerns
            ],
            "kpis": {
                "total_scrip": kpis.total_scrip,
                "gini_coefficient": kpis.gini_coefficient,
                "active_agent_ratio": kpis.active_agent_ratio,
                "frozen_agent_count": kpis.frozen_agent_count,
                "llm_budget_burn_rate": kpis.llm_budget_burn_rate,
                "scrip_velocity": kpis.scrip_velocity,
            },
        }

    @app.get("/api/config")
    async def get_config() -> dict[str, Any]:
        """Get simulation configuration."""
        config = dashboard.get_config()
        return {
            "resources": config.get("resources", {}),
            "costs": config.get("costs", {}),
            "genesis": config.get("genesis", {}),
            "world": config.get("world", {}),
            "budget": config.get("budget", {}),
        }

    @app.get("/api/ticks")
    async def get_tick_summaries() -> list[dict[str, Any]]:
        """Get tick summary history."""
        dashboard.parser.parse_incremental()
        return [t.model_dump() for t in dashboard.parser.state.tick_summaries]

    @app.get("/api/network")
    async def get_network_graph(
        tick_max: int | None = Query(None, description="Max tick to include"),
    ) -> dict[str, Any]:
        """Get network graph data for agent interactions."""
        dashboard.parser.parse_incremental()
        return dashboard.parser.get_network_graph_data(tick_max).model_dump()

    @app.get("/api/activity")
    async def get_activity_feed(
        limit: int = Query(100, ge=1, le=500),
        offset: int = Query(0, ge=0),
        types: str | None = Query(None, description="Comma-separated activity types"),
        agent_id: str | None = Query(None),
    ) -> dict[str, Any]:
        """Get activity feed with filtering."""
        dashboard.parser.parse_incremental()
        types_list = types.split(",") if types else None
        return dashboard.parser.get_activity_feed(
            limit=limit,
            offset=offset,
            activity_types=types_list,
            agent_id=agent_id,
        ).model_dump()

    @app.get("/api/artifacts/{artifact_id}/detail")
    async def get_artifact_detail(artifact_id: str) -> dict[str, Any]:
        """Get detailed info for a single artifact including content."""
        dashboard.parser.parse_incremental()
        detail = dashboard.parser.get_artifact_detail(artifact_id)
        if detail:
            return detail.model_dump()
        return {"error": f"Artifact {artifact_id} not found"}

    @app.get("/api/thinking")
    async def get_thinking_history(
        agent_id: str | None = Query(None, description="Filter by agent ID"),
        tick_min: int | None = Query(None, description="Minimum tick"),
        tick_max: int | None = Query(None, description="Maximum tick"),
        limit: int = Query(100, ge=1, le=500),
    ) -> dict[str, Any]:
        """Get agent thinking history with reasoning content."""
        dashboard.parser.parse_incremental()

        all_thinking: list[dict[str, Any]] = []
        for agent_state in dashboard.parser.state.agents.values():
            for thinking in agent_state.thinking_history:
                if agent_id and thinking.agent_id != agent_id:
                    continue
                if tick_min is not None and thinking.tick < tick_min:
                    continue
                if tick_max is not None and thinking.tick > tick_max:
                    continue
                all_thinking.append(thinking.model_dump())

        # Sort by tick descending
        all_thinking.sort(key=lambda x: (x["tick"], x["timestamp"]), reverse=True)

        return {
            "items": all_thinking[:limit],
            "total_count": len(all_thinking),
        }

    @app.get("/api/simulation/status")
    async def get_simulation_status() -> dict[str, Any]:
        """Get simulation runner status."""
        if not HAS_SIMULATION or SimulationRunner is None:
            return {"available": False, "reason": "Simulation module not loaded"}

        runner = SimulationRunner.get_active()
        if runner is None:
            return {"available": True, "running": False, "reason": "No active simulation"}

        return {
            "available": True,
            **runner.get_status()
        }

    @app.post("/api/simulation/pause")
    async def pause_simulation() -> dict[str, Any]:
        """Pause the running simulation."""
        if not HAS_SIMULATION or SimulationRunner is None:
            raise HTTPException(status_code=503, detail="Simulation module not available")

        runner = SimulationRunner.get_active()
        if runner is None:
            raise HTTPException(status_code=404, detail="No active simulation")

        if runner.is_paused:
            return {"status": "already_paused", "tick": runner.world.tick}

        runner.pause()

        # Broadcast pause to all clients
        await dashboard.connection_manager.broadcast({
            "type": "simulation_control",
            "data": {"action": "paused", "tick": runner.world.tick}
        })

        return {"status": "paused", "tick": runner.world.tick}

    @app.post("/api/simulation/resume")
    async def resume_simulation() -> dict[str, Any]:
        """Resume a paused simulation."""
        if not HAS_SIMULATION or SimulationRunner is None:
            raise HTTPException(status_code=503, detail="Simulation module not available")

        runner = SimulationRunner.get_active()
        if runner is None:
            raise HTTPException(status_code=404, detail="No active simulation")

        if not runner.is_paused:
            return {"status": "already_running", "tick": runner.world.tick}

        runner.resume()

        # Broadcast resume to all clients
        await dashboard.connection_manager.broadcast({
            "type": "simulation_control",
            "data": {"action": "resumed", "tick": runner.world.tick}
        })

        return {"status": "running", "tick": runner.world.tick}

    @app.websocket("/ws")
    async def websocket_endpoint(websocket: WebSocket) -> None:
        """WebSocket endpoint for real-time updates."""
        await dashboard.connection_manager.connect(websocket)

        # Send initial state
        dashboard.parser.parse_incremental()
        try:
            await websocket.send_json({
                "type": "initial_state",
                "data": {
                    "progress": dashboard.parser.get_progress().model_dump(),
                    "agents": [a.model_dump() for a in dashboard.parser.get_all_agent_summaries()],
                    "artifacts": [a.model_dump() for a in dashboard.parser.get_all_artifacts()],
                },
            })

            # Keep connection alive and wait for messages
            while True:
                try:
                    data = await asyncio.wait_for(
                        websocket.receive_text(),
                        timeout=30.0
                    )
                    # Handle ping/pong for keepalive
                    if data == "ping":
                        await websocket.send_text("pong")
                except asyncio.TimeoutError:
                    # Send keepalive ping
                    await websocket.send_text("ping")

        except WebSocketDisconnect:
            pass
        finally:
            dashboard.connection_manager.disconnect(websocket)

    return app


def run_dashboard(
    host: str = "0.0.0.0",
    port: int = 8080,
    jsonl_path: str = DEFAULT_JSONL_PATH,
    reload: bool = False,
) -> None:
    """Run the dashboard server."""
    import uvicorn

    app = create_app(jsonl_path=jsonl_path)
    uvicorn.run(
        app,
        host=host,
        port=port,
        reload=reload,
    )


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Agent Ecology Dashboard Server")
    parser.add_argument("--host", default="0.0.0.0", help="Host to bind to")
    parser.add_argument("--port", type=int, default=8080, help="Port to bind to")
    parser.add_argument("--jsonl", default=DEFAULT_JSONL_PATH, help="Path to JSONL event log")
    parser.add_argument("--reload", action="store_true", help="Enable auto-reload")

    args = parser.parse_args()

    run_dashboard(
        host=args.host,
        port=args.port,
        jsonl_path=args.jsonl,
        reload=args.reload,
    )
