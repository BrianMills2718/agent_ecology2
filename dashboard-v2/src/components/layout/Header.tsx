import { useWebSocketStore } from '../../stores/websocket'
import { useSearchStore } from '../../stores/search'
import { useProgress } from '../../api/queries'

function formatDuration(seconds: number): string {
  const h = Math.floor(seconds / 3600)
  const m = Math.floor((seconds % 3600) / 60)
  const s = Math.floor(seconds % 60)
  if (h > 0) return `${h}h ${m}m ${s}s`
  if (m > 0) return `${m}m ${s}s`
  return `${s}s`
}

export function Header() {
  const { status, wsLatency } = useWebSocketStore()
  const openSearch = useSearchStore((state) => state.open)
  const { data: progress } = useProgress()

  return (
    <header className="bg-[var(--bg-secondary)] border-b border-[var(--border-color)] px-4 py-3 flex items-center justify-between">
      <div className="flex items-center gap-6">
        <h1 className="text-xl font-semibold text-[var(--accent-primary)]">
          Agent Ecology Dashboard
          <span className="ml-2 text-xs text-[var(--text-secondary)] font-normal">v2</span>
        </h1>

        {/* Runtime info - always visible */}
        {progress && (
          <div className="flex items-center gap-4 text-sm text-[var(--text-secondary)]">
            <span>
              <span className="text-[var(--text-tertiary)]">Event:</span>{' '}
              <span className="font-mono">{progress.current_tick}</span>
            </span>
            <span>
              <span className="text-[var(--text-tertiary)]">Runtime:</span>{' '}
              <span className="font-mono">{formatDuration(progress.elapsed_seconds)}</span>
            </span>
          </div>
        )}
      </div>

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
