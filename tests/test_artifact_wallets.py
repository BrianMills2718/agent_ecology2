"""Tests for artifact wallets - artifacts holding scrip."""

import pytest
from pathlib import Path


from src.world.ledger import Ledger


class TestArtifactWallets:
    """Test that artifacts can hold and receive scrip."""

    def test_transfer_to_nonexistent_creates_wallet(self) -> None:
        """Transferring to a non-existent ID should create it."""
        ledger = Ledger()
        ledger.create_principal("alice", starting_scrip=100, starting_compute=50)

        # Transfer to an artifact (doesn't exist yet)
        result = ledger.transfer_scrip("alice", "escrow_contract_1", 30)

        assert result is True
        assert ledger.get_scrip("alice") == 70
        assert ledger.get_scrip("escrow_contract_1") == 30

    def test_artifact_can_receive_multiple_transfers(self) -> None:
        """Artifact wallet can accumulate from multiple sources."""
        ledger = Ledger()
        ledger.create_principal("alice", starting_scrip=100, starting_compute=0)
        ledger.create_principal("bob", starting_scrip=100, starting_compute=0)

        ledger.transfer_scrip("alice", "firm_treasury", 30)
        ledger.transfer_scrip("bob", "firm_treasury", 20)

        assert ledger.get_scrip("firm_treasury") == 50

    def test_artifact_can_send_scrip(self) -> None:
        """Artifact with balance can send to others."""
        ledger = Ledger()
        ledger.create_principal("alice", starting_scrip=100, starting_compute=0)
        ledger.create_principal("bob", starting_scrip=0, starting_compute=0)

        # Fund the artifact
        ledger.transfer_scrip("alice", "payout_contract", 50)

        # Artifact pays out to bob
        result = ledger.transfer_scrip("payout_contract", "bob", 25)

        assert result is True
        assert ledger.get_scrip("payout_contract") == 25
        assert ledger.get_scrip("bob") == 25

    def test_artifact_insufficient_funds_rejected(self) -> None:
        """Artifact can't spend more than it has."""
        ledger = Ledger()
        ledger.create_principal("alice", starting_scrip=100, starting_compute=0)

        ledger.transfer_scrip("alice", "small_contract", 10)

        # Try to spend more than balance
        result = ledger.transfer_scrip("small_contract", "alice", 20)

        assert result is False
        assert ledger.get_scrip("small_contract") == 10

    def test_ensure_principal_creates_with_zero(self) -> None:
        """ensure_principal creates entry with 0 balance."""
        ledger = Ledger()

        ledger.ensure_principal("new_artifact")

        assert ledger.principal_exists("new_artifact")
        assert ledger.get_scrip("new_artifact") == 0
        assert ledger.get_compute("new_artifact") == 0

    def test_principal_exists_checks_both_balances(self) -> None:
        """principal_exists returns True if in scrip OR compute."""
        ledger = Ledger()

        assert not ledger.principal_exists("unknown")

        ledger.ensure_principal("artifact_1")
        assert ledger.principal_exists("artifact_1")

    def test_credit_scrip_to_artifact(self) -> None:
        """credit_scrip (minting) works for artifacts."""
        ledger = Ledger()

        # Mint scrip directly to an artifact (e.g., oracle reward)
        ledger.credit_scrip("winning_contract", 100)

        assert ledger.get_scrip("winning_contract") == 100


class TestArtifactWalletEdgeCases:
    """Edge cases for artifact wallets."""

    def test_transfer_zero_amount_rejected(self) -> None:
        """Zero transfers should be rejected."""
        ledger = Ledger()
        ledger.create_principal("alice", starting_scrip=100, starting_compute=0)

        result = ledger.transfer_scrip("alice", "artifact", 0)
        assert result is False

    def test_transfer_negative_amount_rejected(self) -> None:
        """Negative transfers should be rejected."""
        ledger = Ledger()
        ledger.create_principal("alice", starting_scrip=100, starting_compute=0)

        result = ledger.transfer_scrip("alice", "artifact", -10)
        assert result is False

    def test_artifact_in_all_balances(self) -> None:
        """Artifacts should appear in get_all_balances."""
        ledger = Ledger()
        ledger.create_principal("alice", starting_scrip=100, starting_compute=50)
        ledger.transfer_scrip("alice", "contract_1", 30)

        balances = ledger.get_all_balances()

        assert "alice" in balances
        assert "contract_1" in balances
        assert balances["contract_1"]["scrip"] == 30
        assert balances["contract_1"]["compute"] == 0
