"""Unit tests for has_standing <-> ledger invariant (Plan #231).

Tests that:
- principal_ids is derived from ledger state
- create_principal() atomically sets has_standing + ResourceManager
- validate_principal_invariant() detects violations
"""

from pathlib import Path

import pytest

from src.world.world import World, ConfigDict
from src.world.artifacts import Artifact
from src.world.kernel_interface import KernelActions


@pytest.fixture
def world(tmp_path: Path) -> World:
    """Create a World with two agents."""
    config: ConfigDict = {
        "world": {},
        "costs": {"per_1k_input_tokens": 1, "per_1k_output_tokens": 3},
        "logging": {"output_file": str(tmp_path / "test.jsonl")},
        "principals": [
            {"id": "alice", "starting_scrip": 100},
            {"id": "bob", "starting_scrip": 100},
        ],
        "rights": {"default_llm_tokens_quota": 50, "default_disk_quota": 10000},
        "rate_limiting": {
            "enabled": True,
            "window_seconds": 60.0,
            "resources": {"llm_tokens": {"max_per_window": 1000}},
        },
    }
    return World(config)


@pytest.mark.plans(231)
class TestPrincipalIdsDerived:
    """Test that principal_ids is derived from ledger, not stored."""

    def test_principal_ids_derived_from_ledger(self, world: World) -> None:
        """principal_ids returns agents from ledger state."""
        pids = world.principal_ids
        assert "alice" in pids
        assert "bob" in pids

    def test_principal_ids_excludes_genesis(self, world: World) -> None:
        """Genesis artifacts are not in principal_ids."""
        pids = world.principal_ids
        for pid in pids:
            assert not pid.startswith("genesis_"), f"genesis artifact {pid} in principal_ids"

    def test_principal_ids_includes_spawned(self, world: World) -> None:
        """Spawned agents appear in principal_ids immediately."""
        # Directly create a ledger entry (simulating KernelActions.create_principal)
        world.ledger.create_principal("spawned_1", starting_scrip=0)
        pids = world.principal_ids
        assert "spawned_1" in pids


@pytest.mark.plans(231)
class TestCreatePrincipalAtomic:
    """Test that KernelActions.create_principal() is atomic."""

    def test_create_principal_sets_has_standing(self, world: World) -> None:
        """create_principal() sets has_standing on existing artifact."""
        # Create artifact first
        artifact = Artifact(
            id="new_agent",
            type="agent",
            content="",
            created_by="alice",
            created_at="2026-01-01T00:00:00Z",
            updated_at="2026-01-01T00:00:00Z",
            has_standing=False,
        )
        world.artifacts.artifacts["new_agent"] = artifact

        # Now create principal — should set has_standing
        ka = KernelActions(world)
        result = ka.create_principal("new_agent", starting_scrip=50)
        assert result is True
        assert artifact.has_standing is True

    def test_create_principal_creates_resource_manager_entry(self, world: World) -> None:
        """create_principal() creates ResourceManager entry."""
        ka = KernelActions(world)
        ka.create_principal("new_agent", starting_scrip=0)
        assert world.resource_manager.principal_exists("new_agent")

    def test_create_principal_idempotent(self, world: World) -> None:
        """Returns False for existing principal, no side effects."""
        original_scrip = world.ledger.get_scrip("alice")
        ka = KernelActions(world)
        result = ka.create_principal("alice", starting_scrip=999)
        assert result is False
        assert world.ledger.get_scrip("alice") == original_scrip


@pytest.mark.plans(231)
class TestValidateInvariant:
    """Test the validate_principal_invariant() method."""

    def test_validate_invariant_clean(self, world: World) -> None:
        """No violations in a clean world."""
        violations = world.validate_principal_invariant()
        assert violations == []

    def test_validate_invariant_detects_missing_standing(self, world: World) -> None:
        """Detects ledger entry without has_standing."""
        # Create an artifact with has_standing=False but a ledger entry
        artifact = Artifact(
            id="drift_agent",
            type="agent",
            content="",
            created_by="system",
            created_at="2026-01-01T00:00:00Z",
            updated_at="2026-01-01T00:00:00Z",
            has_standing=False,
        )
        world.artifacts.artifacts["drift_agent"] = artifact
        world.ledger.create_principal("drift_agent", starting_scrip=0)

        violations = world.validate_principal_invariant()
        assert len(violations) == 1
        assert "drift_agent" in violations[0]
        assert "has_standing=False" in violations[0]

    def test_validate_invariant_detects_missing_ledger(self, world: World) -> None:
        """Detects has_standing=True without ledger entry."""
        # Create artifact with standing but no ledger entry
        artifact = Artifact(
            id="orphan_agent",
            type="agent",
            content="",
            created_by="system",
            created_at="2026-01-01T00:00:00Z",
            updated_at="2026-01-01T00:00:00Z",
            has_standing=True,
        )
        world.artifacts.artifacts["orphan_agent"] = artifact
        # Don't create ledger entry

        violations = world.validate_principal_invariant()
        assert len(violations) == 1
        assert "orphan_agent" in violations[0]
        assert "not in ledger" in violations[0]
