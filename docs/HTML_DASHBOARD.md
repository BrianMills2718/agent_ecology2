# HTML Dashboard for Agent Ecology

## Overview

The HTML dashboard provides real-time visibility into the agent ecology simulation. It displays agent status, resource utilization, artifact catalog, economic flows, and simulation progress through an interactive web interface.

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                        Browser (HTML/JS)                        │
├─────────────────────────────────────────────────────────────────┤
│  Agent Panel │ Artifacts │ Timeline │ Events │ Charts │ Controls│
└───────────────────────────┬─────────────────────────────────────┘
                            │ WebSocket + REST API
┌───────────────────────────┴─────────────────────────────────────┐
│                     Dashboard Server (FastAPI)                   │
├─────────────────────────────────────────────────────────────────┤
│  JSONL Parser  │  State Cache  │  WebSocket Hub  │  REST Routes │
└───────────────────────────┬─────────────────────────────────────┘
                            │ File Watch + Direct Access
┌───────────────────────────┴─────────────────────────────────────┐
│                      Simulation Data Layer                       │
├─────────────────────────────────────────────────────────────────┤
│     run.jsonl (events)  │  World state  │  config/config.yaml   │
└─────────────────────────────────────────────────────────────────┘
```

## Components

### 1. Dashboard Server (`src/dashboard/server.py`)

FastAPI-based server providing:
- **REST API** for fetching current state
- **WebSocket endpoint** for real-time event streaming
- **Static file serving** for HTML/CSS/JS
- **JSONL file watcher** for detecting new events

**Endpoints:**

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/` | GET | Serve main dashboard HTML |
| `/api/state` | GET | Current simulation state (tick, balances, artifacts) |
| `/api/events` | GET | Historical events with pagination/filtering |
| `/api/agents` | GET | All agent details |
| `/api/agents/{id}` | GET | Single agent detail with history |
| `/api/artifacts` | GET | All artifacts with metadata |
| `/api/config` | GET | Current config values |
| `/ws` | WebSocket | Real-time event stream |

### 2. JSONL Parser (`src/dashboard/parser.py`)

Parses the `run.jsonl` event log:
- Incremental parsing (tracks file position)
- Event type classification
- State reconstruction from events
- Aggregation for charts (per-tick summaries)

**Event Types Parsed:**

| Event Type | Data Extracted |
|------------|----------------|
| `world_init` | Initial config, principals, costs |
| `tick` | Tick number, all balances snapshot |
| `thinking` | Agent ID, tokens used, compute cost |
| `thinking_failed` | Agent ID, failure reason |
| `action` | Intent, result, costs, balances after |
| `intent_rejected` | Agent ID, validation error |
| `mint` | Artifact ID, score, scrip minted |
| `budget_pause` | Reason simulation paused |
| `max_ticks` | Simulation completed |

### 3. Frontend Dashboard (`src/dashboard/static/`)

Single-page application with panels:

#### Agent Status Panel
- Table of all agents
- Columns: ID, Scrip, Compute (used/quota), Disk (used/quota), Status
- Color coding: green (healthy), yellow (low resources), red (frozen)
- Click to open detail modal

#### Artifact Catalog
- Searchable/sortable table
- Columns: ID, Type, Owner, Price, Executable, Oracle Score, Created
- Filter by owner, type, executable status
- Click to view content/code

#### Action Timeline
- Chronological list of actions per tick
- Grouped by agent or by tick
- Shows: action type, target, cost, success/failure
- Expandable to show full intent and result

#### Tick Progress
- Current tick / max ticks progress bar
- API budget: spent / limit with progress bar
- Ticks per second (performance metric)
- Time elapsed

#### Economic Flow Visualization
- Sankey diagram showing scrip transfers
- Nodes = agents, edges = transfers with amounts
- Filter by tick range
- Hover for transfer details

#### Resource Utilization Charts
- Line chart: compute usage per agent over ticks
- Bar chart: disk usage per agent (current)
- Stacked area: total resource consumption over time

