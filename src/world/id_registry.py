"""Unified ID Registry - Single namespace for all IDs

Plan #7: Single ID Namespace

This module provides a central registry that ensures global uniqueness of IDs
across all entity types: agents, artifacts, and principals.

ADR-0001 says "everything is an artifact" - but currently principals and
artifacts are tracked separately, allowing potential ID collisions. This
registry enforces global uniqueness so the same ID cannot exist in both
the artifact store and the ledger.

Usage:
    registry = IDRegistry()

    # Register IDs (raises if collision)
    registry.register("agent_001", "agent")
    registry.register("my_artifact", "artifact")

    # Check existence
    registry.exists("agent_001")  # True

    # Lookup returns entity type
    registry.lookup("agent_001")  # "agent"

    # Unregister when deleted
    registry.unregister("my_artifact")
"""

from __future__ import annotations

from typing import Literal


EntityType = Literal["agent", "artifact", "principal", "genesis"]


class IDCollisionError(Exception):
    """Raised when attempting to register an ID that already exists."""

    def __init__(self, entity_id: str, existing_type: str, new_type: str) -> None:
        self.entity_id = entity_id
        self.existing_type = existing_type
        self.new_type = new_type
        super().__init__(
            f"ID collision: '{entity_id}' already registered as '{existing_type}', "
            f"cannot register as '{new_type}'"
        )


class IDRegistry:
    """Central registry for global ID uniqueness.

    Ensures no two entities (agents, artifacts, principals) share the same ID.
    All systems that create IDs (ArtifactStore, Ledger) should register
    through this registry.

    Thread-safety: This class is NOT thread-safe. Concurrent access should
    be synchronized externally (which matches the current single-threaded
    tick model).
    """

    _ids: dict[str, EntityType]

    def __init__(self) -> None:
        """Initialize empty registry."""
        self._ids = {}

    def register(self, entity_id: str, entity_type: EntityType) -> None:
        """Register an ID in the global namespace.

        Args:
            entity_id: The unique identifier to register
            entity_type: Type of entity ("agent", "artifact", "principal", "genesis")

        Raises:
            IDCollisionError: If the ID is already registered
        """
        if entity_id in self._ids:
            raise IDCollisionError(entity_id, self._ids[entity_id], entity_type)
        self._ids[entity_id] = entity_type

    def unregister(self, entity_id: str) -> bool:
        """Remove an ID from the registry.

        Args:
            entity_id: The ID to remove

        Returns:
            True if the ID was removed, False if it didn't exist
        """
        if entity_id in self._ids:
            del self._ids[entity_id]
            return True
        return False

    def exists(self, entity_id: str) -> bool:
        """Check if an ID is registered.

        Args:
            entity_id: The ID to check

        Returns:
            True if the ID exists in the registry
        """
        return entity_id in self._ids

    def lookup(self, entity_id: str) -> EntityType | None:
        """Look up the entity type for an ID.

        Args:
            entity_id: The ID to look up

        Returns:
            The entity type if found, None otherwise
        """
        return self._ids.get(entity_id)

    def get_all_ids(self) -> list[str]:
        """Get all registered IDs.

        Returns:
            List of all registered IDs
        """
        return list(self._ids.keys())

    def get_ids_by_type(self, entity_type: EntityType) -> list[str]:
        """Get all IDs of a specific type.

        Args:
            entity_type: The type to filter by

        Returns:
            List of IDs matching the given type
        """
        return [eid for eid, etype in self._ids.items() if etype == entity_type]

    def count(self) -> int:
        """Get total number of registered IDs."""
        return len(self._ids)

    def clear(self) -> None:
        """Clear all registrations. Use with caution - mainly for testing."""
        self._ids.clear()
