"""Genesis Artifacts - Base class and utilities

Genesis artifacts are special artifacts that:
1. Are owned by "system" (cannot be modified by agents)
2. Act as proxies to kernel functions (ledger, mint)
3. Have special cost rules (some functions are free)

These enable agents to interact with core infrastructure through
the same invoke_artifact mechanism they use for agent-created artifacts.
"""

# --- GOVERNANCE START (do not edit) ---
# ADR-0001: Everything is an artifact
# ADR-0003: Contracts can do anything
#
# Genesis artifacts: ledger, mint, escrow, event_log, store, etc.
# System-provided, solve cold-start problem.
# --- GOVERNANCE END ---

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable

from ...config import get
from .types import MethodInfo, GenesisArtifactDict


# System owner ID - cannot be modified by agents
SYSTEM_OWNER: str = "system"


def _get_error_message(error_type: str, **kwargs: Any) -> str:
    """Get a configurable error message with placeholders filled in.

    Args:
        error_type: One of 'escrow_not_owner', etc.
        **kwargs: Placeholder values (artifact_id, escrow_id)

    Returns:
        Formatted error message from config (or default if not configured).
    """
    defaults: dict[str, str] = {
        "escrow_not_owner": "Escrow does not own {artifact_id}. See handbook_trading for the 2-step process: 1) genesis_ledger.transfer_ownership([artifact_id, '{escrow_id}']), 2) deposit.",
    }

    template: str = get(f"agent.errors.{error_type}") or defaults.get(error_type, f"Error: {error_type}")

    try:
        return template.format(**kwargs)
    except KeyError:
        return template


@dataclass
class GenesisMethod:
    """A method exposed by a genesis artifact"""
    name: str
    handler: Callable[[list[Any], str], dict[str, Any]]
    cost: int  # 0 = free (system-subsidized)
    description: str


class GenesisArtifact:
    """Base class for genesis artifacts (system proxies)"""

    id: str
    type: str
    created_by: str
    description: str
    methods: dict[str, GenesisMethod]

    def __init__(self, artifact_id: str, description: str) -> None:
        self.id = artifact_id
        self.type = "genesis"
        self.created_by = SYSTEM_OWNER
        self.description = description
        self.methods = {}

    def register_method(
        self,
        name: str,
        handler: Callable[[list[Any], str], dict[str, Any]],
        cost: int = 0,
        description: str = ""
    ) -> None:
        """Register a callable method on this genesis artifact"""
        self.methods[name] = GenesisMethod(
            name=name,
            handler=handler,
            cost=cost,
            description=description
        )

    def get_method(self, method_name: str) -> GenesisMethod | None:
        """Get a method by name"""
        return self.methods.get(method_name)

    def list_methods(self) -> list[MethodInfo]:
        """List available methods"""
        return [
            {"name": m.name, "cost": m.cost, "description": m.description}
            for m in self.methods.values()
        ]

    def get_interface(self) -> dict[str, Any]:
        """Get the interface schema for this artifact (Plan #14).

        Returns a JSON Schema-compatible interface describing the artifact's
        tools (methods) and their inputs/outputs. Uses MCP-compatible format.

        Override in subclasses to add detailed inputSchema for each method.
        """
        tools = []
        for method in self.methods.values():
            tools.append({
                "name": method.name,
                "description": method.description,
                "cost": method.cost,
            })
        return {
            "description": self.description,
            "tools": tools,
        }

    def to_dict(self) -> GenesisArtifactDict:
        """Convert to dict for artifact listing"""
        return {
            "id": self.id,
            "type": self.type,
            "created_by": self.created_by,
            "content": self.description,
            "methods": self.list_methods()
        }
