"""Integration tests for Vulture Observability - Plan #26

These tests verify the freeze/unfreeze events and asset inventory
API work correctly in an integrated simulation context.
"""

import json
import tempfile
import os
from pathlib import Path

import pytest

from src.world import World
from src.world.actions import WriteArtifactIntent


@pytest.fixture
def vulture_config():
    """Configuration for vulture observability tests."""
    return {
        "world": {},
        "principals": [
            {"id": "alice", "starting_scrip": 100},
            {"id": "bob", "starting_scrip": 200},
            {"id": "vulture", "starting_scrip": 500},
        ],
        "costs": {
            "per_1k_input_tokens": 1,
            "per_1k_output_tokens": 3,
        },
        "rights": {
            "default_quotas": {"compute": 100.0, "disk": 10000.0}
        },
        "logging": {
            "log_dir": "test_logs",
            "output_file": "test_logs/test.jsonl",
        },
        "rate_limiting": {
            "enabled": True,
            "window_seconds": 60.0,
            "resources": {"llm_tokens": {"max_per_window": 1000}}
        },
    }


@pytest.fixture
def world_with_temp_log(vulture_config):
    """Create a World instance with a temporary log file."""
    with tempfile.TemporaryDirectory() as tmpdir:
        vulture_config["logging"]["log_dir"] = tmpdir
        vulture_config["logging"]["output_file"] = os.path.join(tmpdir, "run.jsonl")
        world = World(vulture_config)
        yield world, Path(vulture_config["logging"]["output_file"])


class TestFreezeEventInLog:
    """Test that freeze events appear in the event log."""

    def test_freeze_event_in_log(self, world_with_temp_log) -> None:
        """Freeze events should be written to run.jsonl."""
        world, log_path = world_with_temp_log

        # Initialize resources
        world.advance_tick()

        # Create some artifacts for alice
        world.artifacts.write("alice_art_1", "generic", "content1", "alice")
        world.artifacts.write("alice_art_2", "generic", "content2", "alice")

        # Freeze alice by exhausting compute
        world.ledger.set_resource("alice", "llm_tokens", 0.0)

        # Emit freeze event
        world.emit_agent_frozen("alice", reason="compute_exhausted")

        # Read the log file
        events = []
        with open(log_path) as f:
            for line in f:
                events.append(json.loads(line))

        # Find the freeze event
        freeze_events = [e for e in events if e.get("event_type") == "agent_frozen"]
        assert len(freeze_events) == 1

        event = freeze_events[0]
        assert event["agent_id"] == "alice"
        assert event["reason"] == "compute_exhausted"
        assert event["compute_remaining"] == 0.0
        assert set(event["owned_artifacts"]) == {"alice_art_1", "alice_art_2"}

    def test_unfreeze_event_in_log(self, world_with_temp_log) -> None:
        """Unfreeze events should be written to run.jsonl with rescuer info."""
        world, log_path = world_with_temp_log

        # Initialize resources
        world.advance_tick()

        # Freeze alice
        world.ledger.set_resource("alice", "llm_tokens", 0.0)
        world.emit_agent_frozen("alice", reason="compute_exhausted")

        # Vulture rescues alice
        world.emit_agent_unfrozen(
            "alice",
            unfrozen_by="vulture",
            resources_transferred={"compute": 50.0, "scrip": 10}
        )

        # Read the log file
        events = []
        with open(log_path) as f:
            for line in f:
                events.append(json.loads(line))

        # Find the unfreeze event
        unfreeze_events = [e for e in events if e.get("event_type") == "agent_unfrozen"]
        assert len(unfreeze_events) == 1

        event = unfreeze_events[0]
        assert event["agent_id"] == "alice"
        assert event["unfrozen_by"] == "vulture"
        assert event["resources_transferred"]["compute"] == 50.0
        assert event["resources_transferred"]["scrip"] == 10


class TestArtifactsByOwnerAPI:
    """Test querying artifacts by owner via World API."""

    def test_artifacts_by_owner_api(self, world_with_temp_log) -> None:
        """World provides method to get artifacts owned by agent."""
        world, _ = world_with_temp_log

        # Create artifacts for different owners
        world.artifacts.write("a1", "generic", "content", "alice")
        world.artifacts.write("a2", "generic", "content", "alice")
        world.artifacts.write("b1", "generic", "content", "bob")
        world.artifacts.write("v1", "generic", "content", "vulture")

        # Query via world's artifact store
        alice_arts = world.artifacts.get_artifacts_by_owner("alice")
        bob_arts = world.artifacts.get_artifacts_by_owner("bob")
        vulture_arts = world.artifacts.get_artifacts_by_owner("vulture")
        unknown_arts = world.artifacts.get_artifacts_by_owner("unknown")

        assert set(alice_arts) == {"a1", "a2"}
        assert set(bob_arts) == {"b1"}
        assert set(vulture_arts) == {"v1"}
        assert unknown_arts == []


class TestPublicLedgerAccess:
    """Test that ledger balances are publicly accessible."""

    def test_public_ledger_access(self, world_with_temp_log) -> None:
        """Any principal can query other principals' balances."""
        world, _ = world_with_temp_log

        # Get balances - no access control needed
        alice_scrip = world.ledger.get_scrip("alice")
        bob_scrip = world.ledger.get_scrip("bob")
        vulture_scrip = world.ledger.get_scrip("vulture")

        assert alice_scrip == 100
        assert bob_scrip == 200
        assert vulture_scrip == 500

    def test_genesis_ledger_accessible(self, world_with_temp_log) -> None:
        """Genesis ledger artifact is accessible to agents."""
        world, _ = world_with_temp_log

        # Genesis ledger should exist
        genesis_ledger = world.genesis_artifacts.get("genesis_ledger")
        assert genesis_ledger is not None

        # Should be able to query balance (no auth required for reads)
        # The genesis_ledger provides read access to all principals


class TestFrozenAgentList:
    """Test listing frozen agents for vulture discovery."""

    def test_get_frozen_agents_integration(self, world_with_temp_log) -> None:
        """Can get list of all frozen agents in simulation."""
        world, _ = world_with_temp_log

        # Initialize event counter
        world.increment_event_counter()

        # Initially no one is frozen (rate limiter has capacity)
        frozen = world.get_frozen_agents()
        assert frozen == []

        # Freeze alice by exhausting all rate-limited tokens
        # consume_resource uses rate tracker when enabled
        world.ledger.consume_resource("alice", "llm_tokens", 1000)

        frozen = world.get_frozen_agents()
        assert frozen == ["alice"]

        # Freeze bob too
        world.ledger.consume_resource("bob", "llm_tokens", 1000)

        frozen = world.get_frozen_agents()
        assert set(frozen) == {"alice", "bob"}

        # Vulture still has resources
        assert world.is_agent_frozen("vulture") is False
