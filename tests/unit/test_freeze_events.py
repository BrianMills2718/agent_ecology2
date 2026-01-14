"""Unit tests for agent freeze/unfreeze events - Plan #26"""

import pytest
import tempfile
from pathlib import Path

from src.world.world import World
from src.world.artifacts import ArtifactStore


class TestAgentFrozenEvent:
    """Test that AGENT_FROZEN events are emitted correctly."""

    def test_agent_frozen_event_emitted_on_compute_exhaustion(self) -> None:
        """Agent frozen event emitted when compute exhausted."""
        with tempfile.NamedTemporaryFile(suffix=".jsonl", delete=False) as f:
            output_file = f.name

        config = {
            "world": {"max_ticks": 10},
            "costs": {"per_1k_input_tokens": 1, "per_1k_output_tokens": 1},
            "logging": {"output_file": output_file},
            "principals": [
                {"id": "alice", "starting_scrip": 100},
            ],
            "rights": {
                "default_quotas": {"compute": 10.0, "disk": 10000.0}  # Very low compute
            },
        }
        world = World(config)

        # Exhaust alice's compute
        world.ledger.set_resource("alice", "llm_tokens", 0.0)

        # Emit freeze event
        world.emit_agent_frozen("alice", reason="compute_exhausted")

        # Check event was logged
        events = world.logger.read_recent(10)
        frozen_events = [e for e in events if e.get("event_type") == "agent_frozen"]
        assert len(frozen_events) == 1
        event = frozen_events[0]
        assert event["agent_id"] == "alice"
        assert event["reason"] == "compute_exhausted"
        assert "scrip_balance" in event
        assert "compute_remaining" in event
        assert "owned_artifacts" in event

    def test_frozen_event_includes_owned_artifacts(self) -> None:
        """Frozen event includes list of artifacts owned by agent."""
        with tempfile.NamedTemporaryFile(suffix=".jsonl", delete=False) as f:
            output_file = f.name

        config = {
            "world": {"max_ticks": 10},
            "costs": {"per_1k_input_tokens": 1, "per_1k_output_tokens": 1},
            "logging": {"output_file": output_file},
            "principals": [
                {"id": "alice", "starting_scrip": 100},
            ],
            "rights": {
                "default_quotas": {"compute": 10.0, "disk": 10000.0}
            },
        }
        world = World(config)

        # Create artifacts owned by alice
        world.artifacts.write("art_1", "generic", "content1", "alice")
        world.artifacts.write("art_2", "generic", "content2", "alice")
        world.artifacts.write("art_3", "generic", "content3", "bob")  # Not owned by alice

        # Emit freeze event
        world.emit_agent_frozen("alice", reason="compute_exhausted")

        events = world.logger.read_recent(10)
        frozen_events = [e for e in events if e.get("event_type") == "agent_frozen"]
        assert len(frozen_events) == 1
        owned = frozen_events[0]["owned_artifacts"]
        assert "art_1" in owned
        assert "art_2" in owned
        assert "art_3" not in owned


class TestAgentUnfrozenEvent:
    """Test that AGENT_UNFROZEN events are emitted correctly."""

    def test_agent_unfrozen_event_emitted(self) -> None:
        """Agent unfrozen event emitted when resources restored."""
        with tempfile.NamedTemporaryFile(suffix=".jsonl", delete=False) as f:
            output_file = f.name

        config = {
            "world": {"max_ticks": 10},
            "costs": {"per_1k_input_tokens": 1, "per_1k_output_tokens": 1},
            "logging": {"output_file": output_file},
            "principals": [
                {"id": "alice", "starting_scrip": 100},
            ],
            "rights": {
                "default_quotas": {"compute": 100.0, "disk": 10000.0}
            },
        }
        world = World(config)

        # Emit unfreeze event
        world.emit_agent_unfrozen(
            "alice",
            unfrozen_by="self",
            resources_transferred={"compute": 100.0, "scrip": 0}
        )

        events = world.logger.read_recent(10)
        unfrozen_events = [e for e in events if e.get("event_type") == "agent_unfrozen"]
        assert len(unfrozen_events) == 1
        event = unfrozen_events[0]
        assert event["agent_id"] == "alice"
        assert event["unfrozen_by"] == "self"
        assert event["resources_transferred"]["compute"] == 100.0

    def test_unfrozen_event_includes_rescuer_id(self) -> None:
        """Unfrozen event includes ID of agent who transferred resources."""
        with tempfile.NamedTemporaryFile(suffix=".jsonl", delete=False) as f:
            output_file = f.name

        config = {
            "world": {"max_ticks": 10},
            "costs": {"per_1k_input_tokens": 1, "per_1k_output_tokens": 1},
            "logging": {"output_file": output_file},
            "principals": [
                {"id": "alice", "starting_scrip": 100},
                {"id": "bob", "starting_scrip": 100},
            ],
            "rights": {
                "default_quotas": {"compute": 100.0, "disk": 10000.0}
            },
        }
        world = World(config)

        # Bob rescues alice
        world.emit_agent_unfrozen(
            "alice",
            unfrozen_by="bob",
            resources_transferred={"compute": 50.0, "scrip": 10}
        )

        events = world.logger.read_recent(10)
        unfrozen_events = [e for e in events if e.get("event_type") == "agent_unfrozen"]
        assert len(unfrozen_events) == 1
        assert unfrozen_events[0]["unfrozen_by"] == "bob"


