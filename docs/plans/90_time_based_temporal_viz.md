# Plan 90: Time-Based Temporal Network Visualization

**Status:** 🚧 In Progress
**Complexity:** Medium
**Prerequisites:** None
**Related:** Plan #83 (Remove Tick-Based Execution)

## Goal

Implement the temporal artifact network visualization using timestamps instead of ticks, aligning with the target architecture defined in Plan #83.

## Motivation

- Plan #83 is removing all tick-based code from the codebase
- New dashboard code should use time-based terminology from the start
- Avoids rework when Plan #83 is fully implemented
- Time-based visualization is more meaningful (ticks are artificial, time is real)

## Changes Required

### 1. Backend Models (`src/dashboard/models.py`)
- [x] `ArtifactEdge.tick` → `ArtifactEdge.timestamp` (ISO string)
- [x] `ArtifactNode.created_tick` → `ArtifactNode.created_at` (ISO string)
- [x] `TemporalNetworkData.tick_range` → `time_range` (start/end timestamps)
- [x] `TemporalNetworkData.activity_by_tick` → `activity_by_time` (time-window buckets)

### 2. Parser (`src/dashboard/parser.py`)
- [x] `get_temporal_network_data()` parameters: `time_min`, `time_max` (ISO strings)
- [x] Group activity by time windows (e.g., per-second buckets) instead of ticks
- [x] Return timestamps on edges instead of tick numbers

### 3. Server (`src/dashboard/server.py`)
- [x] Update `/api/temporal-network` to accept `time_min`, `time_max` query params
- [x] Return time-based data structure

### 4. Frontend (`src/dashboard/static/js/panels/temporal-network.js`)
- [x] Slider shows time (elapsed or wall-clock) instead of tick numbers
- [x] Heatmap columns represent time windows, not ticks
- [x] Labels show timestamps or elapsed time

### 5. CSS/HTML
- [x] Update labels from "Tick" to "Time"

## Testing

- Verify visualization works with existing event logs (which still have ticks)
- Verify time slider correctly filters by timestamp
- Verify heatmap shows meaningful time groupings

## Notes

- Event logs currently have both `tick` and `timestamp` fields
- We use the `timestamp` field, ignoring `tick`
- Time windows should be configurable (default: 1 second buckets)
