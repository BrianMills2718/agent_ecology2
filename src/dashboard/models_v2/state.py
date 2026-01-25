"""State models for agents, artifacts, and world.

These models represent the current state built from events,
separate from the raw event models.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Literal

from pydantic import BaseModel


@dataclass
class ResourceUsage:
    """Resource usage for a principal."""

    used: float = 0.0
    quota: float = 0.0
    rate_remaining: float | None = None  # For renewable resources


@dataclass
class AgentState:
    """Current state of an agent built from events."""

    agent_id: str
    status: Literal["active", "frozen", "terminated"] = "active"
    scrip: float = 0.0

    # Resource tracking (per ADR-0020 resource types)
    llm_tokens: ResourceUsage = field(default_factory=ResourceUsage)
    llm_budget: ResourceUsage = field(default_factory=ResourceUsage)
    disk: ResourceUsage = field(default_factory=ResourceUsage)

    # Activity tracking
    action_count: int = 0
    action_successes: int = 0
    action_failures: int = 0
    last_sequence: int | None = None

    # Owned artifacts
    artifacts_owned: list[str] = field(default_factory=list)

    # History (optional, for detail views)
    action_history: list[dict[str, Any]] = field(default_factory=list)
    thinking_history: list[dict[str, Any]] = field(default_factory=list)

    @property
    def llm_tokens_used(self) -> float:
        """Backwards compatibility."""
        return self.llm_tokens.used

    @property
    def llm_tokens_quota(self) -> float:
        """Backwards compatibility."""
        return self.llm_tokens.quota

    @property
    def disk_used(self) -> float:
        """Backwards compatibility."""
        return self.disk.used

    @property
    def disk_quota(self) -> float:
        """Backwards compatibility."""
        return self.disk.quota

    @property
    def llm_budget_spent(self) -> float:
        """Backwards compatibility."""
        return self.llm_budget.used

    @property
    def llm_budget_initial(self) -> float:
        """Backwards compatibility."""
        return self.llm_budget.quota


@dataclass
class OwnershipRecord:
    """Record of an ownership transfer."""

    from_id: str
    to_id: str
    timestamp: str
    sequence: int


@dataclass
class ArtifactState:
    """Current state of an artifact built from events."""

    artifact_id: str
    artifact_type: str
    owner: str
    created_by: str

    # Artifact metadata
    executable: bool = False
    price: float = 0.0
    size_bytes: int = 0
    created_at: str = ""
    updated_at: str = ""
    content: str | None = None

    # Interface for discoverability
    interface: dict[str, Any] | None = None
    methods: list[str] = field(default_factory=list)

    # Mint scoring
    mint_score: float | None = None
    mint_status: Literal["pending", "scored", "none"] = "none"

    # Activity tracking
    invocation_count: int = 0
    invocation_history: list[dict[str, Any]] = field(default_factory=list)

    # Ownership history
    ownership_history: list[OwnershipRecord] = field(default_factory=list)

    # Dependencies (Plan #63)
    depends_on: list[str] = field(default_factory=list)


@dataclass
class GenesisServiceState:
    """State of a genesis service (ledger, escrow, mint)."""

    service_id: str
    total_invocations: int = 0
    recent_activity: list[dict[str, Any]] = field(default_factory=list)


@dataclass
class WorldState:
    """Global simulation state built from events."""

    # Current sequence number
    sequence: int = 0

    # Simulation metrics
    simulation_time: float = 0.0
    total_scrip: float = 0.0
    total_artifacts: int = 0
    active_agents: int = 0

    # Entity collections
    agents: dict[str, AgentState] = field(default_factory=dict)
    artifacts: dict[str, ArtifactState] = field(default_factory=dict)

    # Genesis services
    genesis_services: dict[str, GenesisServiceState] = field(default_factory=dict)

    # Event counts by type
    event_counts: dict[str, int] = field(default_factory=dict)

    def get_agent(self, agent_id: str) -> AgentState | None:
        """Get agent state by ID."""
        return self.agents.get(agent_id)

    def get_artifact(self, artifact_id: str) -> ArtifactState | None:
        """Get artifact state by ID."""
        return self.artifacts.get(artifact_id)

    def get_or_create_agent(self, agent_id: str) -> AgentState:
        """Get or create agent state."""
        if agent_id not in self.agents:
            self.agents[agent_id] = AgentState(agent_id=agent_id)
        return self.agents[agent_id]

    def get_or_create_artifact(
        self,
        artifact_id: str,
        artifact_type: str = "unknown",
        owner: str = "unknown",
        created_by: str = "unknown",
    ) -> ArtifactState:
        """Get or create artifact state."""
        if artifact_id not in self.artifacts:
            self.artifacts[artifact_id] = ArtifactState(
                artifact_id=artifact_id,
                artifact_type=artifact_type,
                owner=owner,
                created_by=created_by,
            )
        return self.artifacts[artifact_id]


# Pydantic versions for API responses


class AgentStateResponse(BaseModel):
    """Agent state for API responses."""

    agent_id: str
    status: str = "active"
    scrip: float = 0.0
    llm_tokens_used: float = 0.0
    llm_tokens_quota: float = 0.0
    llm_budget_spent: float = 0.0
    llm_budget_initial: float = 0.0
    disk_used: float = 0.0
    disk_quota: float = 0.0
    action_count: int = 0
    action_successes: int = 0
    action_failures: int = 0
    artifacts_owned: list[str] = []

    @classmethod
    def from_state(cls, state: AgentState) -> "AgentStateResponse":
        """Create from internal state."""
        return cls(
            agent_id=state.agent_id,
            status=state.status,
            scrip=state.scrip,
            llm_tokens_used=state.llm_tokens.used,
            llm_tokens_quota=state.llm_tokens.quota,
            llm_budget_spent=state.llm_budget.used,
            llm_budget_initial=state.llm_budget.quota,
            disk_used=state.disk.used,
            disk_quota=state.disk.quota,
            action_count=state.action_count,
            action_successes=state.action_successes,
            action_failures=state.action_failures,
            artifacts_owned=state.artifacts_owned,
        )


class ArtifactStateResponse(BaseModel):
    """Artifact state for API responses."""

    artifact_id: str
    artifact_type: str
    owner: str
    created_by: str
    executable: bool = False
    price: float = 0.0
    size_bytes: int = 0
    created_at: str = ""
    updated_at: str = ""
    mint_score: float | None = None
    mint_status: str = "none"
    invocation_count: int = 0
    methods: list[str] = []

    @classmethod
    def from_state(cls, state: ArtifactState) -> "ArtifactStateResponse":
        """Create from internal state."""
        return cls(
            artifact_id=state.artifact_id,
            artifact_type=state.artifact_type,
            owner=state.owner,
            created_by=state.created_by,
            executable=state.executable,
            price=state.price,
            size_bytes=state.size_bytes,
            created_at=state.created_at,
            updated_at=state.updated_at,
            mint_score=state.mint_score,
            mint_status=state.mint_status,
            invocation_count=state.invocation_count,
            methods=state.methods,
        )
