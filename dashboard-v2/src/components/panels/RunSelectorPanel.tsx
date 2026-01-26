/**
 * Run Selector Panel (Plan #224)
 *
 * Displays a list of available simulation runs and allows:
 * - Viewing historical runs
 * - Resuming runs with checkpoints
 * - Seeing current run status
 */

import { useState } from 'react'
import { Panel } from '../shared/Panel'
import { useRuns } from '../../api/queries'
import { useRunsStore } from '../../stores/runs'
import type { RunInfo } from '../../types/api'
import clsx from 'clsx'

function formatDuration(seconds: number): string {
  if (seconds < 60) return `${Math.round(seconds)}s`
  if (seconds < 3600) return `${Math.round(seconds / 60)}m`
  const hours = Math.floor(seconds / 3600)
  const mins = Math.round((seconds % 3600) / 60)
  return `${hours}h ${mins}m`
}

function formatDate(isoString: string | null): string {
  if (!isoString) return '-'
  try {
    const date = new Date(isoString)
    return date.toLocaleString(undefined, {
      month: 'short',
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit',
    })
  } catch {
    return isoString
  }
}

function StatusBadge({ status }: { status: RunInfo['status'] }) {
  const colors = {
    running: 'bg-green-500/20 text-green-400 border-green-500/30',
    completed: 'bg-blue-500/20 text-blue-400 border-blue-500/30',
    stopped: 'bg-gray-500/20 text-gray-400 border-gray-500/30',
  }

  return (
    <span
      className={clsx(
        'px-2 py-0.5 text-xs font-medium rounded border',
        colors[status]
      )}
    >
      {status}
    </span>
  )
}

interface RunRowProps {
  run: RunInfo
  isSelected: boolean
  onSelect: () => void
  onResume: () => void
}

function RunRow({ run, isSelected, onSelect, onResume }: RunRowProps) {
  return (
    <tr
      className={clsx(
        'cursor-pointer hover:bg-[var(--bg-tertiary)] transition-colors',
        isSelected && 'bg-[var(--accent-primary)]/10'
      )}
      onClick={onSelect}
    >
      <td className="px-3 py-2 text-sm">
        <div className="flex items-center gap-2">
          {isSelected && (
            <span className="w-2 h-2 bg-[var(--accent-primary)] rounded-full" />
          )}
          <span className="font-mono text-xs">{run.run_id}</span>
        </div>
      </td>
      <td className="px-3 py-2 text-sm text-[var(--text-secondary)]">
        {formatDate(run.start_time)}
      </td>
      <td className="px-3 py-2 text-sm text-[var(--text-secondary)]">
        {formatDuration(run.duration_seconds)}
      </td>
      <td className="px-3 py-2 text-sm text-[var(--text-secondary)]">
        {run.agent_ids.length}
      </td>
      <td className="px-3 py-2 text-sm text-[var(--text-secondary)]">
        {run.event_count.toLocaleString()}
      </td>
      <td className="px-3 py-2">
        <StatusBadge status={run.status} />
      </td>
      <td className="px-3 py-2">
        {run.has_checkpoint && run.status !== 'running' && (
          <button
            onClick={(e) => {
              e.stopPropagation()
              onResume()
            }}
            className="px-2 py-1 text-xs bg-[var(--accent-primary)]/20 text-[var(--accent-primary)] rounded hover:bg-[var(--accent-primary)]/30"
          >
            Resume
          </button>
        )}
      </td>
    </tr>
  )
}

export function RunSelectorPanel() {
  const { data, isLoading, error, refetch } = useRuns()
  const { currentRunId, selectRun, resumeRun, isLive } = useRunsStore()
  const [isSelecting, setIsSelecting] = useState(false)
  const [resumeError, setResumeError] = useState<string | null>(null)

  const handleSelectRun = async (runId: string) => {
    setIsSelecting(true)
    setResumeError(null)
    try {
      const result = await selectRun(runId)
      if (!result.success) {
        console.error('Failed to select run:', result.message)
      }
      // Refetch data after switching
      refetch()
    } finally {
      setIsSelecting(false)
    }
  }

  const handleResumeRun = async (runId: string) => {
    setResumeError(null)
    try {
      const result = await resumeRun(runId)
      if (!result.success) {
        setResumeError(result.error || 'Failed to resume run')
      }
      refetch()
    } catch (err) {
      setResumeError(err instanceof Error ? err.message : 'Unknown error')
    }
  }

  const runs = data?.runs || []

  return (
    <Panel
      title="Simulation Runs"
      badge={runs.length}
      collapsible
      defaultCollapsed={false}
    >
      {/* Live/Historical indicator */}
      <div className="mb-4 flex items-center gap-4">
        <div className="flex items-center gap-2">
          <span
            className={clsx(
              'w-2 h-2 rounded-full',
              isLive ? 'bg-green-500 animate-pulse' : 'bg-gray-500'
            )}
          />
          <span className="text-sm text-[var(--text-secondary)]">
            {isLive ? 'Live' : 'Viewing Historical'}
          </span>
        </div>
        {currentRunId && (
          <span className="text-xs text-[var(--text-secondary)]">
            Current: <span className="font-mono">{currentRunId}</span>
          </span>
        )}
      </div>

      {resumeError && (
        <div className="mb-4 p-2 bg-red-500/10 border border-red-500/30 rounded text-sm text-red-400">
          {resumeError}
        </div>
      )}

      {isLoading && (
        <div className="flex items-center justify-center py-8">
          <div className="animate-spin w-6 h-6 border-2 border-[var(--accent-primary)] border-t-transparent rounded-full" />
        </div>
      )}

      {error && (
        <p className="text-[var(--accent-danger)] text-sm">
          Failed to load runs: {error.message}
        </p>
      )}

      {!isLoading && runs.length === 0 && (
        <p className="text-sm text-[var(--text-secondary)] text-center py-4">
          No simulation runs found
        </p>
      )}

      {runs.length > 0 && (
        <div className="overflow-x-auto">
          <table className="w-full">
            <thead>
              <tr className="text-left text-xs text-[var(--text-secondary)] border-b border-[var(--border-color)]">
                <th className="px-3 py-2 font-medium">Run ID</th>
                <th className="px-3 py-2 font-medium">Started</th>
                <th className="px-3 py-2 font-medium">Duration</th>
                <th className="px-3 py-2 font-medium">Agents</th>
                <th className="px-3 py-2 font-medium">Events</th>
                <th className="px-3 py-2 font-medium">Status</th>
                <th className="px-3 py-2 font-medium">Actions</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-[var(--border-color)]">
              {runs.map((run) => (
                <RunRow
                  key={run.run_id}
                  run={run}
                  isSelected={run.run_id === currentRunId}
                  onSelect={() => handleSelectRun(run.run_id)}
                  onResume={() => handleResumeRun(run.run_id)}
                />
              ))}
            </tbody>
          </table>
        </div>
      )}

      {isSelecting && (
        <div className="absolute inset-0 bg-black/50 flex items-center justify-center">
          <div className="animate-spin w-8 h-8 border-2 border-[var(--accent-primary)] border-t-transparent rounded-full" />
        </div>
      )}
    </Panel>
  )
}
