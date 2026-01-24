import { useWebSocketStore } from '../../stores/websocket'

export function Header() {
  const { status, wsLatency } = useWebSocketStore()

  return (
    <header className="bg-[var(--bg-secondary)] border-b border-[var(--border-color)] px-4 py-3 flex items-center justify-between">
      <h1 className="text-xl font-semibold text-[var(--accent-primary)]">
        Agent Ecology Dashboard
        <span className="ml-2 text-xs text-[var(--text-secondary)] font-normal">v2</span>
      </h1>

      <div className="flex items-center gap-6">
        {/* Search placeholder */}
        <input
          type="text"
          placeholder="Search agents, artifacts..."
          className="bg-[var(--bg-primary)] border border-[var(--border-color)] rounded px-3 py-1.5 text-sm w-64 focus:outline-none focus:border-[var(--accent-primary)]"
        />

        {/* Connection status */}
        <div className="flex items-center gap-2 text-sm">
          <span
            className={`w-2 h-2 rounded-full ${
              status === 'connected' ? 'bg-[var(--accent-secondary)]' : 'bg-[var(--accent-danger)]'
            }`}
          />
          <span className="text-[var(--text-secondary)]">
            {status === 'connected' ? 'Connected' : 'Disconnected'}
          </span>
          {wsLatency !== null && (
            <span className="text-[var(--text-secondary)]">
              ({wsLatency}ms)
            </span>
          )}
        </div>
      </div>
    </header>
  )
}
