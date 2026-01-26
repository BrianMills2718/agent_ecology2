import { useState } from 'react'
import { useLeaderboard } from '../../api/queries'
import { Panel } from '../shared/Panel'
import { EntityLink } from '../shared/EntityLink'
import { safeFixed } from '../../utils/format'

type LeaderboardCategory = 'scrip' | 'activity' | 'efficiency'

const CATEGORY_LABELS: Record<LeaderboardCategory, string> = {
  scrip: 'Scrip Balance',
  activity: 'Action Count',
  efficiency: 'Success Rate',
}

const CATEGORY_DESCRIPTIONS: Record<LeaderboardCategory, string> = {
  scrip: 'Agents ranked by current scrip balance',
  activity: 'Agents ranked by total actions taken',
  efficiency: 'Agents ranked by action success rate',
}

function formatValue(category: LeaderboardCategory, value: number): string {
  switch (category) {
    case 'scrip':
      return safeFixed(value, 0)
    case 'activity':
      return value.toString()
    case 'efficiency':
      return `${safeFixed(value * 100, 1)}%`
    default:
      return safeFixed(value, 2)
  }
}

function getRankBadgeColor(rank: number): string {
  switch (rank) {
    case 1:
      return 'bg-yellow-500/20 text-yellow-400 border-yellow-500/30'
    case 2:
      return 'bg-gray-400/20 text-gray-300 border-gray-400/30'
    case 3:
      return 'bg-amber-600/20 text-amber-500 border-amber-600/30'
    default:
      return 'bg-[var(--bg-tertiary)] text-[var(--text-secondary)] border-[var(--border-color)]'
  }
}

export function LeaderboardPanel() {
  const [category, setCategory] = useState<LeaderboardCategory>('scrip')
  const { data, isLoading, error } = useLeaderboard(category, 10)

  return (
    <Panel title="Leaderboard" collapsible>
      {/* Category Tabs */}
      <div className="flex gap-2 mb-4">
        {(Object.keys(CATEGORY_LABELS) as LeaderboardCategory[]).map((cat) => (
          <button
            key={cat}
            onClick={() => setCategory(cat)}
            className={`px-3 py-1.5 text-sm rounded transition-colors ${
              category === cat
                ? 'bg-[var(--accent-primary)] text-white'
                : 'bg-[var(--bg-tertiary)] hover:bg-[var(--accent-primary)]/20'
            }`}
          >
            {CATEGORY_LABELS[cat]}
          </button>
        ))}
      </div>

      {/* Description */}
      <p className="text-xs text-[var(--text-secondary)] mb-3">
        {CATEGORY_DESCRIPTIONS[category]}
      </p>

      {/* Loading State */}
      {isLoading && (
        <div className="h-48 flex items-center justify-center">
          <div className="animate-spin w-6 h-6 border-2 border-[var(--accent-primary)] border-t-transparent rounded-full" />
        </div>
      )}

      {/* Error State */}
      {error && (
        <p className="text-[var(--accent-danger)] text-sm">
          Failed to load leaderboard: {error.message}
        </p>
      )}

      {/* Leaderboard List */}
      {data && data.entries.length > 0 && (
        <div className="space-y-2">
          {data.entries.map((entry) => (
            <div
              key={entry.agent_id}
              className="flex items-center gap-3 p-2 bg-[var(--bg-primary)] rounded hover:bg-[var(--bg-tertiary)] transition-colors"
            >
              {/* Rank Badge */}
              <span
                className={`w-7 h-7 flex items-center justify-center rounded-full text-sm font-semibold border ${getRankBadgeColor(
                  entry.rank
                )}`}
              >
                {entry.rank}
              </span>

              {/* Agent Link */}
              <EntityLink
                id={entry.agent_id}
                type="agent"
                className="flex-1 text-sm font-medium"
              />

              {/* Value */}
              <span className="text-sm font-mono text-[var(--text-secondary)]">
                {formatValue(category, entry.value)}
              </span>
            </div>
          ))}
        </div>
      )}

      {/* Empty State */}
      {data && data.entries.length === 0 && (
        <p className="text-sm text-[var(--text-secondary)] text-center py-8">
          No agents in leaderboard yet
        </p>
      )}
    </Panel>
  )
}
