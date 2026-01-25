import { useState, useEffect } from 'react'
import { useAgents } from '../../api/queries'
import { Panel } from '../shared/Panel'
import { Pagination } from '../shared/Pagination'
import { AgentDetailModal } from './AgentDetailModal'
import { safeFixed } from '../../utils/format'
import { useSelectionStore } from '../../stores/selection'
import type { AgentSummary } from '../../types/api'

function StatusBadge({ status }: { status: AgentSummary['status'] }) {
  const colors = {
    active: 'bg-[var(--accent-secondary)]/20 text-[var(--accent-secondary)]',
    idle: 'bg-[var(--text-secondary)]/20 text-[var(--text-secondary)]',
    frozen: 'bg-[var(--accent-primary)]/20 text-[var(--accent-primary)]',
    bankrupt: 'bg-[var(--accent-danger)]/20 text-[var(--accent-danger)]',
  }

  return (
    <span className={`px-2 py-0.5 rounded text-xs font-medium ${colors[status]}`}>
      {status}
    </span>
  )
}

function BudgetBar({ remaining, initial }: { remaining: number; initial: number }) {
  const percent = initial > 0 ? (remaining / initial) * 100 : 0
  const color =
    percent > 50
      ? 'bg-[var(--accent-secondary)]'
      : percent > 20
      ? 'bg-[var(--accent-warning)]'
      : 'bg-[var(--accent-danger)]'

  return (
    <div className="w-20 h-1.5 bg-[var(--bg-primary)] rounded-full overflow-hidden">
      <div
        className={`h-full ${color}`}
        style={{ width: `${Math.min(percent, 100)}%` }}
      />
    </div>
  )
}

export function AgentsPanel() {
  const [page, setPage] = useState(0)
  const [selectedAgent, setSelectedAgent] = useState<string | null>(null)
  const limit = 25

  // Listen for selections from global search
  const globalSelectedAgent = useSelectionStore((s) => s.selectedAgentId)
  const clearSelection = useSelectionStore((s) => s.clearSelection)

  useEffect(() => {
    if (globalSelectedAgent) {
      setSelectedAgent(globalSelectedAgent)
      clearSelection()
    }
  }, [globalSelectedAgent, clearSelection])

  const { data, isLoading, error } = useAgents(page, limit)

  const handleExport = () => {
    if (!data?.agents) return
    const csv = [
      ['ID', 'Scrip', 'Budget Remaining', 'Status', 'Actions'].join(','),
      ...data.agents.map((a) =>
        [
          a.agent_id,
          safeFixed(a.scrip, 2),
          safeFixed(a.llm_budget_remaining, 4),
          a.status,
          a.action_count,
        ].join(',')
      ),
    ].join('\n')

    const blob = new Blob([csv], { type: 'text/csv' })
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = 'agents.csv'
    a.click()
    URL.revokeObjectURL(url)
  }

  return (
    <>
      <Panel title="Agents" badge={data?.total} onExport={handleExport}>
        {isLoading && (
          <div className="animate-pulse space-y-2">
            {[...Array(5)].map((_, i) => (
              <div key={i} className="h-8 bg-[var(--bg-tertiary)] rounded" />
            ))}
          </div>
        )}

        {error && (
          <p className="text-[var(--accent-danger)] text-sm">
            Failed to load agents: {error.message}
          </p>
        )}

        {data && (
          <>
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead>
                  <tr className="text-left text-[var(--text-secondary)] border-b border-[var(--border-color)]">
                    <th className="pb-2 font-medium">ID</th>
                    <th className="pb-2 font-medium">Scrip</th>
                    <th className="pb-2 font-medium">Budget</th>
                    <th className="pb-2 font-medium">Status</th>
                    <th className="pb-2 font-medium">Actions</th>
                  </tr>
                </thead>
                <tbody>
                  {(data.agents ?? []).map((agent) => (
                    <tr
                      key={agent.agent_id}
                      className="border-b border-[var(--border-color)] hover:bg-[var(--bg-tertiary)] cursor-pointer"
                      onClick={() => setSelectedAgent(agent.agent_id)}
                    >
                      <td className="py-2 font-mono text-[var(--accent-primary)]">
                        {agent.agent_id}
                      </td>
                      <td className="py-2">{safeFixed(agent.scrip, 1)}</td>
                      <td className="py-2">
                        <div className="flex items-center gap-2">
                          <BudgetBar
                            remaining={agent.llm_budget_remaining}
                            initial={agent.llm_budget_initial}
                          />
                          <span className="text-xs text-[var(--text-secondary)]">
                            ${safeFixed(agent.llm_budget_remaining, 2)}
                          </span>
                        </div>
                      </td>
                      <td className="py-2">
                        <StatusBadge status={agent.status} />
                      </td>
                      <td className="py-2">{agent.action_count}</td>
                    </tr>
                  ))}
                  {(data.agents?.length ?? 0) === 0 && (
                    <tr>
                      <td
                        colSpan={5}
                        className="py-4 text-center text-[var(--text-secondary)]"
                      >
                        No agents yet
                      </td>
                    </tr>
                  )}
                </tbody>
              </table>
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

      {selectedAgent && (
        <AgentDetailModal
          agentId={selectedAgent}
          onClose={() => setSelectedAgent(null)}
        />
      )}
    </>
  )
}
