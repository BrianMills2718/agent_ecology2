# Dashboard Module

HTML visualization server for observing simulation in real-time.

## Module Responsibilities

| File | Responsibility |
|------|----------------|
| `server.py` | FastAPI server, WebSocket streaming |
| `models.py` | Response schemas |
| `parser.py` | JSONL event parsing |
| `watcher.py` | File watching for live updates |
| `static/` | HTML, CSS, JS assets |

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
