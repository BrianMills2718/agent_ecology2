import { useEffect } from 'react'
import { useWebSocketStore } from '../../stores/websocket'
import { Panel } from '../shared/Panel'
import { ProgressPanel } from '../panels/ProgressPanel'

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
          <Panel title="Agents" badge={0}>
            <p className="text-[var(--text-secondary)] text-sm">
              Agent list will appear here
            </p>
          </Panel>
          <Panel title="Artifacts" badge={0}>
            <p className="text-[var(--text-secondary)] text-sm">
              Artifact list will appear here
            </p>
          </Panel>
        </div>

        {/* Center column - Visualizations */}
        <div className="space-y-4">
          <Panel title="Agent Interactions" collapsible defaultCollapsed>
            <div className="h-64 flex items-center justify-center text-[var(--text-secondary)]">
              Network graph will appear here
            </div>
          </Panel>
          <Panel title="Activity Feed">
            <p className="text-[var(--text-secondary)] text-sm">
              Activity feed will appear here
            </p>
          </Panel>
          <Panel title="Agent Thinking">
            <p className="text-[var(--text-secondary)] text-sm">
              Thinking history will appear here
            </p>
          </Panel>
        </div>

        {/* Right column - Metrics & Events */}
        <div className="space-y-4">
          <Panel title="Emergence Metrics" collapsible defaultCollapsed>
            <p className="text-[var(--text-secondary)] text-sm">
              Emergence metrics will appear here
            </p>
          </Panel>
          <Panel title="Genesis Activity">
            <p className="text-[var(--text-secondary)] text-sm">
              Genesis activity will appear here
            </p>
          </Panel>
          <Panel title="Events">
            <p className="text-[var(--text-secondary)] text-sm">
              Event log will appear here
            </p>
          </Panel>
        </div>
      </div>
    </main>
  )
}
