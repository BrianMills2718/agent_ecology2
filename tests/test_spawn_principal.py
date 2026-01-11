"""Unit tests for spawn_principal and related genesis features.

Tests for the spawn_principal method in GenesisLedger, which allows
agents to create new principals (child agents) in the system.
"""

from pathlib import Path

import pytest


from src.world.ledger import Ledger
from src.world.genesis import GenesisLedger


@pytest.fixture
def ledger() -> Ledger:
    """Create a fresh Ledger instance for each test."""
    return Ledger()


@pytest.fixture
def ledger_with_agent(ledger: Ledger) -> Ledger:
    """Create a Ledger with one agent that has scrip to spawn principals."""
    ledger.create_principal("parent_agent", starting_scrip=100, starting_compute=500)
    return ledger


@pytest.fixture
def genesis_ledger(ledger_with_agent: Ledger) -> GenesisLedger:
    """Create a GenesisLedger wrapping the test ledger."""
    return GenesisLedger(ledger_with_agent)


@pytest.fixture
def poor_ledger(ledger: Ledger) -> Ledger:
    """Create a Ledger with an agent that has 0 scrip."""
    ledger.create_principal("poor_agent", starting_scrip=0, starting_compute=500)
    return ledger


@pytest.fixture
def poor_genesis_ledger(poor_ledger: Ledger) -> GenesisLedger:
    """Create a GenesisLedger with a poor agent."""
    return GenesisLedger(poor_ledger)


class TestSpawnPrincipalCreatesLedgerEntry:
    """Tests verifying spawn_principal creates proper ledger entries."""

    def test_spawn_principal_creates_ledger_entry(
        self, genesis_ledger: GenesisLedger, ledger_with_agent: Ledger
    ) -> None:
        """Verify new principal is created with 0 scrip and 0 compute."""
        # Spawn a new principal
        result = genesis_ledger._spawn_principal([], "parent_agent")

        assert result["success"] is True
        assert "principal_id" in result

        # Get the new principal's ID
        new_id = result["principal_id"]

        # Verify the new principal exists in the ledger with 0 balances
        assert ledger_with_agent.get_scrip(new_id) == 0
        assert ledger_with_agent.get_compute(new_id) == 0

    def test_spawn_principal_new_id_in_all_balances(
        self, genesis_ledger: GenesisLedger, ledger_with_agent: Ledger
    ) -> None:
        """Verify spawned principal appears in all_balances."""
        result = genesis_ledger._spawn_principal([], "parent_agent")
        new_id = result["principal_id"]

        all_balances = ledger_with_agent.get_all_balances()
        assert new_id in all_balances
        assert all_balances[new_id]["scrip"] == 0
        assert all_balances[new_id]["compute"] == 0


class TestSpawnPrincipalReturnsUniqueId:
    """Tests verifying spawn_principal returns UUID-based unique IDs."""

    def test_spawn_principal_returns_unique_id(
        self, genesis_ledger: GenesisLedger
    ) -> None:
        """Verify UUID-based ID is returned."""
        result = genesis_ledger._spawn_principal([], "parent_agent")

        assert result["success"] is True
        assert "principal_id" in result

        principal_id = result["principal_id"]
        # ID should start with "agent_" prefix
        assert principal_id.startswith("agent_")
        # ID should have 8 hex characters after prefix (uuid4.hex[:8])
        suffix = principal_id[6:]  # Skip "agent_"
        assert len(suffix) == 8
        # Verify it's valid hex
        int(suffix, 16)  # This will raise if not valid hex

    def test_spawn_principal_ids_are_different(
        self, genesis_ledger: GenesisLedger
    ) -> None:
        """Verify multiple spawns return different IDs."""
        result1 = genesis_ledger._spawn_principal([], "parent_agent")
        result2 = genesis_ledger._spawn_principal([], "parent_agent")

        assert result1["principal_id"] != result2["principal_id"]


class TestSpawnPrincipalCostsScrip:
    """Tests verifying spawn_principal charges the correct fee."""

    def test_spawn_principal_costs_scrip(
        self, genesis_ledger: GenesisLedger, ledger_with_agent: Ledger
    ) -> None:
        """Verify 1 scrip fee is charged to invoker.

        Note: The fee is charged by the executor when invoking the method,
        not by the method itself. This test verifies the method's cost
        is registered as 1 scrip.
        """
        # Check the method cost
        method = genesis_ledger.get_method("spawn_principal")
        assert method is not None
        assert method.cost == 1

    def test_spawn_principal_method_listed_with_cost(
        self, genesis_ledger: GenesisLedger
    ) -> None:
        """Verify spawn_principal is listed with cost of 1."""
        methods = genesis_ledger.list_methods()
        spawn_method = next(
            (m for m in methods if m["name"] == "spawn_principal"), None
        )

        assert spawn_method is not None
        assert spawn_method["cost"] == 1
        assert "Spawn a new principal" in spawn_method["description"]


