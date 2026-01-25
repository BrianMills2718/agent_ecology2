import { useEffect, useRef, useState } from 'react'
import { Network } from 'vis-network'
import { DataSet } from 'vis-data'
import { useNetwork } from '../../api/queries'
import { Panel } from '../shared/Panel'
import type { NetworkNode, NetworkEdge } from '../../types/api'

const NODE_COLORS = {
  agent: {
    active: { background: '#22c55e', border: '#16a34a' },
    idle: { background: '#6b7280', border: '#4b5563' },
    frozen: { background: '#3b82f6', border: '#2563eb' },
    bankrupt: { background: '#ef4444', border: '#dc2626' },
  },
  artifact: {
    default: { background: '#8b5cf6', border: '#7c3aed' },
    genesis: { background: '#f59e0b', border: '#d97706' },
  },
}

const EDGE_COLORS: Record<string, string> = {
  invoke: '#22c55e',
  transfer: '#3b82f6',
  trade: '#f59e0b',
  create: '#8b5cf6',
  default: '#6b7280',
}

function buildVisNodes(nodes: NetworkNode[]) {
  return nodes.map((node) => {
    const isGenesis = node.id.startsWith('genesis_')
    const colors =
      node.node_type === 'agent'
        ? NODE_COLORS.agent[node.status as keyof typeof NODE_COLORS.agent] ||
          NODE_COLORS.agent.idle
        : isGenesis
        ? NODE_COLORS.artifact.genesis
        : NODE_COLORS.artifact.default

    return {
      id: node.id,
      label: node.label,
      color: colors,
      shape: node.node_type === 'agent' ? 'dot' : 'diamond',
      size: node.node_type === 'agent' ? 15 : 10,
      title: `${node.label}${node.scrip ? ` (${node.scrip.toFixed(1)} scrip)` : ''}`,
    }
  })
}

function buildVisEdges(edges: NetworkEdge[]) {
  return edges.map((edge, i) => ({
    id: `${edge.from}-${edge.to}-${i}`,
    from: edge.from,
    to: edge.to,
    color: EDGE_COLORS[edge.interaction_type] || EDGE_COLORS.default,
    width: Math.min(edge.weight, 5),
    arrows: 'to',
    title: edge.interaction_type,
  }))
}

export function NetworkPanel() {
  const containerRef = useRef<HTMLDivElement>(null)
  const networkRef = useRef<Network | null>(null)
  const nodesDataSet = useRef(new DataSet<ReturnType<typeof buildVisNodes>[0]>())
  const edgesDataSet = useRef(new DataSet<ReturnType<typeof buildVisEdges>[0]>())

  const [physics, setPhysics] = useState(true)
  const { data, isLoading, error } = useNetwork()

  // Initialize network
  useEffect(() => {
    if (!containerRef.current) return

    const options = {
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
        barnesHut: {
          gravitationalConstant: -2000,
          springLength: 150,
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

    // Update nodes
    const existingNodeIds = nodesDataSet.current.getIds()
    const newNodeIds = visNodes.map((n) => n.id)

    // Remove deleted nodes
    const toRemove = existingNodeIds.filter((id) => !newNodeIds.includes(id as string))
    if (toRemove.length > 0) nodesDataSet.current.remove(toRemove)

    // Update/add nodes
    nodesDataSet.current.update(visNodes)

    // Update edges (simpler: just replace all)
    edgesDataSet.current.clear()
    edgesDataSet.current.add(visEdges)
  }, [data])

  return (
    <Panel
      title="Agent Interactions"
      badge={data?.nodes?.length}
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

      {/* Legend */}
      <div className="flex flex-wrap gap-3 mb-3 text-xs">
        <div className="flex items-center gap-1">
          <span className="w-3 h-3 rounded-full bg-green-500" />
          <span>Active</span>
        </div>
        <div className="flex items-center gap-1">
          <span className="w-3 h-3 rounded-full bg-gray-500" />
          <span>Idle</span>
        </div>
        <div className="flex items-center gap-1">
          <span className="w-3 h-3 rounded-full bg-blue-500" />
          <span>Frozen</span>
        </div>
        <div className="flex items-center gap-1">
          <span className="w-3 h-3 bg-purple-500 rotate-45" />
          <span>Artifact</span>
        </div>
        <div className="flex items-center gap-1">
          <span className="w-3 h-3 bg-amber-500 rotate-45" />
          <span>Genesis</span>
        </div>
      </div>

      {isLoading && (
        <div className="h-64 flex items-center justify-center">
          <div className="animate-spin w-8 h-8 border-2 border-[var(--accent-primary)] border-t-transparent rounded-full" />
        </div>
      )}

      {error && (
        <p className="text-[var(--accent-danger)] text-sm">
          Failed to load network: {error.message}
        </p>
      )}

      <div
        ref={containerRef}
        className="h-64 bg-[var(--bg-primary)] rounded"
        style={{ minHeight: '256px' }}
      />

      {data && (data.nodes?.length ?? 0) === 0 && (
        <p className="text-sm text-[var(--text-secondary)] text-center mt-2">
          No interactions yet
        </p>
      )}
    </Panel>
  )
}
