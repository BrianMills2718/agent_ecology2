"""Genesis Rights Registry - Resource quota management

Manages resource rights (means of production) like compute and disk quotas.
This is a thin wrapper around kernel quota primitives (Plan #42).
"""

from __future__ import annotations

from typing import Any, cast

from ...config import get_validated_config
from ...config_schema import GenesisConfig
from ..artifacts import ArtifactStore
from .base import GenesisArtifact


class GenesisRightsRegistry(GenesisArtifact):
    """
    Genesis artifact for managing resource rights (means of production).

    This is a thin wrapper around kernel quota primitives (Plan #42).
    Quotas are kernel state, not genesis artifact state.

    Supports generic resources defined in config. Common resources:
    - llm_tokens: LLM tokens (rate-limited via rolling window)
    - disk: Bytes of storage (fixed pool)

    See docs/architecture/current/resources.md for full design rationale.
    All method costs and descriptions are configurable via config.yaml.
    """

    default_quotas: dict[str, float]
    artifact_store: ArtifactStore | None
    # Legacy storage - used as fallback when _world is not set
    _legacy_quotas: dict[str, dict[str, float]]
    # World reference for kernel delegation (Plan #42)
    _world: Any  # Type is World but avoiding circular import

    def __init__(
        self,
        default_quotas: dict[str, float] | None = None,
        artifact_store: ArtifactStore | None = None,
        genesis_config: GenesisConfig | None = None,
        # Backward compat kwargs
        default_compute: int = 0,
        default_disk: int = 0,
    ) -> None:
        """
        Args:
            default_quotas: Dict of {resource_name: default_amount} for all resources
            artifact_store: ArtifactStore to calculate actual disk usage
            genesis_config: Optional genesis config (uses global if not provided)
            default_compute: DEPRECATED - use default_quotas
            default_disk: DEPRECATED - use default_quotas
        """
        # Get config (use provided or load from global)
        cfg = genesis_config or get_validated_config().genesis
        rights_cfg = cfg.rights_registry

        super().__init__(
            artifact_id=rights_cfg.id,
            description=rights_cfg.description
        )

        # Build default quotas from explicit dict or backward compat params
        if default_quotas:
            self.default_quotas = dict(default_quotas)
        else:
            # Backward compat: build from positional args
            self.default_quotas = {}
            if default_compute > 0:
                self.default_quotas["llm_tokens"] = float(default_compute)
            if default_disk > 0:
                self.default_quotas["disk"] = float(default_disk)

        self.artifact_store = artifact_store

        # Legacy quota storage - used when _world not set (backward compat)
        self._legacy_quotas = {}

        # World reference for kernel delegation - set via set_world()
        self._world = None

        # Register methods with costs/descriptions from config
        self.register_method(
            name="check_quota",
            handler=self._check_quota,
            cost=rights_cfg.methods.check_quota.cost,
            description=rights_cfg.methods.check_quota.description
        )

        self.register_method(
            name="all_quotas",
            handler=self._all_quotas,
            cost=rights_cfg.methods.all_quotas.cost,
            description=rights_cfg.methods.all_quotas.description
        )

        self.register_method(
            name="transfer_quota",
            handler=self._transfer_quota,
            cost=rights_cfg.methods.transfer_quota.cost,
            description=rights_cfg.methods.transfer_quota.description
        )

    def set_world(self, world: Any) -> None:
        """Set world reference for kernel delegation (Plan #42).

        Once set, all quota operations delegate to kernel state.

        Args:
            world: The World instance containing kernel quota primitives
        """
        self._world = world
        # Migrate any legacy quotas to kernel
        for agent_id, quotas in self._legacy_quotas.items():
            for resource, amount in quotas.items():
                self._world.set_quota(agent_id, resource, amount)
        self._legacy_quotas.clear()

    @property
    def quotas(self) -> dict[str, dict[str, float]]:
        """Backward compat: return quotas dict (read-only view).

        When _world is set, this reconstructs from kernel state.
        """
        if self._world is not None:
            # Reconstruct from kernel state
            result: dict[str, dict[str, float]] = {}
            for pid in self._world.principal_ids:
                result[pid] = {}
                for resource in self.default_quotas.keys():
                    result[pid][resource] = self._world.get_quota(pid, resource)
            return result
        return self._legacy_quotas

    def ensure_agent(self, agent_id: str) -> None:
        """Ensure an agent has quota entries (initialize with defaults)."""
        if self._world is not None:
            # Kernel mode: set default quotas if not already set
            for resource, amount in self.default_quotas.items():
                if self._world.get_quota(agent_id, resource) == 0.0:
                    self._world.set_quota(agent_id, resource, amount)
        else:
            # Legacy mode
            if agent_id not in self._legacy_quotas:
                self._legacy_quotas[agent_id] = dict(self.default_quotas)

    def get_quota(self, agent_id: str, resource: str) -> float:
        """Get quota for a specific resource.

        Delegates to kernel when world is set (Plan #42).
        """
        if self._world is not None:
            # Kernel mode: ensure defaults then query
            if self._world.get_quota(agent_id, resource) == 0.0:
                self.ensure_agent(agent_id)
            return cast(float, self._world.get_quota(agent_id, resource))
        # Legacy mode
        self.ensure_agent(agent_id)
        return self._legacy_quotas[agent_id].get(resource, 0.0)

    def set_quota(self, agent_id: str, resource: str, amount: float) -> None:
        """Set quota for a specific resource.

        Delegates to kernel when world is set (Plan #42).
        """
        if self._world is not None:
            self._world.set_quota(agent_id, resource, amount)
        else:
            self.ensure_agent(agent_id)
            self._legacy_quotas[agent_id][resource] = amount

    def get_all_quotas(self, agent_id: str) -> dict[str, float]:
        """Get all quotas for an agent.

        Delegates to kernel when world is set (Plan #42).
        """
        if self._world is not None:
            self.ensure_agent(agent_id)
            result = {}
            for resource in self.default_quotas.keys():
                result[resource] = self._world.get_quota(agent_id, resource)
            return result
        # Legacy mode
        self.ensure_agent(agent_id)
        return dict(self._legacy_quotas[agent_id])

    def get_llm_tokens_quota(self, agent_id: str) -> int:
        """Get LLM tokens quota for an agent."""
        return int(self.get_quota(agent_id, "llm_tokens"))

    # Backward compat: disk = "disk" resource
    def get_disk_quota(self, agent_id: str) -> int:
        """Get disk quota (bytes) for an agent."""
        return int(self.get_quota(agent_id, "disk"))

    def get_disk_used(self, agent_id: str) -> int:
        """Get actual disk space used by an agent."""
        if self.artifact_store:
            return self.artifact_store.get_owner_usage(agent_id)
        return 0

    def can_write(self, agent_id: str, additional_bytes: int) -> bool:
        """Check if agent can write additional_bytes without exceeding disk quota."""
        quota = self.get_disk_quota(agent_id)
        used = self.get_disk_used(agent_id)
        return (used + additional_bytes) <= quota

    # Backward compat aliases (can be removed - no callers)
    def get_flow_quota(self, agent_id: str) -> int:
        """DEPRECATED: Use get_llm_tokens_quota()."""
        return self.get_llm_tokens_quota(agent_id)

    def get_stock_quota(self, agent_id: str) -> int:
        """DEPRECATED: Use get_disk_quota()."""
        return self.get_disk_quota(agent_id)

    def get_stock_used(self, agent_id: str) -> int:
        """DEPRECATED: Use get_disk_used()."""
        return self.get_disk_used(agent_id)

    def _check_quota(self, args: list[Any], invoker_id: str) -> dict[str, Any]:
        """Check quotas for an agent."""
        if not args or len(args) < 1:
            return {"success": False, "error": "check_quota requires [agent_id]"}

        agent_id: str = args[0]
        self.ensure_agent(agent_id)

        all_quotas = self.quotas[agent_id]
        disk_used = self.get_disk_used(agent_id)
        disk_quota = int(all_quotas.get("disk", 0))

        # Include both legacy format and new generic format
        return {
            "success": True,
            "agent_id": agent_id,
            "compute_quota": int(all_quotas.get("compute", 0)),
            "disk_quota": disk_quota,
            "disk_used": disk_used,
            "disk_available": disk_quota - disk_used,
            "quotas": all_quotas  # New: all resource quotas
        }

    def _all_quotas(self, args: list[Any], invoker_id: str) -> dict[str, Any]:
        """Get all agent quotas."""
        result: dict[str, Any] = {}
        for agent_id, quota in self.quotas.items():
            disk_used = self.get_disk_used(agent_id)
            disk_quota = int(quota.get("disk", 0))
            result[agent_id] = {
                "compute_quota": int(quota.get("compute", 0)),
                "disk_quota": disk_quota,
                "disk_used": disk_used,
                "disk_available": disk_quota - disk_used,
                "quotas": quota  # New: all resource quotas
            }
        return {"success": True, "quotas": result}

    def _transfer_quota(self, args: list[Any], invoker_id: str) -> dict[str, Any]:
        """Transfer quota between agents. Works with any resource type.

        Delegates to kernel when world is set (Plan #42).
        """
        if not args or len(args) < 4:
            return {"success": False, "error": "transfer_quota requires [from_id, to_id, resource, amount]"}

        from_id: str = args[0]
        to_id: str = args[1]
        resource: str = args[2]
        amount: Any = args[3]

        # Security check: can only transfer FROM yourself
        if from_id != invoker_id:
            return {"success": False, "error": f"Cannot transfer from {from_id} - you are {invoker_id}"}

        # Validate resource exists in defaults (to prevent typos)
        if resource not in self.default_quotas:
            valid_resources = list(self.default_quotas.keys())
            return {"success": False, "error": f"Unknown resource '{resource}'. Valid: {valid_resources}"}

        if not isinstance(amount, (int, float)) or amount <= 0:
            return {"success": False, "error": "amount must be positive number"}

        self.ensure_agent(from_id)
        self.ensure_agent(to_id)

        # Kernel delegation mode (Plan #42)
        if self._world is not None:
            from src.world.kernel_interface import KernelActions
            kernel_actions = KernelActions(self._world)
            success = kernel_actions.transfer_quota(from_id, to_id, resource, float(amount))

            if not success:
                current = self._world.get_quota(from_id, resource)
                return {
                    "success": False,
                    "error": f"Insufficient {resource} quota. Have {current}, need {amount}"
                }

            return {
                "success": True,
                "transferred": amount,
                "quota_type": resource,  # Keep legacy field name
                "resource": resource,    # New field name
                "from": from_id,
                "to": to_id,
                "from_new_quota": self._world.get_quota(from_id, resource),
                "to_new_quota": self._world.get_quota(to_id, resource)
            }

        # Legacy mode
        current = self._legacy_quotas[from_id].get(resource, 0.0)
        if current < amount:
            return {
                "success": False,
                "error": f"Insufficient {resource} quota. Have {current}, need {amount}"
            }

        # Transfer
        self._legacy_quotas[from_id][resource] = current - amount
        self._legacy_quotas[to_id][resource] = self._legacy_quotas[to_id].get(resource, 0.0) + amount

        return {
            "success": True,
            "transferred": amount,
            "quota_type": resource,  # Keep legacy field name
            "resource": resource,    # New field name
            "from": from_id,
            "to": to_id,
            "from_new_quota": self._legacy_quotas[from_id][resource],
            "to_new_quota": self._legacy_quotas[to_id][resource]
        }

    def get_interface(self) -> dict[str, Any]:
        """Get detailed interface schema for the rights registry (Plan #114)."""
        return {
            "description": self.description,
            "dataType": "service",
            "tools": [
                {
                    "name": "check_quota",
                    "description": "Check quotas for a specific agent (compute, disk, etc.)",
                    "cost": self.methods["check_quota"].cost,
                    "inputSchema": {
                        "type": "object",
                        "properties": {
                            "agent_id": {
                                "type": "string",
                                "description": "ID of the agent to check quotas for"
                            }
                        },
                        "required": ["agent_id"]
                    }
                },
                {
                    "name": "all_quotas",
                    "description": "Get quotas for all agents in the system",
                    "cost": self.methods["all_quotas"].cost,
                    "inputSchema": {
                        "type": "object",
                        "properties": {}
                    }
                },
                {
                    "name": "transfer_quota",
                    "description": "Transfer quota to another agent. Can only transfer FROM yourself.",
                    "cost": self.methods["transfer_quota"].cost,
                    "inputSchema": {
                        "type": "object",
                        "properties": {
                            "from_id": {
                                "type": "string",
                                "description": "Source agent ID (must be the invoker)"
                            },
                            "to_id": {
                                "type": "string",
                                "description": "Destination agent ID"
                            },
                            "resource": {
                                "type": "string",
                                "description": "Resource type to transfer (e.g., 'compute', 'disk')"
                            },
                            "amount": {
                                "type": "number",
                                "description": "Amount of quota to transfer",
                                "minimum": 0
                            }
                        },
                        "required": ["from_id", "to_id", "resource", "amount"]
                    }
                }
            ]
        }
