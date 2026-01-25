import { useState } from 'react'
import { useActivity } from '../../api/queries'
import { Panel } from '../shared/Panel'
import { EntityLink } from '../shared/EntityLink'
import { safeFixed, formatTime } from '../../utils/format'
import type { ActivityItem } from '../../types/api'

const ACTIVITY_TYPES = [
  { value: '', label: 'All' },
  { value: 'transfer', label: 'Transfers' },
  { value: 'spawn', label: 'Spawns' },
  { value: 'action', label: 'Actions' },
  { value: 'creation', label: 'Creations' },
  { value: 'mint', label: 'Minting' },
]

function ActivityIcon({ type }: { type: string }) {
  const icons: Record<string, string> = {
    transfer: '↔',
    spawn: '★',
    action: '⚡',
    creation: '+',
    mint: '◈',
    default: '•',
  }
  return <span className="text-lg">{icons[type] || icons.default}</span>
}

function ActivityCard({ item }: { item: ActivityItem }) {
  return (
    <div className="flex gap-3 p-3 bg-[var(--bg-primary)] rounded hover:bg-[var(--bg-tertiary)] transition-colors">
      <div className="flex-shrink-0 w-8 h-8 flex items-center justify-center bg-[var(--bg-tertiary)] rounded">
        <ActivityIcon type={item.activity_type} />
      </div>
      <div className="flex-1 min-w-0">
        <div className="flex items-center gap-2 mb-1">
          <span className="text-xs text-[var(--text-secondary)]">{formatTime(item.timestamp)}</span>
          <span className="text-xs px-1.5 py-0.5 bg-[var(--bg-tertiary)] rounded">
            {item.activity_type}
          </span>
          {item.agent_id && (
            <EntityLink id={item.agent_id} type="agent" className="text-xs truncate" />
          )}
        </div>
        <p className="text-sm truncate">{item.description}</p>
        {item.amount != null && (
          <p className="text-xs text-[var(--text-secondary)] mt-1">
            Amount: {safeFixed(item.amount, 2)} scrip
          </p>
        )}
      </div>
    </div>
  )
}

export function ActivityPanel() {
  const [typeFilter, setTypeFilter] = useState('')
  const [limit, setLimit] = useState(20)

  const { data, isLoading, error } = useActivity({
    limit,
    types: typeFilter || undefined,
  })

  return (
    <Panel title="Activity Feed" badge={data?.total_count}>
      {/* Filters */}
      <div className="flex gap-2 mb-4 flex-wrap">
        {ACTIVITY_TYPES.map((type) => (
          <button
            key={type.value}
            onClick={() => setTypeFilter(type.value)}
            className={`px-2 py-1 text-xs rounded transition-colors ${
              typeFilter === type.value
                ? 'bg-[var(--accent-primary)] text-white'
                : 'bg-[var(--bg-tertiary)] hover:bg-[var(--accent-primary)]/20'
            }`}
          >
            {type.label}
          </button>
        ))}
      </div>

      {isLoading && (
        <div className="animate-pulse space-y-2">
          {[...Array(5)].map((_, i) => (
            <div key={i} className="h-16 bg-[var(--bg-tertiary)] rounded" />
          ))}
        </div>
      )}

      {error && (
        <p className="text-[var(--accent-danger)] text-sm">
          Failed to load activity: {error.message}
        </p>
      )}

      {data && (
        <>
          <div className="space-y-2 max-h-96 overflow-y-auto">
            {(data.items ?? []).map((item, i) => (
              <ActivityCard key={`${item.tick}-${i}`} item={item} />
            ))}
            {(data.items?.length ?? 0) === 0 && (
              <p className="text-sm text-[var(--text-secondary)] text-center py-4">
                No activity yet
              </p>
            )}
          </div>

          {data.total_count > limit && (
            <button
              onClick={() => setLimit((l) => l + 20)}
              className="mt-3 w-full py-2 text-sm text-[var(--accent-primary)] hover:bg-[var(--bg-tertiary)] rounded"
            >
              Load more ({data.total_count - limit} remaining)
            </button>
          )}
        </>
      )}
    </Panel>
  )
}
