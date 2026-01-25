import { useEmergence, useKPIs } from '../../api/queries'
import { Panel } from '../shared/Panel'
import { safeFixed, safePercent, safeCurrency } from '../../utils/format'
import { useEmergenceAlerts } from '../../hooks/useEmergenceAlerts'
import { useAlertStore } from '../../stores/alerts'

function MetricGauge({
  label,
  value,
  description,
  formula,
}: {
  label: string
  value: number | undefined | null
  description: string
  formula: string
}) {
  const safeValue = value ?? 0
  const displayValue = safePercent(value, 1)
  const barWidth = Math.min(safeValue * 100, 100)

  const color =
    safeValue >= 0.5
      ? 'bg-[var(--accent-secondary)]'
      : safeValue >= 0.2
      ? 'bg-[var(--accent-warning)]'
      : 'bg-gray-500'

  return (
    <div className="p-3 bg-[var(--bg-primary)] rounded group relative">
      <div className="flex items-center justify-between mb-1">
        <span className="text-sm font-medium cursor-help border-b border-dotted border-[var(--text-secondary)]">
          {label}
        </span>
        <span className="text-sm font-mono">{displayValue}</span>
      </div>
      <div className="h-2 bg-[var(--bg-tertiary)] rounded-full overflow-hidden mb-2">
        <div
          className={`h-full ${color} transition-all duration-300`}
          style={{ width: `${barWidth}%` }}
        />
      </div>
      <p className="text-xs text-[var(--text-secondary)]">{description}</p>
      {/* Tooltip with formula */}
      <div className="absolute left-0 bottom-full mb-2 hidden group-hover:block z-10 w-72 p-3 bg-[var(--bg-tertiary)] border border-[var(--border-color)] rounded shadow-lg text-xs">
        <p className="text-[var(--text-primary)] mb-2">{description}</p>
        <p className="text-[var(--text-secondary)]">
          <span className="font-semibold">Formula:</span>{' '}
          <code className="font-mono bg-[var(--bg-primary)] px-1 rounded">{formula}</code>
        </p>
      </div>
    </div>
  )
}

function TrendIndicator({ trend }: { trend: 'up' | 'down' | 'stable' | undefined }) {
  if (!trend) return null
  const config = {
    up: { symbol: '↑', color: 'text-[var(--accent-secondary)]' },
    down: { symbol: '↓', color: 'text-[var(--accent-danger)]' },
    stable: { symbol: '→', color: 'text-[var(--text-secondary)]' },
  }
  const entry = config[trend]
  if (!entry) return null
  return <span className={`${entry.color} font-bold`}>{entry.symbol}</span>
}

function KPICard({
  label,
  value,
  trend,
  format = 'number',
}: {
  label: string
  value: number | undefined | null
  trend?: 'up' | 'down' | 'stable'
  format?: 'number' | 'percent' | 'currency'
}) {
  const displayValue =
    format === 'percent'
      ? safePercent(value, 1)
      : format === 'currency'
      ? safeCurrency(value, 4)
      : safeFixed(value, 2)

  return (
    <div className="p-2 bg-[var(--bg-primary)] rounded">
      <div className="flex items-center justify-between">
        <span className="text-xs text-[var(--text-secondary)]">{label}</span>
        {trend && <TrendIndicator trend={trend} />}
      </div>
      <p className="text-lg font-semibold font-mono">{displayValue}</p>
    </div>
  )
}

function MilestonesBadge() {
  const milestones = useAlertStore((s) => s.milestones)

  if (milestones.length === 0) return null

  return (
    <div className="mb-4 p-3 bg-gradient-to-r from-green-500/10 to-emerald-500/10 border border-green-500/30 rounded-lg">
      <h4 className="text-xs font-semibold text-green-400 uppercase tracking-wide mb-2">
        Milestones Achieved ({milestones.length})
      </h4>
      <div className="flex flex-wrap gap-2">
        {milestones.slice(0, 8).map((m, i) => (
          <span
            key={i}
            className="px-2 py-1 text-xs bg-green-500/20 text-green-300 rounded"
            title={`Achieved at ${new Date(m.achievedAt).toLocaleString()}`}
          >
            {m.metric.replace(/_/g, ' ')} ≥{' '}
            {m.threshold < 1 ? `${(m.threshold * 100).toFixed(0)}%` : m.threshold}
          </span>
        ))}
        {milestones.length > 8 && (
          <span className="px-2 py-1 text-xs text-[var(--text-secondary)]">
            +{milestones.length - 8} more
          </span>
        )}
      </div>
    </div>
  )
}

