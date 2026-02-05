"""Type definitions for simulation module."""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, TypedDict


@dataclass
class ErrorRecord:
    """A single error occurrence."""

    timestamp: datetime
    error_type: str
    agent_id: str
    message: str
    suggestion: str | None = None


@dataclass
class ErrorStats:
    """Aggregated error statistics for the simulation (Plan #129).

    Tracks errors by type and agent for the shutdown summary.
    """

    total_errors: int = 0
    by_type: dict[str, int] = field(default_factory=dict)
    by_agent: dict[str, int] = field(default_factory=dict)
    recent_errors: list[ErrorRecord] = field(default_factory=list)
    max_recent: int = 10  # Keep last N errors

    def record_error(
        self,
        error_type: str,
        agent_id: str,
        message: str,
        suggestion: str | None = None,
    ) -> None:
        """Record an error occurrence."""
        self.total_errors += 1
        self.by_type[error_type] = self.by_type.get(error_type, 0) + 1
        self.by_agent[agent_id] = self.by_agent.get(agent_id, 0) + 1

        record = ErrorRecord(
            timestamp=datetime.now(),
            error_type=error_type,
            agent_id=agent_id,
            message=message,
            suggestion=suggestion,
        )
        self.recent_errors.append(record)

        # Keep only the last N errors
        if len(self.recent_errors) > self.max_recent:
            self.recent_errors = self.recent_errors[-self.max_recent:]


class PrincipalConfig(TypedDict):
    """Configuration for a principal (agent) in the simulation."""

    id: str
    starting_scrip: int


class BalanceInfo(TypedDict):
    """Balance information for an agent."""

    llm_tokens: int
    scrip: int


class AgentCheckpointState(TypedDict, total=False):
    """Serialized agent state for checkpoint persistence (Plan #163).

    Contains runtime state that should survive checkpoint/restore cycles
    so agents can resume with behavioral continuity.
    """

    # Current workflow/behavioral state
    current_state: str | None

    # Working memory contents
    working_memory: dict[str, Any] | None

    # Recent action history for loop detection
    action_history: list[str]

    # Failure history for learning from mistakes
    failure_history: list[str]

    # Opportunity cost metrics (Plan #157)
    actions_taken: int
    successful_actions: int
    failed_actions: int
    revenue_earned: float
    artifacts_completed: int
    starting_balance: float | None

    # Last action result for feedback continuity
    last_action_result: str | None


class CheckpointData(TypedDict, total=False):
    """Structure for checkpoint file data.

    Version history:
    - v1: Original format (event_number/tick, balances, artifacts, agent_ids, reason, cumulative_api_cost)
    - v2: Added agent_states and version field (Plan #163)
    """

    # Version field for format migration
    version: int

    event_number: int
    tick: int  # Legacy alias for backward compat when loading old checkpoints
    balances: dict[str, BalanceInfo]
    cumulative_api_cost: float
    artifacts: list[dict[str, Any]]
    agent_ids: list[str]
    reason: str

    # Plan #163: Agent runtime state for behavioral continuity
    agent_states: dict[str, AgentCheckpointState]

    # Optional timestamp
    timestamp: str
