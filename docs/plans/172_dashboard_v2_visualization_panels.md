# Plan #172: Dashboard v2 Visualization Panels

**Status:** ✅ Complete

**Priority:** High
**Blocked By:** None
**Blocks:** Emergence observability

---

## Problem

Dashboard v2 is missing two key visualization panels that exist in v1 and have full backend support:

1. **Capital Flow Sankey** - Shows where scrip flows between agents/artifacts. Critical for observing economic structure emergence.

2. **Dependency Graph** - Shows artifact dependency relationships with Lindy scores. Identifies emergent "standard library" artifacts.

Both have:
- Backend models defined in `src/dashboard/models.py`
- API endpoints in `src/dashboard/server.py`
- Data generation in `src/dashboard/parser.py`

But no v2 React components.

## Solution

Add two new panels to dashboard v2:

### 1. CapitalFlowPanel

- Sankey diagram showing scrip flow between principals
- Uses recharts or d3-sankey for visualization
- Time range filter (last N minutes)
- Shows total flow volume

API: `GET /api/capital-flow?time_min=&time_max=`

### 2. DependencyGraphPanel

- vis-network graph (like NetworkPanel)
- Nodes = artifacts, colored by type (genesis, agent-created, contracts)
- Edges = dependency relationships
- Node size = Lindy score (age × usage)
- Metrics sidebar showing graph statistics

API: `GET /api/artifacts/dependency-graph`

## Files Affected

- dashboard-v2/src/components/panels/CapitalFlowPanel.tsx (create)
- dashboard-v2/src/components/panels/DependencyGraphPanel.tsx (create)
- dashboard-v2/src/api/queries.ts (modify)
- dashboard-v2/src/types/api.ts (modify)
- dashboard-v2/src/App.tsx (modify)

## Implementation

### Phase 1: Types and Queries

1. Add TypeScript types for CapitalFlowData, DependencyGraphData
2. Add TanStack Query hooks for both endpoints

### Phase 2: CapitalFlowPanel

1. Create panel component
2. Use recharts Sankey or simple flow visualization
3. Add time range controls
4. Handle loading/error states

### Phase 3: DependencyGraphPanel

1. Create panel component
2. Wrap vis-network (similar to NetworkPanel)
3. Color nodes by artifact type
4. Size nodes by Lindy score
5. Show metrics in sidebar

### Phase 4: Integration

1. Add panels to App.tsx layout
2. Build and test
3. Verify with real simulation data

## Verification

```bash
# Build succeeds
cd dashboard-v2 && npm run build

# Manual testing
make dash-run DURATION=60
# Verify both panels render and update
```

## Notes

- Sankey libraries: recharts has basic sankey, d3-sankey is more powerful
- Consider using same vis-network patterns as NetworkPanel for consistency
- Lindy score = age_days × unique_invokers (higher = more "standard")
