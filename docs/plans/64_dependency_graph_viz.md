# Gap 64: Artifact Dependency Graph Visualization

**Status:** 📋 Planned
**Priority:** Medium
**Blocked By:** #63 (Artifact Dependencies) ✅ Complete
**Blocks:** -

---

## Gap

**Current:** Artifact dependencies (`depends_on`) are stored but not visualized. Dashboard shows network graph for agent interactions but not artifact composition.

**Target:** Interactive dependency graph showing artifact capital structure - which artifacts compose which, depth of composition chains, usage patterns.

---

## Motivation

From the project philosophy: we want to observe emergent capital structure without prescribing it. The artifact dependency graph is the clearest proof of Misesian capital accumulation:

- **Flat graph:** Agents only use genesis artifacts → no capital formation
- **Deep graph:** Artifacts build on artifacts → capital chains forming
- **Clusters:** Groups of related artifacts → specialization emerging

This is pure observability - we're not steering toward any particular structure, just making it visible.

---

## Design

### Data Source

Plan #63 added `depends_on: list[str]` to artifacts. We need to:
1. Extract dependency edges from artifact data
2. Build graph structure for visualization
3. Compute metrics (depth, fanout, usage count)

### API Additions

```python
# New endpoint in server.py
@app.get("/api/artifacts/dependency-graph")
async def get_dependency_graph() -> DependencyGraphData:
    """Return artifact dependency graph for visualization."""
    ...

@dataclass
class DependencyGraphData:
    nodes: list[ArtifactNode]      # Artifacts as nodes
    edges: list[DependencyEdge]    # depends_on relationships
    metrics: GraphMetrics          # Computed statistics
```

### Graph Metrics

| Metric | Formula | What It Shows |
|--------|---------|---------------|
| `max_depth` | Longest path from any root | Capital chain length |
| `avg_fanout` | Mean children per node | Composition breadth |
| `genesis_dependency_ratio` | Genesis deps / total deps | How much builds on genesis vs. agent-created |
| `orphan_count` | Artifacts with no dependents | Unused/dead-end artifacts |
| `lindy_score` | age × unique_invokers | Emergent "standard library" candidates |

### Visualization

Frontend addition to dashboard:
- Node-link diagram (D3.js or similar)
- Nodes = artifacts, sized by usage count
- Edges = depends_on relationships
- Color coding: genesis (gold), agent-created (blue), contracts (green)
- Click node → artifact detail modal
- Filter by: depth, owner, type

### Example Output

```
genesis_ledger ←── my_accounting_lib ←── firm_treasury ←── payroll_contract
                                      ↖
                                        budget_tracker
```

This shows a 4-level capital chain: genesis → library → composed artifact → contract.

---

## Plan

### Phase 1: Backend API

1. Add `DependencyGraphData` model to `models.py`
2. Add graph extraction to `parser.py`:
   - Parse `depends_on` from artifact data
   - Build adjacency list
   - Compute metrics
3. Add `/api/artifacts/dependency-graph` endpoint to `server.py`
4. Add unit tests for graph construction

### Phase 2: Frontend Visualization

1. Add D3.js dependency to dashboard
2. Create `dependency-graph.js` component
3. Add graph container to dashboard layout
4. Implement:
   - Force-directed layout
   - Node sizing by usage
   - Edge arrows showing direction
   - Hover tooltips
   - Click-to-detail
5. Add filter controls (depth, type, owner)

### Phase 3: Lindy Effect Heatmap

1. Calculate lindy scores (age × unique invokers)
2. Add heatmap view as alternative to graph
3. Sortable table: artifact, age, invokers, lindy score

---

## Required Tests

### Unit Tests
```
tests/unit/test_dependency_graph.py::test_empty_graph
tests/unit/test_dependency_graph.py::test_single_dependency
tests/unit/test_dependency_graph.py::test_chain_depth_calculation
tests/unit/test_dependency_graph.py::test_genesis_dependency_ratio
tests/unit/test_dependency_graph.py::test_lindy_score_calculation
```

### Integration Tests
```
tests/integration/test_dashboard_dependency_graph.py::test_api_returns_valid_graph
tests/integration/test_dashboard_dependency_graph.py::test_graph_includes_genesis
tests/integration/test_dashboard_dependency_graph.py::test_metrics_computed
```

---

## Out of Scope

- **Real-time updates** - Graph refreshes on poll, not WebSocket push
- **Graph editing** - View only, no creating dependencies from UI
- **Historical graphs** - Current state only, not "graph at tick N"
- **Optimization suggestions** - Pure observation, no "you should depend on X"

---

## Verification

- [ ] Tests pass: `python scripts/check_plan_tests.py --plan 64`
- [ ] API returns valid graph data
- [ ] Frontend renders graph
- [ ] Metrics computed correctly
- [ ] Docs updated

---

## Notes

### Philosophy Alignment

This visualization is **observability, not optimization**:
- We don't define what "good" capital structure looks like
- We don't reward deep chains or penalize flat ones
- We just make the structure visible

If agents discover that composing artifacts is valuable, we'll see deep graphs emerge. If they don't, we'll see flat graphs. Both are valid outcomes that tell us something about the simulation.

### Lindy Effect

The "Lindy score" (age × usage) identifies artifacts that have stood the test of time. High-Lindy artifacts are candidates for emergent standards - not because we define them as standards, but because agents keep using them.

---

## Files to Modify

| File | Change |
|------|--------|
| `src/dashboard/models.py` | Add `DependencyGraphData`, `ArtifactNode`, `DependencyEdge`, `GraphMetrics` |
| `src/dashboard/parser.py` | Add `get_dependency_graph()` method |
| `src/dashboard/server.py` | Add `/api/artifacts/dependency-graph` endpoint |
| `src/dashboard/static/js/dependency-graph.js` | New: D3.js visualization |
| `src/dashboard/static/index.html` | Add graph container |
| `docs/architecture/current/supporting_systems.md` | Document new endpoint |
