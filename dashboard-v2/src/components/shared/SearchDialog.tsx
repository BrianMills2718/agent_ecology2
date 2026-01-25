// Global search dialog (Cmd/Ctrl+K)

import { useState, useEffect, useRef, useCallback } from 'react'
import { useSearch } from '../../api/queries'
import { useSearchStore } from '../../stores/search'
import { useTabNavigation } from '../../hooks/useTabNavigation'
import type { AgentSummary, ArtifactInfo } from '../../types/api'

interface SearchDialogProps {
  onSelectAgent: (agentId: string) => void
  onSelectArtifact: (artifactId: string) => void
}

export function SearchDialog({ onSelectAgent, onSelectArtifact }: SearchDialogProps) {
  const { isOpen, close } = useSearchStore()
  const [query, setQuery] = useState('')
  const [selectedIndex, setSelectedIndex] = useState(0)
  const inputRef = useRef<HTMLInputElement>(null)
  const { setActiveTab } = useTabNavigation()

  const { data, isLoading } = useSearch(query)

  // Focus input when dialog opens
  useEffect(() => {
    if (isOpen && inputRef.current) {
      inputRef.current.focus()
      setQuery('')
      setSelectedIndex(0)
    }
  }, [isOpen])

  // Reset selection when results change
  useEffect(() => {
    setSelectedIndex(0)
  }, [data])

  const handleSelect = useCallback(() => {
    if (!data) return

    const agentCount = data.agents.length
    if (selectedIndex < agentCount) {
      const agent = data.agents[selectedIndex]
      onSelectAgent(agent.agent_id)
      setActiveTab('agents')
    } else {
      const artifact = data.artifacts[selectedIndex - agentCount]
      onSelectArtifact(artifact.artifact_id)
      setActiveTab('artifacts')
    }
    close()
  }, [data, selectedIndex, onSelectAgent, onSelectArtifact, setActiveTab, close])

  // Handle escape key
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (!isOpen) return

      if (e.key === 'Escape') {
        close()
      } else if (e.key === 'ArrowDown') {
        e.preventDefault()
        const maxIndex = (data?.agents.length ?? 0) + (data?.artifacts.length ?? 0) - 1
        setSelectedIndex((i) => Math.min(i + 1, maxIndex))
      } else if (e.key === 'ArrowUp') {
        e.preventDefault()
        setSelectedIndex((i) => Math.max(i - 1, 0))
      } else if (e.key === 'Enter') {
        e.preventDefault()
        handleSelect()
      }
    }
    document.addEventListener('keydown', handleKeyDown)
    return () => document.removeEventListener('keydown', handleKeyDown)
  }, [isOpen, data, selectedIndex, close, handleSelect])

  const handleClickAgent = (agent: AgentSummary) => {
    onSelectAgent(agent.agent_id)
    setActiveTab('agents')
    close()
  }

  const handleClickArtifact = (artifact: ArtifactInfo) => {
    onSelectArtifact(artifact.artifact_id)
    setActiveTab('artifacts')
    close()
  }

  if (!isOpen) return null

  const totalResults = (data?.agents.length ?? 0) + (data?.artifacts.length ?? 0)

  return (
    <div
      className="fixed inset-0 z-50 flex items-start justify-center pt-[15vh] bg-black/50"
      onClick={(e) => {
        if (e.target === e.currentTarget) close()
      }}
    >
      <div className="bg-[var(--bg-secondary)] rounded-lg shadow-xl w-full max-w-lg overflow-hidden">
        {/* Search input */}
        <div className="flex items-center gap-3 px-4 py-3 border-b border-[var(--border-color)]">
          <svg
            className="w-5 h-5 text-[var(--text-secondary)]"
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
          <input
            ref={inputRef}
            type="text"
            placeholder="Search agents and artifacts..."
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            className="flex-1 bg-transparent border-none outline-none text-sm placeholder:text-[var(--text-secondary)]"
          />
          <kbd className="px-1.5 py-0.5 text-xs bg-[var(--bg-primary)] rounded border border-[var(--border-color)] text-[var(--text-secondary)]">
            ESC
          </kbd>
        </div>

        {/* Results */}
        <div className="max-h-80 overflow-y-auto">
          {isLoading && query.length >= 1 && (
            <div className="px-4 py-8 text-center text-[var(--text-secondary)]">
              Searching...
            </div>
          )}

          {!isLoading && query.length >= 1 && totalResults === 0 && (
            <div className="px-4 py-8 text-center text-[var(--text-secondary)]">
              No results for "{query}"
            </div>
          )}

          {!isLoading && query.length < 1 && (
            <div className="px-4 py-8 text-center text-[var(--text-secondary)]">
              Type to search agents and artifacts
            </div>
          )}

          {data && data.agents.length > 0 && (
            <div className="px-2 py-2">
              <div className="px-2 py-1 text-xs font-medium text-[var(--text-secondary)] uppercase">
                Agents
              </div>
              {data.agents.map((agent, idx) => (
                <div
                  key={agent.agent_id}
                  className={`px-3 py-2 rounded cursor-pointer flex items-center justify-between ${
                    selectedIndex === idx
                      ? 'bg-[var(--accent-primary)]/20'
                      : 'hover:bg-[var(--bg-tertiary)]'
                  }`}
                  onClick={() => handleClickAgent(agent)}
                >
                  <div className="flex items-center gap-2">
                    <span className="font-mono text-[var(--accent-primary)]">
                      {agent.agent_id}
                    </span>
                    <StatusBadge status={agent.status} />
                  </div>
                  <span className="text-sm text-[var(--text-secondary)]">
                    {agent.scrip.toFixed(1)} scrip
                  </span>
                </div>
              ))}
            </div>
          )}

          {data && data.artifacts.length > 0 && (
            <div className="px-2 py-2">
              <div className="px-2 py-1 text-xs font-medium text-[var(--text-secondary)] uppercase">
                Artifacts
              </div>
              {data.artifacts.map((artifact, idx) => {
                const resultIdx = (data?.agents.length ?? 0) + idx
                return (
                  <div
                    key={artifact.artifact_id}
                    className={`px-3 py-2 rounded cursor-pointer flex items-center justify-between ${
                      selectedIndex === resultIdx
                        ? 'bg-[var(--accent-primary)]/20'
                        : 'hover:bg-[var(--bg-tertiary)]'
                    }`}
                    onClick={() => handleClickArtifact(artifact)}
                  >
                    <div className="flex items-center gap-2">
                      <span className="font-mono text-[var(--accent-secondary)]">
                        {artifact.artifact_id}
                      </span>
                      <span className="text-xs text-[var(--text-secondary)] bg-[var(--bg-primary)] px-1.5 py-0.5 rounded">
                        {artifact.artifact_type}
                      </span>
                    </div>
                    <span className="text-sm text-[var(--text-secondary)]">
                      by {artifact.created_by}
                    </span>
                  </div>
                )
              })}
            </div>
          )}
        </div>

        {/* Footer with keyboard hints */}
        {totalResults > 0 && (
          <div className="px-4 py-2 border-t border-[var(--border-color)] flex gap-4 text-xs text-[var(--text-secondary)]">
            <span>
              <kbd className="px-1 bg-[var(--bg-primary)] rounded">↑↓</kbd> navigate
            </span>
            <span>
              <kbd className="px-1 bg-[var(--bg-primary)] rounded">↵</kbd> select
            </span>
          </div>
        )}
      </div>
    </div>
  )
}

function StatusBadge({ status }: { status: string }) {
  const colors: Record<string, string> = {
    active: 'bg-[var(--accent-secondary)]/20 text-[var(--accent-secondary)]',
    idle: 'bg-[var(--text-secondary)]/20 text-[var(--text-secondary)]',
    frozen: 'bg-[var(--accent-primary)]/20 text-[var(--accent-primary)]',
    bankrupt: 'bg-[var(--accent-danger)]/20 text-[var(--accent-danger)]',
  }

  return (
    <span className={`px-1.5 py-0.5 rounded text-xs font-medium ${colors[status] ?? colors.idle}`}>
      {status}
    </span>
  )
}
