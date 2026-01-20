# Plan #107: Temporal Network Visualization

**Status:** ✅ Complete
**Priority:** High
**Blocked By:** None
**Blocks:** Dashboard usability for observing agent interactions

---

## Problem Statement

The current network visualization in the dashboard has two critical issues:

1. **No edges displayed**: Genesis artifact invocations are filtered out (line 374 in parser.py), but in typical runs, agents primarily invoke genesis artifacts. Result: empty network graph.

2. **Missing artifact-centric view**: The current implementation only shows agent-to-agent interactions. There's no visualization of:
   - Agent ↔ genesis artifact interactions
   - Artifact dependencies
   - Ownership relationships
   - Temporal evolution of the network

A comprehensive temporal network visualization was implemented on the `temporal-network-viz` branch but never merged due to branch divergence (~14k lines of conflict with main).

---

## Solution

Port the temporal network visualization from `temporal-network-viz` branch to main. This provides:

- **Artifact-centric view**: All artifacts as nodes (agents, genesis, contracts, data)
- **Multiple edge types**: invocation, dependency, ownership, creation, transfer
- **Temporal playback**: Slider to see network evolution over time
- **Activity heatmap**: Visual intensity by time window
- **Genesis inclusion**: Shows agent ↔ genesis interactions (the majority of activity)

---

## Files to Create/Modify

### New Files

| File | Purpose |
|------|---------|
| `src/dashboard/static/js/panels/temporal-network.js` | Temporal network panel (~560 lines) |

### Modified Files

| File | Changes |
|------|---------|
| `src/dashboard/models.py` | Add `ArtifactNode`, `ArtifactEdge`, `TemporalNetworkData` models |
| `src/dashboard/parser.py` | Add `get_temporal_network_data()` method |
| `src/dashboard/server.py` | Add `/api/temporal-network` endpoint |
| `src/dashboard/static/index.html` | Add temporal network panel container |
| `src/dashboard/static/css/dashboard.css` | Temporal network styles |
| `src/dashboard/static/js/main.js` | Initialize temporal network panel |
| `docs/architecture/current/supporting_systems.md` | Document new visualization |

---

## Implementation Details

### Models (from branch)

```python
class ArtifactNode(BaseModel):
    id: str
    label: str
    artifact_type: Literal["agent", "genesis", "contract", "data", "unknown"]
    owner_id: str | None = None
    executable: bool = False
    invocation_count: int = 0
    created_at: str | None = None
    scrip: int = 0
    status: Literal["active", "low_resources", "frozen"] = "active"

class ArtifactEdge(BaseModel):
    from_id: str
    to_id: str
    edge_type: Literal["invocation", "ownership", "dependency", "creation", "transfer"]
    timestamp: str
    weight: int = 1
    details: str | None = None

class TemporalNetworkData(BaseModel):
    nodes: list[ArtifactNode]
    edges: list[ArtifactEdge]
    time_range: tuple[str, str]
    activity_by_time: dict[str, dict[str, int]]
    total_artifacts: int
    total_interactions: int
    time_bucket_seconds: int = 1
```

### Parser Method

The `get_temporal_network_data()` method will:
1. Build nodes from ALL artifacts (agents + genesis + created artifacts)
2. Build edges from invocation events (including genesis)
3. Add ownership edges (agent → artifact)
4. Add dependency edges (if artifact metadata includes dependencies)
5. Support time-range filtering
6. Group activity by time buckets for heatmap

### JavaScript Panel

The temporal network panel features:
- vis.js network visualization
- Node colors by artifact type (agent=green, genesis=blue, contract=purple, data=gray)
- Node shapes by type (agent=dot, genesis=star, contract=diamond, data=square)
- Edge colors by type (invocation=orange, ownership=purple, etc.)
- Time slider for temporal navigation
- Play/pause for temporal playback
- Activity heatmap below the graph

---

## Required Tests

```yaml
tests:
  unit:
    - test_temporal_network_models:
        file: tests/unit/test_dashboard_models.py
        cases:
          - test_artifact_node_types
          - test_artifact_edge_types
          - test_temporal_network_data_structure

    - test_temporal_network_parser:
        file: tests/unit/test_dashboard_parser.py
        cases:
          - test_get_temporal_network_includes_genesis
          - test_get_temporal_network_time_filtering
          - test_activity_bucketing

  integration:
    - test_temporal_network_api:
        file: tests/integration/test_dashboard_api.py
        cases:
          - test_temporal_network_endpoint_returns_data
          - test_temporal_network_includes_all_artifact_types
          - test_temporal_network_time_range_filter
```

