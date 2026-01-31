# Plan #224: Dashboard Run Management

**Status:** ✅ Complete
**Priority:** High
**Blocked By:** None
**Blocks:** Dashboard usability for historical analysis

---

## Problem Statement

After a simulation ends, users cannot:
1. Continue viewing the dashboard (it shows stale data)
2. Select and view previous runs
3. Resume a simulation from its checkpoint
4. Compare different runs

Currently the dashboard only reads from `logs/latest/events.jsonl` or `run.jsonl`. There's no way to browse historical runs or switch between them.

---

## Solution

Add run management capabilities to the dashboard:

### 1. Run Discovery & Metadata

Scan `logs/` directory for runs and extract metadata from each `events.jsonl`:

```python
@dataclass
class RunInfo:
    run_id: str           # e.g., "run_20260126_090847"
    start_time: datetime
    end_time: datetime | None
    duration_seconds: float
    event_count: int
    agent_ids: list[str]
    has_checkpoint: bool
    status: str           # "running", "completed", "stopped"
```

### 2. Backend API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/runs` | GET | List all runs with metadata |
| `/api/runs/{run_id}` | GET | Get details for specific run |
| `/api/runs/current` | GET | Get currently selected run |
| `/api/runs/select` | POST | Switch to viewing a different run |
| `/api/runs/{run_id}/resume` | POST | Resume simulation from checkpoint |

### 3. Frontend Components

**RunSelectorPanel.tsx:**
- Table of runs with columns: Date, Duration, Agents, Events, Status
- Click row to select and view that run
- "Resume" button for runs with checkpoints
- Current run highlighted
- Auto-refresh when new runs appear

**Header Integration:**
- Show current run ID/name
- Dropdown to quickly switch runs
- Visual indicator: "Live" vs "Historical"

---

## Files Affected

### Backend
- `src/dashboard/server.py` - Add run management endpoints
- `src/dashboard/run_manager.py` - NEW: Run discovery and metadata extraction
- `src/dashboard/parser.py` - Support switching jsonl source
- `src/dashboard/process_manager.py` - Add resume from checkpoint

### Frontend
- `dashboard-v2/src/components/panels/RunSelectorPanel.tsx` - NEW
- `dashboard-v2/src/components/layout/Header.tsx` - Add run selector dropdown
- `dashboard-v2/src/api/queries.ts` - Add run API hooks
- `dashboard-v2/src/types/api.ts` - Add RunInfo types
- `dashboard-v2/src/stores/runs.ts` - NEW: Run selection state

---

## Implementation

### Phase 1: Backend Run Discovery

1. Create `run_manager.py`:
   ```python
   class RunManager:
       def __init__(self, logs_dir: Path = Path("logs")):
           self.logs_dir = logs_dir

       def list_runs(self) -> list[RunInfo]:
           """Scan logs directory and extract run metadata."""
           runs = []
           for run_dir in self.logs_dir.glob("run_*"):
               events_file = run_dir / "events.jsonl"
               if events_file.exists():
                   runs.append(self._extract_metadata(run_dir))
           return sorted(runs, key=lambda r: r.start_time, reverse=True)

       def _extract_metadata(self, run_dir: Path) -> RunInfo:
           """Extract metadata from events.jsonl."""
           # Read first and last events for timing
           # Count events, extract agent IDs
           # Check for checkpoint.json
   ```

2. Add endpoints to `server.py`:
   - Integrate RunManager
   - Add `/api/runs` endpoints

### Phase 2: Run Selection

1. Make parser support dynamic jsonl path:
   ```python
   class JSONLParser:
       def set_source(self, jsonl_path: Path):
           """Switch to a different events file."""
           self.jsonl_path = jsonl_path
           self._reset_state()
   ```

2. Add `/api/runs/select` endpoint:
   - Update parser source
   - Clear cached state
   - Broadcast to WebSocket clients

### Phase 3: Resume from Checkpoint

1. Extend `process_manager.py`:
   ```python
   def resume_from_checkpoint(self, run_id: str) -> dict:
       """Start simulation resuming from run's checkpoint."""
       checkpoint_path = self.logs_dir / run_id / "checkpoint.json"
       # Start with --resume flag
   ```

2. Add `/api/runs/{run_id}/resume` endpoint

### Phase 4: Frontend UI

1. Create `RunSelectorPanel.tsx`:
   - Fetch runs list
   - Display in sortable table
   - Handle selection and resume actions

2. Update Header:
   - Add run selector dropdown
   - Show live/historical indicator

3. Add state management:
   - Track current run
   - Handle run switching

---

## Acceptance Criteria

- [ ] `GET /api/runs` returns list of all runs with metadata
- [ ] Clicking a run in the selector switches dashboard to view it
- [ ] "Resume" button starts simulation from checkpoint
- [ ] Header shows current run and live/historical status
- [ ] Dashboard remains viewable after simulation ends
- [ ] Switching runs clears and reloads all data
- [ ] `npm run build` passes

---

## Verification

```bash
# Backend tests
pytest tests/unit/test_run_manager.py -v

# Manual testing
make dash                    # Start dashboard-only
# Verify runs list appears
# Click different run - data should switch
# Click Resume on run with checkpoint - simulation should start
```

---

## Notes

### Run Status Detection

- **running**: `latest` symlink points here AND subprocess active
- **completed**: Has final "simulation_end" event
- **stopped**: No end event, no active subprocess

### Checkpoint Location

Checkpoints are saved to `logs/{run_id}/checkpoint.json` (configurable).
Resume loads this and continues the simulation.

### WebSocket Behavior

When switching runs:
1. Broadcast "run_changed" event to all clients
2. Clients clear local state and refetch
3. If switching to live run, resume streaming

---

## References

- Plan #163: Checkpoint Completeness
- Plan #221: Dashboard Simulation Control
- `src/simulation/checkpoint.py` - Existing checkpoint logic
