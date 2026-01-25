import { useState } from 'react'
import { useEvents } from '../../api/queries'
import { Panel } from '../shared/Panel'
import { Pagination } from '../shared/Pagination'
import type { RawEvent } from '../../types/api'

const EVENT_TYPE_OPTIONS = [
  { value: '', label: 'All Events' },
  { value: 'agent_action', label: 'Agent Actions' },
  { value: 'transfer', label: 'Transfers' },
  { value: 'artifact_created', label: 'Artifact Created' },
  { value: 'mint_submission', label: 'Mint Submissions' },
  { value: 'llm_call', label: 'LLM Calls' },
  { value: 'error', label: 'Errors' },
]

function EventTypeTag({ type }: { type: string }) {
  const colors: Record<string, string> = {
    agent_action: 'bg-blue-500/20 text-blue-400',
    transfer: 'bg-green-500/20 text-green-400',
    artifact_created: 'bg-purple-500/20 text-purple-400',
    mint_submission: 'bg-yellow-500/20 text-yellow-400',
    llm_call: 'bg-cyan-500/20 text-cyan-400',
    error: 'bg-red-500/20 text-red-400',
    default: 'bg-[var(--bg-tertiary)] text-[var(--text-secondary)]',
  }

  return (
    <span className={`px-2 py-0.5 rounded text-xs ${colors[type] || colors.default}`}>
      {type}
    </span>
  )
}

function EventRow({ event }: { event: RawEvent }) {
  const [expanded, setExpanded] = useState(false)
  const tick = event.data.tick as number | undefined
  const agentId = event.data.agent_id as string | undefined

  return (
    <div className="border-b border-[var(--border-color)]">
      <div
        className="flex items-center gap-3 py-2 cursor-pointer hover:bg-[var(--bg-tertiary)]"
        onClick={() => setExpanded(!expanded)}
      >
        <span className="text-xs text-[var(--text-secondary)] w-12">
          {tick != null ? `T${tick}` : '--'}
        </span>
        <EventTypeTag type={event.event_type} />
        <span className="flex-1 text-sm truncate">
          {agentId && (
            <span className="font-mono text-[var(--accent-primary)]">{agentId}</span>
          )}
        </span>
        <span className="text-xs text-[var(--text-secondary)]">
          {new Date(event.timestamp).toLocaleTimeString()}
        </span>
        <span className="text-[var(--text-secondary)]">{expanded ? '▼' : '▶'}</span>
      </div>

      {expanded && (
        <div className="pb-2 pl-12">
          <pre className="p-2 bg-[var(--bg-primary)] rounded text-xs font-mono overflow-x-auto max-h-48">
            {JSON.stringify(event.data, null, 2)}
          </pre>
        </div>
      )}
    </div>
  )
}

export function EventsPanel() {
  const [page, setPage] = useState(0)
  const [eventType, setEventType] = useState('')
  const limit = 25

  const { data, isLoading, error } = useEvents({
    limit,
    offset: page * limit,
    eventTypes: eventType || undefined,
  })

  const handleExport = () => {
    if (!data?.events) return
    const json = JSON.stringify(data.events, null, 2)
    const blob = new Blob([json], { type: 'application/json' })
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = 'events.json'
    a.click()
    URL.revokeObjectURL(url)
  }

  return (
    <Panel title="Events" badge={data?.total} onExport={handleExport}>
      {/* Type filter */}
      <div className="mb-4">
        <select
          value={eventType}
          onChange={(e) => {
            setEventType(e.target.value)
            setPage(0)
          }}
          className="w-full px-3 py-2 text-sm bg-[var(--bg-primary)] border border-[var(--border-color)] rounded focus:outline-none focus:ring-1 focus:ring-[var(--accent-primary)]"
        >
          {EVENT_TYPE_OPTIONS.map((opt) => (
            <option key={opt.value} value={opt.value}>
              {opt.label}
            </option>
          ))}
        </select>
      </div>

      {isLoading && (
        <div className="animate-pulse space-y-2">
          {[...Array(5)].map((_, i) => (
            <div key={i} className="h-8 bg-[var(--bg-tertiary)] rounded" />
          ))}
        </div>
      )}

      {error && (
        <p className="text-[var(--accent-danger)] text-sm">
          Failed to load events: {error.message}
        </p>
      )}

      {data && (
        <>
          <div className="max-h-96 overflow-y-auto">
            {data.events.map((event, i) => (
              <EventRow key={`${event.timestamp}-${i}`} event={event} />
            ))}
            {data.events.length === 0 && (
              <p className="text-sm text-[var(--text-secondary)] text-center py-4">
                No events yet
              </p>
            )}
          </div>

          {data.total > limit && (
            <div className="mt-4">
              <Pagination
                page={page}
                total={data.total}
                perPage={limit}
                onPageChange={setPage}
              />
            </div>
          )}
        </>
      )}
    </Panel>
  )
}
