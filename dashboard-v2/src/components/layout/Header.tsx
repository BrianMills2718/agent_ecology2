import { useWebSocketStore } from '../../stores/websocket'
import { useSearchStore } from '../../stores/search'

export function Header() {
  const { status, wsLatency } = useWebSocketStore()
  const openSearch = useSearchStore((state) => state.open)

  return (
    <header className="bg-[var(--bg-secondary)] border-b border-[var(--border-color)] px-4 py-3 flex items-center justify-between">
      <h1 className="text-xl font-semibold text-[var(--accent-primary)]">
        Agent Ecology Dashboard
        <span className="ml-2 text-xs text-[var(--text-secondary)] font-normal">v2</span>
      </h1>

      <div className="flex items-center gap-6">
        {/* Search trigger */}
        <button
          onClick={openSearch}
          className="flex items-center gap-2 bg-[var(--bg-primary)] border border-[var(--border-color)] rounded px-3 py-1.5 text-sm w-64 text-left text-[var(--text-secondary)] hover:border-[var(--accent-primary)] transition-colors"
        >
          <svg
            className="w-4 h-4"
            fill="none"
            stroke="currentColor"
            viewBox="0 0 24 24"
          >
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              strokeWidth={2}
              d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z"
            />
          </svg>
          <span className="flex-1">Search...</span>
          <kbd className="px-1.5 py-0.5 text-xs bg-[var(--bg-secondary)] rounded border border-[var(--border-color)]">
            ⌘K
          </kbd>
        </button>

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
