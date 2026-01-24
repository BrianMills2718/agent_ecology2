"""FastAPI server for the agent ecology dashboard.

Plan #125: Routes are organized into helper registration functions for maintainability.
"""

from __future__ import annotations
from dataclasses import asdict

import asyncio
import json
from pathlib import Path
from typing import Any, TYPE_CHECKING

from contextlib import asynccontextmanager
from typing import AsyncGenerator

from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Query, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse
from fastapi.middleware.cors import CORSMiddleware

from .parser import JSONLParser
from .kpis import calculate_kpis, EcosystemKPIs, compute_agent_metrics, AgentMetrics, calculate_emergence_metrics
from .auditor import assess_health, AuditorThresholds, HealthReport
from .dependency_graph import build_dependency_graph
from ..config import get_validated_config

if TYPE_CHECKING:
    from .watcher import PollingWatcher

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
    InvocationEvent,
    InvocationStatsResponse,
    DependencyGraphData,
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
        live_mode: bool = False,
    ) -> None:
        """Initialize dashboard app.

        Args:
            jsonl_path: Path to the JSONL event log file
            static_dir: Path to static assets directory
            config_path: Path to config file
            live_mode: If True, start with empty state and only show new events
                      (for new simulations). If False, parse existing logs first
                      (for --dashboard-only or resuming).
        """
        self.jsonl_path = Path(jsonl_path)
        self.static_dir = Path(static_dir)
        self.config_path = Path(config_path)
        self.live_mode = live_mode

        self.parser = JSONLParser(self.jsonl_path)
        # Plan #133: Use polling watcher for WSL compatibility
        # Watchdog-based file watching is unreliable on WSL2
        self.watcher = PollingWatcher(self.jsonl_path)
        self.connection_manager = ConnectionManager()

        # Plan #125: Moved from create_app() nonlocal for cleaner state management
        self.prev_kpis: EcosystemKPIs | None = None

        # Only parse existing logs if not in live mode (viewing old runs)
        if not live_mode and self.jsonl_path.exists():
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



            # Broadcast KPI update (Plan #142)
            kpis = calculate_kpis(self.parser.state)
            emergence = calculate_emergence_metrics(self.parser.state)
            health = assess_health(self.parser.state, self.thresholds)
            await self.connection_manager.broadcast({
                "type": "kpi_update",
                "data": {
                    "kpis": asdict(kpis),
                    "emergence": asdict(emergence),
                    "health": asdict(health),
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


# Plan #125: Helper functions to organize route registration


def _register_simulation_routes(app: FastAPI, dashboard: DashboardApp) -> None:
    """Register simulation control routes.

    Plan #125: Extracted from create_app() for clarity.
    Handles /api/simulation/* endpoints for pause/resume control.
    """

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


def _register_websocket_routes(app: FastAPI, dashboard: DashboardApp) -> None:
    """Register WebSocket endpoint.

    Plan #125: Extracted from create_app() for clarity.
    Handles real-time streaming updates to dashboard clients.
    """

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
            dashboard_timeout = get_validated_config().timeouts.dashboard_server
            while True:
                try:
                    data = await asyncio.wait_for(
                        websocket.receive_text(),
                        timeout=dashboard_timeout
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


def create_app(
    jsonl_path: str | Path = DEFAULT_JSONL_PATH,
    static_dir: str | Path = DEFAULT_STATIC_DIR,
    config_path: str | Path = DEFAULT_CONFIG_PATH,
    live_mode: bool = False,
) -> FastAPI:
    """Create and configure the FastAPI application.

    Args:
        jsonl_path: Path to the JSONL event log file
        static_dir: Path to static assets directory
        config_path: Path to config file
        live_mode: If True, start with empty state for new simulations.
                  If False, parse existing logs (for --dashboard-only).
    """

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
    dashboard = DashboardApp(jsonl_path, static_dir, config_path, live_mode=live_mode)

    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
        """Lifespan context manager for startup/shutdown."""
        await dashboard.start()
        yield
        dashboard.stop()

    # Attach lifespan to app
    app.router.lifespan_context = lifespan

    # Static files - v1 (vanilla JS)
    if dashboard.static_dir.exists():
        app.mount("/static", StaticFiles(directory=str(dashboard.static_dir)), name="static")

    # Static files - v2 (React) if directory exists
    static_v2_dir = dashboard.static_dir.parent / "static-v2"
    if static_v2_dir.exists():
        app.mount("/static-v2", StaticFiles(directory=str(static_v2_dir)), name="static-v2")

    # Routes

    @app.get("/", response_class=HTMLResponse, response_model=None)
    async def index() -> HTMLResponse:
        """Serve the main dashboard page based on config version."""
        config = get_validated_config()
        version = getattr(config.dashboard, 'version', 'v1')

        if version == 'v2':
            # Serve React dashboard
            index_path = static_v2_dir / "index.html"
            if index_path.exists():
                with open(index_path) as f:
                    return HTMLResponse(content=f.read())
            return HTMLResponse("<h1>Dashboard v2 not built. Run: cd dashboard-v2 && npm run build</h1>")

        # Default: serve v1 (vanilla JS)
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
    async def get_agents(
        limit: int = Query(25, ge=1, le=100),
        offset: int = Query(0, ge=0),
    ) -> dict[str, Any]:
        """Get agent summaries with pagination (Plan #142)."""
        dashboard.parser.parse_incremental()
        all_agents = dashboard.parser.get_all_agent_summaries()
        total = len(all_agents)
        paginated = all_agents[offset:offset + limit]
        return {
            "agents": [a.model_dump() for a in paginated],
            "total": total,
            "limit": limit,
            "offset": offset,
        }

    @app.get("/api/agents/{agent_id}")
    async def get_agent(agent_id: str) -> dict[str, Any]:
        """Get detailed info for a single agent."""
        dashboard.parser.parse_incremental()
        detail = dashboard.parser.get_agent_detail(agent_id)
        if detail:
            return detail.model_dump()
        return {"error": f"Agent {agent_id} not found"}

    @app.get("/api/agents/{agent_id}/metrics")
    async def get_agent_metrics(agent_id: str) -> dict[str, Any]:
        """Get computed metrics for a single agent (Plan #76).

        Returns per-agent metrics including:
        - total_actions: Total actions taken
        - success_rate: Ratio of successful actions
        - ticks_since_action: Dormancy indicator
        - is_frozen: Whether agent exhausted LLM tokens
        - scrip_balance: Current scrip balance
        """
        dashboard.parser.parse_incremental()
        metrics = compute_agent_metrics(dashboard.parser.state, agent_id)
        if metrics is None:
            return {"error": f"Agent {agent_id} not found"}
        return {
            "agent_id": agent_id,
            "total_actions": metrics.total_actions,
            "last_action_tick": metrics.last_action_tick,
            "ticks_since_action": metrics.ticks_since_action,
            "is_frozen": metrics.is_frozen,
            "scrip_balance": metrics.scrip_balance,
            "success_rate": metrics.success_rate,
        }


    @app.get("/api/agents/{agent_id}/config")
    async def get_agent_config(agent_id: str) -> dict[str, Any]:
        """Get agent configuration from YAML file (Plan #108).

        Returns the full agent configuration for display in the dashboard,
        including genotype traits, RAG settings, workflow, and state machine.
        """
        import yaml
        from pathlib import Path

        # Find agent config file
        agents_dir = Path(__file__).parent.parent / "agents"
        config_path = agents_dir / agent_id / "agent.yaml"

        if not config_path.exists():
            return {
                "agent_id": agent_id,
                "config_found": False,
                "error": f"Config file not found for agent {agent_id}",
            }


        try:
            with open(config_path) as f:
                config = yaml.safe_load(f)

            # Build response with all config fields
            return {
                "agent_id": config.get("id", agent_id),
                "llm_model": config.get("llm_model"),
                "starting_credits": config.get("starting_credits", 100),
                "enabled": config.get("enabled", True),
                "temperature": config.get("temperature"),
                "max_tokens": config.get("max_tokens"),
                "genotype": config.get("genotype"),
                "rag": config.get("rag"),
                "workflow": config.get("workflow"),
                "error_handling": config.get("error_handling"),
                "config_found": True,
            }

        except Exception as e:
            return {
                "agent_id": agent_id,
                "config_found": False,
                "error": f"Failed to load config: {str(e)}",
            }


    @app.get("/api/artifacts")
    async def get_artifacts(
        limit: int = Query(25, ge=1, le=100),
        offset: int = Query(0, ge=0),
        search: str | None = Query(None, description="Search by artifact ID"),
    ) -> dict[str, Any]:
        """Get artifacts with pagination and search (Plan #142)."""
        dashboard.parser.parse_incremental()
        all_artifacts = dashboard.parser.get_all_artifacts()
        
        # Apply search filter if provided
        if search:
            all_artifacts = [a for a in all_artifacts if search.lower() in a.artifact_id.lower()]
        
        total = len(all_artifacts)
        paginated = all_artifacts[offset:offset + limit]
        return {
            "artifacts": [a.model_dump() for a in paginated],
            "total": total,
            "limit": limit,
            "offset": offset,
        }

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

    @app.get("/api/charts/llm_tokens")
    async def get_llm_tokens_chart() -> dict[str, Any]:
        """Get LLM token utilization chart data."""
        dashboard.parser.parse_incremental()
        return dashboard.parser.get_llm_tokens_chart_data().model_dump()

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
            "actions_per_second": kpis.actions_per_second,
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
            "gini_coefficient_trend": kpis.gini_coefficient_trend,
            "active_agent_ratio_trend": kpis.active_agent_ratio_trend,
            "frozen_count_trend": kpis.frozen_count_trend,
        }


    @app.get("/api/emergence")
    async def get_emergence_metrics() -> dict[str, Any]:
        """Get emergence observability metrics (Plan #110 Phase 3).

        Returns computed metrics for detecting emergent organization patterns:
        - coordination_density: How connected the agent network is
        - specialization_index: How differentiated agents are
        - reuse_ratio: How much agents use each other's artifacts
        - genesis_independence: Ecosystem maturity (non-genesis ops ratio)
        - capital_depth: Max dependency chain length
        - coalition_count: Number of distinct agent clusters
        """
        dashboard.parser.parse_incremental()
        metrics = calculate_emergence_metrics(dashboard.parser.state)
        return metrics.model_dump()

    @app.get("/api/health")
    async def get_health() -> dict[str, Any]:
        """Get ecosystem health report.

        Returns health assessment based on KPIs with threshold-based
        status (healthy/warning/critical), concerns, and trends.
        """
        dashboard.parser.parse_incremental()
        kpis = calculate_kpis(dashboard.parser.state)

        # Get default thresholds (could be made configurable via config.yaml)
        thresholds = AuditorThresholds()

        # Count total agents for ratio calculations
        total_agents = len(dashboard.parser.state.agents)

        # Plan #125: prev_kpis now stored on DashboardApp instance
        report = assess_health(kpis, dashboard.prev_kpis, thresholds, total_agents=max(1, total_agents))

        # Update previous KPIs for next trend calculation
        dashboard.prev_kpis = kpis

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

    @app.get("/api/summary")
    async def get_summary() -> dict[str, Any]:
        """Get tractable tick summary data (Plan #60).

        Reads summary.jsonl (if present) for quick overview metrics.
        Returns aggregated stats and per-tick summaries.
        """
        # Look for summary.jsonl in same directory as events log
        summary_path = dashboard.jsonl_path.parent / "summary.jsonl"

        if not summary_path.exists():
            return {
                "available": False,
                "message": "summary.jsonl not found (enable per-run mode for tractable logs)",
                "summaries": [],
            }


        # Parse summary.jsonl
        summaries: list[dict[str, Any]] = []
        try:
            with open(summary_path) as f:
                for line in f:
                    if line.strip():
                        summaries.append(json.loads(line))
        except Exception as e:
            return {
                "available": False,
                "message": f"Error reading summary.jsonl: {e}",
                "summaries": [],
            }


        if not summaries:
            return {
                "available": True,
                "message": "No tick summaries recorded yet",
                "summaries": [],
                "totals": {},
            }


        # Aggregate stats
        totals = {
            "total_ticks": len(summaries),
            "total_actions": sum(s.get("actions_executed", 0) for s in summaries),
            "total_llm_tokens": sum(s.get("total_llm_tokens", 0) for s in summaries),
            "total_scrip_transferred": sum(s.get("total_scrip_transferred", 0) for s in summaries),
            "total_artifacts_created": sum(s.get("artifacts_created", 0) for s in summaries),
            "total_errors": sum(s.get("errors", 0) for s in summaries),
        }


        # Action type breakdown
        action_types: dict[str, int] = {}
        for s in summaries:
            for action_type, count in s.get("actions_by_type", {}).items():
                action_types[action_type] = action_types.get(action_type, 0) + count
        totals["actions_by_type"] = action_types

        # Collect highlights
        all_highlights: list[dict[str, Any]] = []
        for s in summaries:
            tick = s.get("tick", 0)
            for h in s.get("highlights", []):
                all_highlights.append({"tick": tick, "text": h})

        return {
            "available": True,
            "summaries": summaries,
            "totals": totals,
            "highlights": all_highlights[-50:],  # Last 50 highlights
        }


    @app.get("/api/network")
    async def get_network_graph(
        tick_max: int | None = Query(None, description="Max tick to include"),
    ) -> dict[str, Any]:
        """Get network graph data for agent interactions."""
        dashboard.parser.parse_incremental()
        return dashboard.parser.get_network_graph_data(tick_max).model_dump()

    @app.get("/api/temporal-network")
    async def get_temporal_network(
        time_min: str | None = Query(None, description="Min timestamp (ISO format)"),
        time_max: str | None = Query(None, description="Max timestamp (ISO format)"),
        time_bucket_seconds: int = Query(1, ge=1, le=3600, description="Time bucket size"),
    ) -> dict[str, Any]:
        """Get temporal network data showing ALL artifacts and their interactions (Plan #107).

        Unlike /api/network which only shows agent-to-agent interactions,
        this includes:
        - All artifact types as nodes (agents, genesis, contracts, data)
        - All invocations as edges (including genesis artifact calls)
        - Ownership relationships
        - Activity heatmap data by time bucket
        """
        dashboard.parser.parse_incremental()
        return dashboard.parser.get_temporal_network_data(
            time_min=time_min,
            time_max=time_max,
            time_bucket_seconds=time_bucket_seconds,
        ).model_dump()

    @app.get("/api/activity")
    async def get_activity_feed(
        limit: int = Query(100, ge=1, le=500),
        offset: int = Query(0, ge=0),
        types: str | None = Query(None, description="Comma-separated activity types"),
        agent_id: str | None = Query(None, description="Filter by agent ID"),
        artifact_id: str | None = Query(None, description="Filter by artifact ID (Plan #144)"),
    ) -> dict[str, Any]:
        """Get activity feed with filtering."""
        dashboard.parser.parse_incremental()
        types_list = types.split(",") if types else None
        return dashboard.parser.get_activity_feed(
            limit=limit,
            offset=offset,
            activity_types=types_list,
            agent_id=agent_id,
            artifact_id=artifact_id,
        ).model_dump()

    @app.get("/api/artifacts/{artifact_id}/detail")
    async def get_artifact_detail(artifact_id: str) -> dict[str, Any]:
        """Get detailed info for a single artifact including content."""
        dashboard.parser.parse_incremental()
        detail = dashboard.parser.get_artifact_detail(artifact_id)
        if detail:
            return detail.model_dump()
        return {"error": f"Artifact {artifact_id} not found"}

    @app.get("/api/artifacts/{artifact_id}/invocations")
    async def get_artifact_invocations(artifact_id: str) -> dict[str, Any]:
        """Get invocation statistics for an artifact (Gap #27).

        Returns success rate, average duration, and failure type breakdown.
        """
        dashboard.parser.parse_incremental()
        stats = dashboard.parser.get_invocation_stats(artifact_id)
        return stats.model_dump()

    @app.get("/api/invocations")
    async def get_invocations(
        artifact_id: str | None = Query(None, description="Filter by artifact ID"),
        invoker_id: str | None = Query(None, description="Filter by invoker ID"),
        success: bool | None = Query(None, description="Filter by success status"),
        limit: int = Query(100, ge=1, le=1000),
        offset: int = Query(0, ge=0),
    ) -> list[dict[str, Any]]:
        """Get filtered invocation events (Gap #27).

        Returns list of invocations with filtering options.
        """
        dashboard.parser.parse_incremental()
        invocations = dashboard.parser.get_invocations(
            artifact_id=artifact_id,
            invoker_id=invoker_id,
            success=success,
            limit=limit,
            offset=offset,
        )
        return [i.model_dump() for i in invocations]

    @app.get("/api/artifacts/dependency-graph")
    async def get_dependency_graph() -> dict[str, Any]:
        """Get artifact dependency graph (Plan #64).

        Returns graph data for visualizing artifact composition structure:
        - nodes: Artifacts with metadata (owner, type, genesis status, depth)
        - edges: depends_on relationships
        - metrics: Graph statistics (max_depth, genesis_ratio, orphan_count)

        This is pure observability - we don't define "good" structure,
        just make the emergent capital structure visible.
        """
        dashboard.parser.parse_incremental()

        # Extract artifact data for graph construction
        artifacts = []
        for artifact_id, artifact_state in dashboard.parser.state.artifacts.items():
            # Get invocation count (unique invokers for Lindy score)
            invocations = [
                e for e in dashboard.parser.state.invocation_events
                if e.artifact_id == artifact_id
            ]
            unique_invokers = len({inv.invoker_id for inv in invocations})

            artifacts.append({
                "artifact_id": artifact_id,
                "name": artifact_state.artifact_id,  # Use ID as name
                "owner": artifact_state.created_by,
                "artifact_type": artifact_state.artifact_type,
                "depends_on": getattr(artifact_state, "depends_on", []) or [],
                "created_at": artifact_state.created_at,
                "unique_invokers": unique_invokers,
            })


        graph = build_dependency_graph(artifacts)
        return graph.model_dump()

    @app.get("/api/agents/interactions")
    async def get_agent_interactions(
        from_agent: str = Query(..., description="Source agent ID"),
        to_agent: str = Query(..., description="Target agent ID"),
    ) -> dict[str, Any]:
        """Get pairwise interactions between two agents (Plan #110 Phase 3.1).

        Returns all interactions between the specified agents in either direction,
        with a breakdown by interaction type.
        """
        dashboard.parser.parse_incremental()
        summary = dashboard.parser.get_pairwise_interactions(from_agent, to_agent)
        return summary.model_dump()

    @app.get("/api/artifacts/standards")
    async def get_standard_artifacts(
        min_score: float = Query(0.0, ge=0, description="Minimum Lindy score"),
        limit: int = Query(20, ge=1, le=100, description="Maximum results"),
    ) -> list[dict[str, Any]]:
        """Get artifacts with high Lindy scores (Plan #110 Phase 3.3).

        Lindy score = age_days × unique_invokers
        Higher scores suggest artifacts emerging as 'standard library' components.
        """
        dashboard.parser.parse_incremental()
        artifacts = dashboard.parser.get_standard_artifacts(
            min_lindy_score=min_score,
            limit=limit,
        )
        return [a.model_dump() for a in artifacts]

    @app.get("/api/charts/capital-flow")
    async def get_capital_flow(
        time_min: str | None = Query(None, description="Min timestamp (ISO format)"),
        time_max: str | None = Query(None, description="Max timestamp (ISO format)"),
    ) -> dict[str, Any]:
        """Get capital flow data for sankey diagram (Plan #110 Phase 3.4).

        Returns aggregated scrip transfers between agents for visualization.
        """
        dashboard.parser.parse_incremental()
        return dashboard.parser.get_capital_flow_data(
            time_min=time_min,
            time_max=time_max,
        ).model_dump()

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


    @app.get("/api/search")
    async def global_search(
        q: str = Query(..., min_length=1, description="Search query"),
        limit: int = Query(20, ge=1, le=50, description="Max results per category"),
    ) -> dict[str, Any]:
        """Global search across agents, artifacts, and events (Plan #147).

        Searches by ID and content across all entity types.
        Returns categorized results with relevance.
        """
        dashboard.parser.parse_incremental()
        query = q.lower()

        results: dict[str, list[dict[str, Any]]] = {
            "agents": [],
            "artifacts": [],
            "events": [],
        }

        # Search agents
        for agent_id, agent_state in dashboard.parser.state.agents.items():
            if query in agent_id.lower():
                results["agents"].append({
                    "id": agent_id,
                    "type": "agent",
                    "status": agent_state.status,
                    "scrip": agent_state.scrip,
                    "match_type": "id",
                })
                if len(results["agents"]) >= limit:
                    break

        # Search artifacts
        for artifact_id, artifact_state in dashboard.parser.state.artifacts.items():
            if query in artifact_id.lower():
                results["artifacts"].append({
                    "id": artifact_id,
                    "type": "artifact",
                    "artifact_type": artifact_state.artifact_type,
                    "created_by": artifact_state.created_by,
                    "match_type": "id",
                })
            elif artifact_state.content and query in artifact_state.content.lower():
                results["artifacts"].append({
                    "id": artifact_id,
                    "type": "artifact",
                    "artifact_type": artifact_state.artifact_type,
                    "created_by": artifact_state.created_by,
                    "match_type": "content",
                })
            if len(results["artifacts"]) >= limit:
                break

        # Search events (most recent first, limited scan)
        events_to_scan = dashboard.parser.state.all_events[-500:]  # Last 500 events
        for event in reversed(events_to_scan):
            event_str = json.dumps(event.model_dump()).lower()
            if query in event_str:
                results["events"].append({
                    "id": f"event-{event.tick}-{event.event_type}",
                    "type": "event",
                    "event_type": event.event_type,
                    "tick": event.tick,
                    "agent_id": getattr(event, "agent_id", None),
                    "match_type": "content",
                })
                if len(results["events"]) >= limit:
                    break

        return {
            "query": q,
            "results": results,
            "counts": {
                "agents": len(results["agents"]),
                "artifacts": len(results["artifacts"]),
                "events": len(results["events"]),
            },
        }

    # Plan #125: Extracted route groups for maintainability
    _register_simulation_routes(app, dashboard)
    _register_websocket_routes(app, dashboard)

    return app


def run_dashboard(
    host: str = "0.0.0.0",
    port: int = 8080,
    jsonl_path: str = DEFAULT_JSONL_PATH,
    reload: bool = False,
    live_mode: bool = False,
) -> None:
    """Run the dashboard server."""
    import uvicorn

    app = create_app(jsonl_path=jsonl_path, live_mode=live_mode)
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
