"""Integration tests for the Agent Ecology World simulation.

These tests verify the core world mechanics without any LLM calls.
They directly test the World class by crafting ActionIntent objects
and calling execute_action.
"""

import sys
import tempfile
import os
from pathlib import Path

import pytest

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from world import World
from world.actions import (
    NoopIntent,
    ReadArtifactIntent,
    WriteArtifactIntent,
    InvokeArtifactIntent,
)


@pytest.fixture
def minimal_config():
    """Minimal configuration for testing."""
    return {
        "world": {"max_ticks": 5},
        "principals": [
            {"id": "agent_1", "starting_scrip": 100},
            {"id": "agent_2", "starting_scrip": 100},
        ],
        "costs": {
            "per_1k_input_tokens": 1,
            "per_1k_output_tokens": 3,
        },
        "rights": {
            "default_compute_quota": 50,
            "default_disk_quota": 10000,
        },
        "logging": {
            "log_dir": "test_logs",
            "output_file": "test_logs/test.jsonl",
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
        assert world.tick == 0
        assert world.max_ticks == 5
        assert world.ledger is not None
        assert world.artifacts is not None
        assert world.logger is not None

        # Check principals were created
        assert "agent_1" in world.principal_ids
        assert "agent_2" in world.principal_ids

        # Check starting scrip was set
        assert world.ledger.get_scrip("agent_1") == 100
        assert world.ledger.get_scrip("agent_2") == 100


class TestGenesisArtifacts:
    """Tests for genesis artifacts existence and basic functionality."""

    def test_genesis_artifacts_exist(self, world_with_temp_log):
        """Verify genesis_ledger, genesis_oracle etc. exist after init."""
        world = world_with_temp_log

        # Check genesis artifacts exist
        assert "genesis_ledger" in world.genesis_artifacts
        assert "genesis_oracle" in world.genesis_artifacts
        assert "genesis_event_log" in world.genesis_artifacts
        assert "genesis_rights_registry" in world.genesis_artifacts

        # Verify they are proper genesis artifacts with methods
        genesis_ledger = world.genesis_artifacts["genesis_ledger"]
        assert genesis_ledger.id == "genesis_ledger"
        assert genesis_ledger.owner_id == "system"

        # Check genesis_ledger has expected methods
        methods = [m["name"] for m in genesis_ledger.list_methods()]
        assert "balance" in methods
        assert "all_balances" in methods
        assert "transfer" in methods


class TestAdvanceTick:
    """Tests for World.advance_tick() behavior."""

    def test_advance_tick(self, world_with_temp_log):
        """World.advance_tick() works and increments tick."""
        world = world_with_temp_log

        assert world.tick == 0

        # Advance tick
        result = world.advance_tick()
        assert result is True
        assert world.tick == 1

        # Advance again
        result = world.advance_tick()
        assert result is True
        assert world.tick == 2

    def test_advance_tick_respects_max(self, world_with_temp_log):
        """advance_tick() returns False when max_ticks reached."""
        world = world_with_temp_log

        # Advance to max
        for _ in range(5):
            result = world.advance_tick()
            assert result is True

        assert world.tick == 5

        # Next advance should return False
        result = world.advance_tick()
        assert result is False
        assert world.tick == 5  # Tick should not increment beyond max

    def test_advance_tick_resets_compute(self, world_with_temp_log):
        """advance_tick() resets compute for all principals."""
        world = world_with_temp_log

        # Advance tick to initialize compute
        world.advance_tick()

        # Spend some compute
        initial_compute = world.ledger.get_compute("agent_1")
        assert initial_compute > 0
        world.ledger.spend_compute("agent_1", 10)
        assert world.ledger.get_compute("agent_1") == initial_compute - 10

        # Advance tick should reset compute
        world.advance_tick()
        assert world.ledger.get_compute("agent_1") == initial_compute


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

    def test_execute_read_artifact_genesis(self, world_with_temp_log):
        """Read a genesis artifact successfully."""
        world = world_with_temp_log

        # Need to advance tick first to get compute
        world.advance_tick()

        intent = ReadArtifactIntent(
            principal_id="agent_1",
            artifact_id="genesis_ledger"
        )
        result = world.execute_action(intent)

        assert result.success is True
        assert "genesis_ledger" in result.message
        assert result.data is not None
        assert "artifact" in result.data

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
        assert artifact.owner_id == "agent_1"

    def test_execute_write_artifact_cannot_modify_genesis(self, world_with_temp_log):
        """Cannot write to genesis artifacts."""
        world = world_with_temp_log
        world.advance_tick()

        intent = WriteArtifactIntent(
            principal_id="agent_1",
            artifact_id="genesis_ledger",
            artifact_type="data",
            content="Trying to overwrite genesis"
        )
        result = world.execute_action(intent)

        assert result.success is False
        assert "system artifact" in result.message or "Cannot modify" in result.message


class TestExecuteInvokeArtifact:
    """Tests for invoke_artifact action execution."""

    def test_execute_invoke_ledger_balance(self, world_with_temp_log):
        """Invoke genesis_ledger.balance method successfully."""
        world = world_with_temp_log
        world.advance_tick()

        intent = InvokeArtifactIntent(
            principal_id="agent_1",
            artifact_id="genesis_ledger",
            method="balance",
            args=["agent_1"]
        )
        result = world.execute_action(intent)

        assert result.success is True
        assert result.data is not None
        assert result.data.get("success") is True
        assert result.data.get("agent_id") == "agent_1"
        assert result.data.get("scrip") == 100

    def test_execute_invoke_ledger_all_balances(self, world_with_temp_log):
        """Invoke genesis_ledger.all_balances method."""
        world = world_with_temp_log
        world.advance_tick()

        intent = InvokeArtifactIntent(
            principal_id="agent_1",
            artifact_id="genesis_ledger",
            method="all_balances",
            args=[]
        )
        result = world.execute_action(intent)

        assert result.success is True
        assert result.data is not None
        balances = result.data.get("balances", {})
        assert "agent_1" in balances
        assert "agent_2" in balances

    def test_execute_invoke_method_not_found(self, world_with_temp_log):
        """Invoking non-existent method fails."""
        world = world_with_temp_log
        world.advance_tick()

        intent = InvokeArtifactIntent(
            principal_id="agent_1",
            artifact_id="genesis_ledger",
            method="nonexistent_method",
            args=[]
        )
        result = world.execute_action(intent)

        assert result.success is False
        assert "not found" in result.message


class TestFullTickCycle:
    """Tests for full tick cycle behavior."""

    def test_full_tick_cycle(self, world_with_temp_log):
        """Advance tick, execute actions, verify state."""
        world = world_with_temp_log

        # Initial state
        assert world.tick == 0

        # First tick
        world.advance_tick()
        assert world.tick == 1

        # Get initial compute
        initial_compute = world.ledger.get_compute("agent_1")
        assert initial_compute > 0

        # Execute noop action (actions are free - no compute cost)
        noop_intent = NoopIntent(principal_id="agent_1")
        result = world.execute_action(noop_intent)
        assert result.success is True

        # Compute should be unchanged (actions are free)
        compute_after_action = world.ledger.get_compute("agent_1")
        assert compute_after_action == initial_compute

        # Advance to next tick
        world.advance_tick()
        assert world.tick == 2

        # Compute should still be the same after reset
        compute_after_reset = world.ledger.get_compute("agent_1")
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

        assert state["tick"] == 1
        assert "agent_1" in state["balances"]
        assert "agent_2" in state["balances"]

        # Check our artifact appears in the list
        artifact_ids = [a["id"] for a in state["artifacts"]]
        assert "summary_test_artifact" in artifact_ids

        # Genesis artifacts should also be in the list
        assert "genesis_ledger" in artifact_ids
        assert "genesis_oracle" in artifact_ids


class TestComputeAndScripSeparation:
    """Tests to verify compute (flow) and scrip (stock) are separate resources."""

    def test_compute_is_separate_from_scrip(self, world_with_temp_log):
        """Verify compute and scrip are tracked separately."""
        world = world_with_temp_log
        world.advance_tick()

        # Get initial values
        initial_scrip = world.ledger.get_scrip("agent_1")
        initial_compute = world.ledger.get_compute("agent_1")

        # Execute action - actions are free, but compute can be spent explicitly
        world.ledger.spend_compute("agent_1", 5)

        # Compute should decrease, scrip should stay same
        assert world.ledger.get_compute("agent_1") < initial_compute
        assert world.ledger.get_scrip("agent_1") == initial_scrip

    def test_compute_and_scrip_are_independent(self, world_with_temp_log):
        """Spending compute doesn't affect scrip and vice versa."""
        world = world_with_temp_log
        world.advance_tick()

        initial_scrip = world.ledger.get_scrip("agent_1")
        initial_compute = world.ledger.get_compute("agent_1")

        # Spend some compute
        world.ledger.spend_compute("agent_1", 10)

        # Transfer some scrip
        world.ledger.transfer_scrip("agent_1", "agent_2", 20)

        # Verify they changed independently
        assert world.ledger.get_compute("agent_1") == initial_compute - 10
        assert world.ledger.get_scrip("agent_1") == initial_scrip - 20


class TestTransferVieLedger:
    """Tests for scrip transfer via genesis_ledger."""

    def test_transfer_scrip_via_ledger(self, world_with_temp_log):
        """Transfer scrip using genesis_ledger.transfer method."""
        world = world_with_temp_log
        world.advance_tick()

        initial_agent1 = world.ledger.get_scrip("agent_1")
        initial_agent2 = world.ledger.get_scrip("agent_2")

        intent = InvokeArtifactIntent(
            principal_id="agent_1",
            artifact_id="genesis_ledger",
            method="transfer",
            args=["agent_1", "agent_2", 25]
        )
        result = world.execute_action(intent)

        assert result.success is True
        assert result.data is not None
        assert result.data.get("success") is True
        assert result.data.get("transferred") == 25

        # Verify balances changed
        # Transfer method costs COMPUTE (not scrip), so no scrip fee
        final_agent1 = world.ledger.get_scrip("agent_1")
        final_agent2 = world.ledger.get_scrip("agent_2")

        # agent_1: started with 100, transferred 25 = 75
        # agent_2: started with 100, received 25 = 125
        assert final_agent1 == initial_agent1 - 25  # -25 transfer, no scrip fee
        assert final_agent2 == initial_agent2 + 25

    def test_cannot_transfer_from_other_agent(self, world_with_temp_log):
        """Cannot transfer scrip from another agent's account."""
        world = world_with_temp_log
        world.advance_tick()

        intent = InvokeArtifactIntent(
            principal_id="agent_1",
            artifact_id="genesis_ledger",
            method="transfer",
            args=["agent_2", "agent_1", 25]  # Trying to transfer FROM agent_2
        )
        result = world.execute_action(intent)

        # The method call should fail due to security check
        # When genesis method returns error, it's wrapped in ActionResult
        assert result.success is False
        assert "Cannot transfer from" in result.message
