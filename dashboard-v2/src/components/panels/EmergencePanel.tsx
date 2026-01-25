import { useEmergence, useKPIs } from '../../api/queries'
import { Panel } from '../shared/Panel'
import { safeFixed, safePercent, safeCurrency } from '../../utils/format'

function MetricGauge({
  label,
  value,
  description,
  format = 'percent',
}: {
  label: string
  value: number | undefined | null
  description: string
  format?: 'percent' | 'number' | 'decimal'
}) {
  const safeValue = value ?? 0
  const displayValue =
    format === 'percent'
      ? safePercent(value, 1)
      : format === 'decimal'
      ? safeFixed(value, 3)
      : safeFixed(value, 0)

  const barWidth = format === 'percent' ? Math.min(safeValue * 100, 100) : Math.min(safeValue * 10, 100)

  const color =
    safeValue >= 0.7
      ? 'bg-[var(--accent-secondary)]'
      : safeValue >= 0.3
      ? 'bg-[var(--accent-warning)]'
      : 'bg-[var(--accent-danger)]'

  return (
    <div className="p-3 bg-[var(--bg-primary)] rounded">
      <div className="flex items-center justify-between mb-1">
        <span className="text-sm font-medium">{label}</span>
        <span className="text-sm font-mono">{displayValue}</span>
      </div>
      <div className="h-2 bg-[var(--bg-tertiary)] rounded-full overflow-hidden mb-2">
        <div
          className={`h-full ${color} transition-all duration-300`}
          style={{ width: `${barWidth}%` }}
        />
      </div>
      <p className="text-xs text-[var(--text-secondary)]">{description}</p>
    </div>
  )
}

function TrendIndicator({ trend }: { trend: 'up' | 'down' | 'stable' }) {
  const config = {
    up: { symbol: '↑', color: 'text-[var(--accent-secondary)]' },
    down: { symbol: '↓', color: 'text-[var(--accent-danger)]' },
    stable: { symbol: '→', color: 'text-[var(--text-secondary)]' },
  }
  const { symbol, color } = config[trend]
  return <span className={`${color} font-bold`}>{symbol}</span>
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

export function EmergencePanel() {
  const { data: emergence, isLoading: emergenceLoading, error: emergenceError } = useEmergence()
  const { data: kpis, isLoading: kpisLoading, error: kpisError } = useKPIs()

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
          {/* Emergence Metrics */}
          <div>
            <h4 className="text-xs font-semibold text-[var(--text-secondary)] uppercase tracking-wide mb-3">
              Emergence Indicators
            </h4>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
              <MetricGauge
                label="Coordination Density"
                value={emergence.coordination_density}
                description="How connected the agent network is"
              />
              <MetricGauge
                label="Specialization Index"
                value={emergence.specialization_index}
                description="How differentiated agents are"
              />
              <MetricGauge
                label="Reuse Ratio"
                value={emergence.reuse_ratio}
                description="How much agents use each other's artifacts"
              />
              <MetricGauge
                label="Genesis Independence"
                value={emergence.genesis_independence}
                description="Ecosystem maturity (non-genesis ops ratio)"
              />
              <MetricGauge
                label="Capital Depth"
                value={emergence.capital_depth / 10}
                description={`Max dependency chain: ${emergence.capital_depth}`}
                format="number"
              />
              <MetricGauge
                label="Coalitions"
                value={emergence.coalition_count / 10}
                description={`Distinct agent clusters: ${emergence.coalition_count}`}
                format="number"
              />
            </div>
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
