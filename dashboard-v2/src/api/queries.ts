// TanStack Query hooks for API endpoints

import { useQuery } from '@tanstack/react-query'
import { apiFetch, buildQueryString } from './client'
import type {
  AgentsResponse,
  AgentDetail,
  AgentConfig,
  ArtifactsResponse,
  ArtifactDetail,
  ProgressData,
  GenesisActivitySummary,
  NetworkGraphData,
  ActivityResponse,
  EventsResponse,
} from '../types/api'

// ============================================================================
// PROGRESS
// ============================================================================

export function useProgress() {
  return useQuery({
    queryKey: ['progress'],
    queryFn: () => apiFetch<ProgressData>('/progress'),
    refetchInterval: 2000,
  })
}

// ============================================================================
// AGENTS
// ============================================================================

export function useAgents(page: number = 0, limit: number = 25) {
  const offset = page * limit
  return useQuery({
    queryKey: ['agents', page, limit],
    queryFn: () =>
      apiFetch<AgentsResponse>(`/agents${buildQueryString({ limit, offset })}`),
    refetchInterval: 5000,
  })
}

export function useAgent(agentId: string | null) {
  return useQuery({
    queryKey: ['agent', agentId],
    queryFn: () => apiFetch<AgentDetail>(`/agents/${encodeURIComponent(agentId!)}`),
    enabled: !!agentId,
  })
}

export function useAgentConfig(agentId: string | null) {
  return useQuery({
    queryKey: ['agentConfig', agentId],
    queryFn: () =>
      apiFetch<AgentConfig>(`/agents/${encodeURIComponent(agentId!)}/config`),
    enabled: !!agentId,
  })
}

// ============================================================================
// ARTIFACTS
// ============================================================================

export function useArtifacts(
  page: number = 0,
  limit: number = 25,
  search?: string
) {
  const offset = page * limit
  return useQuery({
    queryKey: ['artifacts', page, limit, search],
    queryFn: () =>
      apiFetch<ArtifactsResponse>(
        `/artifacts${buildQueryString({ limit, offset, search })}`
      ),
    refetchInterval: 5000,
  })
}

export function useArtifactDetail(artifactId: string | null) {
  return useQuery({
    queryKey: ['artifactDetail', artifactId],
    queryFn: () =>
      apiFetch<ArtifactDetail>(
        `/artifacts/${encodeURIComponent(artifactId!)}/detail`
      ),
    enabled: !!artifactId,
  })
}

// ============================================================================
// GENESIS
// ============================================================================

export function useGenesis() {
  return useQuery({
    queryKey: ['genesis'],
    queryFn: () => apiFetch<GenesisActivitySummary>('/genesis'),
    refetchInterval: 5000,
  })
}

// ============================================================================
// NETWORK
// ============================================================================

export function useNetwork(tickMax?: number) {
  return useQuery({
    queryKey: ['network', tickMax],
    queryFn: () =>
      apiFetch<NetworkGraphData>(`/network${buildQueryString({ tick_max: tickMax })}`),
    refetchInterval: 10000,
  })
}

// ============================================================================
// TEMPORAL NETWORK (Plan #107)
// ============================================================================

import type { TemporalNetworkData } from '../types/api'

export function useTemporalNetwork(timeMin?: string, timeMax?: string) {
  const params = {
    time_min: timeMin,
    time_max: timeMax,
  }

  return useQuery({
    queryKey: ['temporalNetwork', params],
    queryFn: () =>
      apiFetch<TemporalNetworkData>(`/temporal-network${buildQueryString(params)}`),
    refetchInterval: 10000,
  })
}

// ============================================================================
// EVENTS
// ============================================================================

export function useEvents(options?: {
  limit?: number
  offset?: number
  eventTypes?: string
  agentId?: string
  artifactId?: string
  tickMin?: number
  tickMax?: number
}) {
  const params = {
    limit: options?.limit ?? 50,
    offset: options?.offset ?? 0,
    event_types: options?.eventTypes,
    agent_id: options?.agentId,
    artifact_id: options?.artifactId,
    tick_min: options?.tickMin,
    tick_max: options?.tickMax,
  }

  return useQuery({
    queryKey: ['events', params],
    queryFn: () => apiFetch<EventsResponse>(`/events${buildQueryString(params)}`),
    refetchInterval: 5000,
  })
}

// ============================================================================
// ACTIVITY FEED
// ============================================================================

export function useActivity(options?: {
  limit?: number
  offset?: number
  types?: string
  agentId?: string
  artifactId?: string
}) {
  const params = {
    limit: options?.limit ?? 50,
    offset: options?.offset ?? 0,
    types: options?.types,
    agent_id: options?.agentId,
    artifact_id: options?.artifactId,
  }

  return useQuery({
    queryKey: ['activity', params],
    queryFn: () => apiFetch<ActivityResponse>(`/activity${buildQueryString(params)}`),
    refetchInterval: 3000,
  })
}

