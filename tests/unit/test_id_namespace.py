"""Unit tests for single ID namespace (Plan #7).

Tests the unified ID registry where all IDs (agents, artifacts, principals)
share one namespace.

Required tests from plan:
- test_no_duplicate_ids: Registration fails if ID exists
- test_lookup_by_id_only: Single lookup mechanism works
- test_agent_is_artifact: Agents stored in artifact store

The ID registry is in world state and ensures:
1. No ID collisions across entity types
2. Single lookup mechanism regardless of type
3. Agents are stored as artifacts with has_standing=True
"""

from __future__ import annotations

import pytest

from src.world.artifacts import ArtifactStore, create_agent_artifact
from src.world.id_registry import IDRegistry, IDType, EntityNotFoundError


class TestIDRegistryBasic:
    """Tests for basic ID registry operations."""

    def test_register_artifact_id(self) -> None:
        """Verify artifact IDs can be registered."""
        registry = IDRegistry()
        registry.register("art_001", IDType.ARTIFACT)
        assert registry.exists("art_001")
        assert registry.get_type("art_001") == IDType.ARTIFACT

    def test_register_agent_id(self) -> None:
        """Verify agent IDs can be registered."""
        registry = IDRegistry()
        registry.register("agent_001", IDType.AGENT)
        assert registry.exists("agent_001")
        assert registry.get_type("agent_001") == IDType.AGENT

    def test_register_principal_id(self) -> None:
        """Verify principal IDs can be registered."""
        registry = IDRegistry()
        registry.register("principal_001", IDType.PRINCIPAL)
        assert registry.exists("principal_001")
        assert registry.get_type("principal_001") == IDType.PRINCIPAL


class TestNoDuplicateIDs:
    """Tests for duplicate ID prevention (required by plan)."""

    def test_no_duplicate_ids(self) -> None:
        """Verify registration fails if ID already exists (any type)."""
        registry = IDRegistry()

        # Register first ID
        registry.register("entity_001", IDType.ARTIFACT)

        # Attempt duplicate registration should fail
        with pytest.raises(ValueError, match="already registered"):
            registry.register("entity_001", IDType.ARTIFACT)

    def test_no_duplicate_cross_type(self) -> None:
        """Verify same ID cannot be used across different types."""
        registry = IDRegistry()

        # Register as artifact
        registry.register("shared_id", IDType.ARTIFACT)

        # Cannot register same ID as agent
        with pytest.raises(ValueError, match="already registered"):
            registry.register("shared_id", IDType.AGENT)

        # Cannot register same ID as principal
        with pytest.raises(ValueError, match="already registered"):
            registry.register("shared_id", IDType.PRINCIPAL)

    def test_different_ids_same_type(self) -> None:
        """Verify different IDs of same type can coexist."""
        registry = IDRegistry()

        registry.register("agent_001", IDType.AGENT)
        registry.register("agent_002", IDType.AGENT)

        assert registry.exists("agent_001")
        assert registry.exists("agent_002")


class TestLookupByIDOnly:
    """Tests for single lookup mechanism (required by plan)."""

    def test_lookup_by_id_only(self) -> None:
        """Verify lookup works by ID alone, without knowing type."""
        registry = IDRegistry()

        # Register entities of different types
        registry.register("artifact_001", IDType.ARTIFACT)
        registry.register("agent_001", IDType.AGENT)
        registry.register("principal_001", IDType.PRINCIPAL)

        # Lookup by ID returns correct info without specifying type
        assert registry.lookup("artifact_001") is not None
        assert registry.lookup("agent_001") is not None
        assert registry.lookup("principal_001") is not None

    def test_lookup_returns_type(self) -> None:
        """Verify lookup returns the entity type."""
        registry = IDRegistry()

        registry.register("test_artifact", IDType.ARTIFACT)
        registry.register("test_agent", IDType.AGENT)

        info = registry.lookup("test_artifact")
        assert info is not None
        assert info["id"] == "test_artifact"
        assert info["type"] == IDType.ARTIFACT

        info = registry.lookup("test_agent")
        assert info is not None
        assert info["id"] == "test_agent"
        assert info["type"] == IDType.AGENT

    def test_lookup_nonexistent_returns_none(self) -> None:
        """Verify lookup of nonexistent ID returns None."""
        registry = IDRegistry()
        assert registry.lookup("does_not_exist") is None