---

## Acceptance Criteria

1. **Genesis artifacts visible**: Network shows agent ↔ genesis_* interactions
2. **All artifact types**: Nodes include agents, genesis, contracts, and data artifacts
3. **Multiple edge types**: Invocation, ownership, and dependency edges displayed
4. **Temporal controls**: Time slider allows navigating network state over time
5. **Activity heatmap**: Shows interaction intensity by time window
6. **No empty graphs**: Typical runs show meaningful network activity

---

## Implementation Approach

Since the branch has ~14k lines of divergence, cherry-picking won't work cleanly. Instead:

1. **Extract relevant code** from `temporal-network-viz` branch
2. **Manually port** to current main codebase
3. **Adapt to current API** (models may have changed)
4. **Test incrementally**

Key commits on branch to reference:
- `d74eb2c` - Initial panel implementation
- `8a95d75` - Fix to include genesis artifacts
- `8a169f0` - Time-based visualization

---

## Risks

| Risk | Mitigation |
|------|------------|
| Branch code may not apply cleanly | Manual adaptation, incremental testing |
| Performance with large networks | Implement node/edge limits, pagination |
| vis.js compatibility | Test with current vis.js version |

---

## Phase 2: Gource Export for Simulation Playback

Add ability to export simulation events as Gource-compatible logs, enabling polished animated visualizations of simulation evolution.

### Why Gource?

Gource provides a well-polished temporal visualization that shows:
- Entities (agents, artifacts) as nodes in a tree
- Interactions as "touches" from avatars
- Time-lapse animation of the entire simulation
- High-quality video export capability

### Implementation

#### New Files

| File | Purpose |
|------|---------|
| `src/dashboard/gource_export.py` | Convert JSONL events to Gource custom log format |

#### New Endpoint

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/export/gource` | GET | Download Gource-compatible log file |

#### Gource Custom Log Format

```
timestamp|username|type|filepath
```

Mapping from simulation events:
- `timestamp`: Unix timestamp from event
- `username`: `agent_id` (the actor)
- `type`: `A` (create artifact), `M` (invoke/modify), `D` (delete/transfer away)
- `filepath`: `artifacts/{artifact_id}` or `agents/{agent_id}` tree structure

#### Example Transformation

**Input (JSONL):**
```json
{"event_type": "action", "timestamp": "2026-01-19T10:00:00Z", "agent_id": "alpha", "action_type": "invoke", "artifact_id": "genesis_store"}
{"event_type": "action", "timestamp": "2026-01-19T10:00:05Z", "agent_id": "beta", "action_type": "write_artifact", "artifact_id": "beta_tool_1"}
{"event_type": "action", "timestamp": "2026-01-19T10:00:10Z", "agent_id": "alpha", "action_type": "invoke", "artifact_id": "beta_tool_1"}
```

**Output (Gource log):**
```
1737280800|alpha|M|genesis/store
1737280805|beta|A|artifacts/beta_tool_1
1737280810|alpha|M|artifacts/beta_tool_1
```

#### Dashboard UI

Add "Export for Gource" button to temporal network panel:
- Downloads `.gource.log` file
- Instructions tooltip: "Run: `gource --log-format custom simulation.gource.log`"

### Usage

```bash
# Download from dashboard
curl http://localhost:8080/api/export/gource > simulation.gource.log

# Generate visualization
gource --log-format custom -1280x720 simulation.gource.log

# Export to video
gource --log-format custom -1280x720 -o - simulation.gource.log | \
  ffmpeg -y -r 60 -f image2pipe -vcodec ppm -i - -vcodec libx264 simulation.mp4
```

### Acceptance Criteria (Phase 2)

1. **Export endpoint works**: `/api/export/gource` returns valid Gource log
2. **All event types mapped**: Invocations, creations, transfers represented
3. **Tree structure meaningful**: Genesis artifacts grouped, agent artifacts nested
4. **Gource renders correctly**: Exported log produces valid visualization
5. **Dashboard button**: UI provides easy export access

---

## References

- Branch: `temporal-network-viz` (local)
- Current network panel: `src/dashboard/static/js/panels/network.js`
- Dashboard docs: `docs/architecture/current/supporting_systems.md`
- Gource custom log format: https://github.com/acaudwell/Gource/wiki/Custom-Log-Format
