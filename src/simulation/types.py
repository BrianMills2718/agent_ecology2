"""Type definitions for simulation module."""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, TypedDict, TYPE_CHECKING

if TYPE_CHECKING:
    from ..agents import Agent
    from ..agents.agent import ActionResult as AgentActionResult


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


class CheckpointData(TypedDict):
    """Structure for checkpoint file data."""

    tick: int
    balances: dict[str, BalanceInfo]
    cumulative_api_cost: float
    artifacts: list[dict[str, Any]]
    agent_ids: list[str]
    reason: str


class ActionProposal(TypedDict):
    """Structure for an agent's action proposal during two-phase commit."""

    agent: "Agent"
    proposal: "AgentActionResult"
    thinking_cost: int
    api_cost: float


class ThinkingResult(TypedDict, total=False):
    """Result from parallel agent thinking."""

    agent: "Agent"
    proposal: "AgentActionResult"
    thinking_cost: int
    api_cost: float
    input_tokens: int
    output_tokens: int
    skipped: bool
    skip_reason: str
    error: str
