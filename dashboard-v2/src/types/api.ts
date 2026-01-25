// API Types - Based on FastAPI Pydantic models
// TODO: Auto-generate from OpenAPI spec

export interface AgentSummary {
  agent_id: string
  scrip: number
  llm_tokens_used: number
  llm_tokens_quota: number
  disk_used: number
  disk_quota: number
  status: 'active' | 'idle' | 'frozen' | 'bankrupt'
  action_count: number
  last_action_tick: number | null
  llm_budget_remaining: number
  llm_budget_initial: number
}

export interface AgentDetail extends AgentSummary {
  actions: ActionEvent[]
  artifacts_owned: string[]
  thinking_history: ThinkingEvent[]
}

export interface AgentConfig {
  config_found: boolean
  llm_model: string | null
  starting_credits: number
  enabled: boolean
  temperature: number | null
  max_tokens: number | null
  genotype: Record<string, string | number | boolean> | null
  rag: Record<string, unknown> | null
  workflow: Record<string, unknown> | null
  error_handling: Record<string, unknown> | null
}

export interface ArtifactInfo {
  artifact_id: string
  artifact_type: string
  created_by: string
  executable: boolean
  price: number
  size_bytes: number
  mint_score: number | null
  mint_status: string
  access_contract_id: string | null
  invocation_count: number
}

export interface ArtifactDetail extends ArtifactInfo {
  content: string | null
  methods: string[]
  interface_schema: Record<string, unknown> | null
  ownership_history: OwnershipTransfer[]
  invocation_history: InvocationEvent[]
}

export interface OwnershipTransfer {
  tick: number
  from_id: string | null
  to_id: string
  timestamp: string
}

export interface ActionEvent {
  tick: number
  action_type: string
  target_id: string | null
  success: boolean
  error: string | null
  llm_cost: number
  scrip_cost: number
}

export interface ThinkingEvent {
  tick: number
  input_tokens: number
  output_tokens: number
  thinking_cost: number
  reasoning: string | null
}

export interface InvocationEvent {
  tick: number
  invoker_id: string
  method: string | null
  success: boolean
  duration_ms: number | null
  error: string | null
}

export interface ProgressData {
  current_tick: number
  elapsed_seconds: number
  api_budget_spent: number
  api_budget_limit: number
  status: string
  events_per_second: number
}

export interface RawEvent {
  timestamp: string
  event_type: string
  data: Record<string, unknown>
}

export interface ActivityItem {
  tick: number
  timestamp: string
  activity_type: string
  agent_id: string | null
  target_id: string | null
  amount: number | null
  description: string
  details: Record<string, unknown> | null
}

export interface GenesisActivitySummary {
  mint: {
    pending_count: number
    recent_scores: number[]
    total_scrip_minted: number
  }
  escrow: {
    active_listings: number
    recent_trades: number
  }
  ledger: {
    recent_transfers: number
    recent_spawns: number
    ownership_transfers: number
  }
}

export interface NetworkNode {
  id: string
  label: string
  node_type: 'agent' | 'artifact'
  scrip?: number
  status?: string
}

export interface NetworkEdge {
  from: string
  to: string
  interaction_type: string
  tick: number
  weight: number
}

export interface NetworkGraphData {
  nodes: NetworkNode[]
  edges: NetworkEdge[]
  tick_range: [number, number]
}

// Paginated response wrapper
export interface PaginatedResponse<T> {
  items: T[]
  total: number
  limit: number
  offset: number
}

export interface AgentsResponse {
  agents: AgentSummary[]
  total: number
  limit: number
  offset: number
}

export interface ArtifactsResponse {
  artifacts: ArtifactInfo[]
  total: number
  limit: number
  offset: number
}

export interface EventsResponse {
  events: RawEvent[]
  total: number
}

export interface ActivityResponse {
  items: ActivityItem[]
  total_count: number
}

// ============================================================================
// CHARTS
// ============================================================================

export interface ChartDataPoint {
  tick: number
  value: number
  label?: string
}

export interface AgentChartData {
  agent_id: string
  data: ChartDataPoint[]
}

export interface ResourceChartData {
  resource_name: string
  agents: AgentChartData[]
  totals: ChartDataPoint[]
}

// ============================================================================
// KPIs
// ============================================================================

export interface KPIsData {
  total_scrip: number
  scrip_velocity: number
  gini_coefficient: number
  median_scrip: number
  active_agent_ratio: number
  frozen_agent_count: number
  actions_per_second: number
  thinking_cost_rate: number
  escrow_volume: number
  escrow_active_listings: number
  mint_scrip_rate: number
  artifact_creation_rate: number
  llm_budget_remaining: number
  llm_budget_burn_rate: number
  agent_spawn_rate: number
  coordination_events: number
  artifact_diversity: number
  scrip_velocity_trend: 'up' | 'down' | 'stable'
  activity_trend: 'up' | 'down' | 'stable'
  gini_coefficient_trend: 'up' | 'down' | 'stable'
  active_agent_ratio_trend: 'up' | 'down' | 'stable'
  frozen_count_trend: 'up' | 'down' | 'stable'
}

// ============================================================================
// EMERGENCE
// ============================================================================

export interface EmergenceMetrics {
  coordination_density: number
  specialization_index: number
  reuse_ratio: number
  genesis_independence: number
  capital_depth: number
  coalition_count: number
}
