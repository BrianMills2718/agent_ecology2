import { useCapitalFlow } from '../../api/queries'
import { Panel } from '../shared/Panel'
import { safeFixed } from '../../utils/format'

const NODE_COLORS: Record<string, string> = {
  agent: '#22c55e',
  genesis: '#f59e0b',
  artifact: '#8b5cf6',
}

export function CapitalFlowPanel() {
  const { data, isLoading, error } = useCapitalFlow()

  return (
    <Panel title="Capital Flow" badge={data?.total_flow} collapsible>
      {isLoading && (
        <div className="h-48 flex items-center justify-center">
          <div className="animate-spin w-6 h-6 border-2 border-[var(--accent-primary)] border-t-transparent rounded-full" />
        </div>
      )}

      {error && (
        <p className="text-[var(--accent-danger)] text-sm">
          Failed to load capital flow: {error.message}
        </p>
      )}

      {data && (
        <div className="space-y-4">
          {/* Summary stats */}
          <div className="grid grid-cols-3 gap-2 text-center">
            <div className="bg-[var(--bg-primary)] rounded p-2">
              <p className="text-xs text-[var(--text-secondary)]">Total Flow</p>
              <p className="text-lg font-semibold">{safeFixed(data.total_flow, 0)}</p>
            </div>
            <div className="bg-[var(--bg-primary)] rounded p-2">
              <p className="text-xs text-[var(--text-secondary)]">Principals</p>
              <p className="text-lg font-semibold">{data.nodes?.length ?? 0}</p>
            </div>
            <div className="bg-[var(--bg-primary)] rounded p-2">
              <p className="text-xs text-[var(--text-secondary)]">Transfers</p>
              <p className="text-lg font-semibold">{data.links?.length ?? 0}</p>
            </div>
          </div>

          {/* Flow list */}
          {(data.links?.length ?? 0) > 0 ? (
            <div className="space-y-2 max-h-64 overflow-y-auto">
              <p className="text-xs text-[var(--text-secondary)] font-semibold">Top Flows</p>
              {[...(data.links ?? [])]
                .sort((a, b) => b.value - a.value)
                .slice(0, 10)
                .map((link, i) => {
                  const sourceNode = data.nodes?.find(n => n.id === link.source)
                  const targetNode = data.nodes?.find(n => n.id === link.target)
                  return (
                    <div
                      key={i}
                      className="flex items-center gap-2 p-2 bg-[var(--bg-primary)] rounded text-sm"
                    >
                      <span
                        className="w-2 h-2 rounded-full"
                        style={{ backgroundColor: NODE_COLORS[sourceNode?.node_type ?? 'agent'] }}
                      />
                      <span className="font-mono text-xs truncate max-w-20">
                        {sourceNode?.name ?? link.source}
                      </span>
                      <span className="text-[var(--text-secondary)]">→</span>
                      <span
                        className="w-2 h-2 rounded-full"
                        style={{ backgroundColor: NODE_COLORS[targetNode?.node_type ?? 'agent'] }}
                      />
                      <span className="font-mono text-xs truncate max-w-20">
                        {targetNode?.name ?? link.target}
                      </span>
                      <span className="ml-auto font-semibold">
                        {safeFixed(link.value, 0)}
                      </span>
                      <span className="text-xs text-[var(--text-secondary)]">
                        ({link.count}x)
                      </span>
                    </div>
                  )
                })}
            </div>
          ) : (
            <p className="text-sm text-[var(--text-secondary)] text-center py-4">
              No transfers yet
            </p>
          )}

          {/* Legend */}
          <div className="flex gap-4 text-xs">
            <div className="flex items-center gap-1">
              <span className="w-2 h-2 rounded-full bg-green-500" />
              <span>Agent</span>
            </div>
            <div className="flex items-center gap-1">
              <span className="w-2 h-2 rounded-full bg-amber-500" />
              <span>Genesis</span>
            </div>
            <div className="flex items-center gap-1">
              <span className="w-2 h-2 rounded-full bg-purple-500" />
              <span>Artifact</span>
            </div>
          </div>
        </div>
      )}
    </Panel>
  )
}
