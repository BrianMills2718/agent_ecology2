"""Pydantic models for dashboard API responses."""

from __future__ import annotations

from datetime import datetime
from pydantic import BaseModel, Field, field_validator
from typing import Any, Literal


class ResourceBalance(BaseModel):
    """Balance for a single resource."""
    current: float
    quota: float
    used: float = 0


class AgentSummary(BaseModel):
    """Summary of agent for list view."""
    agent_id: str
    scrip: int = 0
    llm_tokens_used: float = 0
    llm_tokens_quota: float = 0
    disk_used: float = 0
    disk_quota: float = 0
    status: Literal["active", "low_resources", "frozen"] = "active"
    action_count: int = 0
    last_action_tick: int | None = None
    # Plan #153: LLM budget tracking in $
    llm_budget_initial: float = 0.0
    llm_budget_spent: float = 0.0
    llm_budget_remaining: float = 0.0


class LLMBudgetInfo(BaseModel):
    """LLM budget information (Plan #153)."""
    initial: float = 0.0  # Starting budget in $
    spent: float = 0.0  # Total spent in $
    remaining: float = 0.0  # Budget left in $


class AgentDetail(BaseModel):
    """Full agent detail with history."""
    agent_id: str
    scrip: int = 0
    llm_tokens: ResourceBalance
    disk: ResourceBalance
    llm_budget: LLMBudgetInfo = Field(default_factory=LLMBudgetInfo)  # Plan #153
    status: Literal["active", "low_resources", "frozen"] = "active"
    actions: list[ActionEvent] = Field(default_factory=list)
    artifacts_owned: list[str] = Field(default_factory=list)
    thinking_history: list[ThinkingEvent] = Field(default_factory=list)


class ArtifactInfo(BaseModel):
    """Artifact information."""
    artifact_id: str
    artifact_type: str
    created_by: str
    executable: bool = False
    price: int = 0
    size_bytes: int = 0
    created_at: str
    updated_at: str
    mint_score: float | None = None
    mint_status: Literal["pending", "scored", "none"] = "none"
    access_contract_id: str = "kernel_contract_freeware"  # Plan #133


class ActionEvent(BaseModel):
    """Action event from the timeline."""
    tick: int
    timestamp: str
    agent_id: str
    action_type: str
    target: str | None = None
    llm_tokens_cost: float = 0
    scrip_cost: int = 0
    success: bool = True
    error: str | None = None
    result: Any = None


class ThinkingEvent(BaseModel):
    """Agent thinking event."""
    tick: int
    timestamp: str
    agent_id: str
    input_tokens: int = 0
    output_tokens: int = 0
    thinking_cost: float = 0
    success: bool = True
    error: str | None = None
    reasoning: str | None = None  # Agent's reasoning (Plan #132: standardized field)


class InvocationEvent(BaseModel):
    """Single invocation event (success or failure)."""
    tick: int
    timestamp: str
    invoker_id: str
    artifact_id: str
    method: str
    success: bool
    duration_ms: float = 0.0
    error_type: str | None = None
    error_message: str | None = None
    result_type: str | None = None


class InvocationStatsResponse(BaseModel):
    """Invocation statistics for an artifact."""
    artifact_id: str
    total_invocations: int = 0
    successful: int = 0
    failed: int = 0
    success_rate: float = 0.0
    avg_duration_ms: float = 0.0
    failure_types: dict[str, int] = Field(default_factory=dict)


class TickSummary(BaseModel):
    """Summary of a single tick."""
    tick: int
    timestamp: str
    agent_count: int = 0
    action_count: int = 0
    total_llm_tokens_used: float = 0
    total_scrip_transferred: int = 0
    artifacts_created: int = 0
    mint_results: int = 0


class GenesisMintStatus(BaseModel):
    """Mint submission status."""
    pending_count: int = 0
    pending_artifacts: list[str] = Field(default_factory=list)
    recent_scores: list[MintScore] = Field(default_factory=list)
    total_scrip_minted: int = 0


class MintScore(BaseModel):
    """Single mint score."""
    artifact_id: str
    submitter: str
    score: float
    scrip_minted: int
    timestamp: str


