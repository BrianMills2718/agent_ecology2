import { useEffect, useRef, useState, useMemo, useCallback } from 'react'
import { Network } from 'vis-network'
import { DataSet } from 'vis-data'
import { useTemporalNetwork } from '../../api/queries'
import { useSelectionStore } from '../../stores/selection'
import { Panel } from '../shared/Panel'
import type { TemporalArtifactNode, TemporalArtifactEdge } from '../../types/api'

// Node colors by artifact type
const NODE_COLORS: Record<string, { background: string; border: string }> = {
  agent: { background: '#22c55e', border: '#16a34a' },
  genesis: { background: '#3b82f6', border: '#2563eb' },
  contract: { background: '#8b5cf6', border: '#7c3aed' },
  data: { background: '#6b7280', border: '#4b5563' },
  unknown: { background: '#9ca3af', border: '#6b7280' },
}

// Node shapes by artifact type
const NODE_SHAPES: Record<string, string> = {
  agent: 'dot',
  genesis: 'star',
  contract: 'diamond',
  data: 'square',
  unknown: 'ellipse',
}

// Edge colors by relationship type
const EDGE_COLORS: Record<string, string> = {
  invocation: '#f97316',
  ownership: '#8b5cf6',
  dependency: '#6b7280',
  creation: '#22c55e',
  transfer: '#3b82f6',
}

function buildVisNodes(nodes: TemporalArtifactNode[]) {
  return nodes.map((node) => {
    const colors = NODE_COLORS[node.artifact_type] || NODE_COLORS.unknown
    const shape = NODE_SHAPES[node.artifact_type] || NODE_SHAPES.unknown

    return {
      id: node.id,
      label: node.label,
      color: colors,
      shape,
      size: node.artifact_type === 'agent' ? 20 : 15,
      title: `${node.label}\nType: ${node.artifact_type}${node.scrip ? `\nScrip: ${node.scrip}` : ''}${node.invocation_count ? `\nInvocations: ${node.invocation_count}` : ''}`,
    }
  })
}

function buildVisEdges(edges: TemporalArtifactEdge[]) {
  return edges.map((edge, i) => ({
    id: `${edge.from_id}-${edge.to_id}-${edge.edge_type}-${i}`,
    from: edge.from_id,
    to: edge.to_id,
    color: { color: EDGE_COLORS[edge.edge_type] || EDGE_COLORS.dependency },
    width: Math.min(edge.weight, 5),
    arrows: 'to',
    title: `${edge.edge_type}${edge.details ? `: ${edge.details}` : ''}`,
  }))
}

interface TemporalNetworkPanelProps {
  fullHeight?: boolean
}

