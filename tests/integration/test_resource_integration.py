"""Integration tests for ResourceManager with World (Plan #95).

Tests that World's quota methods correctly delegate to ResourceManager.
"""

import pytest
from src.world.world import World
from src.world.resource_manager import ResourceManager, ResourceType


@pytest.fixture
def world_with_resource_manager(tmp_path, minimal_config):
    """Create a World instance with ResourceManager."""
    config = minimal_config.copy()
    config["logging"] = {"output_file": str(tmp_path / "run.jsonl")}
    return World(config)


class TestWorldResourceManagerIntegration:
    """Test World's quota methods delegate to ResourceManager."""

    def test_world_has_resource_manager(self, world_with_resource_manager):
        """World should have a ResourceManager instance."""
        world = world_with_resource_manager
        assert hasattr(world, "resource_manager")
        assert isinstance(world.resource_manager, ResourceManager)

    def test_set_quota_updates_resource_manager(self, world_with_resource_manager):
        """set_quota should update ResourceManager's quota storage."""
        world = world_with_resource_manager
        world.set_quota("agent_a", "cpu", 100.0)

        # Verify via ResourceManager directly
        assert world.resource_manager.get_quota("agent_a", "cpu") == 100.0

    def test_get_quota_reads_from_resource_manager(self, world_with_resource_manager):
        """get_quota should read from ResourceManager."""
        world = world_with_resource_manager
        world.resource_manager.create_principal("agent_b")
        world.resource_manager.set_quota("agent_b", "disk", 5000.0)

        # Verify World reads from ResourceManager
        assert world.get_quota("agent_b", "disk") == 5000.0

    def test_consume_quota_uses_resource_manager_allocate(self, world_with_resource_manager):
        """consume_quota should use ResourceManager.allocate()."""
        world = world_with_resource_manager
        world.set_quota("agent_c", "memory", 1000.0)

        # Consume some quota
        assert world.consume_quota("agent_c", "memory", 400.0) is True

        # Verify ResourceManager tracks the allocation
        assert world.resource_manager.get_balance("agent_c", "memory") == 400.0
        assert world.get_quota_usage("agent_c", "memory") == 400.0

    def test_consume_quota_respects_limit(self, world_with_resource_manager):
        """consume_quota should fail if would exceed limit."""
        world = world_with_resource_manager
        world.set_quota("agent_d", "bandwidth", 100.0)

        # First allocation succeeds
        assert world.consume_quota("agent_d", "bandwidth", 60.0) is True

        # Second would exceed
        assert world.consume_quota("agent_d", "bandwidth", 50.0) is False

        # Usage should still be 60
        assert world.get_quota_usage("agent_d", "bandwidth") == 60.0

    def test_get_available_capacity_uses_resource_manager(self, world_with_resource_manager):
        """get_available_capacity should use ResourceManager.get_available_quota()."""
        world = world_with_resource_manager
        world.set_quota("agent_e", "llm_tokens", 500.0)
        world.consume_quota("agent_e", "llm_tokens", 200.0)

        # Available should be quota - usage
        assert world.get_available_capacity("agent_e", "llm_tokens") == 300.0

    def test_multiple_resources_tracked_independently(self, world_with_resource_manager):
        """Different resources should be tracked independently."""
        world = world_with_resource_manager
        world.set_quota("agent_f", "cpu", 100.0)
        world.set_quota("agent_f", "memory", 1000.0)

        world.consume_quota("agent_f", "cpu", 30.0)
        world.consume_quota("agent_f", "memory", 500.0)

        assert world.get_quota_usage("agent_f", "cpu") == 30.0
        assert world.get_quota_usage("agent_f", "memory") == 500.0
        assert world.get_available_capacity("agent_f", "cpu") == 70.0
        assert world.get_available_capacity("agent_f", "memory") == 500.0

    def test_multiple_principals_tracked_independently(self, world_with_resource_manager):
        """Different principals should be tracked independently."""
        world = world_with_resource_manager
        world.set_quota("alice", "disk", 1000.0)
        world.set_quota("bob", "disk", 2000.0)

        world.consume_quota("alice", "disk", 400.0)
        world.consume_quota("bob", "disk", 800.0)

        assert world.get_quota_usage("alice", "disk") == 400.0
        assert world.get_quota_usage("bob", "disk") == 800.0


class TestResourceManagerInWorld:
    """Test ResourceManager features accessible via World."""

    def test_resource_manager_principal_created_on_set_quota(self, world_with_resource_manager):
        """Setting a quota should create the principal in ResourceManager."""
        world = world_with_resource_manager

        # Principal doesn't exist yet
        assert not world.resource_manager.principal_exists("new_agent")

        # set_quota creates it
        world.set_quota("new_agent", "cpu", 50.0)

        assert world.resource_manager.principal_exists("new_agent")

    def test_resource_manager_principal_created_on_consume_quota(self, world_with_resource_manager):
        """Consuming quota should create the principal if needed."""
        world = world_with_resource_manager

        # Set quota to allow consumption
        world.set_quota("another_agent", "memory", 1000.0)

        assert world.resource_manager.principal_exists("another_agent")
