// Overview tab - Quick health check with progress and key metrics

import { ProgressPanel } from '../panels/ProgressPanel'
import { useEmergence, useKPIs } from '../../api/queries'
import { useAlertStore } from '../../stores/alerts'
import { safeFixed, safePercent, safeCurrency } from '../../utils/format'
import { useEmergenceAlerts } from '../../hooks/useEmergenceAlerts'

function QuickStat({
  label,
  value,
  trend,
}: {
  label: string
  value: string
  trend?: 'up' | 'down' | 'stable'
}) {
  const trendIcons = { up: '↑', down: '↓', stable: '→' }
  const trendColors = {
    up: 'text-green-400',
    down: 'text-red-400',
    stable: 'text-gray-400',
  }

  return (
    <div className="bg-[var(--bg-secondary)] rounded-lg p-4">
      <p className="text-xs text-[var(--text-secondary)] mb-1">{label}</p>
      <div className="flex items-center gap-2">
        <span className="text-2xl font-semibold font-mono">{value}</span>
        {trend && (
          <span className={trendColors[trend]}>{trendIcons[trend]}</span>
        )}
      </div>
    </div>
  )
}

function MilestonesList() {
  const milestones = useAlertStore((s) => s.milestones)

  if (milestones.length === 0) {
    return (
      <div className="bg-[var(--bg-secondary)] rounded-lg p-4">
        <h3 className="text-sm font-semibold mb-2">Milestones</h3>
        <p className="text-sm text-[var(--text-secondary)]">
          No emergence milestones achieved yet
        </p>
      </div>
    )
  }

  return (
    <div className="bg-[var(--bg-secondary)] rounded-lg p-4">
      <h3 className="text-sm font-semibold mb-3">
        Milestones Achieved ({milestones.length})
      </h3>
      <div className="space-y-2">
        {milestones.slice(0, 6).map((m, i) => (
          <div
            key={i}
            className="flex items-center justify-between text-sm"
          >
            <span className="text-green-400">✓</span>
            <span className="flex-1 mx-2">
              {m.metric.replace(/_/g, ' ')}
            </span>
            <span className="text-[var(--text-secondary)] font-mono">
              ≥ {m.threshold < 1 ? `${(m.threshold * 100).toFixed(0)}%` : m.threshold}
            </span>
          </div>
        ))}
        {milestones.length > 6 && (
          <p className="text-xs text-[var(--text-secondary)]">
            +{milestones.length - 6} more
          </p>
        )}
      </div>
    </div>
  )
}

interface MetricInfo {
  label: string
  value: number
  tooltip: string
  formula: string
}

function EmergenceGauges() {
  const { data: emergence } = useEmergence()

  // Enable alerts
  useEmergenceAlerts(emergence)

  if (!emergence) return null

  const metrics: MetricInfo[] = [
    {
      label: 'Coordination',
      value: emergence.coordination_density,
      tooltip: '% of agent pairs that have interacted at least once',
      formula: 'unique_pairs / max_possible_pairs',
    },
    {
      label: 'Reuse',
      value: emergence.reuse_ratio,
      tooltip: '% of artifacts used by agents other than their creator',
      formula: 'artifacts_used_by_others / total_artifacts',
    },
    {
      label: 'Independence',
      value: emergence.genesis_independence,
      tooltip: '% of invocations that target non-genesis artifacts',
      formula: 'non_genesis_invokes / total_invokes',
    },
  ]

  return (
    <div className="bg-[var(--bg-secondary)] rounded-lg p-4">
      <h3 className="text-sm font-semibold mb-3">Emergence Indicators</h3>
      <div className="space-y-3">
        {metrics.map((m) => (
          <div key={m.label} className="group relative">
            <div className="flex justify-between text-xs mb-1">
              <span className="cursor-help border-b border-dotted border-[var(--text-secondary)]">
                {m.label}
              </span>
              <span className="font-mono">{safePercent(m.value, 0)}</span>
            </div>
            <div className="h-2 bg-[var(--bg-tertiary)] rounded-full overflow-hidden">
              <div
                className={`h-full transition-all duration-300 ${
                  m.value >= 0.5
                    ? 'bg-green-500'
                    : m.value >= 0.2
                    ? 'bg-yellow-500'
                    : 'bg-gray-500'
                }`}
                style={{ width: `${Math.min(m.value * 100, 100)}%` }}
              />
            </div>
            {/* Tooltip */}
            <div className="absolute left-0 bottom-full mb-2 hidden group-hover:block z-10 w-64 p-2 bg-[var(--bg-primary)] border border-[var(--border-color)] rounded shadow-lg text-xs">
              <p className="text-[var(--text-primary)] mb-1">{m.tooltip}</p>
              <p className="text-[var(--text-secondary)] font-mono">{m.formula}</p>
            </div>
          </div>
        ))}
        {emergence.coalition_count > 0 && (
          <div className="pt-2 border-t border-[var(--border-color)]">
            <div className="flex justify-between text-xs">
              <span
                className="cursor-help border-b border-dotted border-[var(--text-secondary)]"
                title="Number of disconnected agent clusters"
              >
                Coalitions
              </span>
              <span className="font-mono">{emergence.coalition_count}</span>
            </div>
          </div>
        )}
      </div>
    </div>
  )
}

export function OverviewTab() {
  const { data: kpis } = useKPIs()

  return (
    <div className="p-4 space-y-4">
      {/* Progress at top */}
      <ProgressPanel />

      {/* Quick stats grid */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        <QuickStat
          label="Total Scrip"
          value={safeFixed(kpis?.total_scrip, 0)}
          trend={kpis?.scrip_velocity_trend}
        />
        <QuickStat
          label="Active Agents"
          value={safePercent(kpis?.active_agent_ratio, 0)}
          trend={kpis?.active_agent_ratio_trend}
        />
        <QuickStat
          label="Actions/sec"
          value={safeFixed(kpis?.actions_per_second, 1)}
          trend={kpis?.activity_trend}
        />
        <QuickStat
          label="LLM Budget"
          value={safeCurrency(kpis?.llm_budget_remaining, 2)}
        />
      </div>

      {/* Two column layout for emergence and milestones */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        <EmergenceGauges />
        <MilestonesList />
      </div>
    </div>
  )
}