class EscrowListing(BaseModel):
    """Escrow listing info."""
    artifact_id: str
    seller_id: str
    price: int
    buyer_id: str | None = None
    status: Literal["active", "sold", "cancelled"] = "active"


class GenesisEscrowStatus(BaseModel):
    """Escrow status summary."""
    active_listings: list[EscrowListing] = Field(default_factory=list)
    recent_trades: list[EscrowTrade] = Field(default_factory=list)


class EscrowTrade(BaseModel):
    """Completed escrow trade."""
    artifact_id: str
    seller_id: str
    buyer_id: str
    price: int
    timestamp: str


class LedgerTransfer(BaseModel):
    """Ledger transfer event."""
    from_id: str
    to_id: str
    amount: int
    timestamp: str
    tick: int


class GenesisLedgerStatus(BaseModel):
    """Ledger activity summary."""
    recent_transfers: list[LedgerTransfer] = Field(default_factory=list)
    recent_spawns: list[str] = Field(default_factory=list)
    recent_ownership_transfers: list[OwnershipTransfer] = Field(default_factory=list)


class OwnershipTransfer(BaseModel):
    """Artifact ownership transfer."""
    artifact_id: str
    from_id: str
    to_id: str
    timestamp: str


class GenesisActivitySummary(BaseModel):
    """Combined genesis artifact activity."""
    mint: GenesisMintStatus
    escrow: GenesisEscrowStatus
    ledger: GenesisLedgerStatus


class SimulationProgress(BaseModel):
    """Overall simulation progress."""
    current_tick: int = 0  # Event counter (not a limit)
    api_cost_spent: float = 0
    api_cost_limit: float = 1.0
    start_time: str | None = None
    elapsed_seconds: float = 0
    events_per_second: float = 0  # Renamed from ticks_per_second
    status: Literal["running", "paused", "completed", "budget_exhausted"] = "running"


class SimulationState(BaseModel):
    """Complete simulation state snapshot."""
    progress: SimulationProgress
    agents: list[AgentSummary] = Field(default_factory=list)
    artifacts: list[ArtifactInfo] = Field(default_factory=list)
    genesis: GenesisActivitySummary | None = None
    recent_events: list[RawEvent] = Field(default_factory=list)


class RawEvent(BaseModel):
    """Raw event from JSONL log."""
    timestamp: str
    event_type: str
    data: dict[str, Any] = Field(default_factory=dict)

    @field_validator("timestamp", mode="before")
    @classmethod
    def normalize_timestamp(cls, v: str | float | int) -> str:
        """Accept both ISO string and Unix float timestamps."""
        if isinstance(v, (int, float)):
            return datetime.fromtimestamp(v).isoformat()
        return v


class ChartDataPoint(BaseModel):
    """Single data point for charts."""
    tick: int
    value: float
    label: str | None = None
    timestamp: str | None = None  # ISO timestamp for time-based charts


class AgentChartData(BaseModel):
    """Chart data for a single agent."""
    agent_id: str
    data: list[ChartDataPoint] = Field(default_factory=list)


class ResourceChartData(BaseModel):
    """Resource utilization chart data."""
    resource_name: str
    agents: list[AgentChartData] = Field(default_factory=list)
    totals: list[ChartDataPoint] = Field(default_factory=list)


class EconomicFlowData(BaseModel):
    """Data for economic flow visualization."""
    nodes: list[FlowNode] = Field(default_factory=list)
    links: list[FlowLink] = Field(default_factory=list)


class FlowNode(BaseModel):
    """Node in flow diagram."""
    id: str
    name: str
    type: Literal["agent", "artifact", "genesis"] = "agent"


class FlowLink(BaseModel):
    """Link in flow diagram."""
    source: str
    target: str
    value: int
    tick: int | None = None


# Network Graph Models

class Interaction(BaseModel):
    """Single interaction between agents."""
    tick: int
    timestamp: str
    from_id: str
    to_id: str
    interaction_type: Literal["scrip_transfer", "escrow_trade", "ownership_transfer", "artifact_invoke", "genesis_invoke"]
    amount: int | None = None  # For scrip transfers
    artifact_id: str | None = None  # For trades/ownership/invokes
    details: str | None = None  # Human-readable description


