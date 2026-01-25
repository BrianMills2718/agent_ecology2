import { useState } from 'react'
import { useWebSocketStore } from '../../stores/websocket'
import { useSearchStore } from '../../stores/search'
import { useProgress, useSimulationStatus, pauseSimulation, resumeSimulation, stopSimulation } from '../../api/queries'
import { SimulationConfigForm } from '../panels/SimulationConfigForm'

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
  const { data: progress, refetch: refetchProgress } = useProgress()
  const { data: simStatus, refetch: refetchStatus } = useSimulationStatus()
  const [isToggling, setIsToggling] = useState(false)
  const [isStopping, setIsStopping] = useState(false)
  const [showConfigForm, setShowConfigForm] = useState(false)

  const handleTogglePause = async () => {
    if (!simStatus?.has_runner || isToggling) return
    setIsToggling(true)
    try {
      if (simStatus.paused) {
        await resumeSimulation()
      } else {
        await pauseSimulation()
      }
    } catch (e) {
      console.error('Failed to toggle pause:', e)
    } finally {
      setIsToggling(false)
    }
  }

  const handleStop = async () => {
    if (isStopping) return
    setIsStopping(true)
    try {
      await stopSimulation()
      refetchStatus()
    } catch (e) {
      console.error('Failed to stop simulation:', e)
    } finally {
      setIsStopping(false)
    }
  }

  const handleStarted = () => {
    // Refetch status after starting
    refetchStatus()
    refetchProgress()
  }

  // Determine current mode
  const hasInProcessRunner = simStatus?.has_runner === true
  const hasSubprocess = simStatus?.has_subprocess === true
  const canStart = !hasInProcessRunner && !hasSubprocess

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

        {/* Simulation controls */}
        {hasInProcessRunner && (
          <div className="flex items-center gap-2">
            <button
              onClick={handleTogglePause}
              disabled={isToggling}
              className={`px-3 py-1 text-sm rounded transition-colors ${
                simStatus?.paused
                  ? 'bg-[var(--accent-secondary)] text-white hover:bg-[var(--accent-secondary)]/80'
                  : 'bg-[var(--accent-warning)] text-black hover:bg-[var(--accent-warning)]/80'
              } disabled:opacity-50`}
            >
              {isToggling ? '...' : simStatus?.paused ? '▶ Resume' : '⏸ Pause'}
            </button>
            <span className={`text-xs px-2 py-0.5 rounded ${
              simStatus?.paused
                ? 'bg-[var(--accent-warning)]/20 text-[var(--accent-warning)]'
                : 'bg-[var(--accent-secondary)]/20 text-[var(--accent-secondary)]'
            }`}>
              {simStatus?.paused ? 'Paused' : 'Running'}
            </span>
          </div>
        )}

        {/* Subprocess running - show stop button */}
        {hasSubprocess && (
          <div className="flex items-center gap-2">
            <button
              onClick={handleStop}
              disabled={isStopping}
              className="px-3 py-1 text-sm rounded bg-[var(--accent-danger)] text-white hover:bg-[var(--accent-danger)]/80 transition-colors disabled:opacity-50"
            >
              {isStopping ? 'Stopping...' : '⏹ Stop'}
            </button>
            <span className="text-xs px-2 py-0.5 rounded bg-[var(--accent-secondary)]/20 text-[var(--accent-secondary)]">
              Running (PID: {simStatus?.subprocess_pid})
            </span>
          </div>
        )}

        {/* No simulation - show start button */}
        {canStart && (
          <div className="flex items-center gap-2">
            <button
              onClick={() => setShowConfigForm(true)}
              className="px-3 py-1 text-sm rounded bg-[var(--accent-secondary)] text-white hover:bg-[var(--accent-secondary)]/80 transition-colors"
            >
              ▶ Start New
            </button>
            <span className="text-xs px-2 py-0.5 rounded bg-[var(--text-tertiary)]/20 text-[var(--text-tertiary)]">
              View Only
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

      {/* Simulation config modal */}
      <SimulationConfigForm
        isOpen={showConfigForm}
        onClose={() => setShowConfigForm(false)}
        onStarted={handleStarted}
      />
    </header>
  )
}
