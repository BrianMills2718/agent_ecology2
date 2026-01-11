"""Type definitions for simulation module."""

from typing import Any, TypedDict, TYPE_CHECKING

if TYPE_CHECKING:
    from ..agents import Agent
    from ..agents.agent import ActionResult as AgentActionResult


class PrincipalConfig(TypedDict):
    """Configuration for a principal (agent) in the simulation."""

    id: str
    starting_scrip: int


class BalanceInfo(TypedDict):
    """Balance information for an agent."""

    compute: int
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
