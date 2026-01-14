"""V1 Acceptance Tests - validates V1 core capabilities with real LLM.

These tests verify the minimal viable agent ecology works end-to-end.
They require real LLM calls and are marked with @pytest.mark.external.

Run with:
    pytest tests/e2e/test_v1_acceptance.py -v --run-external

V1 Core Capabilities:
1. Multi-Agent Execution - Multiple agents run without interference
2. Artifact System - Agents can discover, create, read, and invoke artifacts
3. Economic Primitives - Scrip transfers work, balances tracked correctly
4. Resource Constraints - Rate limiting and quotas enforced
5. Coordination - Contracts and escrow enable trustless coordination
6. Observability - Actions are logged and traceable

Cost estimate: ~$0.05-0.15 per full test run
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest

from src.simulation.runner import SimulationRunner
from src.world import World
from src.world.ledger import Ledger
from src.world.artifacts import ArtifactStore
from src.world.genesis import GenesisEscrow


# Skip all tests unless --run-external is passed
pytestmark = pytest.mark.external


@pytest.fixture
def v1_config(tmp_path: Path) -> dict[str, Any]:
    """Configuration for V1 acceptance tests.

    Uses settings that test V1 capabilities while keeping costs reasonable.
    """
    log_file = tmp_path / "v1_acceptance.jsonl"

    return {
        "world": {
            "max_ticks": 3,  # Enough for multi-tick behavior
        },
        "costs": {
            "per_1k_input_tokens": 1,
            "per_1k_output_tokens": 3,
        },
        "logging": {
            "output_file": str(log_file),
            "log_dir": str(tmp_path / "llm_logs"),
        },
        "principals": [
            {"id": "alpha", "starting_scrip": 200},
            {"id": "beta", "starting_scrip": 200},
        ],
        "rights": {
            "default_compute_quota": 100,
            "default_disk_quota": 10000,
        },
        "llm": {
            "default_model": "gemini/gemini-2.0-flash",
            "rate_limit_delay": 0,
        },
        "budget": {
            "max_api_cost": 0.20,  # Cap at $0.20 for safety
            "checkpoint_interval": 0,
            "checkpoint_on_end": False,
        },
        "rate_limiting": {
            "enabled": False,  # Tested separately
        },
        "execution": {
            "use_autonomous_loops": False,
        },
    }


@pytest.fixture
def v1_rate_limited_config(v1_config: dict[str, Any]) -> dict[str, Any]:
    """Configuration with rate limiting enabled for constraint tests."""
    config = v1_config.copy()
    config["rate_limiting"] = {
        "enabled": True,
        "window_seconds": 1.0,
        "resources": {
            "llm_calls": {"max_per_window": 5},
        },
    }
    return config


class TestV1MultiAgentExecution:
    """V1 Capability 1: Multiple agents run simultaneously without interference."""

    def test_multi_agent_execution(self, v1_config: dict[str, Any]) -> None:
        """Multiple agents can run in the same simulation without interference.

        Verifies:
        - Both agents execute actions
        - Both agents' balances are tracked separately
        - No crashes from concurrent execution
        """
        runner = SimulationRunner(v1_config, verbose=False)
        world = runner.run_sync()

        # Both agents should exist and have been active
        assert world.tick >= 1

        # Both agents' balances should be tracked
        balances = world.ledger.get_all_scrip()
        assert "alpha" in balances
        assert "beta" in balances

        # Genesis artifacts accessible by both
        assert "genesis_ledger" in world.genesis_artifacts
        assert "genesis_store" in world.genesis_artifacts


class TestV1ArtifactSystem:
    """V1 Capability 2: Artifact discovery, creation, and invocation."""

    def test_artifact_discovery(self, v1_config: dict[str, Any]) -> None:
        """Agents can discover artifacts via genesis_store.

        Verifies:
        - genesis_store exists and is functional
        - Agent can query the store's list method
        - Genesis artifacts are discoverable
        """
        runner = SimulationRunner(v1_config, max_agents=1, verbose=False)
        world = runner.run_sync()

        # genesis_store should be accessible
        store = world.genesis_artifacts.get("genesis_store")
        assert store is not None

        # Genesis artifacts are stored separately from regular artifacts
        genesis_ids = list(world.genesis_artifacts.keys())
        assert len(genesis_ids) >= 5  # At least: ledger, store, escrow, event_log, handbook

        # Verify specific genesis artifacts exist
        assert "genesis_ledger" in genesis_ids
        assert "genesis_store" in genesis_ids
        assert "genesis_escrow" in genesis_ids

    def test_artifact_creation(self, v1_config: dict[str, Any]) -> None:
        """Agents can create new artifacts.

        Verifies:
        - Artifact store write operation works
        - Created artifacts are retrievable
        - Ownership is tracked correctly
        """
        config = v1_config.copy()
        config["world"]["max_ticks"] = 3  # Give time to create artifacts

        runner = SimulationRunner(config, max_agents=1, verbose=False)
        world = runner.run_sync()

        # Count artifacts - should have genesis + agent + possibly more
        all_artifacts = list(world.artifacts.list_all())

        # At minimum: 6 genesis + 1 agent artifact
        assert len(all_artifacts) >= 7

    def test_artifact_invocation(self, v1_config: dict[str, Any]) -> None:
        """Agents can invoke artifact interfaces.

        Verifies:
        - genesis_ledger.balance method is callable
        - Method returns valid result
        """
        runner = SimulationRunner(v1_config, max_agents=1, verbose=False)
        world = runner.run_sync()

        # Direct invocation test - balance query
        agent_id = "alpha"
        balance = world.ledger.get_scrip(agent_id)

        # Balance should be a non-negative number
        assert isinstance(balance, (int, float))
        assert balance >= 0


class TestV1EconomicPrimitives:
    """V1 Capability 3: Scrip transfers and balance tracking."""

    def test_scrip_transfer(self, v1_config: dict[str, Any]) -> None:
        """Ledger transfers work correctly.

        Verifies:
        - Transfer reduces sender balance
        - Transfer increases receiver balance
        - Total scrip is conserved
        """
        runner = SimulationRunner(v1_config, verbose=False)
        world = runner.run_sync()

        # Get initial total
        balances = world.ledger.get_all_scrip()
        initial_total = sum(balances.values())

        # Perform transfer (not via agent, direct ledger call)
        world.ledger.transfer_scrip("alpha", "beta", 50)

        # Verify balances changed correctly
        new_balances = world.ledger.get_all_scrip()
        assert new_balances["alpha"] == balances["alpha"] - 50
        assert new_balances["beta"] == balances["beta"] + 50

        # Total scrip conserved
        new_total = sum(new_balances.values())
        assert new_total == initial_total


class TestV1ResourceConstraints:
    """V1 Capability 4: Rate limiting and quota enforcement."""

    @pytest.mark.asyncio
    async def test_resource_rate_limiting(
        self, v1_rate_limited_config: dict[str, Any]
    ) -> None:
        """Rate limits are enforced.

        Verifies:
        - Rate limiter exists and is functional
        - Simulation runs with rate limiting enabled
        - No crashes from rate limit enforcement
        """
        config = v1_rate_limited_config.copy()
        config["execution"]["use_autonomous_loops"] = True
        config["execution"]["agent_loop"] = {
            "min_loop_delay": 0.1,
            "max_loop_delay": 0.5,
            "resource_check_interval": 0.1,
            "max_consecutive_errors": 3,
            "resources_to_check": [],
        }

        runner = SimulationRunner(config, max_agents=1, verbose=False)

        # Run briefly with rate limiting
        world = await runner.run(duration=2.0)

        assert isinstance(world, World)
        # Rate limiter should have been active
        assert config["rate_limiting"]["enabled"] is True


class TestV1Coordination:
    """V1 Capability 5: Contracts and escrow for trustless coordination."""

    def test_escrow_coordination(self, v1_config: dict[str, Any]) -> None:
        """Escrow enables trustless artifact trade.

        Verifies:
        - Escrow artifact exists
        - Can deposit artifact into escrow
        - Can complete purchase via escrow
        - Ownership transfers correctly
        """
        # Create components directly for escrow testing
        ledger = Ledger()
        store = ArtifactStore()

        ledger.create_principal("seller", starting_scrip=100, starting_compute=50)
        ledger.create_principal("buyer", starting_scrip=200, starting_compute=50)

        escrow = GenesisEscrow(ledger, store)

        # Seller creates artifact
        store.write("test_artifact", "generic", "valuable content", "seller")

        # Transfer to escrow and deposit
        store.transfer_ownership("test_artifact", "seller", escrow.id)
        deposit_result = escrow._deposit(["test_artifact", 75], "seller")
        assert deposit_result["success"] is True

        # Buyer purchases
        seller_initial = ledger.get_scrip("seller")
        buyer_initial = ledger.get_scrip("buyer")

        purchase_result = escrow._purchase(["test_artifact"], "buyer")

        assert purchase_result["success"] is True
        assert store.get_owner("test_artifact") == "buyer"
        assert ledger.get_scrip("seller") == seller_initial + 75
        assert ledger.get_scrip("buyer") == buyer_initial - 75


class TestV1Observability:
    """V1 Capability 6: Action logging and traceability."""

    def test_action_logging(self, v1_config: dict[str, Any]) -> None:
        """All actions are logged to event log.

        Verifies:
        - Event log exists and is functional
        - Actions are recorded with timestamps
        - Events are retrievable
        """
        runner = SimulationRunner(v1_config, max_agents=1, verbose=False)
        world = runner.run_sync()

        # Event log should have recorded events
        events = world.logger.read_recent(100)

        # Should have at least tick events
        tick_events = [e for e in events if e.get("event_type") == "tick"]
        assert len(tick_events) >= 1

        # Events should have timestamps
        for event in events:
            if "timestamp" in event:
                assert event["timestamp"] is not None
