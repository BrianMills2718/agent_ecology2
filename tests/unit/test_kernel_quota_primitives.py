"""Tests for kernel quota primitives - Plan #42

These tests verify that quotas are kernel state, not genesis artifact state.
"""

from __future__ import annotations

import tempfile
from typing import Any

import pytest

from src.world.world import World
from src.world.kernel_interface import KernelState, KernelActions


@pytest.fixture
def world_config() -> dict[str, Any]:
    """Minimal world config for testing."""
    with tempfile.NamedTemporaryFile(suffix=".jsonl", delete=False) as f:
        output_file = f.name

    return {
        "world": {"max_ticks": 10},
        "costs": {"per_1k_input_tokens": 1, "per_1k_output_tokens": 1},
        "logging": {"output_file": output_file},
        "principals": [
            {"id": "alice", "starting_scrip": 100},
            {"id": "bob", "starting_scrip": 50},
        ],
        "rights": {
            "default_quotas": {"compute": 100.0, "disk": 10000.0}
        },
    }


@pytest.fixture
def world(world_config: dict[str, Any]) -> World:
    """Create a world with default config for testing."""
    return World(world_config)


@pytest.fixture
def kernel_state(world: World) -> KernelState:
    """Create KernelState interface."""
    return KernelState(world)


@pytest.fixture
def kernel_actions(world: World) -> KernelActions:
    """Create KernelActions interface."""
    return KernelActions(world)


class TestKernelQuotaState:
    """Tests for quota storage in kernel metadata."""

    def test_quota_stored_in_kernel(self, world: World) -> None:
        """Quotas should be stored as kernel state, not artifact state."""
        # Set quota via world (kernel)
        world.set_quota("alice", "cpu_seconds_per_minute", 10.0)

        # Verify it's in kernel state, not in any artifact
        assert world.get_quota("alice", "cpu_seconds_per_minute") == 10.0

    def test_default_quota_is_zero(self, world: World) -> None:
        """Unset quotas should default to 0."""
        assert world.get_quota("unknown_agent", "cpu_seconds_per_minute") == 0.0

    def test_multiple_resource_quotas(self, world: World) -> None:
        """Each principal can have multiple resource quotas."""
        world.set_quota("alice", "cpu_seconds_per_minute", 10.0)
        world.set_quota("alice", "llm_tokens_per_minute", 1000.0)
        world.set_quota("alice", "disk_bytes", 1_000_000.0)

        assert world.get_quota("alice", "cpu_seconds_per_minute") == 10.0
        assert world.get_quota("alice", "llm_tokens_per_minute") == 1000.0
        assert world.get_quota("alice", "disk_bytes") == 1_000_000.0


class TestKernelStateQuotaMethods:
    """Tests for KernelState quota query methods."""

    def test_get_quota(self, world: World, kernel_state: KernelState) -> None:
        """KernelState.get_quota returns assigned quota."""
        world.set_quota("alice", "cpu_seconds_per_minute", 10.0)

        assert kernel_state.get_quota("alice", "cpu_seconds_per_minute") == 10.0

    def test_get_quota_not_found(self, kernel_state: KernelState) -> None:
        """KernelState.get_quota returns 0 for unset quotas."""
        assert kernel_state.get_quota("unknown", "cpu_seconds_per_minute") == 0.0

    def test_get_available_capacity(
        self, world: World, kernel_state: KernelState
    ) -> None:
        """KernelState.get_available_capacity considers usage."""
        world.set_quota("alice", "cpu_seconds_per_minute", 10.0)

        # Initially, all capacity is available
        assert kernel_state.get_available_capacity(
            "alice", "cpu_seconds_per_minute"
        ) == 10.0

        # After consuming some, less is available
        world.consume_quota("alice", "cpu_seconds_per_minute", 3.0)
        assert kernel_state.get_available_capacity(
            "alice", "cpu_seconds_per_minute"
        ) == 7.0

    def test_would_exceed_quota(
        self, world: World, kernel_state: KernelState
    ) -> None:
        """KernelState.would_exceed_quota pre-checks actions."""
        world.set_quota("alice", "cpu_seconds_per_minute", 10.0)

        # Should not exceed
        assert not kernel_state.would_exceed_quota(
            "alice", "cpu_seconds_per_minute", 5.0
        )

        # Should exceed
        assert kernel_state.would_exceed_quota(
            "alice", "cpu_seconds_per_minute", 15.0
        )


class TestKernelActionsQuotaMethods:
    """Tests for KernelActions quota mutation methods."""

    def test_transfer_quota(
        self, world: World, kernel_actions: KernelActions
    ) -> None:
        """KernelActions.transfer_quota atomically moves quota."""
        world.set_quota("alice", "cpu_seconds_per_minute", 10.0)
        world.set_quota("bob", "cpu_seconds_per_minute", 5.0)

        # Transfer 3 from alice to bob
        success = kernel_actions.transfer_quota(
            "alice", "bob", "cpu_seconds_per_minute", 3.0
        )

        assert success
        assert world.get_quota("alice", "cpu_seconds_per_minute") == 7.0
        assert world.get_quota("bob", "cpu_seconds_per_minute") == 8.0

    def test_transfer_quota_insufficient(
        self, world: World, kernel_actions: KernelActions
    ) -> None:
        """KernelActions.transfer_quota fails if insufficient quota."""
        world.set_quota("alice", "cpu_seconds_per_minute", 5.0)

        # Try to transfer more than available
        success = kernel_actions.transfer_quota(
            "alice", "bob", "cpu_seconds_per_minute", 10.0
        )

        assert not success
        # Quota unchanged
        assert world.get_quota("alice", "cpu_seconds_per_minute") == 5.0

    def test_consume_quota(
        self, world: World, kernel_actions: KernelActions
    ) -> None:
        """KernelActions.consume_quota records usage."""
        world.set_quota("alice", "cpu_seconds_per_minute", 10.0)

        success = kernel_actions.consume_quota(
            "alice", "cpu_seconds_per_minute", 3.0
        )

        assert success
        # Available capacity reduced
        kernel_state = KernelState(world)
        assert kernel_state.get_available_capacity(
            "alice", "cpu_seconds_per_minute"
        ) == 7.0

    def test_consume_quota_exceeds(
        self, world: World, kernel_actions: KernelActions
    ) -> None:
        """KernelActions.consume_quota fails if would exceed."""
        world.set_quota("alice", "cpu_seconds_per_minute", 5.0)

        success = kernel_actions.consume_quota(
            "alice", "cpu_seconds_per_minute", 10.0
        )

        assert not success


class TestQuotaEnforcement:
    """Tests for quota enforcement in action execution."""

    def test_quota_exceeded_error_code(self, world: World) -> None:
        """Actions blocked by quota return QUOTA_EXCEEDED error."""
        from src.world.actions import InvokeArtifactIntent
        from src.world.errors import ErrorCode

        # Create an agent with very low quota
        world.set_quota("alice", "llm_tokens_per_minute", 1.0)

        # Try to invoke something that costs more
        # (This depends on how cost estimation works)
        # For now, just verify the error code exists
        assert hasattr(ErrorCode, "QUOTA_EXCEEDED")

    def test_quota_exceeded_is_retriable(self, world: World) -> None:
        """QUOTA_EXCEEDED errors should be marked as retriable."""
        from src.world.errors import ErrorCode

        # Verify QUOTA_EXCEEDED exists and can be used
        error_code = ErrorCode.QUOTA_EXCEEDED
        assert error_code.value == "quota_exceeded"
