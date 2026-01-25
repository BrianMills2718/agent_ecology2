# Plan #174: Dashboard Tab-Based Layout Refactor

**Status:** ✅ Complete

**Priority:** High
**Blocked By:** None
**Blocks:** Future dashboard features

---

## Problem

The dashboard v2 has grown to 14 panel components crammed into a single scrolling view:
- Visual clutter makes it hard to focus
- Large files (200+ lines) are difficult to maintain and edit
- Adding new features compounds the problem
- No clear organization by user intent

## Solution

Refactor to a tab-based layout that organizes panels by purpose:

### Tab Structure

| Tab | Panels | Purpose |
|-----|--------|---------|
| **Overview** | ProgressPanel, KPI summary, Milestones | Quick health check |
| **Agents** | AgentsPanel (with inline details) | Agent-focused view |
| **Artifacts** | ArtifactsPanel, DependencyGraphPanel | Artifact-focused view |
| **Economy** | CapitalFlowPanel, ChartsPanel, GenesisPanel | Resource flows |
| **Activity** | EventsPanel, ActivityPanel, ThinkingPanel | Event streams |
| **Network** | NetworkPanel (full-width) | Interaction visualization |

### Component Architecture

```
src/components/
├── layout/
│   ├── Header.tsx          # Keep as-is
│   ├── TabNavigation.tsx   # NEW: Tab bar component
│   └── TabContainer.tsx    # NEW: Tab content wrapper
├── tabs/
│   ├── OverviewTab.tsx     # NEW: Composes overview panels
│   ├── AgentsTab.tsx       # NEW: Agent-focused view
│   ├── ArtifactsTab.tsx    # NEW: Artifact-focused view
│   ├── EconomyTab.tsx      # NEW: Economy panels
│   ├── ActivityTab.tsx     # NEW: Event streams
│   └── NetworkTab.tsx      # NEW: Full network view
├── panels/                 # Keep existing, refactor as needed
└── shared/
    └── ...
```

### URL-Based Tab State

Use URL hash for tab state so links can deep-link to specific tabs:
- `/#overview` (default)
- `/#agents`
- `/#artifacts`
- etc.

## Files Affected

- dashboard-v2/src/App.tsx (modify)
- dashboard-v2/src/components/layout/TabNavigation.tsx (create)
- dashboard-v2/src/components/layout/TabContainer.tsx (create)
- dashboard-v2/src/components/tabs/OverviewTab.tsx (create)
- dashboard-v2/src/components/tabs/AgentsTab.tsx (create)
- dashboard-v2/src/components/tabs/ArtifactsTab.tsx (create)
- dashboard-v2/src/components/tabs/EconomyTab.tsx (create)
- dashboard-v2/src/components/tabs/ActivityTab.tsx (create)
- dashboard-v2/src/components/tabs/NetworkTab.tsx (create)
- dashboard-v2/src/components/layout/MainGrid.tsx (delete or repurpose)
- dashboard-v2/src/hooks/useTabNavigation.ts (create)
- dashboard-v2/src/components/tabs/index.ts (create)

## Implementation

### Phase 1: Tab Infrastructure

1. Create `useTabNavigation` hook:
   - Read/write URL hash
   - Provide current tab and setTab function
   - Handle browser back/forward

2. Create `TabNavigation` component:
   - Horizontal tab bar
   - Highlight active tab
   - Keyboard accessible

3. Create `TabContainer` component:
   - Renders active tab content
   - Lazy loads tab content (optional)

### Phase 2: Create Tab Components

Create each tab component that composes existing panels:

1. **OverviewTab**: ProgressPanel + condensed EmergencePanel metrics + MilestonesBadge
2. **AgentsTab**: AgentsPanel (expand to show details inline instead of modal)
3. **ArtifactsTab**: ArtifactsPanel + DependencyGraphPanel side-by-side
4. **EconomyTab**: CapitalFlowPanel + ChartsPanel + GenesisPanel
5. **ActivityTab**: EventsPanel + ActivityPanel + ThinkingPanel
6. **NetworkTab**: NetworkPanel full-width with controls

### Phase 3: Integration

1. Update App.tsx to use tab layout
2. Remove/repurpose MainGrid.tsx
3. Update AlertToastContainer positioning

### Phase 4: Polish

1. Add keyboard shortcuts (1-6 for tabs)
2. Persist last-used tab in localStorage
3. Add tab badges for important counts (e.g., error count on Activity tab)

## Verification

```bash
# Build succeeds
cd dashboard-v2 && npm run build

# Manual testing
make dash-run DURATION=60
# Verify all tabs render correctly
# Verify URL hash changes with tabs
# Verify browser back/forward works
# Verify no regressions in panel functionality
```

## Notes

- Keep panel components mostly unchanged - tabs just compose them
- Consider lazy loading tabs for performance
- AlertToastContainer should float above all tabs
- EmergencePanel metrics may need to be extracted into reusable components
- AgentsTab could show details inline instead of modal for better UX
