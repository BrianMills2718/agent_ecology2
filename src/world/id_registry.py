"""Unified ID Registry (Plan #7: Single ID Namespace).

Provides a single namespace where every ID is unique across all entity types
(agents, artifacts, principals). This prevents ID collisions and simplifies
lookups.

Design:
- All IDs registered here before use
- Registration fails if ID exists (any type)
- Lookup by ID only, returns type info
- Type prefix (e.g., "agent_", "art_") is convention, not enforcement

See docs/plans/07_single_id_namespace.md for design rationale.
"""

from __future__ import annotations

from enum import Enum
from typing import TypedDict


class IDType(Enum):
    """Types of entities in the ID namespace."""

    ARTIFACT = "artifact"
    AGENT = "agent"
    PRINCIPAL = "principal"


class IDInfo(TypedDict):
    """Information about a registered ID."""

    id: str
    type: IDType


class EntityNotFoundError(Exception):
    """Raised when an entity ID is not found in the registry."""

    pass


class IDRegistry:
    """Unified ID registry for all entity types.

    Ensures no ID collisions across agents, artifacts, and principals.
    All IDs share a single namespace.

    Example:
        >>> registry = IDRegistry()
        >>> registry.register("agent_001", IDType.AGENT)
        >>> registry.register("agent_001", IDType.ARTIFACT)  # Raises!
        ValueError: ID 'agent_001' already registered as AGENT

        >>> registry.lookup("agent_001")
        {"id": "agent_001", "type": IDType.AGENT}
    """

    _registry: dict[str, IDType]

    def __init__(self) -> None:
        """Initialize an empty ID registry."""
        self._registry = {}

    def register(self, entity_id: str, entity_type: IDType) -> None:
        """Register an ID in the namespace.

        Args:
            entity_id: The unique ID to register
            entity_type: The type of entity (ARTIFACT, AGENT, PRINCIPAL)

        Raises:
            ValueError: If ID is already registered (any type)
        """
        if entity_id in self._registry:
            existing_type = self._registry[entity_id]
            raise ValueError(
                f"ID '{entity_id}' already registered as {existing_type.name}"
            )
        self._registry[entity_id] = entity_type

    def unregister(self, entity_id: str) -> None:
        """Remove an ID from the registry.

        Args:
            entity_id: The ID to unregister

        Raises:
            EntityNotFoundError: If ID is not registered
        """
        if entity_id not in self._registry:
            raise EntityNotFoundError(f"ID '{entity_id}' not found in registry")
        del self._registry[entity_id]

    def exists(self, entity_id: str) -> bool:
        """Check if an ID is registered.

        Args:
            entity_id: The ID to check

        Returns:
            True if registered, False otherwise
        """
        return entity_id in self._registry

    def get_type(self, entity_id: str) -> IDType | None:
        """Get the type of a registered ID.

        Args:
            entity_id: The ID to look up

        Returns:
            The IDType if registered, None otherwise
        """
        return self._registry.get(entity_id)

    def lookup(self, entity_id: str) -> IDInfo | None:
        """Look up an ID and return its info.

        This is the single lookup mechanism - works by ID alone
        without needing to know the entity type.

        Args:
            entity_id: The ID to look up

        Returns:
            IDInfo dict with id and type, or None if not found
        """
        entity_type = self._registry.get(entity_id)
        if entity_type is None:
            return None
        return {"id": entity_id, "type": entity_type}

    def list_by_type(self, entity_type: IDType) -> list[str]:
        """List all IDs of a specific type.

        Args:
            entity_type: The type to filter by

        Returns:
            List of IDs of that type
        """
        return [
            entity_id
            for entity_id, etype in self._registry.items()
            if etype == entity_type
        ]

    def count(self) -> int:
        """Get the total count of registered IDs.

        Returns:
            Number of registered IDs
        """
        return len(self._registry)

    def all_ids(self) -> list[str]:
        """Get all registered IDs.

        Returns:
            List of all registered IDs
        """
        return list(self._registry.keys())
