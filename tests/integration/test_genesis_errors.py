"""Integration tests for error response conventions in genesis artifacts.

Tests that genesis artifacts return errors using the new standardized format
with error codes and categories.
"""

import pytest

from src.world.ledger import Ledger
from src.world.artifacts import ArtifactStore
from src.world.genesis import GenesisLedger


@pytest.fixture
def ledger() -> Ledger:
    """Create a test ledger."""
    return Ledger()


@pytest.fixture
def artifact_store() -> ArtifactStore:
    """Create a test artifact store."""
    return ArtifactStore()


@pytest.fixture
def genesis_ledger(ledger: Ledger, artifact_store: ArtifactStore) -> GenesisLedger:
    """Create a genesis ledger with test dependencies."""
    return GenesisLedger(ledger, artifact_store=artifact_store)


class TestLedgerErrorFormat:
    """Tests for genesis_ledger error format."""

    def test_balance_missing_args_error_format(
        self, genesis_ledger: GenesisLedger
    ) -> None:
        """Balance with missing args returns validation error format."""
        result = genesis_ledger._balance([], "alice")

        assert result["success"] is False
        assert "code" in result
        assert "category" in result
        assert result["code"] == "missing_argument"
        assert result["category"] == "validation"
        assert result["retriable"] is False

    def test_transfer_missing_args_error_format(
        self, genesis_ledger: GenesisLedger
    ) -> None:
        """Transfer with missing args returns validation error format."""
        result = genesis_ledger._transfer([], "alice")

        assert result["success"] is False
        assert result["code"] == "missing_argument"
        assert result["category"] == "validation"
        assert "details" in result
        assert result["details"]["required"] == ["from_id", "to_id", "amount"]

    def test_transfer_permission_error_format(
        self, genesis_ledger: GenesisLedger
    ) -> None:
        """Transfer from another account returns permission error format."""
        result = genesis_ledger._transfer(["bob", "charlie", 10], "alice")

        assert result["success"] is False
        assert result["code"] == "not_authorized"
        assert result["category"] == "permission"
        assert "details" in result
        assert result["details"]["invoker"] == "alice"
        assert result["details"]["target"] == "bob"

    def test_transfer_invalid_amount_error_format(
        self, genesis_ledger: GenesisLedger
    ) -> None:
        """Transfer with invalid amount returns validation error format."""
        result = genesis_ledger._transfer(["alice", "bob", -10], "alice")

        assert result["success"] is False
        assert result["code"] == "invalid_argument"
        assert result["category"] == "validation"

    def test_transfer_ownership_missing_args_error_format(
        self, genesis_ledger: GenesisLedger
    ) -> None:
        """Transfer_ownership with missing args returns validation error format."""
        result = genesis_ledger._transfer_ownership([], "alice")

        assert result["success"] is False
        assert result["code"] == "missing_argument"
        assert result["category"] == "validation"
        assert result["details"]["required"] == ["artifact_id", "to_id"]

    def test_transfer_ownership_not_found_error_format(
        self, genesis_ledger: GenesisLedger
    ) -> None:
        """Transfer_ownership for nonexistent artifact returns resource error."""
        result = genesis_ledger._transfer_ownership(["nonexistent", "bob"], "alice")

        assert result["success"] is False
        assert result["code"] == "not_found"
        assert result["category"] == "resource"
        assert "details" in result
        assert result["details"]["artifact_id"] == "nonexistent"


class TestBackwardsCompatibility:
    """Tests that new error format is backwards compatible."""

    def test_error_still_has_success_field(
        self, genesis_ledger: GenesisLedger
    ) -> None:
        """Errors still have success field for backwards compatibility."""
        result = genesis_ledger._balance([], "alice")

        # Old code checks these two fields
        assert "success" in result
        assert "error" in result
        assert result["success"] is False

    def test_can_check_success_field(
        self, genesis_ledger: GenesisLedger
    ) -> None:
        """Code checking result['success'] still works."""
        result = genesis_ledger._balance([], "alice")

        # This is how existing code checks for errors
        if not result["success"]:
            # Can still get error message
            assert len(result["error"]) > 0

    def test_new_fields_are_additive(
        self, genesis_ledger: GenesisLedger
    ) -> None:
        """New fields (code, category, retriable) are additive."""
        result = genesis_ledger._balance([], "alice")

        # Old fields still present
        assert "success" in result
        assert "error" in result

        # New fields added
        assert "code" in result
        assert "category" in result
        assert "retriable" in result
