# Plan #110: Dashboard Overhaul for Autonomous Mode & Emergence Observability

**Status:** 📋 Planned
**Priority:** High
**Blocked By:** None
**Blocks:** Simulation observability, emergence detection

---

## Problem Statement

The dashboard was built around tick-based execution but the simulation now runs in autonomous mode. This causes multiple failures:

| Issue | Root Cause |
|-------|------------|
| "Tick: 0 / 100" always | No `tick` events emitted in autonomous mode |
| "0.00 ticks/sec" | Calculated from `current_tick / elapsed` where tick=0 |
| API Budget $0.0000 | `thinking_cost` never populated in events |
| "undefined: undefined" in events | Duplicate action events with different schemas |
| Agent compute/disk 0% | Usage tracked via tick events only |
| Network graph nearly empty | Genesis interactions filtered out |
| Resource charts broken | Data populated from tick events |

Additionally, key observability features for emergence detection are missing or incomplete.

---

## Scope

This plan consolidates three concerns:

1. **Phase 1: Autonomous Mode Fixes** - Fix all broken dashboard elements
2. **Phase 2: Temporal Network** - Port Plan #107 work (genesis interactions, temporal playback)
3. **Phase 3: Emergence Observability** - New metrics for capital structure, coordination, specialization

---

## Phase 1: Autonomous Mode Fixes

### 1.1 Progress Display

**Current:** Shows tick counter (always 0)
**Target:** Show elapsed time, iteration count, actions/minute

| File | Change |
|------|--------|
| `src/dashboard/parser.py` | Track `iteration_count` from action events |
| `src/dashboard/models.py` | Add `iterations`, `actions_per_minute` to SimulationProgress |
| `src/dashboard/static/js/panels/progress.js` | Display time-based metrics instead of ticks |

### 1.2 API Budget Tracking

**Current:** `thinking_cost: 0` in all events
**Target:** Track actual API costs from LLM calls

| File | Change |
|------|--------|
| `src/simulation/runner.py` | Log actual API costs in thinking events |
| `src/world/simulation_engine.py` | Pass cost data through to logger |
| `src/dashboard/parser.py` | Accumulate `api_cost_spent` from thinking events |

### 1.3 Event Feed "undefined: undefined" Fix

**Current:** Two action event formats - one with `intent.principal_id`, one with `agent_id`
**Target:** Handle both formats in frontend

| File | Change |
|------|--------|
| `src/dashboard/static/js/panels/events.js` | Check both `intent.principal_id` and `data.agent_id` |

Alternative: Fix backend to emit single consistent format.

### 1.4 Resource Usage Tracking

**Current:** Usage updated via tick events only
**Target:** Track from action/thinking events

| File | Change |
|------|--------|
| `src/dashboard/parser.py` | Update `llm_tokens_used` from thinking events |
| `src/dashboard/parser.py` | Update `disk_used` from write_artifact events |

### 1.5 Chart Data Without Ticks

**Current:** Chart data keyed by tick number
**Target:** Key by timestamp or iteration

| File | Change |
|------|--------|
| `src/dashboard/parser.py` | Use timestamp-bucketed data for charts |
| `src/dashboard/models.py` | Add `TimeSeriesDataPoint` with timestamp |
| `src/dashboard/static/js/panels/*.js` | Update chart rendering for time-based data |

---

## Phase 2: Temporal Network Visualization

