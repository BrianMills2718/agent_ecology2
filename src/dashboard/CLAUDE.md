# Dashboard Module

Visualization server for observing simulation state in real-time.
Server-rendered HTML/JS served from `static/` with WebSocket streaming.

## Module Files

| File | Responsibility |
|------|----------------|
| `__init__.py` | Package exports (create_app, run_dashboard, JSONLParser, etc.) |
| `server.py` | FastAPI server, route registration, static file serving |
| `parser.py` | JSONL event log parsing, simulation state reconstruction |
| `models.py` | Pydantic response schemas (ArtifactInfo, AgentSummary, etc.) |
| `watcher.py` | File watching (watchdog) for live JSONL updates |
| `auditor.py` | Threshold-based ecosystem health assessment and reports |
| `dependency_graph.py` | Artifact dependency graph construction and metrics |
| `kpis.py` | Ecosystem health KPI calculations (capital flow, emergence) |
| `process_manager.py` | Simulation subprocess spawning/stopping from dashboard |
| `run_manager.py` | Run discovery, selection, and resume for historical runs |

## Subdirectories

| Directory | Purpose |
|-----------|---------|
| `static/` | HTML/CSS/JS assets |

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
