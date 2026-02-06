"""Integration tests for the Agent Ecology World simulation.

These tests verify the core world mechanics without any LLM calls.
They directly test the World class by crafting ActionIntent objects
and calling execute_action.
"""

import tempfile
import os
from pathlib import Path

import pytest

from src.world import World
from src.world.actions import (
    NoopIntent,
    ReadArtifactIntent,
    WriteArtifactIntent,
    InvokeArtifactIntent,
)


@pytest.fixture
def minimal_config():
    """Minimal configuration for testing.

    Note: max_ticks removed in Plan #102. Execution limits are now
    time-based (duration) or cost-based (budget). Rate limiting must be
    enabled for compute resources to be available.
    """
    return {
        "world": {},
        "principals": [
            {"id": "agent_1", "starting_scrip": 100},
            {"id": "agent_2", "starting_scrip": 100},
        ],
        "costs": {
            "per_1k_input_tokens": 1,
            "per_1k_output_tokens": 3,
        },
        "resources": {
            "stock": {
                "disk": {"total": 20000, "unit": "bytes"},  # 10000 per agent
            }
        },
        "logging": {
            "log_dir": "test_logs",
            "output_file": "test_logs/test.jsonl",
        },
        # Enable rate limiting for compute resources (Plan #102)
        "rate_limiting": {
            "enabled": True,
            "window_seconds": 60.0,
            "resources": {
                "llm_tokens": {"max_per_window": 1000},
            }
        },
    }


@pytest.fixture
def world_with_temp_log(minimal_config):
    """Create a World instance with a temporary log file."""
    with tempfile.TemporaryDirectory() as tmpdir:
        minimal_config["logging"]["log_dir"] = tmpdir
        minimal_config["logging"]["output_file"] = os.path.join(tmpdir, "test.jsonl")
        yield World(minimal_config)


class TestWorldInitialization:
    """Tests for World initialization."""

    def test_world_initialization(self, world_with_temp_log):
        """Create World with minimal config, verify it initializes."""
        world = world_with_temp_log

        # Basic initialization checks
        assert world.event_number == 0
        assert world.ledger is not None
        assert world.artifacts is not None
        assert world.logger is not None

        # Check principals were created
        assert "agent_1" in world.principal_ids
        assert "agent_2" in world.principal_ids

        # Check starting scrip was set
        assert world.ledger.get_scrip("agent_1") == 100
        assert world.ledger.get_scrip("agent_2") == 100


class TestEventCounter:
    """Tests for World event counter behavior.

    Note: Plan #102 changed advance_tick() to a simple event counter incrementer.
    It no longer has max_ticks limits or compute resets. Those are now handled
    by time-based rate limiting.
    """

    def test_increment_event_counter(self, world_with_temp_log):
        """increment_event_counter() works and increments event_number."""
        world = world_with_temp_log

        assert world.event_number == 0

        # Increment counter
        result = world.increment_event_counter()
        assert result == 1
        assert world.event_number == 1

        # Increment again
        result = world.increment_event_counter()
        assert result == 2
        assert world.event_number == 2

    def test_advance_tick_deprecated_compat(self, world_with_temp_log):
        """Deprecated advance_tick() still works for backward compatibility."""
        world = world_with_temp_log

        assert world.event_number == 0

        # Advance tick (deprecated but should work)
        result = world.advance_tick()
        assert result is True  # Always returns True now (no max_ticks)
        assert world.event_number == 1

        # Advance again - no limit
        for _ in range(10):
            result = world.advance_tick()
            assert result is True  # Always True

        assert world.event_number == 11  # No max_ticks limit


class TestExecuteNoop:
    """Tests for noop action execution."""

    def test_execute_noop(self, world_with_temp_log):
        """Execute a noop action successfully."""
        world = world_with_temp_log

        # Need to advance tick first to get compute
        world.advance_tick()

        intent = NoopIntent(principal_id="agent_1")
        result = world.execute_action(intent)

        assert result.success is True
        assert "Noop" in result.message


class TestExecuteReadArtifact:
    """Tests for read_artifact action execution."""

    def test_execute_read_artifact_not_found(self, world_with_temp_log):
        """Reading non-existent artifact fails."""
        world = world_with_temp_log
        world.advance_tick()

        intent = ReadArtifactIntent(
            principal_id="agent_1",
            artifact_id="nonexistent_artifact"
        )
        result = world.execute_action(intent)

        assert result.success is False
        assert "not found" in result.message


