# HTML Dashboard for Agent Ecology

## Overview

The HTML dashboard provides real-time visibility into the agent ecology simulation. It displays agent status, resource utilization, artifact catalog, economic flows, agent interactions, and simulation progress through an interactive web interface.

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                        Browser (HTML/JS)                        │
├─────────────────────────────────────────────────────────────────┤
│ Network Graph │ Activity Feed │ Agents │ Artifacts │ Genesis   │
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
- **Simulation control** (pause/resume)

**Endpoints:**

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/` | GET | Serve main dashboard HTML |
| `/api/state` | GET | Current simulation state (tick, balances, artifacts) |
| `/api/progress` | GET | Simulation progress (tick, budget, status) |
| `/api/events` | GET | Historical events with pagination/filtering |
| `/api/agents` | GET | All agent summaries |
| `/api/agents/{id}` | GET | Single agent detail with history |
| `/api/artifacts` | GET | All artifacts with metadata |
| `/api/artifacts/{id}/detail` | GET | Full artifact detail with content |
| `/api/network` | GET | Network graph data (nodes, edges, interactions) |
| `/api/activity` | GET | Activity feed with filtering |
| `/api/thinking` | GET | Agent thinking history with reasoning content |
| `/api/genesis` | GET | Genesis artifact activity |
| `/api/charts/compute` | GET | Compute usage chart data |
| `/api/charts/scrip` | GET | Scrip balance chart data |
| `/api/config` | GET | Current config values |
| `/api/ticks` | GET | Tick summary history |
| `/api/simulation/status` | GET | Simulation runner status |
| `/api/simulation/pause` | POST | Pause simulation |
| `/api/simulation/resume` | POST | Resume simulation |
| `/ws` | WebSocket | Real-time event stream |

### 2. JSONL Parser (`src/dashboard/parser.py`)

Parses the `run.jsonl` event log:
- Incremental parsing (tracks file position)
- **File truncation detection** (resets state on simulation restart)
- Event type classification
- State reconstruction from events
- **Interaction tracking** for network graph
- **Activity feed generation**
- Aggregation for charts (per-tick summaries)

**Event Types Parsed:**

| Event Type | Data Extracted |
|------------|----------------|
| `world_init` | Initial config, principals, costs, max_ticks |
| `tick` | Tick number, all balances snapshot |
| `thinking` | Agent ID, tokens used, compute cost |
| `thinking_failed` | Agent ID, failure reason |
| `action` | Intent, result, costs, balances after |
| `intent_rejected` | Agent ID, validation error |
| `mint` | Artifact ID, score, scrip minted |
| `budget_pause` | Reason simulation paused |
| `max_ticks` | Simulation completed |

**Interactions Tracked:**

| Interaction Type | Source | Description |
|-----------------|--------|-------------|
| `scrip_transfer` | Ledger transfer | Agent A sends scrip to Agent B |
| `escrow_trade` | Escrow purchase | Agent A buys artifact from Agent B |
| `ownership_transfer` | Ledger ownership | Agent A transfers artifact to Agent B |
| `artifact_invoke` | Action | Agent A invokes artifact owned by Agent B |

### 3. Frontend Dashboard (`src/dashboard/static/`)

Single-page application with panels:

#### Network Graph Panel (NEW)
- **vis.js force-directed graph** of agent interactions
- Nodes represent agents (colored by status)
- Edges represent interactions (colored by type):
  - 🟢 Green: Scrip transfers
  - 🔵 Blue: Escrow trades
  - 🟣 Purple: Ownership transfers
  - 🟡 Yellow: Artifact invocations
- **Time slider** to filter interactions by tick
- Click nodes to view agent details
- Hover for interaction details

#### Activity Feed Panel (NEW)
- Unified chronological feed of all activity
- Activity types: artifact created/updated, transfers, trades, mints
- **Clickable links** to agents and artifacts
- Filter dropdown by activity type
- Real-time updates via WebSocket

#### Agent Status Panel
- Table of all agents
- Columns: ID, Scrip, Compute (used/quota), Disk (used/quota), Status
- Color coding: green (healthy), yellow (low resources), red (frozen)
- Click to open detail modal

#### Artifact Catalog
- Searchable/sortable table
- Columns: ID, Type, Owner, Price, Executable, Oracle Score
- Filter by owner, type, executable status
- Click to view artifact detail modal (NEW)

#### Artifact Detail Modal (NEW)
- Full artifact information
- **Code/content viewer** (up to 10KB)
- Ownership history (all transfers)
- Invocation count and history
- Oracle score and status

#### Resource Utilization Charts
- Collapsible panel (click header to expand)
- Tabs: Compute usage, Scrip balances
- Line charts showing per-agent trends over ticks

#### Genesis Activity Panel
- **Oracle**: Pending submissions, recent scores, scrip minted
- **Escrow**: Active listings, recent trades
- **Ledger**: Recent transfers, principal spawns, ownership transfers

#### Live Event Stream
- Real-time feed of events as they occur
- Filter by event type
- Pause/resume and clear controls

#### Tick Progress
- Current tick / max ticks progress bar
- API budget: spent / limit with progress bar
- Ticks per second (performance metric)
- Status badge (running/paused/completed)

#### Simulation Controls
- Pause button (yellow): Pauses after current tick
- Resume button (green): Resumes paused simulation
- Status syncs across all browser tabs via WebSocket

## Data Flow

### Real-Time Updates

1. Simulation writes event to `run.jsonl`
2. Dashboard server detects file change (polling watcher)
3. Server parses new events, updates state
4. Server broadcasts via WebSocket to all clients
5. Frontend updates affected panels (network graph, activity feed, etc.)

### File Truncation Handling

When simulation restarts:
1. Logger clears `run.jsonl` (truncates to 0 bytes)
2. Parser detects file size < file position
3. Parser resets state and re-parses from beginning
4. Dashboard shows correct max_ticks from new world_init

### Initial Load

1. Browser opens dashboard
2. Frontend fetches `/api/state` for current snapshot
3. Frontend initializes all panels with data
4. Frontend establishes WebSocket connection
5. Live updates begin flowing

## Configuration

Dashboard settings in `config/config.yaml`:

```yaml
dashboard:
  enabled: true
  host: "0.0.0.0"
  port: 8081
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
├── parser.py          # JSONL parsing, state reconstruction, interactions
├── models.py          # Pydantic models for API responses
├── watcher.py         # File watcher for run.jsonl
└── static/
    ├── index.html     # Main dashboard page
    ├── css/
    │   └── dashboard.css   # Dark theme styling
    └── js/
        ├── main.js         # Application entry point
        ├── websocket.js    # WebSocket connection manager
        ├── panels/
        │   ├── agents.js       # Agent status panel
        │   ├── artifacts.js    # Artifact catalog
        │   ├── events.js       # Live event stream
        │   ├── progress.js     # Tick progress
        │   ├── charts.js       # Resource charts (Chart.js)
        │   ├── genesis.js      # Genesis activity
        │   ├── controls.js     # Simulation controls
        │   ├── network.js      # Network graph (vis.js)
        │   ├── activity.js     # Activity feed
        │   └── thinking.js     # Agent thinking panel
        └── utils/
            └── api.js          # REST API client
