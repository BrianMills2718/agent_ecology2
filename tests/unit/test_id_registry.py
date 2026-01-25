"""Unit tests for Plan #7: Single ID Namespace

Tests the IDRegistry class and its integration with ArtifactStore and Ledger
to ensure global ID uniqueness across all entity types.

Required tests (from plan):
- test_no_duplicate_ids
- test_lookup_by_id_only
- test_agent_is_artifact
"""

import pytest

from src.world.id_registry import IDRegistry, IDCollisionError
from src.world.artifacts import ArtifactStore, create_agent_artifact
from src.world.ledger import Ledger


class TestIDRegistry:
    """Unit tests for the IDRegistry class itself."""

    def test_register_and_exists(self) -> None:
        """Basic registration and existence check."""
        registry = IDRegistry()

        assert not registry.exists("entity_1")
        registry.register("entity_1", "artifact")
        assert registry.exists("entity_1")

    def test_no_duplicate_ids(self) -> None:
        """Test that duplicate IDs raise IDCollisionError."""
        registry = IDRegistry()

        registry.register("shared_id", "artifact")

        # Same type collision
        with pytest.raises(IDCollisionError) as exc_info:
            registry.register("shared_id", "artifact")
        assert exc_info.value.entity_id == "shared_id"
        assert exc_info.value.existing_type == "artifact"

        # Different type collision - principal trying to use artifact's ID
        with pytest.raises(IDCollisionError) as exc_info:
            registry.register("shared_id", "principal")
        assert exc_info.value.entity_id == "shared_id"
        assert exc_info.value.existing_type == "artifact"
        assert exc_info.value.new_type == "principal"

    def test_lookup_by_id_only(self) -> None:
        """Test that lookup works by ID regardless of type."""
        registry = IDRegistry()

        registry.register("agent_1", "agent")
        registry.register("artifact_1", "artifact")
        registry.register("principal_1", "principal")

        # Lookup returns type, works without knowing type in advance
        assert registry.lookup("agent_1") == "agent"
        assert registry.lookup("artifact_1") == "artifact"
        assert registry.lookup("principal_1") == "principal"
        assert registry.lookup("nonexistent") is None

    def test_unregister(self) -> None:
        """Test ID unregistration."""
        registry = IDRegistry()

        registry.register("entity_1", "artifact")
        assert registry.exists("entity_1")

        result = registry.unregister("entity_1")
        assert result is True
        assert not registry.exists("entity_1")

        # Re-register after unregister should work
        registry.register("entity_1", "principal")
        assert registry.lookup("entity_1") == "principal"

        # Unregister non-existent returns False
        assert registry.unregister("nonexistent") is False

    def test_get_ids_by_type(self) -> None:
        """Test filtering IDs by type."""
        registry = IDRegistry()

        registry.register("agent_1", "agent")
        registry.register("agent_2", "agent")
        registry.register("artifact_1", "artifact")
        registry.register("genesis_ledger", "genesis")

        agents = registry.get_ids_by_type("agent")
        assert set(agents) == {"agent_1", "agent_2"}

        artifacts = registry.get_ids_by_type("artifact")
        assert artifacts == ["artifact_1"]

        genesis = registry.get_ids_by_type("genesis")
        assert genesis == ["genesis_ledger"]

    def test_count_and_get_all(self) -> None:
        """Test count and get_all_ids."""
        registry = IDRegistry()

        assert registry.count() == 0
        assert registry.get_all_ids() == []

        registry.register("id_1", "agent")
        registry.register("id_2", "artifact")
        registry.register("id_3", "principal")

        assert registry.count() == 3
        assert set(registry.get_all_ids()) == {"id_1", "id_2", "id_3"}

    def test_clear(self) -> None:
        """Test clearing the registry."""
        registry = IDRegistry()

        registry.register("id_1", "agent")
        registry.register("id_2", "artifact")
        assert registry.count() == 2

        registry.clear()
        assert registry.count() == 0
        assert not registry.exists("id_1")


class TestAgentIsArtifact:
    """Test that agents are stored as artifacts (ADR-0001 compliance)."""

    def test_agent_is_artifact(self) -> None:
        """Test that agent creation uses artifact storage, not separate tracking."""
        store = ArtifactStore()
        registry = IDRegistry()

        # Create agent artifact (factory function from artifacts.py)
        agent = create_agent_artifact(
            agent_id="agent_001",
            created_by="agent_001",
            agent_config={"model": "test", "system_prompt": "You are a test agent."}
        )

        # Store it (normally done by World)
        store.artifacts[agent.id] = agent
        registry.register(agent.id, "agent")

        # Verify agent IS an artifact
        stored = store.get("agent_001")
        assert stored is not None
        assert stored.is_agent is True
        assert stored.is_principal is True
        assert stored.type == "agent"

        # Verify in registry
        assert registry.lookup("agent_001") == "agent"


