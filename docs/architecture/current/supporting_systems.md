# Current Supporting Systems

Operational infrastructure: checkpointing, logging, and dashboard.

**Last verified:** 2026-01-20 (Plan #139: quota_set handler, API cost estimation, fullscreen mode)

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
| Periodic interval | `"periodic_tick_{N}"` | `budget.checkpoint_interval` |
| Simulation end | `"simulation_complete"` | `budget.checkpoint_on_end` |

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

### SummaryLogger Class (Plan #60)

**`SummaryLogger`** - `logger.py:14-71` - Tractable per-tick summaries

```python
class SummaryLogger:
    def __init__(self, path: Path)
    def log_tick_summary(
        self, tick: int, agents_active: int, actions_executed: int,
        actions_by_type: dict | None = None, total_llm_tokens: int = 0,
        total_scrip_transferred: int = 0, artifacts_created: int = 0,
        errors: int = 0, highlights: list[str] | None = None
    ) -> None
```

**`TickSummaryCollector`** - `logger.py:74-187` - Accumulates metrics within a tick

```python
class TickSummaryCollector:
    def record_action(self, action_type: str, success: bool = True, agent_id: str | None = None)
    def record_llm_tokens(self, count: int, agent_id: str | None = None)
    def record_scrip_transfer(self, amount: int)
    def record_artifact_created(self)
    def add_highlight(self, text: str)
    def finalize(self, tick: int, agents_active: int) -> dict
```

When `agent_id` is provided, per-agent stats are tracked and included in `finalize()` output under `per_agent` key (Plan #76).

### Summary Format (summary.jsonl)

```json
{
    "tick": 5,
    "timestamp": "2026-01-16T12:00:00Z",
    "agents_active": 3,
    "actions_executed": 3,
    "actions_by_type": {"invoke": 2, "write": 1},
    "total_llm_tokens": 150,
    "total_scrip_transferred": 25,
    "artifacts_created": 1,
    "errors": 0,
    "highlights": ["alpha created tool_x"]
}
```

In per-run mode, `EventLogger` creates a companion `SummaryLogger` at `logs/{run_id}/summary.jsonl`.

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

| Event Type | When Logged | Source |
|------------|-------------|--------|
| `tick` | Start of each tick | `world.py` |
| `action` | Agent action executed | `world.py` |
| `thinking` | Agent thinking completed | `runner.py` |
| `thinking_failed` | Agent ran out of compute | `runner.py` |
| `intent_rejected` | Invalid action rejected | `runner.py` |
| `mint_auction` | Auction resolved | `runner.py` |
| `mint` | Scrip minted | `world.py` |
| `world_init` | World initialized | `world.py` |
| `budget_pause` | API budget exhausted | `runner.py` |
| `agent_frozen` | Agent exhausts compute | `world.py` |
| `agent_unfrozen` | Agent resources restored | `world.py` |

### Vulture Observability Events (Plan #26)

Events for market-based rescue of frozen agents.

**AGENT_FROZEN Event** - Emitted when an agent exhausts compute:
```json
{
    "event_type": "agent_frozen",
    "tick": 1500,
    "agent_id": "alice",
    "reason": "compute_exhausted",
    "scrip_balance": 200,
    "compute_remaining": 0,
    "owned_artifacts": ["art_1", "art_2"],
    "last_action_tick": 1480
}
```

**AGENT_UNFROZEN Event** - Emitted when an agent is rescued or recovers:
```json
{
    "event_type": "agent_unfrozen",
    "tick": 1600,
    "agent_id": "alice",
    "unfrozen_by": "vulture_bob",
    "resources_transferred": {
        "compute": 100,
        "scrip": 0
    }
}
```

**World API Methods:**
- `world.is_agent_frozen(agent_id)` - Check if agent has compute <= 0
- `world.get_frozen_agents()` - List all frozen agents
- `world.emit_agent_frozen(agent_id, reason)` - Log AGENT_FROZEN event
- `world.emit_agent_unfrozen(agent_id, unfrozen_by, resources)` - Log AGENT_UNFROZEN event
- `world.artifacts.get_artifacts_by_owner(owner_id)` - Get artifact IDs owned by principal

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

### Modes

| Mode | Flag | Behavior |
|------|------|----------|
| Live | `--dashboard` | Start empty, receive events as simulation runs |
| Replay | `--dashboard-only` | Parse existing logs to view completed runs |

The `live_mode` parameter controls this:
- `live_mode=True`: New simulations - don't parse old logs at startup
- `live_mode=False`: Replay mode - parse all existing events first

### Components

| File | Purpose |
|------|---------|
| `server.py` | FastAPI server with WebSocket |
| `parser.py` | JSONL parsing and state extraction |
| `watcher.py` | File change detection (watchdog + polling fallback) |
| `models.py` | Pydantic models for API responses (normalizes mixed timestamp formats) |
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
| `/api/state` | GET | Complete simulation state |
| `/api/progress` | GET | Simulation progress only |
| `/api/agents` | GET | Agent summaries |
| `/api/agents/{id}` | GET | Agent details |
| `/api/agents/{id}/config` | GET | Agent YAML configuration (Plan #108) |
| `/api/agents/{id}/metrics` | GET | Per-agent computed metrics (Plan #76) |
| `/api/artifacts` | GET | All artifacts |
| `/api/artifacts/{id}/detail` | GET | Artifact details with content |
| `/api/artifacts/{id}/invocations` | GET | Invocation statistics for artifact |
| `/api/artifacts/dependency-graph` | GET | Artifact dependency graph with metrics (Plan #64) |
| `/api/invocations` | GET | Filtered invocation events |
| `/api/events` | GET | Filtered events |
| `/api/genesis` | GET | Genesis artifact activity |
| `/api/charts/compute` | GET | Compute utilization chart data |
| `/api/charts/scrip` | GET | Scrip balance chart data |
| `/api/charts/flow` | GET | Economic flow visualization |
| `/api/kpis` | GET | Ecosystem health KPIs |
| `/api/health` | GET | Health assessment with concerns and trends |
| `/api/config` | GET | Simulation configuration |
| `/api/ticks` | GET | Tick summary history |
| `/api/summary` | GET | Tractable tick summaries from summary.jsonl (Plan #60) |
| `/api/network` | GET | Agent interaction graph |
| `/api/activity` | GET | Activity feed with filtering |
| `/api/thinking` | GET | Agent thinking history |
| `/api/simulation/status` | GET | Runner status |
| `/api/simulation/pause` | POST | Pause simulation |
| `/api/simulation/resume` | POST | Resume simulation |

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
| `src/dashboard/auditor.py` | `HealthReport`, `assess_health()` | Health assessment |
| `src/dashboard/kpis.py` | `EcosystemKPIs`, `calculate_kpis()`, `AgentMetrics`, `compute_agent_metrics()` | KPI calculations |
| `src/world/invocation_registry.py` | `InvocationRegistry`, `InvocationRecord` | Invocation tracking |

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

---

## Per-Run Event Logging (Plan #56)

EventLogger supports per-run directory organization for preserving event history.

### Two Modes

| Mode | Config | Behavior |
|------|--------|----------|
| **Per-run** (recommended) | `logs_dir` + `run_id` | Creates timestamped directories |
| **Legacy** | `output_file` only | Single file, overwritten each run |

### Per-Run Directory Structure

When `logs_dir` is configured, each run creates a timestamped directory:

```
logs/
├── run_20260115_100000/
│   └── events.jsonl
├── run_20260115_110000/
│   └── events.jsonl
├── run_20260115_120000/
│   └── events.jsonl
└── latest -> run_20260115_120000/  # Symlink to most recent
```

### Configuration

```yaml
logging:
  output_file: "run.jsonl"      # Legacy mode fallback
  logs_dir: "logs"              # Per-run logs directory
  log_dir: "llm_logs"           # Separate directory for LLM logs
  default_recent: 50
```

### Usage

**Per-run mode (when run_id provided):**
```python
# SimulationRunner generates run_id and passes to World
self.run_id = datetime.now().strftime("run_%Y%m%d_%H%M%S")
self.world = World(config, run_id=self.run_id)

# EventLogger creates:
#   logs/{run_id}/events.jsonl
#   logs/latest -> {run_id}/
```

**Legacy mode (backward compatible):**
```python
# World created without run_id uses legacy mode
self.world = World(config)  # Uses output_file, overwrites each run
```

### Benefits

- **History preserved**: Previous runs available for comparison
- **Easy access**: `logs/latest/events.jsonl` always points to current
- **Backward compatible**: Legacy single-file mode still works
