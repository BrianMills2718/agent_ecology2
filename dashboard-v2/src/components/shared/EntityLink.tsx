// Clickable entity link that opens the appropriate detail modal
// Uses the selection store to trigger modal display

import { useSelectionStore } from '../../stores/selection'

export type EntityType = 'agent' | 'artifact' | 'auto'

interface EntityLinkProps {
  id: string
  type?: EntityType
  className?: string
}

/**
 * Detect entity type from ID pattern.
 * - Agents: simple names like 'alpha', 'beta', 'gamma'
 * - Artifacts: contain underscore like 'genesis_ledger', 'alpha_tool_1'
 */
function detectEntityType(id: string): 'agent' | 'artifact' {
  // Genesis artifacts, contracts, and agent-created artifacts contain underscores
  if (id.includes('_')) return 'artifact'
  // Simple names are agents
  return 'agent'
}

/**
 * Clickable entity link that navigates to entity details.
 *
 * Usage:
 *   <EntityLink id="alpha" />  // Auto-detects as agent
 *   <EntityLink id="genesis_ledger" />  // Auto-detects as artifact
 *   <EntityLink id="custom_agent" type="agent" />  // Force type
 */
export function EntityLink({ id, type = 'auto', className = '' }: EntityLinkProps) {
  const setSelectedAgent = useSelectionStore((s) => s.setSelectedAgent)
  const setSelectedArtifact = useSelectionStore((s) => s.setSelectedArtifact)

  const entityType = type === 'auto' ? detectEntityType(id) : type

  const handleClick = (e: React.MouseEvent) => {
    e.preventDefault()
    e.stopPropagation()
    if (entityType === 'agent') {
      setSelectedAgent(id)
    } else {
      setSelectedArtifact(id)
    }
  }

  return (
    <button
      onClick={handleClick}
      className={`
        font-mono text-[var(--accent-primary)] hover:underline
        hover:text-[var(--accent-secondary)] transition-colors
        cursor-pointer bg-transparent border-none p-0
        ${className}
      `}
      title={`View ${entityType} details`}
    >
      {id}
    </button>
  )
}
