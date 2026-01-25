import { useState } from 'react'
import { useThinking } from '../../api/queries'
import { Panel } from '../shared/Panel'
import { safeFixed } from '../../utils/format'

interface ThinkingEntry {
  tick: number
  agent_id: string
  input_tokens: number
  output_tokens: number
  thinking_cost: number
  reasoning: string | null
}

export function ThinkingPanel() {
  const [agentFilter, setAgentFilter] = useState('')
  const [limit, setLimit] = useState(20)

  const { data, isLoading, error } = useThinking({
    agentId: agentFilter || undefined,
    limit,
  })

  const items = (data?.items || []) as ThinkingEntry[]

  return (
    <Panel title="Agent Thinking" badge={data?.total_count}>
      {/* Agent filter */}
      <div className="mb-4">
        <input
          type="text"
          placeholder="Filter by agent ID..."
          value={agentFilter}
          onChange={(e) => setAgentFilter(e.target.value)}
          className="w-full px-3 py-2 text-sm bg-[var(--bg-primary)] border border-[var(--border-color)] rounded focus:outline-none focus:ring-1 focus:ring-[var(--accent-primary)]"
        />
      </div>

      {isLoading && (
        <div className="animate-pulse space-y-2">
          {[...Array(5)].map((_, i) => (
            <div key={i} className="h-20 bg-[var(--bg-tertiary)] rounded" />
          ))}
        </div>
      )}

      {error && (
        <p className="text-[var(--accent-danger)] text-sm">
          Failed to load thinking: {error.message}
        </p>
      )}

      {data && (
        <>
          <div className="space-y-3 max-h-96 overflow-y-auto">
            {items.map((entry, i) => (
              <ThinkingCard key={`${entry.tick}-${entry.agent_id}-${i}`} entry={entry} />
            ))}
            {items.length === 0 && (
              <p className="text-sm text-[var(--text-secondary)] text-center py-4">
                No thinking recorded yet
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

function ThinkingCard({ entry }: { entry: ThinkingEntry }) {
  const [expanded, setExpanded] = useState(false)

  return (
    <div
      className="p-3 bg-[var(--bg-primary)] rounded cursor-pointer hover:bg-[var(--bg-tertiary)] transition-colors"
      onClick={() => setExpanded(!expanded)}
    >
      <div className="flex items-center justify-between mb-2">
        <div className="flex items-center gap-2">
          <span className="text-xs text-[var(--text-secondary)]">T{entry.tick}</span>
          <span className="font-mono text-xs text-[var(--accent-primary)]">
            {entry.agent_id}
          </span>
        </div>
        <span className="text-xs text-[var(--text-secondary)]">
          {entry.input_tokens ?? 0}in/{entry.output_tokens ?? 0}out • ${safeFixed(entry.thinking_cost, 4)}
        </span>
      </div>

      {entry.reasoning && (
        <p
          className={`text-sm text-[var(--text-secondary)] ${
            expanded ? '' : 'line-clamp-2'
          }`}
        >
          {entry.reasoning}
        </p>
      )}

      {entry.reasoning && entry.reasoning.length > 100 && (
        <button
          className="text-xs text-[var(--accent-primary)] mt-1"
          onClick={(e) => {
            e.stopPropagation()
            setExpanded(!expanded)
          }}
        >
          {expanded ? 'Show less' : 'Show more'}
        </button>
      )}
    </div>
  )
}
