import { useEffect } from 'react'
import { useWebSocketStore } from '../../stores/websocket'
import { ProgressPanel } from '../panels/ProgressPanel'
import { AgentsPanel } from '../panels/AgentsPanel'
import { ArtifactsPanel } from '../panels/ArtifactsPanel'
import { ActivityPanel } from '../panels/ActivityPanel'
import { EventsPanel } from '../panels/EventsPanel'
import { GenesisPanel } from '../panels/GenesisPanel'
import { ThinkingPanel } from '../panels/ThinkingPanel'
import { NetworkPanel } from '../panels/NetworkPanel'
import { ChartsPanel } from '../panels/ChartsPanel'
import { EmergencePanel } from '../panels/EmergencePanel'

export function MainGrid() {
  const connect = useWebSocketStore((state) => state.connect)

  // Connect WebSocket on mount
  useEffect(() => {
    connect()
  }, [connect])

  return (
    <main className="flex-1 p-4 overflow-auto">
      {/* Progress section at top */}
      <ProgressPanel />

      {/* Three column layout */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-4 mt-4">
        {/* Left column - Agents & Artifacts */}
        <div className="space-y-4">
          <AgentsPanel />
          <ArtifactsPanel />
        </div>

        {/* Center column - Visualizations */}
        <div className="space-y-4">
          <NetworkPanel />
          <ChartsPanel />
          <ActivityPanel />
          <ThinkingPanel />
        </div>

        {/* Right column - Metrics & Events */}
        <div className="space-y-4">
          <EmergencePanel />
          <GenesisPanel />
          <EventsPanel />
        </div>
      </div>
    </main>
  )
}
