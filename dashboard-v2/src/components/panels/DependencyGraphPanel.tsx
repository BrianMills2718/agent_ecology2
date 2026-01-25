import { useEffect, useRef, useState } from 'react'
import { Network } from 'vis-network'
import type { Options } from 'vis-network'
import { DataSet } from 'vis-data'
import { useDependencyGraph } from '../../api/queries'
import { Panel } from '../shared/Panel'
import { safeFixed } from '../../utils/format'
import type { DependencyNode, DependencyEdge } from '../../types/api'

const NODE_COLORS = {
  genesis: { background: '#f59e0b', border: '#d97706' },
  agent: { background: '#22c55e', border: '#16a34a' },
  contract: { background: '#3b82f6', border: '#2563eb' },
  data: { background: '#8b5cf6', border: '#7c3aed' },
  unknown: { background: '#6b7280', border: '#4b5563' },
}

function buildVisNodes(nodes: DependencyNode[]) {
  return nodes.map((node) => {
    const colors = NODE_COLORS[node.artifact_type as keyof typeof NODE_COLORS] || NODE_COLORS.unknown
    // Scale size by Lindy score (min 10, max 30)
    const size = Math.min(30, Math.max(10, 10 + node.lindy_score * 2))
    
    return {
      id: node.artifact_id,
      label: node.name,
      color: colors,
      size,
      shape: node.is_genesis ? 'diamond' : 'dot',
      title: `${node.name}\nOwner: ${node.owner}\nLindy: ${safeFixed(node.lindy_score, 1)}\nUsage: ${node.usage_count}`,
    }
  })
}

function buildVisEdges(edges: DependencyEdge[]) {
  return edges.map((edge, i) => ({
    id: `${edge.source}-${edge.target}-${i}`,
    from: edge.source,
    to: edge.target,
    arrows: 'to',
    color: '#6b7280',
  }))
}

export function DependencyGraphPanel() {
  const containerRef = useRef<HTMLDivElement>(null)
  const networkRef = useRef<Network | null>(null)
  const nodesDataSet = useRef(new DataSet<ReturnType<typeof buildVisNodes>[0]>())
  const edgesDataSet = useRef(new DataSet<ReturnType<typeof buildVisEdges>[0]>())

  const [physics, setPhysics] = useState(true)
  const { data, isLoading, error } = useDependencyGraph()

  // Initialize network
  useEffect(() => {
    if (!containerRef.current) return

    const options: Options = {
      nodes: {
        font: { size: 12, color: '#e5e7eb' },
        borderWidth: 2,
      },
      edges: {
        smooth: false,
        font: { size: 10, color: '#9ca3af' },
      },
      physics: {
        enabled: physics,
        stabilization: { iterations: 100 },
        hierarchicalRepulsion: {
          nodeDistance: 150,
        },
      },
      layout: {
        hierarchical: {
          enabled: true,
          direction: 'UD',
          sortMethod: 'directed',
          levelSeparation: 100,
        },
      },
      interaction: {
        hover: true,
        tooltipDelay: 100,
      },
    }

    networkRef.current = new Network(
      containerRef.current,
      { nodes: nodesDataSet.current, edges: edgesDataSet.current },
      options
    )

    return () => {
      networkRef.current?.destroy()
    }
  }, [])

  // Update physics setting
  useEffect(() => {
    networkRef.current?.setOptions({ physics: { enabled: physics } })
  }, [physics])

  // Update data
  useEffect(() => {
    if (!data) return

    const visNodes = buildVisNodes(data.nodes ?? [])
    const visEdges = buildVisEdges(data.edges ?? [])

    nodesDataSet.current.clear()
    edgesDataSet.current.clear()
    nodesDataSet.current.add(visNodes)
    edgesDataSet.current.add(visEdges)
  }, [data])

  return (
    <Panel
      title="Dependency Graph"
      badge={data?.metrics?.total_nodes}
      collapsible
    >
      {/* Controls */}
      <div className="flex items-center gap-4 mb-3">
        <label className="flex items-center gap-2 text-sm">
          <input
            type="checkbox"
            checked={physics}
            onChange={(e) => setPhysics(e.target.checked)}
            className="rounded"
          />
          Physics
        </label>
        <button
          onClick={() => networkRef.current?.fit()}
          className="ml-auto px-2 py-1 text-xs bg-[var(--bg-tertiary)] rounded hover:bg-[var(--accent-primary)]/20"
        >
          Fit
        </button>
      </div>

      {/* Metrics */}
      {data?.metrics && (
        <div className="grid grid-cols-3 gap-2 mb-3 text-center">
          <div className="bg-[var(--bg-primary)] rounded p-2">
            <p className="text-xs text-[var(--text-secondary)]">Max Depth</p>
            <p className="font-semibold">{data.metrics.max_depth}</p>
          </div>
          <div className="bg-[var(--bg-primary)] rounded p-2">
            <p className="text-xs text-[var(--text-secondary)]">Avg Fanout</p>
            <p className="font-semibold">{safeFixed(data.metrics.avg_fanout, 1)}</p>
          </div>
          <div className="bg-[var(--bg-primary)] rounded p-2">
            <p className="text-xs text-[var(--text-secondary)]">Genesis Deps</p>
            <p className="font-semibold">{safeFixed(data.metrics.genesis_dependency_ratio * 100, 0)}%</p>
          </div>
        </div>
      )}

      {/* Legend */}
      <div className="flex flex-wrap gap-3 mb-3 text-xs">
        <div className="flex items-center gap-1">
          <span className="w-3 h-3 bg-amber-500 rotate-45" />
          <span>Genesis</span>
        </div>
        <div className="flex items-center gap-1">
          <span className="w-3 h-3 rounded-full bg-green-500" />
          <span>Agent</span>
        </div>
        <div className="flex items-center gap-1">
          <span className="w-3 h-3 rounded-full bg-blue-500" />
          <span>Contract</span>
        </div>
        <div className="flex items-center gap-1">
          <span className="w-3 h-3 rounded-full bg-purple-500" />
          <span>Data</span>
        </div>
      </div>

      {isLoading && (
        <div className="h-64 flex items-center justify-center">
          <div className="animate-spin w-8 h-8 border-2 border-[var(--accent-primary)] border-t-transparent rounded-full" />
        </div>
      )}

      {error && (
        <p className="text-[var(--accent-danger)] text-sm">
          Failed to load dependency graph: {error.message}
        </p>
      )}

      <div
        ref={containerRef}
        className="h-64 bg-[var(--bg-primary)] rounded"
        style={{ minHeight: '256px' }}
      />

      {data && (data.nodes?.length ?? 0) === 0 && (
        <p className="text-sm text-[var(--text-secondary)] text-center mt-2">
          No dependencies yet
        </p>
      )}
    </Panel>
  )
}
