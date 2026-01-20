"""Model Access Manager - Plan #113: Contractable Model Access.

Manages per-agent model access quotas. Each model is treated as a renewable
resource with global limits (reflecting real API rate limits) and per-agent
quotas that can be traded.

This enables emergence: agents can trade model access, specialize in arbitrage,
and make strategic model selection decisions based on task importance.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


class NoModelQuotaError(Exception):
    """Raised when an agent has no quota for a model."""

    pass


@dataclass
class ModelConfig:
    """Configuration for a single model.

    Attributes:
        id: Model identifier (e.g., "gemini/gemini-2.5-flash")
        global_limit_rpd: Global requests per day limit
        cost_per_1k_input: Cost per 1K input tokens
        cost_per_1k_output: Cost per 1K output tokens
        properties: Model properties (e.g., ["fast", "cheap"])
    """

    id: str
    global_limit_rpd: int
    cost_per_1k_input: float
    cost_per_1k_output: float
    properties: list[str] = field(default_factory=list)


class ModelAccessManager:
    """Manages per-agent model access quotas.

    Each model is treated as a renewable resource with:
    - Global limit (reflecting real API rate limits)
    - Per-agent quotas (tradeable)
    - Rolling window tracking

    Agents receive initial quotas based on allocation strategy and can
    transfer quota to each other (enabling trading).
    """

    def __init__(
        self,
        models: list[ModelConfig],
        allocation_strategy: str = "equal",
        initial_per_agent: float = 0.2,
    ) -> None:
        """Initialize the model access manager.

        Args:
            models: List of model configurations
            allocation_strategy: How to allocate initial quota ("equal", "fixed")
            initial_per_agent: Fraction of global limit allocated per agent
        """
        self._models: dict[str, ModelConfig] = {m.id: m for m in models}
        self._allocation_strategy = allocation_strategy
        self._initial_per_agent = initial_per_agent

        # Per-agent quota tracking: {agent_id: {model_id: remaining_quota}}
        self._quotas: dict[str, dict[str, int]] = {}

    def register_agent(self, agent_id: str) -> None:
        """Register an agent and allocate initial quotas.

        Args:
            agent_id: The agent's identifier
        """
        if agent_id in self._quotas:
            return  # Already registered

        # Allocate initial quota for each model
        self._quotas[agent_id] = {}
        for model_id, config in self._models.items():
            initial_quota = int(config.global_limit_rpd * self._initial_per_agent)
            self._quotas[agent_id][model_id] = initial_quota

    def get_quota(self, agent_id: str, model: str) -> int:
        """Get agent's remaining quota for a model.

        Args:
            agent_id: The agent's identifier
            model: The model identifier

        Returns:
            Remaining quota (tokens)

        Raises:
            KeyError: If agent or model not registered
        """
        if agent_id not in self._quotas:
            raise KeyError(f"Agent {agent_id} not registered")
        if model not in self._models:
            raise KeyError(f"Model {model} not configured")

        return self._quotas[agent_id].get(model, 0)

    def has_capacity(self, agent_id: str, model: str, tokens: int) -> bool:
        """Check if agent has quota for the specified tokens.

        Args:
            agent_id: The agent's identifier
            model: The model identifier
            tokens: Number of tokens requested

        Returns:
            True if agent has sufficient quota
        """
        try:
            quota = self.get_quota(agent_id, model)
            return quota >= tokens
        except KeyError:
            return False

    def consume(self, agent_id: str, model: str, tokens: int) -> None:
        """Record usage against agent's quota.

        Args:
            agent_id: The agent's identifier
            model: The model identifier
            tokens: Number of tokens consumed

        Raises:
            NoModelQuotaError: If agent has insufficient quota
            KeyError: If agent or model not registered
        """
        if agent_id not in self._quotas:
            raise KeyError(f"Agent {agent_id} not registered")
        if model not in self._models:
            raise KeyError(f"Model {model} not configured")

        current = self._quotas[agent_id].get(model, 0)
        if current < tokens:
            raise NoModelQuotaError(
                f"Agent {agent_id} has insufficient quota for {model}: "
                f"has {current}, needs {tokens}"
            )

        self._quotas[agent_id][model] = current - tokens

    def transfer_quota(
        self,
        from_agent: str,
        to_agent: str,
        model: str,
        amount: int,
    ) -> bool:
        """Transfer quota from one agent to another.

        Args:
            from_agent: Source agent ID
            to_agent: Destination agent ID
            model: Model identifier
            amount: Amount of quota to transfer

        Returns:
            True if transfer succeeded, False if insufficient quota
        """
        # Check source has enough
        try:
            source_quota = self.get_quota(from_agent, model)
        except KeyError:
            return False

        if source_quota < amount:
            return False

        # Perform transfer
        self._quotas[from_agent][model] -= amount
        self._quotas[to_agent][model] = self._quotas[to_agent].get(model, 0) + amount

        return True

    def get_available_models(self, agent_id: str) -> list[str]:
        """Get models agent has quota for, ordered by remaining quota.

        Models with zero quota are excluded.

        Args:
            agent_id: The agent's identifier

        Returns:
            List of model IDs with remaining quota, sorted by quota (highest first)
        """
        if agent_id not in self._quotas:
            return []

        available: list[tuple[str, int]] = []
        for model_id, quota in self._quotas[agent_id].items():
            if quota > 0:
                available.append((model_id, quota))

        # Sort by quota descending
        available.sort(key=lambda x: x[1], reverse=True)

        return [model_id for model_id, _ in available]

    def list_models(self) -> list[ModelConfig]:
        """List all configured models.

        Returns:
            List of ModelConfig objects
        """
        return list(self._models.values())

    def advance_window(self, model: str) -> None:
        """Advance the rate limit window, restoring quotas.

        This simulates time passing. In production, this would be called
        by a scheduler based on actual time.

        Args:
            model: Model identifier to refresh
        """
        if model not in self._models:
            return

        config = self._models[model]
        initial_quota = int(config.global_limit_rpd * self._initial_per_agent)

        # Restore all agents' quotas for this model
        for agent_id in self._quotas:
            self._quotas[agent_id][model] = initial_quota