```

## Usage

### Starting the Dashboard

```bash
# Run simulation WITH dashboard (auto-opens browser)
python run.py --dashboard

# Run simulation with dashboard but don't auto-open browser
python run.py --dashboard --no-browser

# Run with custom tick count
python run.py --dashboard --ticks 100

# Dashboard-only mode (view existing run.jsonl, no simulation)
python run.py --dashboard-only
```

### Accessing the Dashboard

Open `http://localhost:8081` in your browser.

### Controlling the Simulation

When running with `--dashboard`, control from browser:
- **Pause** button: Pauses after current tick completes
- **Resume** button: Resumes a paused simulation

### API Examples

```bash
# Get simulation progress
curl http://localhost:8081/api/progress

# Get network graph data
curl http://localhost:8081/api/network

# Get network graph up to tick 50
curl "http://localhost:8081/api/network?tick_max=50"

# Get activity feed
curl http://localhost:8081/api/activity

# Get activity feed filtered by type
curl "http://localhost:8081/api/activity?types=scrip_transfer,escrow_purchased"

# Get full artifact detail with content
curl http://localhost:8081/api/artifacts/my_artifact/detail

# Pause simulation
curl -X POST http://localhost:8081/api/simulation/pause

# Resume simulation
curl -X POST http://localhost:8081/api/simulation/resume
```

## Dependencies

Required in `requirements.txt`:
```
fastapi>=0.104.0
uvicorn>=0.24.0
websockets>=12.0
watchdog>=3.0.0
```

External JS libraries (loaded via CDN):
- Chart.js 4.4.1 - Resource charts
- vis-network 9.1.6 - Network graph

## Implemented Features ✅

- [x] Real-time WebSocket updates
- [x] Agent status panel with detail modal
- [x] Artifact catalog with search/filter
- [x] Artifact detail modal with content view
- [x] Network graph with agent interactions
- [x] Time slider for temporal filtering
- [x] Activity feed with filtering
- [x] Genesis activity panels (Oracle, Escrow, Ledger)
- [x] Resource charts (Compute, Scrip)
- [x] Simulation controls (pause/resume)
- [x] Progress bars (ticks, budget)
- [x] File truncation detection (simulation restart)
- [x] Dark theme UI
- [x] **Agent Thinking Panel** - Display agent reasoning/thought processes
  - Expandable items showing full reasoning
  - Filter by agent
  - Token usage and compute cost display
- [x] **Enhanced Agent Modal** - Shows recent thinking in agent detail

## Planned Features (Next)

### Phase 1: Economic Dashboard
- [ ] **Wealth Distribution View** - Gini coefficient, distribution chart
- [ ] **Trade Volume Chart** - Volume over time
- [ ] **Price Trends** - Artifact price changes
- [ ] **Economic Health Indicators** - Circulation, velocity

### Phase 2: Advanced Visualization
- [ ] **Network Animation** - Replay interactions over time
- [ ] **Cluster Detection** - Identify agent groups
- [ ] **Node Sizing** - Size by wealth/activity
- [ ] **Edge Thickness** - Based on interaction frequency

### Phase 3: Analysis Tools
- [ ] **Agent Comparison** - Side-by-side analysis
- [ ] **Execution Trace Viewer** - See artifact execution details
- [ ] **Search Across All Data** - Global search
- [ ] **Export Features** - CSV, JSON, PNG

### Future Enhancements
- [ ] Authentication/authorization
- [ ] Multiple simulation tracking
- [ ] Historical simulation replay
- [ ] Custom dashboard layouts
- [ ] Mobile-responsive design
- [ ] Alerting on agent failures

## Security Notes

- Dashboard is read-only by default (except pause/resume)
- No authentication required (local development)
- For production: add auth middleware, restrict CORS
- Simulation controls require running simulation process
