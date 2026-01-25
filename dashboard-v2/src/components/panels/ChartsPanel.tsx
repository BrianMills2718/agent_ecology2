import { useState } from 'react'
import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ResponsiveContainer,
} from 'recharts'
import { useScripChart, useLLMTokensChart } from '../../api/queries'
import { Panel } from '../shared/Panel'
import type { ResourceChartData } from '../../types/api'

type ChartType = 'scrip' | 'llm_tokens'

const CHART_COLORS = [
  '#22c55e', // green
  '#3b82f6', // blue
  '#f59e0b', // amber
  '#8b5cf6', // purple
  '#ef4444', // red
  '#06b6d4', // cyan
  '#ec4899', // pink
  '#84cc16', // lime
]

function formatChartData(data: ResourceChartData | undefined) {
  if (!data) return []

  // Create a map of tick -> { tick, total, agent1, agent2, ... }
  const tickMap: Record<number, Record<string, number>> = {}

  // Add totals
  for (const point of data.totals ?? []) {
    if (!tickMap[point.tick]) tickMap[point.tick] = { tick: point.tick }
    tickMap[point.tick].total = point.value
  }

  // Add per-agent data
  for (const agent of data.agents ?? []) {
    for (const point of agent.data) {
      if (!tickMap[point.tick]) tickMap[point.tick] = { tick: point.tick }
      tickMap[point.tick][agent.agent_id] = point.value
    }
  }

  return Object.values(tickMap).sort((a, b) => a.tick - b.tick)
}

function ChartView({
  data,
  isLoading,
  error,
  showAgents,
}: {
  data: ResourceChartData | undefined
  isLoading: boolean
  error: Error | null
  showAgents: boolean
}) {
  if (isLoading) {
    return (
      <div className="h-48 flex items-center justify-center">
        <div className="animate-spin w-6 h-6 border-2 border-[var(--accent-primary)] border-t-transparent rounded-full" />
      </div>
    )
  }

  if (error) {
    return (
      <p className="text-[var(--accent-danger)] text-sm">
        Failed to load chart: {error.message}
      </p>
    )
  }

  if (!data || data.totals.length === 0) {
    return (
      <p className="text-sm text-[var(--text-secondary)] text-center py-8">
        No data yet
      </p>
    )
  }

  const chartData = formatChartData(data)
  const agentIds = (data.agents ?? []).map((a) => a.agent_id)

  return (
    <ResponsiveContainer width="100%" height={200}>
      <LineChart data={chartData}>
        <CartesianGrid strokeDasharray="3 3" stroke="var(--border-color)" />
        <XAxis
          dataKey="tick"
          stroke="var(--text-secondary)"
          fontSize={12}
          tickFormatter={(v) => `T${v}`}
        />
        <YAxis
          stroke="var(--text-secondary)"
          fontSize={12}
          tickFormatter={(v) =>
            v >= 1000 ? `${(v / 1000).toFixed(1)}k` : v.toFixed(0)
          }
        />
        <Tooltip
          contentStyle={{
            backgroundColor: 'var(--bg-secondary)',
            border: '1px solid var(--border-color)',
            borderRadius: '4px',
          }}
          labelFormatter={(v) => `Tick ${v}`}
        />
        <Legend />

        {/* Total line */}
        <Line
          type="monotone"
          dataKey="total"
          stroke="#ffffff"
          strokeWidth={2}
          dot={false}
          name="Total"
        />

        {/* Per-agent lines (if enabled) */}
        {showAgents &&
          agentIds.slice(0, 8).map((agentId, i) => (
            <Line
              key={agentId}
              type="monotone"
              dataKey={agentId}
              stroke={CHART_COLORS[i % CHART_COLORS.length]}
              strokeWidth={1}
              dot={false}
              name={agentId}
            />
          ))}
      </LineChart>
    </ResponsiveContainer>
  )
}

export function ChartsPanel() {
  const [chartType, setChartType] = useState<ChartType>('scrip')
  const [showAgents, setShowAgents] = useState(false)

  const {
    data: scripData,
    isLoading: scripLoading,
    error: scripError,
  } = useScripChart()
  const {
    data: tokensData,
    isLoading: tokensLoading,
    error: tokensError,
  } = useLLMTokensChart()

  const data = chartType === 'scrip' ? scripData : tokensData
  const isLoading = chartType === 'scrip' ? scripLoading : tokensLoading
  const error = chartType === 'scrip' ? scripError : tokensError

  return (
    <Panel title="Resource Charts" collapsible>
      {/* Controls */}
      <div className="flex items-center gap-4 mb-4">
        <div className="flex gap-2">
          <button
            onClick={() => setChartType('scrip')}
            className={`px-3 py-1 text-sm rounded ${
              chartType === 'scrip'
                ? 'bg-[var(--accent-primary)] text-white'
                : 'bg-[var(--bg-tertiary)] hover:bg-[var(--accent-primary)]/20'
            }`}
          >
            Scrip
          </button>
          <button
            onClick={() => setChartType('llm_tokens')}
            className={`px-3 py-1 text-sm rounded ${
              chartType === 'llm_tokens'
                ? 'bg-[var(--accent-primary)] text-white'
                : 'bg-[var(--bg-tertiary)] hover:bg-[var(--accent-primary)]/20'
            }`}
          >
            LLM Tokens
          </button>
        </div>

        <label className="flex items-center gap-2 text-sm ml-auto">
          <input
            type="checkbox"
            checked={showAgents}
            onChange={(e) => setShowAgents(e.target.checked)}
            className="rounded"
          />
          Show per-agent
        </label>
      </div>

      <ChartView
        data={data}
        isLoading={isLoading}
        error={error}
        showAgents={showAgents}
      />
    </Panel>
  )
}
