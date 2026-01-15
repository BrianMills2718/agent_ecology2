"""Integration tests for LLM budget trading via genesis ledger.

Plan #30: LLM Budget Trading
Tests that agents can trade budget through genesis_ledger artifact.
"""

import pytest

from src.world.world import World


@pytest.mark.plans([30])
class TestGenesisLedgerBudgetTrading:
    """Test budget trading through genesis_ledger artifact."""

    def test_transfer_budget_via_genesis(self, test_world: World) -> None:
        """Test agents can transfer budget via genesis_ledger.transfer_budget method."""
        # test_world already has genesis artifacts created
        # Setup agents with budget and compute (needed for method cost)
        test_world.ledger.create_principal("alice", starting_scrip=100, starting_compute=100)
        test_world.ledger.create_principal("bob", starting_scrip=100, starting_compute=100)
        test_world.ledger.set_resource("alice", "llm_budget", 1000.0)
        test_world.ledger.set_resource("bob", "llm_budget", 500.0)

        # Verify genesis_ledger artifact exists
        assert "genesis_ledger" in test_world.genesis_artifacts

        # Invoke transfer_budget method as alice
        result = test_world.invoke_artifact(
            invoker_id="alice",
            artifact_id="genesis_ledger",
            method="transfer_budget",
            args=["bob", 200.0],  # Transfer 200 from alice to bob
        )

        assert result.get("success") is True
        assert test_world.ledger.get_resource("alice", "llm_budget") == 800.0
        assert test_world.ledger.get_resource("bob", "llm_budget") == 700.0

    def test_cannot_transfer_others_budget(self, test_world: World) -> None:
        """Test that agents cannot transfer budget FROM another agent."""
        # test_world already has genesis artifacts created
        test_world.ledger.create_principal("alice", starting_scrip=100)
        test_world.ledger.create_principal("bob", starting_scrip=100)
        test_world.ledger.create_principal("mallory", starting_scrip=100)
        test_world.ledger.set_resource("alice", "llm_budget", 1000.0)

        # Mallory tries to transfer alice's budget to herself
        result = test_world.invoke_artifact(
            invoker_id="mallory",  # mallory is the invoker
            artifact_id="genesis_ledger",
            method="transfer_budget",
            args=["mallory", 200.0],  # Args: [to, amount] - transfers to mallory
        )

        # Mallory can only transfer FROM herself, not from alice
        # So this should fail due to insufficient budget (mallory has 0)
        assert result.get("success") is False
        # Alice's budget unchanged
        assert test_world.ledger.get_resource("alice", "llm_budget") == 1000.0

    def test_get_budget_via_genesis(self, test_world: World) -> None:
        """Test agents can query their budget via genesis_ledger.get_budget method."""
        # test_world already has genesis artifacts created
        test_world.ledger.create_principal("alice", starting_scrip=100)
        test_world.ledger.set_resource("alice", "llm_budget", 1234.5)

        result = test_world.invoke_artifact(
            invoker_id="alice",
            artifact_id="genesis_ledger",
            method="get_budget",
            args=["alice"],
        )

        assert result.get("success") is True
        # Result data is nested in "data" from invoke_artifact wrapper
        assert result.get("data", {}).get("budget") == 1234.5