#### Genesis Activity Panel
- **Oracle**: Pending submissions, recent scores, scrip minted
- **Escrow**: Active listings, recent trades
- **Ledger**: Recent transfers, principal spawns
- **Rights Registry**: Quota transfers

#### Live Event Stream
- Real-time feed of events as they occur
- Filter by: event type, principal ID, artifact ID
- Pause/resume stream
- Search within events

#### Agent Detail Modal
- Full agent info when clicked
- Sections: Current balances, Action history, Artifacts owned, Memory/context
- Resource usage graphs for this agent

#### Simulation Controls
- Start/Pause/Resume buttons (when integrated with runner)
- Tick delay slider
- Load checkpoint file picker
- Export current state as JSON

## Data Flow

### Real-Time Updates

1. Simulation writes event to `run.jsonl`
2. Dashboard server detects file change (watchdog)
3. Server parses new events
4. Server broadcasts via WebSocket to all clients
5. Frontend updates affected panels

### Initial Load

1. Browser opens dashboard
2. Frontend fetches `/api/state` for current snapshot
3. Frontend fetches `/api/events?limit=1000` for history
4. Frontend establishes WebSocket connection
5. Panels render with data

## Configuration

Dashboard settings in `config/config.yaml`:

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

## File Structure

```
src/dashboard/
├── __init__.py
├── server.py          # FastAPI application
├── parser.py          # JSONL parsing and state reconstruction
├── models.py          # Pydantic models for API responses
├── watcher.py         # File watcher for run.jsonl
└── static/
    ├── index.html     # Main dashboard page
    ├── css/
    │   └── dashboard.css
    └── js/
        ├── main.js        # Application entry point
        ├── websocket.js   # WebSocket connection manager
        ├── panels/
        │   ├── agents.js      # Agent status panel
        │   ├── artifacts.js   # Artifact catalog
        │   ├── timeline.js    # Action timeline
        │   ├── events.js      # Live event stream
        │   ├── progress.js    # Tick progress
        │   ├── charts.js      # Resource charts
        │   ├── genesis.js     # Genesis activity
        │   └── controls.js    # Simulation controls
        └── utils/
            ├── api.js         # REST API client
            └── charts.js      # Chart.js helpers
```

## Usage

### Starting the Dashboard

```bash
# Run simulation WITH dashboard (auto-opens browser)
python run.py --dashboard

# Run simulation with dashboard but don't auto-open browser
python run.py --dashboard --no-browser

# Dashboard-only mode (view existing run.jsonl, no simulation)
python run.py --dashboard-only

# Standalone dashboard server
python -m src.dashboard.server

# Custom port
python -m src.dashboard.server --port 9000
```

### Accessing the Dashboard

The dashboard automatically opens in your browser at `http://localhost:8080`

### Controlling the Simulation

When running with `--dashboard`, you can control the simulation from the browser:

- **Pause** button (yellow): Pauses simulation after the current tick completes
- **Resume** button (green): Resumes a paused simulation

These controls appear in the header when a simulation is actively running. The pause/resume state syncs in real-time across all connected browser tabs via WebSocket.

### API Examples

```bash
# Get current state
curl http://localhost:8080/api/state

# Get all agents
curl http://localhost:8080/api/agents

# Get events filtered by type
curl "http://localhost:8080/api/events?type=action&limit=50"

# Get specific agent
curl http://localhost:8080/api/agents/alpha
```

## Dependencies

Add to `requirements.txt`:
```
fastapi>=0.104.0
uvicorn>=0.24.0
websockets>=12.0
watchdog>=3.0.0
aiofiles>=23.0.0
```

## Security Notes

- Dashboard is read-only by default
- No authentication required (local development)
- For production: add auth middleware, restrict CORS
- Simulation controls require explicit enable in config

## Future Enhancements

- [ ] Authentication/authorization
- [ ] Multiple simulation tracking
- [ ] Historical simulation replay
- [ ] Custom dashboard layouts (drag-and-drop)
- [ ] Export to PNG/PDF
- [ ] Mobile-responsive design
- [ ] Dark mode theme
- [ ] Alerting on agent failures