class TestExecuteWriteArtifact:
    """Tests for write_artifact action execution."""

    def test_execute_write_artifact(self, world_with_temp_log):
        """Write a new artifact successfully."""
        world = world_with_temp_log
        world.advance_tick()

        intent = WriteArtifactIntent(
            principal_id="agent_1",
            artifact_id="test_artifact",
            artifact_type="data",
            content="This is test content"
        )
        result = world.execute_action(intent)

        assert result.success is True
        assert "test_artifact" in result.message or result.data is not None

        # Verify artifact was created
        artifact = world.artifacts.get("test_artifact")
        assert artifact is not None
        assert artifact.content == "This is test content"
        assert artifact.created_by == "agent_1"

class TestFullTickCycle:
    """Tests for full tick cycle behavior."""

    def test_full_tick_cycle(self, world_with_temp_log):
        """Advance tick, execute actions, verify state."""
        world = world_with_temp_log

        # Initial state
        assert world.event_number == 0

        # First tick
        world.advance_tick()
        assert world.event_number == 1

        # Get initial compute (RateTracker capacity, not raw balance)
        initial_compute = world.ledger.get_resource_remaining("agent_1", "llm_tokens")
        assert initial_compute > 0

        # Execute noop action (actions are free - no compute cost)
        noop_intent = NoopIntent(principal_id="agent_1")
        result = world.execute_action(noop_intent)
        assert result.success is True

        # Compute should be unchanged (actions are free)
        compute_after_action = world.ledger.get_resource_remaining("agent_1", "llm_tokens")
        assert compute_after_action == initial_compute

        # Advance to next tick
        world.advance_tick()
        assert world.event_number == 2

        # Compute should still be the same after tick (RateTracker, no reset)
        compute_after_reset = world.ledger.get_resource_remaining("agent_1", "llm_tokens")
        assert compute_after_reset == initial_compute

        # Scrip should NOT change (it persists)
        assert world.ledger.get_scrip("agent_1") == 100

    def test_state_summary_after_actions(self, world_with_temp_log):
        """Verify get_state_summary returns correct state after actions."""
        world = world_with_temp_log
        world.advance_tick()

        # Write an artifact
        write_intent = WriteArtifactIntent(
            principal_id="agent_1",
            artifact_id="summary_test_artifact",
            artifact_type="data",
            content="Test content for summary"
        )
        world.execute_action(write_intent)

        # Get state summary
        state = world.get_state_summary()

        assert state["event_number"] == 1
        assert "agent_1" in state["balances"]
        assert "agent_2" in state["balances"]

        # Check our artifact appears in the list
        artifact_ids = [a["id"] for a in state["artifacts"]]
        assert "summary_test_artifact" in artifact_ids

        # Plan #254: Pre-seeded artifacts (kernel_mint_agent) replace genesis
        assert "kernel_mint_agent" in artifact_ids


class TestTransferKernelAction:
    """Tests for scrip transfer via kernel action (Plan #254)."""

    def test_transfer_scrip_via_kernel(self, world_with_temp_log):
        """Transfer scrip using transfer kernel action."""
        from src.world.actions import TransferIntent

        world = world_with_temp_log
        world.advance_tick()

        initial_agent1 = world.ledger.get_scrip("agent_1")
        initial_agent2 = world.ledger.get_scrip("agent_2")

        intent = TransferIntent(
            principal_id="agent_1",
            recipient_id="agent_2",
            amount=25,
        )
        result = world.execute_action(intent)

        assert result.success is True

        # Verify balances changed
        final_agent1 = world.ledger.get_scrip("agent_1")
        final_agent2 = world.ledger.get_scrip("agent_2")

        # Plan #254: transfer is a free kernel action (no method cost)
        assert final_agent1 == initial_agent1 - 25  # -25 transfer
        assert final_agent2 == initial_agent2 + 25

    def test_cannot_transfer_more_than_balance(self, world_with_temp_log):
        """Cannot transfer more scrip than you have."""
        from src.world.actions import TransferIntent

        world = world_with_temp_log
        world.advance_tick()

        intent = TransferIntent(
            principal_id="agent_1",
            recipient_id="agent_2",
            amount=500,  # More than the 100 starting scrip
        )
        result = world.execute_action(intent)

        # Should fail due to insufficient funds
        assert result.success is False
        assert "insufficient" in result.message.lower() or "balance" in result.message.lower()
