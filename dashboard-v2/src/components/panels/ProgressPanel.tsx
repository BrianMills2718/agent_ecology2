import { useQuery } from '@tanstack/react-query'
import { safeFixed } from '../../utils/format'

interface ProgressData {
  current_tick: number
  elapsed_seconds: number
  api_budget_spent: number
  api_budget_limit: number
  status: string
  events_per_second: number
}

async function fetchProgress(): Promise<ProgressData> {
  const response = await fetch('/api/progress')
  if (!response.ok) throw new Error('Failed to fetch progress')
  return response.json()
}

export function ProgressPanel() {
  const { data, isLoading, error } = useQuery({
    queryKey: ['progress'],
    queryFn: fetchProgress,
    refetchInterval: 2000, // Refresh every 2 seconds
  })

  if (isLoading) {
    return (
      <div className="bg-[var(--bg-secondary)] border border-[var(--border-color)] rounded-lg p-4">
        <div className="animate-pulse flex space-x-4">
          <div className="flex-1 space-y-2">
            <div className="h-4 bg-[var(--bg-tertiary)] rounded w-1/4"></div>
            <div className="h-2 bg-[var(--bg-tertiary)] rounded"></div>
          </div>
        </div>
      </div>
    )
  }

  if (error) {
    return (
      <div className="bg-[var(--bg-secondary)] border border-[var(--border-color)] rounded-lg p-4">
        <p className="text-[var(--accent-danger)] text-sm">
          Failed to load progress: {error.message}
        </p>
      </div>
    )
  }

  if (!data) return null

  const budgetPercent = data.api_budget_limit > 0
    ? (data.api_budget_spent / data.api_budget_limit) * 100
    : 0

  const formatTime = (seconds: number) => {
    const mins = Math.floor(seconds / 60)
    const secs = Math.floor(seconds % 60)
    return `${mins}:${secs.toString().padStart(2, '0')}`
  }

  return (
    <div className="bg-[var(--bg-secondary)] border border-[var(--border-color)] rounded-lg p-4">
      <div className="flex items-center justify-between mb-3">
        <div className="flex items-center gap-4">
          <div>
            <span className="text-[var(--text-secondary)] text-xs">Events</span>
            <p className="text-2xl font-bold text-[var(--accent-primary)]">
              {data.current_tick}
            </p>
          </div>
          <div>
            <span className="text-[var(--text-secondary)] text-xs">Elapsed</span>
            <p className="text-lg font-medium">
              {formatTime(data.elapsed_seconds)}
            </p>
          </div>
          <div>
            <span className="text-[var(--text-secondary)] text-xs">Events/sec</span>
            <p className="text-lg font-medium">
              {safeFixed(data.events_per_second, 1)}
            </p>
          </div>
        </div>

        <div className={`px-3 py-1 rounded text-sm font-medium ${
          data.status === 'running'
            ? 'bg-[var(--accent-secondary)]/20 text-[var(--accent-secondary)]'
            : data.status === 'paused'
            ? 'bg-[var(--accent-warning)]/20 text-[var(--accent-warning)]'
            : 'bg-[var(--text-secondary)]/20 text-[var(--text-secondary)]'
        }`}>
          {data.status}
        </div>
      </div>

      {/* Budget bar */}
      <div>
        <div className="flex justify-between text-xs text-[var(--text-secondary)] mb-1">
          <span>API Budget</span>
          <span>
            ${safeFixed(data.api_budget_spent, 2)} / ${safeFixed(data.api_budget_limit, 2)}
            {' '}({safeFixed(budgetPercent, 1)}%)
          </span>
        </div>
        <div className="h-2 bg-[var(--bg-primary)] rounded-full overflow-hidden">
          <div
            className={`h-full transition-all ${
              budgetPercent > 90
                ? 'bg-[var(--accent-danger)]'
                : budgetPercent > 70
                ? 'bg-[var(--accent-warning)]'
                : 'bg-[var(--accent-primary)]'
            }`}
            style={{ width: `${Math.min(budgetPercent, 100)}%` }}
          />
        </div>
      </div>
    </div>
  )
}