class NetworkNode(BaseModel):
    """Node in the network graph."""
    id: str
    label: str
    node_type: Literal["agent", "genesis", "artifact"] = "agent"
    scrip: int = 0
    status: Literal["active", "low_resources", "frozen"] = "active"


class NetworkEdge(BaseModel):
    """Edge in the network graph."""
    from_id: str
    to_id: str
    interaction_type: str
    tick: int
    weight: int = 1  # For aggregated views
    label: str | None = None


class NetworkGraphData(BaseModel):
    """Complete network graph data."""
    nodes: list[NetworkNode] = Field(default_factory=list)
    edges: list[NetworkEdge] = Field(default_factory=list)
    interactions: list[Interaction] = Field(default_factory=list)
    tick_range: tuple[int, int] = (0, 0)


# Temporal Network Models (Plan #107)


class ArtifactNode(BaseModel):
    """Node representing any artifact in the temporal network.

    Unlike NetworkNode which only shows agents, this includes ALL artifacts:
    agents, genesis services, contracts, and data artifacts.
    """
    id: str
    label: str
    artifact_type: Literal["agent", "genesis", "contract", "data", "unknown"] = "unknown"
    created_by: str | None = None
    executable: bool = False
    invocation_count: int = 0
    created_at: str | None = None  # ISO timestamp
    # For agents specifically
    scrip: int = 0
    status: Literal["active", "low_resources", "frozen"] = "active"


class ArtifactEdge(BaseModel):
    """Edge representing relationship between artifacts.

    Supports multiple edge types for richer visualization:
    - invocation: A called B
    - ownership: A owns B
    - dependency: A depends on B (from artifact metadata)
    - creation: A created B
    - transfer: ownership transferred from A to B
    """
    from_id: str
    to_id: str
    edge_type: Literal["invocation", "ownership", "dependency", "creation", "transfer"]
    timestamp: str  # ISO format timestamp
    weight: int = 1
    details: str | None = None


class TemporalNetworkData(BaseModel):
    """Artifact-centric temporal network graph data.

    Provides a complete view of the artifact ecosystem over time,
    including all artifacts as nodes and multiple relationship types as edges.
    """
    nodes: list[ArtifactNode] = Field(default_factory=list)
    edges: list[ArtifactEdge] = Field(default_factory=list)
    time_range: tuple[str, str] = ("", "")  # (start, end) ISO timestamps
    # Activity counts per time bucket for heatmap (bucket key = ISO timestamp)
    activity_by_time: dict[str, dict[str, int]] = Field(default_factory=dict)
    # Metadata
    total_artifacts: int = 0
    total_interactions: int = 0
    # Time bucket size in seconds (for heatmap grouping)
    time_bucket_seconds: int = 1


# Activity Feed Models

class ActivityItem(BaseModel):
    """Single item in the activity feed."""
    tick: int
    timestamp: str
    activity_type: Literal[
        "artifact_created", "artifact_updated", "escrow_listed", "escrow_purchased",
        "escrow_cancelled", "scrip_transfer", "ownership_transfer", "mint_result",
        "principal_spawned", "thinking", "action"
    ]
    agent_id: str | None = None
    target_id: str | None = None  # Other agent or artifact
    amount: int | None = None
    artifact_id: str | None = None
    description: str
    details: dict[str, Any] = Field(default_factory=dict)


class ActivityFeed(BaseModel):
    """Activity feed response."""
    items: list[ActivityItem] = Field(default_factory=list)
    total_count: int = 0


# Artifact Detail Models

class ArtifactDetail(BaseModel):
    """Full artifact detail with content."""
    artifact_id: str
    artifact_type: str
    created_by: str
    executable: bool = False
    price: int = 0
    size_bytes: int = 0
    created_at: str
    updated_at: str
    content: str | None = None  # The actual code/data
    methods: list[str] = Field(default_factory=list)  # For executable artifacts
    mint_score: float | None = None
    mint_status: Literal["pending", "scored", "none"] = "none"
    invocation_count: int = 0
    ownership_history: list[OwnershipTransfer] = Field(default_factory=list)
    invocation_history: list[ActionEvent] = Field(default_factory=list)
    # Interface schema for discoverability (Plan #54)
    interface: dict[str, Any] | None = None
    # Access control contract (Plan #133)
    access_contract_id: str = "kernel_contract_freeware"