class TestArtifactsByOwner:
    """Test querying artifacts by owner."""

    def test_get_artifacts_by_owner(self) -> None:
        """Can get list of artifact IDs owned by a principal."""
        store = ArtifactStore()

        store.write("art_1", "generic", "content1", "alice")
        store.write("art_2", "generic", "content2", "alice")
        store.write("art_3", "generic", "content3", "bob")

        alice_artifacts = store.get_artifacts_by_owner("alice")
        assert set(alice_artifacts) == {"art_1", "art_2"}

        bob_artifacts = store.get_artifacts_by_owner("bob")
        assert set(bob_artifacts) == {"art_3"}

        charlie_artifacts = store.get_artifacts_by_owner("charlie")
        assert charlie_artifacts == []

    def test_get_artifacts_by_owner_excludes_deleted(self) -> None:
        """Deleted artifacts are excluded from owner query by default."""
        store = ArtifactStore()

        store.write("art_1", "generic", "content1", "alice")
        store.write("art_2", "generic", "content2", "alice")

        # Delete one
        artifact = store.get("art_1")
        assert artifact is not None
        artifact.deleted = True

        alice_artifacts = store.get_artifacts_by_owner("alice")
        assert alice_artifacts == ["art_2"]

    def test_get_artifacts_by_owner_includes_deleted_with_flag(self) -> None:
        """Can include deleted artifacts in owner query."""
        store = ArtifactStore()

        store.write("art_1", "generic", "content1", "alice")
        store.write("art_2", "generic", "content2", "alice")

        # Delete one
        artifact = store.get("art_1")
        assert artifact is not None
        artifact.deleted = True

        alice_artifacts = store.get_artifacts_by_owner("alice", include_deleted=True)
        assert set(alice_artifacts) == {"art_1", "art_2"}


class TestFreezeStateTracking:
    """Test tracking agent frozen state."""

    def test_is_agent_frozen(self) -> None:
        """Can check if an agent is frozen (compute exhausted)."""
        with tempfile.NamedTemporaryFile(suffix=".jsonl", delete=False) as f:
            output_file = f.name

        config = {
            "world": {"max_ticks": 10},
            "costs": {"per_1k_input_tokens": 1, "per_1k_output_tokens": 1},
            "logging": {"output_file": output_file},
            "principals": [
                {"id": "alice", "starting_scrip": 100},
            ],
            "rights": {
                "default_quotas": {"compute": 100.0, "disk": 10000.0}
            },
        }
        world = World(config)

        # Initialize resources by starting first tick
        world.advance_tick()

        # Initially not frozen (has compute quota)
        assert world.is_agent_frozen("alice") is False

        # Exhaust compute
        world.ledger.set_resource("alice", "llm_tokens", 0.0)

        # Now frozen
        assert world.is_agent_frozen("alice") is True

    def test_get_frozen_agents(self) -> None:
        """Can get list of all frozen agents."""
        with tempfile.NamedTemporaryFile(suffix=".jsonl", delete=False) as f:
            output_file = f.name

        config = {
            "world": {"max_ticks": 10},
            "costs": {"per_1k_input_tokens": 1, "per_1k_output_tokens": 1},
            "logging": {"output_file": output_file},
            "principals": [
                {"id": "alice", "starting_scrip": 100},
                {"id": "bob", "starting_scrip": 100},
                {"id": "charlie", "starting_scrip": 100},
            ],
            "rights": {
                "default_quotas": {"compute": 100.0, "disk": 10000.0}
            },
        }
        world = World(config)

        # Initialize resources by starting first tick
        world.advance_tick()

        # Freeze alice and charlie (bob keeps compute)
        world.ledger.set_resource("alice", "llm_tokens", 0.0)
        world.ledger.set_resource("charlie", "llm_tokens", 0.0)

        frozen = world.get_frozen_agents()
        assert set(frozen) == {"alice", "charlie"}