class TestSpawnPrincipalFailsInsufficientScrip:
    """Tests verifying spawn fails when invoker lacks scrip.

    Note: The scrip check is performed by the executor before calling
    the method, so we test that the method cost is properly configured.
    """

    def test_spawn_principal_fails_insufficient_scrip(
        self, poor_genesis_ledger: GenesisLedger, poor_ledger: Ledger
    ) -> None:
        """Verify spawn would fail if invoker has < 1 scrip.

        The actual fee deduction happens in the executor layer, but
        we can verify the method has a cost that would require scrip.
        """
        # Verify the poor agent has no scrip
        assert poor_ledger.get_scrip("poor_agent") == 0

        # The method itself doesn't check scrip (executor does),
        # but we verify the cost is configured
        method = poor_genesis_ledger.get_method("spawn_principal")
        assert method.cost == 1

        # If the executor were to check, it would fail because:
        assert not poor_ledger.can_afford_scrip("poor_agent", method.cost)


class TestSpawnMultiplePrincipals:
    """Tests verifying multiple spawns create distinct principals."""

    def test_spawn_multiple_principals(
        self, genesis_ledger: GenesisLedger, ledger_with_agent: Ledger
    ) -> None:
        """Verify multiple spawns create distinct IDs."""
        # Spawn multiple principals
        ids = []
        for _ in range(5):
            result = genesis_ledger._spawn_principal([], "parent_agent")
            assert result["success"] is True
            ids.append(result["principal_id"])

        # All IDs should be unique
        assert len(ids) == len(set(ids))

        # All should exist in ledger
        for principal_id in ids:
            assert principal_id in ledger_with_agent.get_all_balances()

    def test_spawn_multiple_all_start_with_zero(
        self, genesis_ledger: GenesisLedger, ledger_with_agent: Ledger
    ) -> None:
        """Verify all spawned principals start with 0 resources."""
        ids = []
        for _ in range(3):
            result = genesis_ledger._spawn_principal([], "parent_agent")
            ids.append(result["principal_id"])

        for principal_id in ids:
            assert ledger_with_agent.get_scrip(principal_id) == 0
            assert ledger_with_agent.get_compute(principal_id) == 0


class TestSpawnedPrincipalCanReceiveTransfer:
    """Tests verifying parent can transfer resources to spawned child."""

    def test_spawned_principal_can_receive_transfer(
        self, genesis_ledger: GenesisLedger, ledger_with_agent: Ledger
    ) -> None:
        """Verify parent can transfer scrip to child."""
        # Spawn a child
        result = genesis_ledger._spawn_principal([], "parent_agent")
        child_id = result["principal_id"]

        # Parent transfers scrip to child
        initial_parent_scrip = ledger_with_agent.get_scrip("parent_agent")
        transfer_amount = 25

        # Perform transfer using the ledger directly
        success = ledger_with_agent.transfer_scrip(
            "parent_agent", child_id, transfer_amount
        )

        assert success is True
        assert ledger_with_agent.get_scrip(child_id) == transfer_amount
        assert (
            ledger_with_agent.get_scrip("parent_agent")
            == initial_parent_scrip - transfer_amount
        )

    def test_spawned_principal_can_receive_via_genesis_transfer(
        self, genesis_ledger: GenesisLedger, ledger_with_agent: Ledger
    ) -> None:
        """Verify parent can transfer via genesis_ledger.transfer method."""
        # Spawn a child
        spawn_result = genesis_ledger._spawn_principal([], "parent_agent")
        child_id = spawn_result["principal_id"]

        initial_parent_scrip = ledger_with_agent.get_scrip("parent_agent")
        transfer_amount = 10

        # Transfer via genesis method
        transfer_result = genesis_ledger._transfer(
            ["parent_agent", child_id, transfer_amount], "parent_agent"
        )

        assert transfer_result["success"] is True
        assert transfer_result["transferred"] == transfer_amount
        assert transfer_result["to"] == child_id
        assert ledger_with_agent.get_scrip(child_id) == transfer_amount

    def test_spawned_principal_can_accumulate_transfers(
        self, genesis_ledger: GenesisLedger, ledger_with_agent: Ledger
    ) -> None:
        """Verify child can receive multiple transfers."""
        # Spawn a child
        result = genesis_ledger._spawn_principal([], "parent_agent")
        child_id = result["principal_id"]

        # Multiple transfers
        ledger_with_agent.transfer_scrip("parent_agent", child_id, 10)
        ledger_with_agent.transfer_scrip("parent_agent", child_id, 15)
        ledger_with_agent.transfer_scrip("parent_agent", child_id, 5)

        assert ledger_with_agent.get_scrip(child_id) == 30


class TestSpawnPrincipalEdgeCases:
    """Additional edge case tests for spawn_principal."""

    def test_spawn_principal_ignores_args(
        self, genesis_ledger: GenesisLedger
    ) -> None:
        """Verify spawn_principal ignores any passed arguments."""
        # Pass various args - should all be ignored
        result1 = genesis_ledger._spawn_principal([], "parent_agent")
        result2 = genesis_ledger._spawn_principal(["ignored"], "parent_agent")
        result3 = genesis_ledger._spawn_principal(
            ["ignored", "args", 123], "parent_agent"
        )

        assert result1["success"] is True
        assert result2["success"] is True
        assert result3["success"] is True

    def test_spawn_principal_result_format(
        self, genesis_ledger: GenesisLedger
    ) -> None:
        """Verify spawn_principal returns correct result format."""
        result = genesis_ledger._spawn_principal([], "parent_agent")

        # Should have exactly these keys on success
        assert "success" in result
        assert "principal_id" in result
        assert result["success"] is True
        assert isinstance(result["principal_id"], str)
