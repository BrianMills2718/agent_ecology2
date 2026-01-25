// Artifacts tab - Artifact list and dependency graph

import { ArtifactsPanel } from '../panels/ArtifactsPanel'
import { DependencyGraphPanel } from '../panels/DependencyGraphPanel'

export function ArtifactsTab() {
  return (
    <div className="p-4 space-y-4">
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
        <ArtifactsPanel />
        <DependencyGraphPanel />
      </div>
    </div>
  )
}
