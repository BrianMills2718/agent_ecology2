# Plan #221: Dashboard Simulation Control

**Status:** complete
**Created:** 2025-01-25
**Feature:** dashboard

## Problem

When running the dashboard in "dashboard-only" mode (viewing historical data), there's no way to start a new simulation from the UI. Users must manually run CLI commands.

## Solution

Add start/stop controls to the dashboard that spawn a simulation subprocess.

### Backend

1. **`src/dashboard/process_manager.py`** - New file for subprocess lifecycle
   - Singleton pattern for managing one subprocess at a time
   - `start()` - Spawn `python run.py --dashboard --no-browser ...`
   - `stop()` - SIGTERM for graceful shutdown, SIGKILL as fallback
   - `get_status()` - Check if subprocess alive

2. **`src/dashboard/server.py`** - New endpoints
   - `POST /api/simulation/start` - Start with config params (duration, agents, budget, model)
   - `POST /api/simulation/stop` - Stop gracefully
   - Extended `GET /api/simulation/status` to include subprocess info

### Frontend

1. **`SimulationConfigForm.tsx`** - Modal with simple config form
   - Duration (seconds)
   - Agents (count or all)
   - Budget ($)
   - Model (dropdown)
   - Rate limit delay (seconds)

2. **Header updates**
   - "Start New" button when no simulation running
   - "Stop" button when subprocess running
   - Status badges (Running/View Only)

## Files Changed

- `src/dashboard/process_manager.py` (NEW)
- `src/dashboard/server.py`
- `dashboard-v2/src/components/panels/SimulationConfigForm.tsx` (NEW)
- `dashboard-v2/src/components/layout/Header.tsx`
- `dashboard-v2/src/api/queries.ts`
- `dashboard-v2/src/types/api.ts`
- `dashboard-v2/src/components/shared/Modal.tsx`

## Verification

1. Run `make dash` (dashboard-only mode)
2. Click "Start New" → fill form → click "Start"
3. Verify events appear in dashboard
4. Click "Stop" → verify graceful shutdown