Port from `temporal-network-viz` branch (Plan #107).

### 2.1 Include Genesis Interactions

**Current:** `parser.py:374` filters out genesis artifact invocations
**Target:** Show all interactions including genesis

| File | Change |
|------|--------|
| `src/dashboard/parser.py` | Remove genesis filtering in `get_network_graph_data()` |
| `src/dashboard/parser.py` | Add `get_temporal_network_data()` method |

### 2.2 New Models

```python
class ArtifactNode(BaseModel):
    id: str
    label: str
    artifact_type: Literal["agent", "genesis", "contract", "data", "executable"]
    owner_id: str | None = None
    invocation_count: int = 0
    status: Literal["active", "low_resources", "frozen"] = "active"

class ArtifactEdge(BaseModel):
    from_id: str
    to_id: str
    edge_type: Literal["invocation", "ownership", "dependency", "transfer"]
    timestamp: str
    weight: int = 1

class TemporalNetworkData(BaseModel):
    nodes: list[ArtifactNode]
    edges: list[ArtifactEdge]
    time_range: tuple[str, str]
    activity_by_time: dict[str, int]  # timestamp -> interaction count
```

### 2.3 Temporal Playback UI

| File | Change |
|------|--------|
| `src/dashboard/static/js/panels/temporal-network.js` | Create new panel |
| `src/dashboard/static/index.html` | Add temporal network container |
| `src/dashboard/server.py` | Add `/api/temporal-network` endpoint |

Features:
- Time slider for temporal navigation
- Play/pause for automatic playback
- Activity heatmap below graph
- Node colors by artifact type
- Edge colors by interaction type

---

## Phase 3: Emergence Observability

### 3.1 Agent Pair Interactions

**New Feature:** Select two agents → see all their interactions

| File | Change |
|------|--------|
| `src/dashboard/parser.py` | Add `get_pairwise_interactions(agent1, agent2)` |
| `src/dashboard/server.py` | Add `/api/agents/interactions?from=X&to=Y` |
| `src/dashboard/static/js/panels/network.js` | Edge click → show interaction detail modal |

### 3.2 Emergence Metrics

New computed metrics for detecting emergent organization:

| Metric | Formula | Meaning |
|--------|---------|---------|
| `coordination_density` | interactions / (agents × (agents-1)) | How connected is the network |
| `specialization_index` | std_dev(action_type_distribution) | How differentiated are agents |
| `reuse_ratio` | artifacts_used_by_others / total_artifacts | Infrastructure building |
| `genesis_independence` | non_genesis_ops / total_ops | Ecosystem maturity |
| `capital_depth` | max(dependency_chain_length) | Capital structure emergence |
| `coalition_count` | count(interaction_clusters) | Emergent groups |

| File | Change |
|------|--------|
| `src/dashboard/kpis.py` | Add emergence metric calculations |
| `src/dashboard/models.py` | Add `EmergenceMetrics` model |
| `src/dashboard/server.py` | Add `/api/emergence` endpoint |
| `src/dashboard/static/js/panels/emergence.js` | New emergence dashboard panel |

### 3.3 Standard Library Detection

Identify artifacts with high Lindy scores (age × unique_invokers):

| File | Change |
|------|--------|
| `src/dashboard/dependency_graph.py` | Already calculates Lindy scores |
| `src/dashboard/server.py` | Add `/api/artifacts/standards` endpoint |
| `src/dashboard/static/js/panels/dependency-graph.js` | Highlight high-Lindy nodes |

### 3.4 Capital Flow Sankey Diagram

Visualize scrip flowing between agents over time:

| File | Change |
|------|--------|
| `src/dashboard/parser.py` | Add `get_capital_flow_data(time_window)` |
| `src/dashboard/server.py` | Add `/api/charts/capital-flow` endpoint |
| `src/dashboard/static/js/panels/capital-flow.js` | D3 Sankey diagram |

---

## Files Affected

### Phase 1 (Autonomous Fixes)
- `src/dashboard/parser.py` (modify)
- `src/dashboard/models.py` (modify)
- `src/dashboard/static/js/panels/progress.js` (modify)
- `src/dashboard/static/js/panels/events.js` (modify)
- `src/dashboard/static/js/panels/agents.js` (modify)
- `src/simulation/runner.py` (modify - API cost logging)
- `src/world/simulation_engine.py` (modify - cost tracking)

### Phase 2 (Temporal Network)
- `src/dashboard/parser.py` (modify)
- `src/dashboard/models.py` (modify)
- `src/dashboard/server.py` (modify)
- `src/dashboard/static/js/panels/temporal-network.js` (create)
- `src/dashboard/static/js/panels/network.js` (modify)
- `src/dashboard/static/index.html` (modify)
- `src/dashboard/static/css/dashboard.css` (modify)

### Phase 3 (Emergence Observability)
- `src/dashboard/kpis.py` (modify)
- `src/dashboard/parser.py` (modify)
- `src/dashboard/models.py` (modify)
- `src/dashboard/server.py` (modify)
- `src/dashboard/static/js/panels/emergence.js` (create)
- `src/dashboard/static/js/panels/capital-flow.js` (create)
- `src/dashboard/static/index.html` (modify)

### Documentation
- `docs/architecture/current/supporting_systems.md` (modify)
- `src/dashboard/CLAUDE.md` (modify)

---

## Required Tests

### Phase 1 Tests

| Test File | Test Function |
|-----------|---------------|
| `tests/unit/test_dashboard_parser.py` | `test_progress_without_tick_events` |
| `tests/unit/test_dashboard_parser.py` | `test_api_cost_accumulation` |
| `tests/unit/test_dashboard_parser.py` | `test_resource_tracking_from_actions` |
| `tests/integration/test_dashboard_api.py` | `test_progress_endpoint_autonomous_mode` |

### Phase 2 Tests

| Test File | Test Function |
|-----------|---------------|
| `tests/unit/test_dashboard_parser.py` | `test_temporal_network_includes_genesis` |
| `tests/unit/test_dashboard_parser.py` | `test_temporal_network_time_filtering` |
| `tests/integration/test_dashboard_api.py` | `test_temporal_network_endpoint` |

### Phase 3 Tests

| Test File | Test Function |
|-----------|---------------|
| `tests/unit/test_kpis.py` | `test_coordination_density` |
| `tests/unit/test_kpis.py` | `test_specialization_index` |
| `tests/unit/test_kpis.py` | `test_reuse_ratio` |
| `tests/unit/test_dashboard_parser.py` | `test_pairwise_interactions` |
| `tests/integration/test_dashboard_api.py` | `test_emergence_endpoint` |

---

## Implementation Order

1. **Phase 1.3** - Event feed fix (quick win)
2. **Phase 1.1** - Progress display (visible improvement)
3. **Phase 1.4** - Resource tracking (enables agent status)
4. **Phase 2.1** - Include genesis interactions (unblocks network graph)
5. **Phase 3.1** - Agent pair interactions (core UX improvement)
6. **Phase 1.2** - API budget tracking (requires backend changes)
7. **Phase 2.3** - Temporal playback (complex UI)
8. **Phase 3.2** - Emergence metrics (analytical value)
9. **Phase 3.4** - Capital flow sankey (nice to have)
10. **Phase 1.5** - Chart data refactor (breaking change, do last)

---

## Verification

### Phase 1
- [ ] Progress shows elapsed time, not ticks
- [ ] API budget updates during simulation
- [ ] Event feed shows agent:action, not undefined:undefined
- [ ] Agent compute/disk percentages update
- [ ] Charts show data over time

### Phase 2
- [ ] Network graph shows genesis interactions
- [ ] Time slider filters interactions by time
- [ ] Activity heatmap shows interaction intensity

### Phase 3
- [ ] Can click edge to see interaction details
- [ ] Emergence metrics endpoint returns data
- [ ] High-Lindy artifacts highlighted in dependency graph

---

## Notes

### Relation to Other Plans

- **Plan #102** (Tick Removal): This plan implements the dashboard portion of tick removal
- **Plan #107** (Temporal Network): This plan supersedes #107 by including it in Phase 2
- **Plan #64** (Dependency Graph): Already complete, Phase 3 builds on it
- **Plan #76** (Simulation Metrics): Already complete, this extends KPIs

### Philosophy Alignment

All visualizations are **observability, not prescription**:
- We don't define "good" emergence patterns
- We don't reward deep capital chains
- We just make structure visible

If agents discover that coordination and composition are valuable, we'll see it emerge. If they don't, that's also valid data.

### Breaking Changes

Phase 1.5 (time-based charts) may require frontend changes in consumers. Consider backward compatibility wrapper or versioned API.
