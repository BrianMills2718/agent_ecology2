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
