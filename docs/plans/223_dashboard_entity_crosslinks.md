# Plan 223: Dashboard Entity Cross-Linking

**Status:** ✅ Complete
**Priority:** Medium
**Blocked By:** None
**Blocks:** Dashboard usability

---

## Problem Statement

Dashboard-v2 has entity detail modals (AgentDetailModal, ArtifactDetailModal) but clicking on entity IDs throughout the dashboard doesn't navigate to their details. Users must manually search or scroll through lists to find related entities.

**Missing cross-links:**
1. AgentDetailModal "Artifacts Owned" - artifact IDs not clickable
2. AgentDetailModal "Recent Actions" - target_id not clickable
3. ArtifactDetailModal "Creator" - not clickable
4. ArtifactDetailModal "Recent Invocations" - invoker_id not clickable
5. ArtifactDetailModal "Ownership History" - from_id/to_id not clickable
6. ActivityPanel - agent_id/target_id/artifact_id not clickable
7. NetworkPanel/TemporalNetworkPanel - nodes not clickable
8. CapitalFlowPanel - source/target not clickable
9. DependencyGraphPanel - nodes not clickable

---

## Solution

Create a reusable `EntityLink` component that renders clickable entity IDs. When clicked, it uses the selection store to open the appropriate detail modal.

---

## Files to Modify

| File | Changes |
|------|---------|
| `dashboard-v2/src/components/shared/EntityLink.tsx` | NEW - reusable clickable entity link |
| `dashboard-v2/src/components/panels/AgentDetailModal.tsx` | Use EntityLink for artifact IDs and target_ids |
| `dashboard-v2/src/components/panels/ArtifactDetailModal.tsx` | Use EntityLink for creator, invoker, ownership history |
| `dashboard-v2/src/components/panels/ActivityPanel.tsx` | Use EntityLink for agent_id, target_id, artifact_id |
| `dashboard-v2/src/components/panels/NetworkPanel.tsx` | Add click handler for nodes |
| `dashboard-v2/src/components/panels/TemporalNetworkPanel.tsx` | Add click handler for nodes |
| `dashboard-v2/src/components/panels/CapitalFlowPanel.tsx` | Use EntityLink for source/target |
| `dashboard-v2/src/components/panels/DependencyGraphPanel.tsx` | Add click handler for nodes |

---

## Implementation Details

### EntityLink Component

```tsx
interface EntityLinkProps {
  id: string
  type: 'agent' | 'artifact' | 'auto'  // 'auto' detects from ID pattern
  className?: string
}

export function EntityLink({ id, type = 'auto', className }: EntityLinkProps) {
  const setSelectedAgent = useSelectionStore((s) => s.setSelectedAgent)
  const setSelectedArtifact = useSelectionStore((s) => s.setSelectedArtifact)

  const entityType = type === 'auto' ? detectEntityType(id) : type

  const handleClick = () => {
    if (entityType === 'agent') {
      setSelectedAgent(id)
    } else {
      setSelectedArtifact(id)
    }
  }

  return (
    <button onClick={handleClick} className={`hover:underline text-[var(--accent-primary)] ${className}`}>
      {id}
    </button>
  )
}

function detectEntityType(id: string): 'agent' | 'artifact' {
  // Agents typically have simple names: alpha, beta, gamma
  // Artifacts have prefixes: genesis_*, {agent}_artifact_*, contract_*
  if (id.includes('_')) return 'artifact'
  return 'agent'
}
```

### Network Click Handlers

For vis-network panels, add click event handler:

```tsx
network.on('click', (params) => {
  if (params.nodes.length > 0) {
    const nodeId = params.nodes[0]
    const node = nodesDataSet.current.get(nodeId)
    if (node.node_type === 'agent') {
      setSelectedAgent(nodeId)
    } else {
      setSelectedArtifact(nodeId)
    }
  }
})
```

---

## Acceptance Criteria

1. Clicking artifact ID in AgentDetailModal opens ArtifactDetailModal
2. Clicking agent ID in ArtifactDetailModal opens AgentDetailModal
3. Clicking entities in ActivityPanel opens appropriate modal
4. Clicking nodes in NetworkPanel/TemporalNetworkPanel opens appropriate modal
5. Clicking entities in CapitalFlowPanel opens appropriate modal
6. Clicking nodes in DependencyGraphPanel opens ArtifactDetailModal
7. EntityLink styling indicates clickability (color, hover underline)

---

## References

- `dashboard-v2/src/stores/selection.ts` - existing selection store
- `dashboard-v2/src/components/shared/SearchDialog.tsx` - reference for navigation pattern