export function TemporalNetworkPanel({ fullHeight = false }: TemporalNetworkPanelProps) {
  const containerRef = useRef<HTMLDivElement>(null)
  const networkRef = useRef<Network | null>(null)
  const nodesDataSet = useRef(new DataSet<ReturnType<typeof buildVisNodes>[0]>())
  const edgesDataSet = useRef(new DataSet<ReturnType<typeof buildVisEdges>[0]>())

  const [physics, setPhysics] = useState(true)
  const [isPlaying, setIsPlaying] = useState(false)
  const [currentTime, setCurrentTime] = useState<number>(100) // Percentage of time range
  const playIntervalRef = useRef<number | null>(null)

  const { data, isLoading, error } = useTemporalNetwork()
  const setSelectedAgent = useSelectionStore((s) => s.setSelectedAgent)
  const setSelectedArtifact = useSelectionStore((s) => s.setSelectedArtifact)

  // Handle node click - open entity details
  const handleNodeClick = useCallback(
    (nodeId: string) => {
      const node = data?.nodes?.find((n) => n.id === nodeId)
      if (!node) return
      if (node.artifact_type === 'agent') {
        setSelectedAgent(nodeId)
      } else {
        setSelectedArtifact(nodeId)
      }
    },
    [data?.nodes, setSelectedAgent, setSelectedArtifact]
  )

  // Parse time range from data
  const timeRange = useMemo(() => {
    if (!data?.time_range || !data.time_range[0] || !data.time_range[1]) {
      return { start: 0, end: Date.now() }
    }
    return {
      start: new Date(data.time_range[0]).getTime(),
      end: new Date(data.time_range[1]).getTime(),
    }
  }, [data?.time_range])

  // Calculate the cutoff timestamp based on slider position
  const cutoffTime = useMemo(() => {
    const { start, end } = timeRange
    return start + ((end - start) * currentTime) / 100
  }, [timeRange, currentTime])

  // Filter nodes and edges based on current time
  const filteredData = useMemo(() => {
    if (!data) return { nodes: [], edges: [] }

    // Filter nodes that existed at cutoff time
    const filteredNodes = data.nodes.filter((node) => {
      if (!node.created_at) return true // Include nodes without timestamp
      return new Date(node.created_at).getTime() <= cutoffTime
    })

    const nodeIds = new Set(filteredNodes.map((n) => n.id))

    // Filter edges by timestamp and ensure both nodes exist
    const filteredEdges = data.edges.filter((edge) => {
      const edgeTime = new Date(edge.timestamp).getTime()
      return (
        edgeTime <= cutoffTime &&
        nodeIds.has(edge.from_id) &&
        nodeIds.has(edge.to_id)
      )
    })

    return { nodes: filteredNodes, edges: filteredEdges }
  }, [data, cutoffTime])

  // Initialize network
  useEffect(() => {
    if (!containerRef.current) return

    const options = {
      nodes: {
        font: { size: 12, color: '#e5e7eb' },
        borderWidth: 2,
      },
      edges: {
        smooth: { enabled: true, type: 'continuous', roundness: 0.5 },
        font: { size: 10, color: '#9ca3af' },
      },
      physics: {
        enabled: physics,
        stabilization: { iterations: 100 },
        barnesHut: {
          gravitationalConstant: -3000,
          springLength: 200,
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

    // Add click handler for nodes
    networkRef.current.on('click', (params) => {
      if (params.nodes.length > 0) {
        handleNodeClick(params.nodes[0] as string)
      }
    })

    return () => {
      networkRef.current?.destroy()
    }
  }, [handleNodeClick])

  // Update physics setting
  useEffect(() => {
    networkRef.current?.setOptions({ physics: { enabled: physics } })
  }, [physics])

  // Update data when filtered data changes
  useEffect(() => {
    const visNodes = buildVisNodes(filteredData.nodes)
    const visEdges = buildVisEdges(filteredData.edges)

    // Update nodes
    const existingNodeIds = nodesDataSet.current.getIds()
    const newNodeIds = visNodes.map((n) => n.id)

    // Remove deleted nodes
    const toRemove = existingNodeIds.filter((id) => !newNodeIds.includes(id as string))
    if (toRemove.length > 0) nodesDataSet.current.remove(toRemove)

    // Update/add nodes
    nodesDataSet.current.update(visNodes)

    // Update edges
    edgesDataSet.current.clear()
    edgesDataSet.current.add(visEdges)
  }, [filteredData])

  // Playback logic
  const startPlayback = useCallback(() => {
    if (playIntervalRef.current) return
    setIsPlaying(true)
    playIntervalRef.current = window.setInterval(() => {
      setCurrentTime((prev) => {
        if (prev >= 100) {
          stopPlayback()
          return 100
        }
        return Math.min(prev + 1, 100)
      })
    }, 200)
  }, [])

  const stopPlayback = useCallback(() => {
    if (playIntervalRef.current) {
      clearInterval(playIntervalRef.current)
      playIntervalRef.current = null
    }
    setIsPlaying(false)
  }, [])

  // Cleanup on unmount
  useEffect(() => {
    return () => {
      if (playIntervalRef.current) {
        clearInterval(playIntervalRef.current)
      }
    }
  }, [])

  // Format time for display
  const formatTime = (timestamp: number) => {
    const date = new Date(timestamp)
    return date.toLocaleTimeString()
  }

  return (
    <Panel
      title="Temporal Network"
      badge={filteredData.nodes.length}
      collapsible
    >
      {/* Controls */}
      <div className="flex flex-wrap items-center gap-4 mb-3">
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
          className="px-2 py-1 text-xs bg-[var(--bg-tertiary)] rounded hover:bg-[var(--accent-primary)]/20"
        >
          Fit
        </button>
        <button
          onClick={isPlaying ? stopPlayback : startPlayback}
          className="px-2 py-1 text-xs bg-[var(--bg-tertiary)] rounded hover:bg-[var(--accent-primary)]/20"
        >
          {isPlaying ? 'Pause' : 'Play'}
        </button>
        <button
          onClick={() => setCurrentTime(100)}
          className="px-2 py-1 text-xs bg-[var(--bg-tertiary)] rounded hover:bg-[var(--accent-primary)]/20"
        >
          Show All
        </button>
      </div>

      {/* Time Slider */}
      <div className="mb-3">
        <div className="flex justify-between text-xs text-[var(--text-secondary)] mb-1">
          <span>{formatTime(timeRange.start)}</span>
          <span className="font-medium text-[var(--text-primary)]">
            {formatTime(cutoffTime)}
          </span>
          <span>{formatTime(timeRange.end)}</span>
        </div>
        <input
          type="range"
          min="0"
          max="100"
          value={currentTime}
          onChange={(e) => {
            stopPlayback()
            setCurrentTime(Number(e.target.value))
          }}
          className="w-full h-2 bg-[var(--bg-tertiary)] rounded-lg appearance-none cursor-pointer accent-[var(--accent-primary)]"
        />
      </div>

      {/* Legend */}
      <div className="flex flex-wrap gap-3 mb-3 text-xs">
        <span className="text-[var(--text-secondary)] font-medium">Nodes:</span>
        <div className="flex items-center gap-1">
          <span className="w-3 h-3 rounded-full bg-green-500" />
          <span>Agent</span>
        </div>
        <div className="flex items-center gap-1">
          <span className="w-3 h-3 bg-blue-500" style={{ clipPath: 'polygon(50% 0%, 100% 50%, 50% 100%, 0% 50%)' }} />
          <span>Genesis</span>
        </div>
        <div className="flex items-center gap-1">
          <span className="w-3 h-3 bg-purple-500 rotate-45" />
          <span>Contract</span>
        </div>
        <div className="flex items-center gap-1">
          <span className="w-3 h-3 bg-gray-500" />
          <span>Data</span>
        </div>
      </div>
      <div className="flex flex-wrap gap-3 mb-3 text-xs">
        <span className="text-[var(--text-secondary)] font-medium">Edges:</span>
        <div className="flex items-center gap-1">
          <span className="w-4 h-0.5 bg-orange-500" />
          <span>Invocation</span>
        </div>
        <div className="flex items-center gap-1">
          <span className="w-4 h-0.5 bg-purple-500" />
          <span>Ownership</span>
        </div>
        <div className="flex items-center gap-1">
          <span className="w-4 h-0.5 bg-green-500" />
          <span>Creation</span>
        </div>
        <div className="flex items-center gap-1">
          <span className="w-4 h-0.5 bg-blue-500" />
          <span>Transfer</span>
        </div>
      </div>

      {isLoading && (
        <div className={`${fullHeight ? 'h-[calc(100vh-320px)]' : 'h-64'} flex items-center justify-center`}>
          <div className="animate-spin w-8 h-8 border-2 border-[var(--accent-primary)] border-t-transparent rounded-full" />
        </div>
      )}

      {error && (
        <p className="text-[var(--accent-danger)] text-sm">
          Failed to load temporal network: {error.message}
        </p>
      )}

      <div
        ref={containerRef}
        className={`${fullHeight ? 'h-[calc(100vh-320px)]' : 'h-64'} bg-[var(--bg-primary)] rounded`}
        style={{ minHeight: fullHeight ? '400px' : '256px' }}
      />

      {data && filteredData.nodes.length === 0 && (
        <p className="text-sm text-[var(--text-secondary)] text-center mt-2">
          No artifacts yet
        </p>
      )}

      {/* Stats */}
      {data && (
        <div className="mt-3 flex gap-4 text-xs text-[var(--text-secondary)]">
          <span>
            Showing: {filteredData.nodes.length} / {data.total_artifacts} artifacts
          </span>
          <span>
            {filteredData.edges.length} / {data.total_interactions} interactions
          </span>
        </div>
      )}
    </Panel>
  )
}
