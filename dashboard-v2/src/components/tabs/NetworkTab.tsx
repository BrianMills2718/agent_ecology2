// Network tab - Full-width network visualization with temporal playback

import { useState } from 'react'
import { NetworkPanel } from '../panels/NetworkPanel'
import { TemporalNetworkPanel } from '../panels/TemporalNetworkPanel'

type ViewMode = 'interactions' | 'temporal'

export function NetworkTab() {
  const [viewMode, setViewMode] = useState<ViewMode>('interactions')

  return (
    <div className="p-4">
      {/* View Mode Toggle */}
      <div className="flex gap-2 mb-4">
        <button
          onClick={() => setViewMode('interactions')}
          className={`px-3 py-1.5 text-sm rounded transition-colors ${
            viewMode === 'interactions'
              ? 'bg-[var(--accent-primary)] text-white'
              : 'bg-[var(--bg-tertiary)] text-[var(--text-secondary)] hover:bg-[var(--bg-secondary)]'
          }`}
        >
          Agent Interactions
        </button>
        <button
          onClick={() => setViewMode('temporal')}
          className={`px-3 py-1.5 text-sm rounded transition-colors ${
            viewMode === 'temporal'
              ? 'bg-[var(--accent-primary)] text-white'
              : 'bg-[var(--bg-tertiary)] text-[var(--text-secondary)] hover:bg-[var(--bg-secondary)]'
          }`}
        >
          Temporal Network
        </button>
      </div>

      {/* Network panels - show based on selected mode */}
      {viewMode === 'interactions' && <NetworkPanel fullHeight />}
      {viewMode === 'temporal' && <TemporalNetworkPanel fullHeight />}
    </div>
  )
}