# Dependency Graph Models (Plan #64)


class DependencyNode(BaseModel):
    """Node in the artifact dependency graph."""

    artifact_id: str
    name: str
    owner: str
    artifact_type: str
    is_genesis: bool = False
    usage_count: int = 0
    created_at: datetime
    depth: int = 0  # Distance from root (no dependencies)
    lindy_score: float = 0.0  # age_days × unique_invokers


class DependencyEdge(BaseModel):
    """Edge representing a dependency relationship."""

    source: str  # The artifact that depends on target
    target: str  # The artifact being depended on


class DependencyGraphMetrics(BaseModel):
    """Computed metrics for the dependency graph."""

    max_depth: int = 0  # Longest path from any root
    avg_fanout: float = 0.0  # Mean dependents per node
    genesis_dependency_ratio: float = 0.0  # Genesis deps / total deps
    orphan_count: int = 0  # Artifacts with no dependents
    total_nodes: int = 0
    total_edges: int = 0


class DependencyGraphData(BaseModel):
    """Complete dependency graph data for visualization."""

    nodes: list[DependencyNode] = Field(default_factory=list)
    edges: list[DependencyEdge] = Field(default_factory=list)
    metrics: DependencyGraphMetrics = Field(default_factory=DependencyGraphMetrics)


# Ecosystem Health KPIs


# Emergence Observability Metrics (Plan #110 Phase 3)


class EmergenceMetrics(BaseModel):
    """Metrics for detecting emergent organization patterns.

    These metrics measure structural properties of the agent ecosystem
    to detect emergent coordination, specialization, and infrastructure building.
    """

    # Network metrics
    coordination_density: float = 0.0  # interactions / (n × (n-1))
    coalition_count: int = 0  # Number of interaction clusters

    # Specialization metrics
    specialization_index: float = 0.0  # std_dev of action type distributions

    # Infrastructure metrics
    reuse_ratio: float = 0.0  # artifacts_used_by_others / total_artifacts
    genesis_independence: float = 0.0  # non_genesis_ops / total_ops
    capital_depth: int = 0  # max(dependency_chain_length)

    # Metadata
    agent_count: int = 0
    total_interactions: int = 0
    total_artifacts: int = 0
    genesis_invocations: int = 0
    non_genesis_invocations: int = 0

    # Per-agent specialization data (for drill-down)
    agent_specializations: dict[str, dict[str, int]] = Field(
        default_factory=dict
    )  # agent_id -> {action_type: count}


# Pairwise Interactions (Plan #110 Phase 3.1)


class PairwiseInteractionSummary(BaseModel):
    """Summary of interactions between two specific agents."""

    from_agent: str
    to_agent: str
    interactions: list[Interaction] = Field(default_factory=list)
    total_count: int = 0

    # Breakdown by type
    scrip_transfers: int = 0
    scrip_total: int = 0  # Total scrip transferred
    escrow_trades: int = 0
    ownership_transfers: int = 0
    artifact_invocations: int = 0
    genesis_invocations: int = 0

    # Bidirectional summary
    bidirectional: bool = False  # True if both directions exist


# Capital Flow (Plan #110 Phase 3.4)


class CapitalFlowNode(BaseModel):
    """Node in capital flow sankey diagram."""

    id: str
    name: str
    node_type: Literal["agent", "genesis", "artifact"] = "agent"


class CapitalFlowLink(BaseModel):
    """Link in capital flow sankey diagram."""

    source: str
    target: str
    value: int  # Total scrip transferred
    count: int = 1  # Number of transfers


class CapitalFlowData(BaseModel):
    """Data for capital flow sankey visualization."""

    nodes: list[CapitalFlowNode] = Field(default_factory=list)
    links: list[CapitalFlowLink] = Field(default_factory=list)
    time_range: tuple[str, str] = ("", "")  # ISO timestamps
    total_flow: int = 0


# Standard Library Detection (Plan #110 Phase 3.3)


class StandardArtifact(BaseModel):
    """Artifact with high Lindy score (standard library candidate)."""

    artifact_id: str
    name: str
    owner: str
    artifact_type: str
    lindy_score: float  # age_days × unique_invokers
    age_days: float
    unique_invokers: int
    total_invocations: int
    is_genesis: bool = False
