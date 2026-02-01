# Dashboard Module

Visualization server for observing simulation state in real-time. Supports two versions:
v1 (server-rendered HTML) and v2 (React SPA built from `dashboard-v2/`).

## Architecture

- **v1**: Server-rendered HTML/JS served from `static/`. WebSocket streaming.
- **v2**: React frontend built to `static-v2/`. REST API + WebSocket. Source lives at repo root `dashboard-v2/`.
- `server.py` serves v1 or v2 based on `dashboard.version` in config.

## Module Files

| File | Responsibility |
|------|----------------|
| `__init__.py` | Package exports (create_app, run_dashboard, JSONLParser, etc.) |
| `server.py` | FastAPI server, route registration, static file serving, v1/v2 switching |
| `parser.py` | JSONL event log parsing, simulation state reconstruction |
| `models.py` | Pydantic response schemas (AgentBalance, ArtifactInfo, etc.) |
| `watcher.py` | File watching (watchdog) for live JSONL updates |
| `auditor.py` | Threshold-based ecosystem health assessment and reports |
| `dependency_graph.py` | Artifact dependency graph construction and metrics |
| `kpis.py` | Ecosystem health KPI calculations (capital flow, emergence) |
| `process_manager.py` | Simulation subprocess spawning/stopping from dashboard |
| `run_manager.py` | Run discovery, selection, and resume for historical runs |

## Subdirectories

| Directory | Purpose |
|-----------|---------|
| `api/` | REST API endpoints (v2) |
| `api/routes/` | Route modules: agents, artifacts, metrics, search |
| `api/websocket.py` | WebSocket handler for v2 |
| `core_v2/` | v2 event processing (event_parser, metrics_engine, state_tracker) |
| `models_v2/` | v2 data schemas (events, metrics, state) |
| `static/` | v1 HTML/CSS/JS assets |
| `static-v2/` | v2 React build output (from `dashboard-v2/`) |

## Running the Dashboard

```bash
# With simulation
python run.py --dashboard

# View existing run.jsonl
python run.py --dashboard-only

# Without auto-opening browser
python run.py --dashboard --no-browser
```

## Configuration

From `config/config.yaml`:

```yaml
dashboard:
  enabled: true
  host: "0.0.0.0"
  port: 8080
  version: "v1"           # "v1" or "v2"
  static_dir: "src/dashboard/static"
  jsonl_file: "run.jsonl"
  websocket_path: "/ws"
```

## WebSocket Protocol

Dashboard connects to `/ws` and receives events as JSON:

```json
{"type": "tick", "tick": 5, ...}
{"type": "action", "agent_id": "alpha", "action_type": "invoke", ...}
{"type": "thinking", "agent_id": "beta", ...}
```

## Strict Couplings

Changes here MUST update `docs/architecture/current/supporting_systems.md`.
