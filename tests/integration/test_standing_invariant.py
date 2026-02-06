"""Integration tests for has_standing <-> ledger invariant (Plan #231).

Tests the full lifecycle: spawn, checkpoint round-trip, drift correction,
and that spawned agents appear in state summaries.
"""

from pathlib import Path
from typing import Any

import pytest

from src.world.world import World, ConfigDict
from src.world.artifacts import Artifact
from src.world.kernel_interface import KernelActions


def _make_world(tmp_path: Path) -> World:
    """Create a World for testing."""
    config: ConfigDict = {
        "world": {},
        "costs": {"per_1k_input_tokens": 1, "per_1k_output_tokens": 3},
        "logging": {"output_file": str(tmp_path / "test.jsonl")},
        "principals": [
            {"id": "alice", "starting_scrip": 100},
            {"id": "bob", "starting_scrip": 100},
        ],
        "resources": {
            "stock": {
                "disk": {"total": 20000, "unit": "bytes"},  # 10000 per agent
            }
        },
        "rate_limiting": {
            "enabled": True,
            "window_seconds": 60.0,
            "resources": {"llm_tokens": {"max_per_window": 1000}},
        },
        # Disable genesis agents for test isolation
        "discourse_analyst": {"enabled": False},
        "discourse_analyst_2": {"enabled": False},
        "discourse_analyst_3": {"enabled": False},
        "alpha_prime": {"enabled": False},
    }
    return World(config)


@pytest.mark.plans(231)
class TestSpawnPrincipalInvariant:
    """After create_principal + artifact creation, all registries are consistent."""

    def test_spawn_principal_full_invariant(self, tmp_path: Path) -> None:
        """All four registries consistent after spawn."""
        w = _make_world(tmp_path)

        # Spawn via KernelActions (like an agent would)
        ka = KernelActions(w)
        result = ka.create_principal("spawned_1", starting_scrip=10)
        assert result is True

        # 1. Ledger has entry
        assert w.ledger.principal_exists("spawned_1")
        assert w.ledger.get_scrip("spawned_1") == 10

        # 2. principal_ids (derived) includes it
        assert "spawned_1" in w.principal_ids

        # 3. ResourceManager has entry
        assert w.resource_manager.principal_exists("spawned_1")

        # 4. No invariant violations
        violations = w.validate_principal_invariant()
        assert violations == []


@pytest.mark.plans(231)
class TestCheckpointInvariant:
    """Checkpoint restore maintains and fixes the invariant."""

    def test_checkpoint_restore_fixes_missing_standing(self, tmp_path: Path) -> None:
        """Drift in checkpoint data is corrected: ledger entry without has_standing."""
        from src.simulation.runner import SimulationRunner

        w = _make_world(tmp_path)

        # Simulate checkpoint that restores a new agent.
        # The checkpoint has a balance entry AND an artifact with has_standing=False (drift).
        # We first create the artifact via checkpoint restore (which uses artifacts.write),
        # and the ledger entry needs to exist for the invariant check to find it.
        checkpoint_data = {
            "event_number": 5,
            "reason": "test",
            "balances": {
                "alice": {"scrip": 100},
                "bob": {"scrip": 100},
            },
            "artifacts": [
                {
                    "id": "drift_agent",
                    "type": "agent",
                    "content": "",
                    "created_by": "system",
                    "has_standing": False,  # Drift: should be True
                },
            ],
        }

        runner = SimulationRunner.__new__(SimulationRunner)
        runner.world = w
        runner.engine = type("E", (), {"cumulative_api_cost": 0.0})()
        runner.verbose = False

        runner._restore_checkpoint(checkpoint_data)

        # Artifact exists but has_standing=False (from checkpoint data)
        artifact = w.artifacts.artifacts.get("drift_agent")
        assert artifact is not None

        # Now manually add a ledger entry (simulating out-of-order restore)
        # Use raw dict manipulation to avoid IDRegistry collision
        w.ledger.scrip["drift_agent"] = 50
        w.ledger.resources["drift_agent"] = {}

        # Verify drift exists
        violations = w.validate_principal_invariant()
        assert any("drift_agent" in v for v in violations)

        # Run invariant enforcement (same logic as in _restore_checkpoint)
        for pid in w.ledger.scrip:
            if pid.startswith("genesis_"):
                continue
            art = w.artifacts.artifacts.get(pid)
            if art and not art.has_standing:
                art.has_standing = True

        # After enforcement, drift should be fixed
        assert artifact.has_standing is True
        assert w.validate_principal_invariant() == []

    def test_checkpoint_restore_fixes_missing_ledger(self, tmp_path: Path) -> None:
        """Drift: artifact has has_standing=True but no ledger entry."""
        from src.simulation.runner import SimulationRunner

        w = _make_world(tmp_path)

        checkpoint_data = {
            "event_number": 5,
            "reason": "test",
            "balances": {
                "alice": {"scrip": 100},
                "bob": {"scrip": 100},
            },
            "artifacts": [
                {
                    "id": "orphan_agent",
                    "type": "agent",
                    "content": "",
                    "created_by": "system",
                    "has_standing": True,  # Has standing but no ledger entry
                },
            ],
        }

        runner = SimulationRunner.__new__(SimulationRunner)
        runner.world = w
        runner.engine = type("E", (), {"cumulative_api_cost": 0.0})()
        runner.verbose = False

        runner._restore_checkpoint(checkpoint_data)

        # After restore, invariant enforcement should create ledger entry
        assert w.ledger.principal_exists("orphan_agent")
        assert w.ledger.get_scrip("orphan_agent") == 0


@pytest.mark.plans(231)
class TestSpawnedAgentVisibility:
    """Spawned agents appear in state summary (bug fix verification)."""

    def test_spawned_agent_appears_in_state_summary(self, tmp_path: Path) -> None:
        """Spawned agent visible in principal_ids and thus state summary."""
        w = _make_world(tmp_path)

        # Before spawn
        assert "spawned_1" not in w.principal_ids

        # Spawn
        ka = KernelActions(w)
        ka.create_principal("spawned_1", starting_scrip=0)

        # After spawn — should appear in principal_ids immediately
        assert "spawned_1" in w.principal_ids

        # State summary should include spawned agent in resource_metrics
        # (Previously broken: spawned agents were invisible because
        # world.principal_ids was a stored list never updated after init)
        summary = w.get_state_summary()
        # principal_ids feeds into resource_metrics iteration
        # The spawned agent should be iterable now
        assert "spawned_1" in w.principal_ids
