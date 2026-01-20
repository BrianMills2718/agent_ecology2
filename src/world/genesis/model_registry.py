"""Genesis Model Registry - Manage LLM model access as tradeable resource

This genesis artifact makes LLM model access scarce and tradeable:
1. Models have global rate limits (reflecting real API constraints)
2. Agents receive initial quotas and can trade/contract for model access
3. Enables emergence: markets for premium models, specialists who arbitrage access
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, cast

from ...config import get_validated_config
from ...config_schema import GenesisConfig
from ..errors import (
    ErrorCode,
    permission_error,
    resource_error,
    validation_error,
)
from .base import GenesisArtifact


@dataclass
class ModelInfo:
    """Information about an available model."""

    model_id: str
    global_limit: float  # Total tokens/calls per window across all agents
    cost_per_1k_input: float  # API cost per 1K input tokens
    cost_per_1k_output: float  # API cost per 1K output tokens
    properties: list[str] = field(default_factory=list)  # e.g., ["fast", "cheap"]


@dataclass
class QuotaInfo:
    """Quota information for a specific agent and model."""

    agent_id: str
    model_id: str
    quota: float  # Allocated quota
    used: float  # Amount consumed
    available: float  # quota - used


class GenesisModelRegistry(GenesisArtifact):
    """
    Genesis artifact for model access management.

    Tracks:
    - Available models and their properties
    - Per-agent quotas for each model
    - Usage consumption
    - Quota transfers between agents

    This transforms LLM model access into a scarce, tradeable resource,
    enabling emergence of model markets and access trading.
    """

    _models: dict[str, ModelInfo]
    _quotas: dict[str, dict[str, float]]  # agent_id -> {model_id: quota}
    _usage: dict[str, dict[str, float]]   # agent_id -> {model_id: used}
    _world: Any  # World reference for kernel delegation

    def __init__(
        self,
        genesis_config: GenesisConfig | None = None
    ) -> None:
        # Get config (use provided or load from global)
        cfg = genesis_config or get_validated_config().genesis

        # Use hardcoded values for now since config doesn't have model_registry yet
        artifact_id = "genesis_model_registry"
        description = "Model access management - list models, check/transfer quotas"

        super().__init__(
            artifact_id=artifact_id,
            description=description
        )

        self._models = {}
        self._quotas = {}
        self._usage = {}
        self._world = None

        # Register methods
        self.register_method(
            name="list_models",
            handler=self._list_models,
            cost=0,
            description="List available models and their properties. Args: []"
        )

        self.register_method(
            name="get_quota",
            handler=self._get_quota,
            cost=0,
            description="Check agent's quota for a model. Args: [agent_id, model_id]"
        )

        self.register_method(
            name="request_access",
            handler=self._request_access,
            cost=1,
            description="Request quota allocation from global pool. Args: [agent_id, model_id, amount]"
        )

        self.register_method(
            name="release_quota",
            handler=self._release_quota,
            cost=0,
            description="Release unused quota back to pool. Args: [agent_id, model_id, amount]"
        )

        self.register_method(
            name="transfer_quota",
            handler=self._transfer_quota,
            cost=1,
            description="Transfer quota to another agent. Args: [to_agent, model_id, amount]"
        )

        self.register_method(
            name="get_available_models",
            handler=self._get_available_models,
            cost=0,
            description="Get models agent has capacity for. Args: [agent_id]"
        )

        self.register_method(
            name="consume",
            handler=self._consume,
            cost=0,
            description="Record usage against agent's quota. Args: [agent_id, model_id, amount]"
        )

    def set_world(self, world: Any) -> None:
        """Set world reference for kernel delegation (Plan #111)."""
        self._world = world

    def configure_model(
        self,
        model_id: str,
        global_limit: float,
        cost_per_1k_input: float = 0.0,
        cost_per_1k_output: float = 0.0,
        properties: list[str] | None = None
    ) -> None:
        """Configure an available model (called during world setup).

        Args:
            model_id: Unique identifier for the model
            global_limit: Total quota available across all agents
            cost_per_1k_input: API cost per 1K input tokens
            cost_per_1k_output: API cost per 1K output tokens
            properties: Tags like ["fast", "cheap", "experimental"]
        """
        self._models[model_id] = ModelInfo(
            model_id=model_id,
            global_limit=global_limit,
            cost_per_1k_input=cost_per_1k_input,
            cost_per_1k_output=cost_per_1k_output,
            properties=properties or []
        )

    def allocate_initial_quota(
        self,
        agent_id: str,
        model_id: str,
        quota: float
    ) -> bool:
        """Allocate initial quota to an agent (called during world setup).

        Args:
            agent_id: The agent to receive quota
            model_id: The model to allocate quota for
            quota: Amount of quota to allocate

        Returns:
            True if allocation succeeded
        """
        if model_id not in self._models:
            return False

        if agent_id not in self._quotas:
            self._quotas[agent_id] = {}
            self._usage[agent_id] = {}

        self._quotas[agent_id][model_id] = quota
        self._usage[agent_id][model_id] = 0.0
        return True

    def _get_total_allocated(self, model_id: str) -> float:
        """Get total quota allocated for a model across all agents."""
        total = 0.0
        for agent_quotas in self._quotas.values():
            total += agent_quotas.get(model_id, 0.0)
        return total

    def _list_models(self, args: list[Any], invoker_id: str) -> dict[str, Any]:
        """List available models and their properties."""
        models = []
        for model in self._models.values():
            allocated = self._get_total_allocated(model.model_id)
            models.append({
                "model_id": model.model_id,
                "global_limit": model.global_limit,
                "allocated": allocated,
                "available": model.global_limit - allocated,
                "cost_per_1k_input": model.cost_per_1k_input,
                "cost_per_1k_output": model.cost_per_1k_output,
                "properties": model.properties,
            })
        return {
            "success": True,
            "models": models,
            "count": len(models)
        }

    def _get_quota(self, args: list[Any], invoker_id: str) -> dict[str, Any]:
        """Check agent's quota for a model."""
        if not args or len(args) < 2:
            return validation_error(
                "get_quota requires [agent_id, model_id]",
                code=ErrorCode.MISSING_ARGUMENT,
                required=["agent_id", "model_id"],
            )

        agent_id: str = args[0]
        model_id: str = args[1]

        if model_id not in self._models:
            return resource_error(
                f"Model {model_id} not found",
                code=ErrorCode.NOT_FOUND,
                model_id=model_id,
            )

        quota = self._quotas.get(agent_id, {}).get(model_id, 0.0)
        used = self._usage.get(agent_id, {}).get(model_id, 0.0)

        return {
            "success": True,
            "agent_id": agent_id,
            "model_id": model_id,
            "quota": quota,
            "used": used,
            "available": quota - used
        }

    def _request_access(self, args: list[Any], invoker_id: str) -> dict[str, Any]:
        """Request quota allocation from global pool."""
        if not args or len(args) < 3:
            return validation_error(
                "request_access requires [agent_id, model_id, amount]",
                code=ErrorCode.MISSING_ARGUMENT,
                required=["agent_id", "model_id", "amount"],
            )

        agent_id: str = args[0]
        model_id: str = args[1]
        amount: float = float(args[2])

        # Security check: can only request for yourself
        if agent_id != invoker_id:
            return permission_error(
                f"Cannot request quota for {agent_id} - you are {invoker_id}",
                code=ErrorCode.NOT_AUTHORIZED,
                invoker=invoker_id,
                target=agent_id,
            )

        if model_id not in self._models:
            return resource_error(
                f"Model {model_id} not found",
                code=ErrorCode.NOT_FOUND,
                model_id=model_id,
            )

        if amount <= 0:
            return validation_error(
                "Amount must be positive",
                code=ErrorCode.INVALID_ARGUMENT,
                provided=amount,
            )

        model = self._models[model_id]
        allocated = self._get_total_allocated(model_id)
        available = model.global_limit - allocated

        if amount > available:
            return resource_error(
                f"Insufficient global quota. Requested {amount}, available {available}",
                code=ErrorCode.INSUFFICIENT_FUNDS,
                requested=amount,
                available=available,
            )

        # Allocate the quota
        if agent_id not in self._quotas:
            self._quotas[agent_id] = {}
            self._usage[agent_id] = {}

        current = self._quotas.get(agent_id, {}).get(model_id, 0.0)
        self._quotas[agent_id][model_id] = current + amount
        if model_id not in self._usage[agent_id]:
            self._usage[agent_id][model_id] = 0.0

        return {
            "success": True,
            "agent_id": agent_id,
            "model_id": model_id,
            "allocated": amount,
            "new_quota": self._quotas[agent_id][model_id]
        }

    def _release_quota(self, args: list[Any], invoker_id: str) -> dict[str, Any]:
        """Release unused quota back to pool."""
        if not args or len(args) < 3:
            return validation_error(
                "release_quota requires [agent_id, model_id, amount]",
                code=ErrorCode.MISSING_ARGUMENT,
                required=["agent_id", "model_id", "amount"],
            )

        agent_id: str = args[0]
        model_id: str = args[1]
        amount: float = float(args[2])

        # Security check: can only release your own quota
        if agent_id != invoker_id:
            return permission_error(
                f"Cannot release quota for {agent_id} - you are {invoker_id}",
                code=ErrorCode.NOT_AUTHORIZED,
                invoker=invoker_id,
                target=agent_id,
            )

        if model_id not in self._models:
            return resource_error(
                f"Model {model_id} not found",
                code=ErrorCode.NOT_FOUND,
                model_id=model_id,
            )

        if amount <= 0:
            return validation_error(
                "Amount must be positive",
                code=ErrorCode.INVALID_ARGUMENT,
                provided=amount,
            )

        current_quota = self._quotas.get(agent_id, {}).get(model_id, 0.0)
        current_usage = self._usage.get(agent_id, {}).get(model_id, 0.0)
        available_to_release = current_quota - current_usage

        if amount > available_to_release:
            return resource_error(
                f"Cannot release {amount} - only {available_to_release} unused",
                code=ErrorCode.INSUFFICIENT_FUNDS,
                requested=amount,
                available_to_release=available_to_release,
            )

        self._quotas[agent_id][model_id] = current_quota - amount

        return {
            "success": True,
            "agent_id": agent_id,
            "model_id": model_id,
            "released": amount,
            "new_quota": self._quotas[agent_id][model_id]
        }

    def _transfer_quota(self, args: list[Any], invoker_id: str) -> dict[str, Any]:
        """Transfer quota to another agent."""
        if not args or len(args) < 3:
            return validation_error(
                "transfer_quota requires [to_agent, model_id, amount]",
                code=ErrorCode.MISSING_ARGUMENT,
                required=["to_agent", "model_id", "amount"],
            )

        to_agent: str = args[0]
        model_id: str = args[1]
        amount: float = float(args[2])
        from_agent = invoker_id  # Transfer from the invoker

        if model_id not in self._models:
            return resource_error(
                f"Model {model_id} not found",
                code=ErrorCode.NOT_FOUND,
                model_id=model_id,
            )

        if amount <= 0:
            return validation_error(
                "Amount must be positive",
                code=ErrorCode.INVALID_ARGUMENT,
                provided=amount,
            )

        current_quota = self._quotas.get(from_agent, {}).get(model_id, 0.0)
        current_usage = self._usage.get(from_agent, {}).get(model_id, 0.0)
        available_to_transfer = current_quota - current_usage

        if amount > available_to_transfer:
            return resource_error(
                f"Cannot transfer {amount} - only {available_to_transfer} unused",
                code=ErrorCode.INSUFFICIENT_FUNDS,
                requested=amount,
                available_to_transfer=available_to_transfer,
            )

        # Deduct from sender
        self._quotas[from_agent][model_id] = current_quota - amount

        # Add to recipient
        if to_agent not in self._quotas:
            self._quotas[to_agent] = {}
            self._usage[to_agent] = {}

        recipient_quota = self._quotas.get(to_agent, {}).get(model_id, 0.0)
        self._quotas[to_agent][model_id] = recipient_quota + amount
        if model_id not in self._usage[to_agent]:
            self._usage[to_agent][model_id] = 0.0

        return {
            "success": True,
            "from_agent": from_agent,
            "to_agent": to_agent,
            "model_id": model_id,
            "transferred": amount,
            "from_quota_after": self._quotas[from_agent][model_id],
            "to_quota_after": self._quotas[to_agent][model_id]
        }

    def _get_available_models(self, args: list[Any], invoker_id: str) -> dict[str, Any]:
        """Get models agent has capacity for."""
        if not args or len(args) < 1:
            return validation_error(
                "get_available_models requires [agent_id]",
                code=ErrorCode.MISSING_ARGUMENT,
                required=["agent_id"],
            )

        agent_id: str = args[0]

        available = []
        for model_id in self._models:
            quota = self._quotas.get(agent_id, {}).get(model_id, 0.0)
            used = self._usage.get(agent_id, {}).get(model_id, 0.0)
            remaining = quota - used
            if remaining > 0:
                available.append({
                    "model_id": model_id,
                    "remaining": remaining,
                    "properties": self._models[model_id].properties
                })

        # Sort by remaining capacity (highest first)
        available.sort(key=lambda x: cast(int, x["remaining"]), reverse=True)

        return {
            "success": True,
            "agent_id": agent_id,
            "models": available,
            "count": len(available)
        }

    def _consume(self, args: list[Any], invoker_id: str) -> dict[str, Any]:
        """Record usage against agent's quota."""
        if not args or len(args) < 3:
            return validation_error(
                "consume requires [agent_id, model_id, amount]",
                code=ErrorCode.MISSING_ARGUMENT,
                required=["agent_id", "model_id", "amount"],
            )

        agent_id: str = args[0]
        model_id: str = args[1]
        amount: float = float(args[2])

        if model_id not in self._models:
            return resource_error(
                f"Model {model_id} not found",
                code=ErrorCode.NOT_FOUND,
                model_id=model_id,
            )

        if amount <= 0:
            return validation_error(
                "Amount must be positive",
                code=ErrorCode.INVALID_ARGUMENT,
                provided=amount,
            )

        quota = self._quotas.get(agent_id, {}).get(model_id, 0.0)
        used = self._usage.get(agent_id, {}).get(model_id, 0.0)
        remaining = quota - used

        if amount > remaining:
            return resource_error(
                f"Insufficient quota. Need {amount}, have {remaining}",
                code=ErrorCode.INSUFFICIENT_FUNDS,
                requested=amount,
                remaining=remaining,
            )

        # Record usage
        if agent_id not in self._usage:
            self._usage[agent_id] = {}
        self._usage[agent_id][model_id] = used + amount

        return {
            "success": True,
            "agent_id": agent_id,
            "model_id": model_id,
            "consumed": amount,
            "remaining": quota - self._usage[agent_id][model_id]
        }

    def has_capacity(self, agent_id: str, model_id: str, amount: float = 1.0) -> bool:
        """Check if agent has quota for this model (convenience method).

        Args:
            agent_id: The agent to check
            model_id: The model to check
            amount: Amount of quota needed (default 1.0)

        Returns:
            True if agent has sufficient remaining quota
        """
        quota = self._quotas.get(agent_id, {}).get(model_id, 0.0)
        used = self._usage.get(agent_id, {}).get(model_id, 0.0)
        return (quota - used) >= amount

    def get_interface(self) -> dict[str, Any]:
        """Get detailed interface schema for the model registry (Plan #14)."""
        return {
            "description": self.description,
            "tools": [
                {
                    "name": "list_models",
                    "description": "List available models and their properties",
                    "cost": self.methods["list_models"].cost,
                    "inputSchema": {
                        "type": "object",
                        "properties": {}
                    }
                },
                {
                    "name": "get_quota",
                    "description": "Check agent's quota for a model",
                    "cost": self.methods["get_quota"].cost,
                    "inputSchema": {
                        "type": "object",
                        "properties": {
                            "agent_id": {
                                "type": "string",
                                "description": "ID of the agent to query"
                            },
                            "model_id": {
                                "type": "string",
                                "description": "ID of the model"
                            }
                        },
                        "required": ["agent_id", "model_id"]
                    }
                },
                {
                    "name": "request_access",
                    "description": "Request quota allocation from global pool",
                    "cost": self.methods["request_access"].cost,
                    "inputSchema": {
                        "type": "object",
                        "properties": {
                            "agent_id": {
                                "type": "string",
                                "description": "ID of the agent (must be invoker)"
                            },
                            "model_id": {
                                "type": "string",
                                "description": "ID of the model"
                            },
                            "amount": {
                                "type": "number",
                                "description": "Amount of quota to request"
                            }
                        },
                        "required": ["agent_id", "model_id", "amount"]
                    }
                },
                {
                    "name": "release_quota",
                    "description": "Release unused quota back to pool",
                    "cost": self.methods["release_quota"].cost,
                    "inputSchema": {
                        "type": "object",
                        "properties": {
                            "agent_id": {
                                "type": "string",
                                "description": "ID of the agent (must be invoker)"
                            },
                            "model_id": {
                                "type": "string",
                                "description": "ID of the model"
                            },
                            "amount": {
                                "type": "number",
                                "description": "Amount of quota to release"
                            }
                        },
                        "required": ["agent_id", "model_id", "amount"]
                    }
                },
                {
                    "name": "transfer_quota",
                    "description": "Transfer quota to another agent",
                    "cost": self.methods["transfer_quota"].cost,
                    "inputSchema": {
                        "type": "object",
                        "properties": {
                            "to_agent": {
                                "type": "string",
                                "description": "ID of the recipient agent"
                            },
                            "model_id": {
                                "type": "string",
                                "description": "ID of the model"
                            },
                            "amount": {
                                "type": "number",
                                "description": "Amount of quota to transfer"
                            }
                        },
                        "required": ["to_agent", "model_id", "amount"]
                    }
                },
                {
                    "name": "get_available_models",
                    "description": "Get models agent has capacity for",
                    "cost": self.methods["get_available_models"].cost,
                    "inputSchema": {
                        "type": "object",
                        "properties": {
                            "agent_id": {
                                "type": "string",
                                "description": "ID of the agent"
                            }
                        },
                        "required": ["agent_id"]
                    }
                },
                {
                    "name": "consume",
                    "description": "Record usage against agent's quota",
                    "cost": self.methods["consume"].cost,
                    "inputSchema": {
                        "type": "object",
                        "properties": {
                            "agent_id": {
                                "type": "string",
                                "description": "ID of the agent"
                            },
                            "model_id": {
                                "type": "string",
                                "description": "ID of the model"
                            },
                            "amount": {
                                "type": "number",
                                "description": "Amount to consume"
                            }
                        },
                        "required": ["agent_id", "model_id", "amount"]
                    }
                }
            ]
        }
