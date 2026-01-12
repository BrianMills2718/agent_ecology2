# Current Supporting Systems

Operational infrastructure: checkpointing, logging, and dashboard.

**Last verified:** 2026-01-12

---

## Overview

| System | Purpose | Key File |
|--------|---------|----------|
| Checkpoint | Save/restore simulation state | `src/simulation/checkpoint.py` |
| EventLogger | Append-only JSONL event log | `src/world/logger.py` |
| Dashboard | Real-time web UI | `src/dashboard/` |

---

## Checkpoint System

Enables simulation pause/resume across runs.

### Save Checkpoint

**`save_checkpoint()`** - `checkpoint.py:13-45`

```python
from simulation.checkpoint import save_checkpoint

path = save_checkpoint(
    world=world,
    agents=agents,
    cumulative_cost=1.50,
    config=config,
    reason="budget_exhausted"
)
```

### Checkpoint Data

```python
CheckpointData = {
    "tick": int,
    "balances": dict[str, BalanceInfo],  # {agent_id: {compute, scrip}}
    "cumulative_api_cost": float,
    "artifacts": list[dict],             # Artifact dicts
    "agent_ids": list[str],
    "reason": str                         # Why checkpoint was saved
}
```

### Load Checkpoint

**`load_checkpoint()`** - `checkpoint.py:48-85`

```python
from simulation.checkpoint import load_checkpoint

checkpoint = load_checkpoint("checkpoint.json")
if checkpoint:
    # Resume from checkpoint
    start_tick = checkpoint["tick"]
```

### When Checkpoints Are Saved

| Trigger | Reason | Config |
|---------|--------|--------|
| Budget exhausted | `"budget_exhausted"` | Always |
| Periodic interval | `"periodic"` | `budget.checkpoint_interval` |
| Simulation end | `"completed"` | `budget.checkpoint_on_end` |

---

## Event Logger

Append-only JSONL file for all simulation events.

### EventLogger Class

**`EventLogger`** - `logger.py:13-52`

```python
class EventLogger:
    def __init__(self, output_file: str | None = None)
    def log(self, event_type: str, data: dict[str, Any]) -> None
    def read_recent(self, n: int | None = None) -> list[dict[str, Any]]
```

### Event Format

```json
{
    "timestamp": "2026-01-12T10:30:00.123456",
    "event_type": "action_executed",
    "agent_id": "alice",
    "action_type": "write_artifact",
    "success": true,
    ...
}
```

### Event Types

| Event Type | When Logged |
|------------|-------------|
| `tick_started` | Start of each tick |
| `tick_completed` | End of each tick |
| `action_executed` | Agent action completed |
| `thinking_completed` | Agent thinking finished |
| `transfer` | Scrip/resource transfer |
| `oracle_auction` | Oracle auction resolved |
| `error` | Any error occurred |

### Configuration

```yaml
logging:
  output_file: "run.jsonl"
  log_dir: "llm_logs"
  default_recent: 50
```

---

## Dashboard

Real-time web UI for monitoring simulation.

### Components

| File | Purpose |
|------|---------|
| `server.py` | FastAPI server with WebSocket |
| `parser.py` | JSONL parsing and state extraction |
| `watcher.py` | File change polling |
| `models.py` | Pydantic models for API responses |
| `static/` | HTML/CSS/JS frontend |

### Architecture

```
┌──────────────────┐     ┌─────────────────┐
│   run.jsonl      │────▶│  PollingWatcher │
└──────────────────┘     └────────┬────────┘
                                  │ on change
                                  ▼
                         ┌─────────────────┐
                         │   JSONLParser   │
                         └────────┬────────┘
                                  │ parse events
                                  ▼
                         ┌─────────────────┐
                         │  DashboardApp   │
                         └────────┬────────┘
                                  │ WebSocket broadcast
                                  ▼
                         ┌─────────────────┐
                         │    Browsers     │
                         └─────────────────┘
```

### API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/` | GET | Dashboard HTML |
| `/ws` | WebSocket | Real-time updates |
| `/api/state` | GET | Current simulation state |
| `/api/agents` | GET | Agent summaries |
| `/api/agents/{id}` | GET | Agent details |
| `/api/artifacts` | GET | All artifacts |
| `/api/events` | GET | Recent events (filterable) |

### WebSocket Messages

```json
{
    "type": "state_update",
    "data": {
        "tick": 42,
        "agents": [...],
        "artifacts": [...]
    }
}
```

### Configuration

```yaml
dashboard:
  enabled: true
  host: "0.0.0.0"
  port: 8080
  static_dir: "src/dashboard/static"
  jsonl_file: "run.jsonl"
  websocket_path: "/ws"
  cors_origins: ["*"]
  max_events_cache: 10000
```

---

## Key Files

| File | Key Classes | Description |
|------|-------------|-------------|
| `src/simulation/checkpoint.py` | `save_checkpoint()`, `load_checkpoint()` | Checkpointing |
| `src/simulation/types.py` | `CheckpointData`, `BalanceInfo` | TypedDicts |
| `src/world/logger.py` | `EventLogger` | JSONL event logging |
| `src/dashboard/server.py` | `DashboardApp`, `ConnectionManager` | FastAPI server |
| `src/dashboard/parser.py` | `JSONLParser` | Event parsing |
| `src/dashboard/watcher.py` | `PollingWatcher` | File change detection |
| `src/dashboard/models.py` | Pydantic models | API response types |

---

## Implications

### Single Source of Truth
- All events go through `EventLogger`
- Dashboard reads from same JSONL
- Checkpoints save minimal state (can replay from logs)

### Real-Time Observability
- WebSocket pushes updates immediately
- No polling from browser (server pushes)
- Multiple viewers see same state

### Resumable Simulations
- Checkpoint on budget exhaustion
- Load checkpoint to continue later
- Artifacts and balances preserved