class TestAgentIsArtifact:
    """Tests for agents stored as artifacts (required by plan)."""

    def test_agent_is_artifact(self) -> None:
        """Verify agents are stored in artifact store with is_agent=True."""
        store = ArtifactStore()
        registry = IDRegistry()

        # Create agent artifact
        agent = create_agent_artifact(
            agent_id="agent_001",
            owner_id="agent_001",
            agent_config={"model": "test"},
        )

        # Store in artifact store
        store.artifacts[agent.id] = agent

        # Register in ID registry as AGENT type
        registry.register("agent_001", IDType.AGENT)

        # Verify agent exists as artifact
        retrieved = store.get("agent_001")
        assert retrieved is not None
        assert retrieved.is_agent is True
        assert retrieved.type == "agent"

        # Verify registry knows it's an agent
        assert registry.get_type("agent_001") == IDType.AGENT

    def test_agent_registration_links_to_artifact_store(self) -> None:
        """Verify ID registry can be used alongside artifact store."""
        store = ArtifactStore()
        registry = IDRegistry()

        # Create and store agent
        agent = create_agent_artifact(
            agent_id="my_agent",
            owner_id="my_agent",
            agent_config={},
        )
        store.artifacts[agent.id] = agent
        registry.register("my_agent", IDType.AGENT)

        # Create and store regular artifact
        store.write(
            artifact_id="my_data",
            type="data",
            content="some data",
            owner_id="my_agent",
        )
        registry.register("my_data", IDType.ARTIFACT)

        # Both exist in registry
        assert registry.exists("my_agent")
        assert registry.exists("my_data")

        # Both exist in artifact store
        assert store.exists("my_agent")
        assert store.exists("my_data")

        # Only agent is marked as agent
        assert store.get("my_agent").is_agent is True  # type: ignore[union-attr]
        assert store.get("my_data").is_agent is False  # type: ignore[union-attr]


class TestIDRegistryOperations:
    """Tests for additional ID registry operations."""

    def test_unregister_id(self) -> None:
        """Verify IDs can be unregistered."""
        registry = IDRegistry()
        registry.register("temp_id", IDType.ARTIFACT)
        assert registry.exists("temp_id")

        registry.unregister("temp_id")
        assert not registry.exists("temp_id")

    def test_unregister_nonexistent_raises(self) -> None:
        """Verify unregistering nonexistent ID raises error."""
        registry = IDRegistry()
        with pytest.raises(EntityNotFoundError):
            registry.unregister("does_not_exist")

    def test_list_by_type(self) -> None:
        """Verify can list all IDs of a specific type."""
        registry = IDRegistry()
        registry.register("agent_1", IDType.AGENT)
        registry.register("agent_2", IDType.AGENT)
        registry.register("artifact_1", IDType.ARTIFACT)

        agents = registry.list_by_type(IDType.AGENT)
        assert set(agents) == {"agent_1", "agent_2"}

        artifacts = registry.list_by_type(IDType.ARTIFACT)
        assert set(artifacts) == {"artifact_1"}

    def test_count(self) -> None:
        """Verify count of registered IDs."""
        registry = IDRegistry()
        assert registry.count() == 0

        registry.register("id_1", IDType.ARTIFACT)
        assert registry.count() == 1

        registry.register("id_2", IDType.AGENT)
        assert registry.count() == 2

    def test_all_ids(self) -> None:
        """Verify can get all registered IDs."""
        registry = IDRegistry()
        registry.register("a", IDType.ARTIFACT)
        registry.register("b", IDType.AGENT)
        registry.register("c", IDType.PRINCIPAL)

        all_ids = registry.all_ids()
        assert set(all_ids) == {"a", "b", "c"}


class TestPrincipalAsArtifactMetadata:
    """Tests for principals tracked as artifact metadata (Plan #7 Phase 2)."""

    def test_principal_is_artifact_with_has_standing(self) -> None:
        """Verify principals are artifacts with has_standing=True."""
        store = ArtifactStore()
        registry = IDRegistry()

        # Create agent (which is a principal)
        agent = create_agent_artifact(
            agent_id="principal_agent",
            owner_id="principal_agent",
            agent_config={},
        )
        store.artifacts[agent.id] = agent
        registry.register("principal_agent", IDType.AGENT)

        # Verify agent is a principal (has_standing=True)
        retrieved = store.get("principal_agent")
        assert retrieved is not None
        assert retrieved.is_principal is True
        assert retrieved.has_standing is True

    def test_regular_artifact_is_not_principal(self) -> None:
        """Verify regular artifacts are not principals."""
        store = ArtifactStore()
        registry = IDRegistry()

        store.write(
            artifact_id="data_artifact",
            type="data",
            content="some data",
            owner_id="owner",
        )
        registry.register("data_artifact", IDType.ARTIFACT)

        retrieved = store.get("data_artifact")
        assert retrieved is not None
        assert retrieved.is_principal is False
        assert retrieved.has_standing is False


class TestIDTypePrefixes:
    """Tests for ID type prefixes for readability (Plan #7 Phase 3)."""

    def test_ids_can_have_type_prefix(self) -> None:
        """Verify IDs can include type prefix for readability."""
        registry = IDRegistry()

        # Register with prefixes (common convention)
        registry.register("agent_alpha", IDType.AGENT)
        registry.register("art_document", IDType.ARTIFACT)
        registry.register("principal_dao", IDType.PRINCIPAL)

        # All unique despite similar prefixes
        assert registry.count() == 3

    def test_uniqueness_is_global_not_per_prefix(self) -> None:
        """Verify uniqueness is global regardless of prefix convention."""
        registry = IDRegistry()

        # Even if we wanted "agent_001" and "art_001" to be same entity
        # they are different IDs in the global namespace
        registry.register("agent_001", IDType.AGENT)
        registry.register("art_001", IDType.ARTIFACT)

        assert registry.count() == 2
        assert registry.get_type("agent_001") == IDType.AGENT
        assert registry.get_type("art_001") == IDType.ARTIFACT