class TestCrossSystemCollision:
    """Test collision prevention between ArtifactStore and Ledger."""

    def test_artifact_then_principal_collision(self) -> None:
        """Cannot create principal with same ID as existing artifact."""
        registry = IDRegistry()

        # Register as artifact first
        registry.register("shared_id", "artifact")

        # Trying to register as principal should fail
        with pytest.raises(IDCollisionError) as exc_info:
            registry.register("shared_id", "principal")

        assert "already registered as 'artifact'" in str(exc_info.value)

    def test_principal_then_artifact_collision(self) -> None:
        """Cannot create artifact with same ID as existing principal."""
        registry = IDRegistry()

        # Register as principal first
        registry.register("shared_id", "principal")

        # Trying to register as artifact should fail
        with pytest.raises(IDCollisionError) as exc_info:
            registry.register("shared_id", "artifact")

        assert "already registered as 'principal'" in str(exc_info.value)

    def test_genesis_artifact_collision(self) -> None:
        """Genesis artifacts also participate in collision prevention."""
        registry = IDRegistry()

        # Register genesis artifact
        registry.register("genesis_ledger", "genesis")

        # Cannot use same ID for anything else
        with pytest.raises(IDCollisionError):
            registry.register("genesis_ledger", "artifact")

        with pytest.raises(IDCollisionError):
            registry.register("genesis_ledger", "principal")

        with pytest.raises(IDCollisionError):
            registry.register("genesis_ledger", "agent")


class TestWorldIntegration:
    """Test IDRegistry integration with World (full collision prevention)."""

    def test_genesis_artifacts_registered_on_world_init(self) -> None:
        """Genesis artifacts are registered when World is created."""
        from src.world.world import World
        from src.world.id_registry import IDRegistry

        config = {
            "world": {"max_ticks": 10},
            "costs": {"per_1k_input_tokens": 1, "per_1k_output_tokens": 2},
            "logging": {"output_file": "/dev/null"},
            "principals": [],
            "rights": {"default_quotas": {"compute": 100.0, "disk": 10000.0}},
        }
        world = World(config)

        # Genesis artifacts should be registered
        # Note: genesis_store removed in Plan #190 - use query_kernel action
        assert world.id_registry.exists("genesis_ledger")
        assert world.id_registry.exists("genesis_mint")
        assert world.id_registry.exists("genesis_escrow")
        assert world.id_registry.lookup("genesis_ledger") == "genesis"

    def test_principals_registered_on_world_init(self) -> None:
        """Principals are registered when World is created."""
        from src.world.world import World

        config = {
            "world": {"max_ticks": 10},
            "costs": {"per_1k_input_tokens": 1, "per_1k_output_tokens": 2},
            "logging": {"output_file": "/dev/null"},
            "principals": [
                {"id": "alice", "starting_scrip": 100},
                {"id": "bob", "starting_scrip": 100},
            ],
            "rights": {"default_quotas": {"compute": 100.0, "disk": 10000.0}},
        }
        world = World(config)

        # Principals should be registered
        assert world.id_registry.exists("alice")
        assert world.id_registry.exists("bob")
        assert world.id_registry.lookup("alice") == "principal"
        assert world.id_registry.lookup("bob") == "principal"

    def test_artifact_cannot_use_principal_id(self) -> None:
        """Cannot create artifact with same ID as existing principal."""
        from src.world.world import World
        from src.world.id_registry import IDCollisionError

        config = {
            "world": {"max_ticks": 10},
            "costs": {"per_1k_input_tokens": 1, "per_1k_output_tokens": 2},
            "logging": {"output_file": "/dev/null"},
            "principals": [{"id": "alice", "starting_scrip": 100}],
            "rights": {"default_quotas": {"compute": 100.0, "disk": 10000.0}},
        }
        world = World(config)

        # Try to create artifact with principal's ID
        with pytest.raises(IDCollisionError) as exc_info:
            world.artifacts.write(
                artifact_id="alice",  # Same as principal
                type="data",
                content="some data",
                created_by="system",
            )

        assert exc_info.value.entity_id == "alice"
        assert exc_info.value.existing_type == "principal"

    def test_update_existing_artifact_allowed(self) -> None:
        """Updating an existing artifact is allowed (not a collision)."""
        from src.world.world import World

        config = {
            "world": {"max_ticks": 10},
            "costs": {"per_1k_input_tokens": 1, "per_1k_output_tokens": 2},
            "logging": {"output_file": "/dev/null"},
            "principals": [],
            "rights": {"default_quotas": {"compute": 100.0, "disk": 10000.0}},
        }
        world = World(config)

        # First create an artifact
        world.artifacts.write(
            artifact_id="my_artifact",
            type="data",
            content="original content",
            created_by="system",
        )

        # Updating it should work fine (no collision error)
        world.artifacts.write(
            artifact_id="my_artifact",
            type="data",
            content="updated content",
            created_by="system",
        )

        # Verify it was updated
        artifact = world.artifacts.get("my_artifact")
        assert artifact is not None
        assert artifact.content == "updated content"

    def test_new_artifact_gets_registered(self) -> None:
        """New artifacts created via World are registered in ID namespace."""
        from src.world.world import World

        config = {
            "world": {"max_ticks": 10},
            "costs": {"per_1k_input_tokens": 1, "per_1k_output_tokens": 2},
            "logging": {"output_file": "/dev/null"},
            "principals": [],
            "rights": {"default_quotas": {"compute": 100.0, "disk": 10000.0}},
        }
        world = World(config)

        # Create a new artifact
        world.artifacts.write(
            artifact_id="my_artifact",
            type="data",
            content="some data",
            created_by="system",
        )

        # Should be registered
        assert world.id_registry.exists("my_artifact")
        assert world.id_registry.lookup("my_artifact") == "artifact"
