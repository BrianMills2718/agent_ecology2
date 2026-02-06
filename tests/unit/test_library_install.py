"""Tests for library installation (Plan #29).

These tests verify the kernel action for installing Python libraries:
- Genesis libraries are free (no quota cost)
- Non-genesis libraries cost disk quota
- Blocked packages are rejected
- Insufficient quota fails the install
"""

import pytest

from src.config import load_config
from src.world.world import World
from src.world.kernel_interface import KernelActions, KernelState


@pytest.fixture
def world_with_quota() -> World:
    """Create a world with an agent that has disk quota."""
    load_config()

    config = {
        "world": {"max_ticks": 10},
        "costs": {"per_1k_input_tokens": 1, "per_1k_output_tokens": 3},
        "logging": {"output_file": "/dev/null"},
        "principals": [{"id": "agent_1", "starting_scrip": 100}],
    }
    world = World(config)
    # Plan #254: Set disk quota directly via ResourceManager
    # (rights.default_quotas config removed)
    world.resource_manager.set_quota("agent_1", "disk", 10_000_000.0)  # 10MB
    return world


class TestLibraryInstall:
    """Tests for kernel_actions.install_library()."""

    def test_genesis_library_is_free(self, world_with_quota: World) -> None:
        """Genesis libraries don't consume quota."""
        actions = KernelActions(world_with_quota)
        state = KernelState(world_with_quota)

        # Get initial disk capacity
        initial_capacity = state.get_available_capacity("agent_1", "disk")

        # Install a genesis library (numpy is in the default list)
        result = actions.install_library("agent_1", "numpy")

        assert result["success"] is True
        assert "genesis library" in result["message"].lower()
        assert result.get("quota_cost", 0) == 0

        # Capacity should be unchanged
        final_capacity = state.get_available_capacity("agent_1", "disk")
        assert final_capacity == initial_capacity

    def test_install_deducts_quota(self, world_with_quota: World) -> None:
        """Non-genesis library installation deducts from disk quota."""
        actions = KernelActions(world_with_quota)
        state = KernelState(world_with_quota)

        # Get initial disk capacity
        initial_capacity = state.get_available_capacity("agent_1", "disk")

        # Install a non-genesis library
        result = actions.install_library("agent_1", "flask")

        assert result["success"] is True
        assert result["quota_cost"] > 0

        # Capacity should be reduced
        final_capacity = state.get_available_capacity("agent_1", "disk")
        assert final_capacity < initial_capacity
        assert initial_capacity - final_capacity == result["quota_cost"]

    def test_blocked_package_rejected(self, world_with_quota: World) -> None:
        """Blocked packages are rejected with clear error."""
        actions = KernelActions(world_with_quota)
        state = KernelState(world_with_quota)

        # Get initial disk capacity
        initial_capacity = state.get_available_capacity("agent_1", "disk")

        # Try to install a blocked package (docker is in the default blocklist)
        result = actions.install_library("agent_1", "docker")

        assert result["success"] is False
        assert result["error_code"] == "BLOCKED_PACKAGE"
        assert "blocked" in result["error"].lower()

        # Capacity should be unchanged (no quota consumed)
        final_capacity = state.get_available_capacity("agent_1", "disk")
        assert final_capacity == initial_capacity

    def test_insufficient_quota_fails(self) -> None:
        """Installation fails when disk quota is insufficient."""
        load_config()

        # Create world with very limited disk quota
        config = {
            "world": {"max_ticks": 10},
            "costs": {"per_1k_input_tokens": 1, "per_1k_output_tokens": 3},
            "logging": {"output_file": "/dev/null"},
            "principals": [{"id": "agent_1", "starting_scrip": 100}],
        }
        world = World(config)
        # Plan #254: Set disk quota directly via ResourceManager
        # (rights.default_quotas config removed)
        world.resource_manager.set_quota("agent_1", "disk", 100.0)  # Very small - only 100 bytes
        actions = KernelActions(world)
        state = KernelState(world)

        # Get initial disk capacity
        initial_capacity = state.get_available_capacity("agent_1", "disk")

        # Try to install a non-genesis library (estimated at 5MB)
        result = actions.install_library("agent_1", "flask")

        assert result["success"] is False
        assert result["error_code"] == "QUOTA_EXCEEDED"
        assert "quota" in result["error"].lower()

        # Capacity should be unchanged
        final_capacity = state.get_available_capacity("agent_1", "disk")
        assert final_capacity == initial_capacity

    def test_library_installation_is_recorded(self, world_with_quota: World) -> None:
        """Installed libraries are tracked in world state."""
        actions = KernelActions(world_with_quota)

        # Initially no libraries installed
        installed = world_with_quota.get_installed_libraries("agent_1")
        assert installed == []

        # Install a non-genesis library
        result = actions.install_library("agent_1", "flask", ">=2.0.0")
        assert result["success"] is True

        # Should be recorded
        installed = world_with_quota.get_installed_libraries("agent_1")
        assert len(installed) == 1
        assert installed[0] == ("flask", ">=2.0.0")

    def test_genesis_library_not_recorded(self, world_with_quota: World) -> None:
        """Genesis libraries are not recorded (they're always available)."""
        actions = KernelActions(world_with_quota)

        # Install a genesis library
        result = actions.install_library("agent_1", "numpy")
        assert result["success"] is True

        # Should NOT be recorded (genesis libs are pre-installed)
        installed = world_with_quota.get_installed_libraries("agent_1")
        assert installed == []

    def test_case_insensitive_package_names(self, world_with_quota: World) -> None:
        """Package name matching is case-insensitive."""
        actions = KernelActions(world_with_quota)

        # Genesis library with different casing
        result = actions.install_library("agent_1", "NumPy")
        assert result["success"] is True
        assert "genesis library" in result["message"].lower()

        # Blocked package with different casing
        result = actions.install_library("agent_1", "DOCKER")
        assert result["success"] is False
        assert result["error_code"] == "BLOCKED_PACKAGE"