export function EmergencePanel() {
  const { data: emergence, isLoading: emergenceLoading, error: emergenceError } = useEmergence()
  const { data: kpis, isLoading: kpisLoading, error: kpisError } = useKPIs()

  // Enable emergence alerts
  useEmergenceAlerts(emergence)

  const isLoading = emergenceLoading || kpisLoading
  const error = emergenceError || kpisError

  return (
    <Panel title="Emergence Metrics" collapsible>
      {isLoading && (
        <div className="animate-pulse space-y-4">
          <div className="grid grid-cols-2 gap-2">
            {[...Array(6)].map((_, i) => (
              <div key={i} className="h-20 bg-[var(--bg-tertiary)] rounded" />
            ))}
          </div>
        </div>
      )}

      {error && (
        <p className="text-[var(--accent-danger)] text-sm">
          Failed to load metrics: {error.message}
        </p>
      )}

      {emergence && (
        <div className="space-y-6">
          {/* Milestones */}
          <MilestonesBadge />

          {/* Emergence Metrics */}
          <div>
            <h4 className="text-xs font-semibold text-[var(--text-secondary)] uppercase tracking-wide mb-3">
              Emergence Indicators
            </h4>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
              <MetricGauge
                label="Coordination"
                value={emergence.coordination_density}
                description="% of agent pairs that have interacted"
                formula="unique_pairs / (n × (n-1) / 2)"
              />
              <MetricGauge
                label="Reuse"
                value={emergence.reuse_ratio}
                description="% of artifacts used by non-creators"
                formula="artifacts_used_by_others / total_artifacts"
              />
              <MetricGauge
                label="Independence"
                value={emergence.genesis_independence}
                description="% of invocations targeting non-genesis"
                formula="non_genesis_invokes / total_invokes"
              />
            </div>
            {/* Coalition count as simple stat */}
            {emergence.coalition_count > 0 && (
              <div className="mt-3 p-2 bg-[var(--bg-primary)] rounded flex justify-between items-center">
                <span className="text-sm">Agent Clusters</span>
                <span className="font-mono text-lg">{emergence.coalition_count}</span>
              </div>
            )}
          </div>

          {/* KPIs */}
          {kpis && (
            <div>
              <h4 className="text-xs font-semibold text-[var(--text-secondary)] uppercase tracking-wide mb-3">
                Key Performance Indicators
              </h4>
              <div className="grid grid-cols-2 md:grid-cols-3 gap-2">
                <KPICard
                  label="Scrip Velocity"
                  value={kpis.scrip_velocity}
                  trend={kpis.scrip_velocity_trend}
                />
                <KPICard
                  label="Gini Coefficient"
                  value={kpis.gini_coefficient}
                  trend={kpis.gini_coefficient_trend}
                  format="percent"
                />
                <KPICard
                  label="Active Ratio"
                  value={kpis.active_agent_ratio}
                  trend={kpis.active_agent_ratio_trend}
                  format="percent"
                />
                <KPICard
                  label="Actions/sec"
                  value={kpis.actions_per_second}
                  trend={kpis.activity_trend}
                />
                <KPICard
                  label="Thinking Rate"
                  value={kpis.thinking_cost_rate}
                  format="currency"
                />
                <KPICard
                  label="LLM Budget"
                  value={kpis.llm_budget_remaining}
                  format="currency"
                />
              </div>

              {/* Additional stats */}
              <div className="mt-3 grid grid-cols-3 gap-2 text-xs">
                <div className="text-center p-2 bg-[var(--bg-primary)] rounded">
                  <p className="text-[var(--text-secondary)]">Total Scrip</p>
                  <p className="font-mono">{safeFixed(kpis.total_scrip, 1)}</p>
                </div>
                <div className="text-center p-2 bg-[var(--bg-primary)] rounded">
                  <p className="text-[var(--text-secondary)]">Frozen</p>
                  <p className="font-mono">{kpis.frozen_agent_count ?? 0}</p>
                </div>
                <div className="text-center p-2 bg-[var(--bg-primary)] rounded">
                  <p className="text-[var(--text-secondary)]">Escrow Vol</p>
                  <p className="font-mono">{safeFixed(kpis.escrow_volume, 1)}</p>
                </div>
              </div>
            </div>
          )}
        </div>
      )}
    </Panel>
  )
}