// ============================================================================
// THINKING
// ============================================================================

export function useThinking(options?: {
  agentId?: string
  tickMin?: number
  tickMax?: number
  limit?: number
}) {
  const params = {
    agent_id: options?.agentId,
    tick_min: options?.tickMin,
    tick_max: options?.tickMax,
    limit: options?.limit ?? 50,
  }

  return useQuery({
    queryKey: ['thinking', params],
    queryFn: () =>
      apiFetch<{ items: unknown[]; total_count: number }>(
        `/thinking${buildQueryString(params)}`
      ),
    refetchInterval: 5000,
  })
}

// ============================================================================
// CHARTS
// ============================================================================

import type { ResourceChartData, KPIsData, EmergenceMetrics } from '../types/api'

export function useScripChart() {
  return useQuery({
    queryKey: ['charts', 'scrip'],
    queryFn: () => apiFetch<ResourceChartData>('/charts/scrip'),
    refetchInterval: 5000,
  })
}

export function useLLMTokensChart() {
  return useQuery({
    queryKey: ['charts', 'llm_tokens'],
    queryFn: () => apiFetch<ResourceChartData>('/charts/llm_tokens'),
    refetchInterval: 5000,
  })
}

// ============================================================================
// KPIs
// ============================================================================

export function useKPIs() {
  return useQuery({
    queryKey: ['kpis'],
    queryFn: () => apiFetch<KPIsData>('/kpis'),
    refetchInterval: 5000,
  })
}

// ============================================================================
// EMERGENCE
// ============================================================================

export function useEmergence() {
  return useQuery({
    queryKey: ['emergence'],
    queryFn: () => apiFetch<EmergenceMetrics>('/emergence'),
    refetchInterval: 5000,
  })
}


// ============================================================================
// CAPITAL FLOW
// ============================================================================

import type { CapitalFlowData, DependencyGraphData } from '../types/api'

export function useCapitalFlow(timeMin?: string, timeMax?: string) {
  const params = {
    time_min: timeMin,
    time_max: timeMax,
  }

  return useQuery({
    queryKey: ['capitalFlow', params],
    queryFn: () => apiFetch<CapitalFlowData>(`/capital-flow${buildQueryString(params)}`),
    refetchInterval: 10000,
  })
}

// ============================================================================
// DEPENDENCY GRAPH
// ============================================================================

export function useDependencyGraph() {
  return useQuery({
    queryKey: ['dependencyGraph'],
    queryFn: () => apiFetch<DependencyGraphData>('/artifacts/dependency-graph'),
    refetchInterval: 10000,
  })
}

// ============================================================================
// SEARCH
// ============================================================================

import type { SearchResponse } from '../types/api'

export function useSearch(query: string, limit: number = 10) {
  return useQuery({
    queryKey: ['search', query, limit],
    queryFn: () =>
      apiFetch<SearchResponse>(`/search${buildQueryString({ q: query, limit })}`),
    enabled: query.length >= 1,
    staleTime: 30000, // Cache for 30 seconds
  })
}

// ============================================================================
// SIMULATION CONTROL
// ============================================================================

import type { SimulationStatus } from '../types/api'

export function useSimulationStatus() {
  return useQuery({
    queryKey: ['simulationStatus'],
    queryFn: () => apiFetch<SimulationStatus>('/simulation/status'),
    refetchInterval: 2000,
  })
}

export async function pauseSimulation(): Promise<{ status: string; tick: number }> {
  return apiFetch('/simulation/pause', { method: 'POST' })
}

export async function resumeSimulation(): Promise<{ status: string; tick: number }> {
  return apiFetch('/simulation/resume', { method: 'POST' })
}

import type { SimulationStartRequest, SimulationStartResponse, SimulationStopResponse } from '../types/api'

export async function startSimulation(config: SimulationStartRequest): Promise<SimulationStartResponse> {
  const params = new URLSearchParams()
  if (config.duration !== undefined) params.set('duration', String(config.duration))
  if (config.agents !== undefined) params.set('agents', String(config.agents))
  if (config.budget !== undefined) params.set('budget', String(config.budget))
  if (config.model !== undefined) params.set('model', config.model)
  if (config.rate_limit_delay !== undefined) params.set('rate_limit_delay', String(config.rate_limit_delay))

  return apiFetch(`/simulation/start?${params.toString()}`, { method: 'POST' })
}

export async function stopSimulation(): Promise<SimulationStopResponse> {
  return apiFetch('/simulation/stop', { method: 'POST' })
}
