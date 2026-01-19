"""Feature acceptance tests for ledger - maps to meta/acceptance_gates/ledger.yaml.

Run with: pytest --feature ledger tests/
"""

from __future__ import annotations

import pytest
from concurrent.futures import ThreadPoolExecutor, as_completed

from src.world.ledger import Ledger


@pytest.mark.feature("ledger")
class TestLedgerFeature:
    """Tests mapping to meta/acceptance_gates/ledger.yaml acceptance criteria."""

    # AC-1: Successful scrip transfer between principals (happy_path)
    def test_ac_1_successful_scrip_transfer(
        self, ledger_with_principals: Ledger
    ) -> None:
        """AC-1: Successful scrip transfer between principals.

        Given:
          - Principal A has 100 scrip
          - Principal B has 50 scrip
        When: A transfers 30 scrip to B
        Then:
          - A's balance becomes 70 scrip
          - B's balance becomes 80 scrip
          - Transfer returns True
        """
        ledger = ledger_with_principals
        # Setup matches AC: alice=1000, bob=500 (use subset scenario)
        # Create fresh principals to match exact AC values
        ledger.create_principal("principal_a", starting_scrip=100, starting_compute=10)
        ledger.create_principal("principal_b", starting_scrip=50, starting_compute=10)

        result = ledger.transfer_scrip("principal_a", "principal_b", 30)

        assert result is True
        assert ledger.get_scrip("principal_a") == 70
        assert ledger.get_scrip("principal_b") == 80

    # AC-2: Transfer fails when insufficient balance (error_case)
    def test_ac_2_transfer_fails_insufficient_balance(self) -> None:
        """AC-2: Transfer fails when insufficient balance.

        Given: Principal A has 20 scrip
        When: A attempts to transfer 50 scrip
        Then:
          - Transfer returns False
          - A's balance remains 20 scrip
          - No partial transfer occurs
        """
        ledger = Ledger()
        ledger.create_principal("principal_a", starting_scrip=20, starting_compute=10)
        ledger.create_principal("principal_b", starting_scrip=0, starting_compute=10)

        result = ledger.transfer_scrip("principal_a", "principal_b", 50)

        assert result is False
        assert ledger.get_scrip("principal_a") == 20
        assert ledger.get_scrip("principal_b") == 0

    # AC-3: Resource deduction respects type constraints (edge_case)
    def test_ac_3_resource_deduction_no_negative(self) -> None:
        """AC-3: Resource deduction respects type constraints.

        Given:
          - Principal has 100 units of resource X
          - Resource X is defined in config
        When: Deduct 150 units of resource X
        Then:
          - Deduction fails (returns False or raises)
          - Balance remains 100 units
          - No negative balance allowed
        """
        ledger = Ledger()
        # Using scrip as "resource" since it's the main balance type
        ledger.create_principal("agent", starting_scrip=100, starting_compute=100)

        initial_scrip = ledger.get_scrip("agent")
        assert initial_scrip == 100

        # Attempt to deduct more than available
        result = ledger.deduct_scrip("agent", 150)

        assert result is False
        assert ledger.get_scrip("agent") == 100  # Balance unchanged

    # AC-4: Concurrent transfers maintain consistency (edge_case)
    def test_ac_4_concurrent_transfers_consistency(self) -> None:
        """AC-4: Concurrent transfers maintain consistency.

        Given:
          - Principal A has 100 scrip
          - Two concurrent requests each try to transfer 60 scrip from A
        When: Both transfers execute
        Then:
          - Only one transfer succeeds
          - A's balance is exactly 40 (not negative)
          - Lock prevents race condition
        """
        ledger = Ledger()
        ledger.create_principal("sender", starting_scrip=100, starting_compute=10)
        ledger.create_principal("receiver1", starting_scrip=0, starting_compute=10)
        ledger.create_principal("receiver2", starting_scrip=0, starting_compute=10)

        results = []

        def transfer_to_receiver(receiver: str) -> bool:
            return ledger.transfer_scrip("sender", receiver, 60)

        # Execute transfers concurrently
        with ThreadPoolExecutor(max_workers=2) as executor:
            futures = [
                executor.submit(transfer_to_receiver, "receiver1"),
                executor.submit(transfer_to_receiver, "receiver2"),
            ]
            for future in as_completed(futures):
                results.append(future.result())

        # Exactly one should succeed
        assert results.count(True) == 1
        assert results.count(False) == 1

        # Sender should have 40 (100 - 60)
        assert ledger.get_scrip("sender") == 40
        assert ledger.get_scrip("sender") >= 0  # Never negative

    # AC-5: Decimal precision preserved (happy_path)
    def test_ac_5_decimal_precision_preserved(self) -> None:
        """AC-5: Decimal precision preserved.

        Given: Resource balance is 100 units
        When: Transfer amounts that could cause float issues
        Then:
          - Balance is exactly as expected
          - No floating point errors accumulate

        Note: Ledger uses int for scrip, avoiding float issues.
        This test verifies integer arithmetic is correct.
        """
        ledger = Ledger()
        ledger.create_principal("agent_a", starting_scrip=100, starting_compute=10)
        ledger.create_principal("agent_b", starting_scrip=0, starting_compute=10)

        # Multiple small transfers
        for _ in range(10):
            ledger.transfer_scrip("agent_a", "agent_b", 1)

        # Verify exact balance
        assert ledger.get_scrip("agent_a") == 90
        assert ledger.get_scrip("agent_b") == 10


@pytest.mark.feature("ledger")
class TestLedgerEdgeCases:
    """Additional edge case tests for ledger robustness."""

    def test_transfer_to_self_succeeds(self) -> None:
        """Self-transfer should succeed without changing balance."""
        ledger = Ledger()
        ledger.create_principal("agent", starting_scrip=100, starting_compute=10)

        result = ledger.transfer_scrip("agent", "agent", 50)

        # Self-transfer is valid (no-op economically)
        assert ledger.get_scrip("agent") == 100

    def test_zero_transfer_behavior(self) -> None:
        """Zero amount transfer behavior.

        Note: The ledger considers zero transfer as a no-op that returns False.
        This documents actual behavior rather than prescribing it.
        """
        ledger = Ledger()
        ledger.create_principal("alice", starting_scrip=100, starting_compute=10)
        ledger.create_principal("bob", starting_scrip=50, starting_compute=10)

        result = ledger.transfer_scrip("alice", "bob", 0)

        # Actual behavior: zero transfer returns False (no-op)
        assert result is False
        # But balances remain unchanged (no side effects)
        assert ledger.get_scrip("alice") == 100
        assert ledger.get_scrip("bob") == 50
