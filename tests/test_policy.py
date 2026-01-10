"""Unit tests for artifact policy pipeline.

These tests verify that the artifact policy system correctly:
- Stores and applies policies
- Applies default policies when none specified
- Enforces read/write/invoke permissions
- Charges read_price to artifact owner
- Allows owner to always bypass restrictions
"""

import sys
from pathlib import Path

import pytest

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))
from world.artifacts import Artifact, ArtifactStore, default_policy
from world.ledger import Ledger


@pytest.fixture
def artifact_store() -> ArtifactStore:
    """Create a fresh artifact store for each test."""
    return ArtifactStore()


@pytest.fixture
def ledger() -> Ledger:
    """Create a ledger with test principals."""
    ledger = Ledger()
    ledger.create_principal("owner", starting_scrip=1000, starting_compute=100)
    ledger.create_principal("reader", starting_scrip=500, starting_compute=100)
    ledger.create_principal("writer", starting_scrip=500, starting_compute=100)
    ledger.create_principal("invoker", starting_scrip=500, starting_compute=100)
    ledger.create_principal("unauthorized", starting_scrip=500, starting_compute=100)
    return ledger


class TestWriteArtifactWithPolicy:
    """Tests for storing artifacts with custom policies."""

    def test_write_artifact_with_policy(self, artifact_store: ArtifactStore) -> None:
        """Verify that policy is stored when writing an artifact."""
        custom_policy = {
            "read_price": 10,
            "invoke_price": 20,
            "allow_read": ["reader", "owner"],
            "allow_write": ["writer"],
            "allow_invoke": ["invoker", "owner"],
        }

        artifact = artifact_store.write(
            artifact_id="test_artifact",
            type="document",
            content="Test content",
            owner_id="owner",
            policy=custom_policy,
        )

        assert artifact.policy["read_price"] == 10
        assert artifact.policy["invoke_price"] == 20
        assert artifact.policy["allow_read"] == ["reader", "owner"]
        assert artifact.policy["allow_write"] == ["writer"]
        assert artifact.policy["allow_invoke"] == ["invoker", "owner"]

    def test_write_artifact_policy_persists(self, artifact_store: ArtifactStore) -> None:
        """Verify that policy persists after retrieval."""
        custom_policy = {
            "read_price": 5,
            "allow_read": ["specific_agent"],
        }

        artifact_store.write(
            artifact_id="persist_test",
            type="document",
            content="Test",
            owner_id="owner",
            policy=custom_policy,
        )

        retrieved = artifact_store.get("persist_test")
        assert retrieved is not None
        assert retrieved.policy["read_price"] == 5
        assert retrieved.policy["allow_read"] == ["specific_agent"]


class TestDefaultPolicyApplied:
    """Tests for default policy application."""

    def test_default_policy_applied(self, artifact_store: ArtifactStore) -> None:
        """Verify defaults are applied when no policy specified."""
        artifact = artifact_store.write(
            artifact_id="no_policy_artifact",
            type="document",
            content="No explicit policy",
            owner_id="owner",
        )

        expected_defaults = default_policy()
        assert artifact.policy["read_price"] == expected_defaults["read_price"]
        assert artifact.policy["invoke_price"] == expected_defaults["invoke_price"]
        assert artifact.policy["allow_read"] == expected_defaults["allow_read"]
        assert artifact.policy["allow_write"] == expected_defaults["allow_write"]
        assert artifact.policy["allow_invoke"] == expected_defaults["allow_invoke"]

    def test_default_policy_values(self) -> None:
        """Verify default policy has expected values."""
        defaults = default_policy()
        assert defaults["read_price"] == 0
        assert defaults["invoke_price"] == 0
        assert defaults["allow_read"] == ["*"]
        assert defaults["allow_write"] == []
        assert defaults["allow_invoke"] == ["*"]

    def test_partial_policy_merged_with_defaults(
        self, artifact_store: ArtifactStore
    ) -> None:
        """Verify partial policy is merged with defaults."""
        partial_policy = {
            "read_price": 15,  # Override default
            # allow_read, allow_write, etc. should use defaults
        }

        artifact = artifact_store.write(
            artifact_id="partial_policy",
            type="document",
            content="Partial policy",
            owner_id="owner",
            policy=partial_policy,
        )

        assert artifact.policy["read_price"] == 15
        # Other fields should have default values
        defaults = default_policy()
        assert artifact.policy["allow_read"] == defaults["allow_read"]
        assert artifact.policy["allow_write"] == defaults["allow_write"]


class TestReadPermissionDenied:
    """Tests for read permission denial."""

    def test_read_permission_denied(self, artifact_store: ArtifactStore) -> None:
        """Verify can_read blocks unauthorized agents."""
        artifact = artifact_store.write(
            artifact_id="restricted_read",
            type="document",
            content="Restricted content",
            owner_id="owner",
            policy={"allow_read": ["authorized_only"]},
        )

        # Unauthorized agent should be denied
        assert artifact.can_read("unauthorized") is False

    def test_read_permission_granted_to_allowed(
        self, artifact_store: ArtifactStore
    ) -> None:
        """Verify can_read allows authorized agents."""
        artifact = artifact_store.write(
            artifact_id="restricted_read",
            type="document",
            content="Restricted content",
            owner_id="owner",
            policy={"allow_read": ["authorized_agent"]},
        )

        assert artifact.can_read("authorized_agent") is True

    def test_read_permission_wildcard(self, artifact_store: ArtifactStore) -> None:
        """Verify wildcard allows all agents to read."""
        artifact = artifact_store.write(
            artifact_id="public_read",
            type="document",
            content="Public content",
            owner_id="owner",
            policy={"allow_read": ["*"]},
        )

        assert artifact.can_read("any_agent") is True
        assert artifact.can_read("another_agent") is True


class TestWritePermissionDenied:
    """Tests for write permission denial."""

    def test_write_permission_denied(self, artifact_store: ArtifactStore) -> None:
        """Verify can_write blocks unauthorized agents."""
        artifact = artifact_store.write(
            artifact_id="restricted_write",
            type="document",
            content="Original content",
            owner_id="owner",
            policy={"allow_write": ["authorized_writer"]},
        )

        # Unauthorized agent should be denied
        assert artifact.can_write("unauthorized") is False

    def test_write_permission_granted_to_allowed(
        self, artifact_store: ArtifactStore
    ) -> None:
        """Verify can_write allows authorized agents."""
        artifact = artifact_store.write(
            artifact_id="restricted_write",
            type="document",
            content="Original content",
            owner_id="owner",
            policy={"allow_write": ["authorized_writer"]},
        )

        assert artifact.can_write("authorized_writer") is True

    def test_write_permission_empty_list(self, artifact_store: ArtifactStore) -> None:
        """Verify empty allow_write means owner-only."""
        artifact = artifact_store.write(
            artifact_id="owner_only_write",
            type="document",
            content="Owner only",
            owner_id="owner",
            policy={"allow_write": []},
        )

        assert artifact.can_write("any_other_agent") is False
        # Owner should still be able to write (tested separately)


class TestInvokePermissionDenied:
    """Tests for invoke permission denial."""

    def test_invoke_permission_denied(self, artifact_store: ArtifactStore) -> None:
        """Verify can_invoke blocks unauthorized agents."""
        artifact = artifact_store.write(
            artifact_id="restricted_invoke",
            type="executable",
            content="Service description",
            owner_id="owner",
            executable=True,
            code="def run(): return 42",
            policy={"allow_invoke": ["authorized_invoker"]},
        )

        # Unauthorized agent should be denied
        assert artifact.can_invoke("unauthorized") is False

    def test_invoke_permission_granted_to_allowed(
        self, artifact_store: ArtifactStore
    ) -> None:
        """Verify can_invoke allows authorized agents."""
        artifact = artifact_store.write(
            artifact_id="restricted_invoke",
            type="executable",
            content="Service description",
            owner_id="owner",
            executable=True,
            code="def run(): return 42",
            policy={"allow_invoke": ["authorized_invoker"]},
        )

        assert artifact.can_invoke("authorized_invoker") is True

    def test_invoke_permission_non_executable(
        self, artifact_store: ArtifactStore
    ) -> None:
        """Verify non-executable artifacts cannot be invoked."""
        artifact = artifact_store.write(
            artifact_id="non_executable",
            type="document",
            content="Just a document",
            owner_id="owner",
            executable=False,
            policy={"allow_invoke": ["*"]},
        )

        # Even with wildcard allow, non-executable cannot be invoked
        assert artifact.can_invoke("any_agent") is False


class TestReadPriceCharged:
    """Tests for read_price payment to owner."""

    def test_read_price_charged(
        self, artifact_store: ArtifactStore, ledger: Ledger
    ) -> None:
        """Verify read_price is correctly stored and can be used for payment."""
        read_price = 10

        artifact = artifact_store.write(
            artifact_id="paid_content",
            type="document",
            content="Premium content",
            owner_id="owner",
            policy={"read_price": read_price, "allow_read": ["*"]},
        )

        # Get initial balances
        owner_initial = ledger.get_scrip("owner")
        reader_initial = ledger.get_scrip("reader")

        # Verify read_price is set correctly
        assert artifact.policy["read_price"] == read_price

        # Simulate payment: reader pays owner
        # In actual implementation, this would be done by the kernel
        assert ledger.transfer_scrip("reader", "owner", read_price) is True

        # Verify balances after transfer
        assert ledger.get_scrip("owner") == owner_initial + read_price
        assert ledger.get_scrip("reader") == reader_initial - read_price

    def test_read_price_zero_default(self, artifact_store: ArtifactStore) -> None:
        """Verify default read_price is zero (free to read)."""
        artifact = artifact_store.write(
            artifact_id="free_content",
            type="document",
            content="Free content",
            owner_id="owner",
        )

        assert artifact.policy["read_price"] == 0

    def test_invoke_price_stored(self, artifact_store: ArtifactStore) -> None:
        """Verify invoke_price is stored in policy."""
        artifact = artifact_store.write(
            artifact_id="paid_service",
            type="executable",
            content="Service",
            owner_id="owner",
            executable=True,
            code="def run(): return 'result'",
            policy={"invoke_price": 25},
        )

        assert artifact.policy["invoke_price"] == 25
        assert artifact.price == 25  # Backwards compat property


class TestOwnerAlwaysHasAccess:
    """Tests verifying owner bypasses all restrictions."""

    def test_owner_always_has_access_read(
        self, artifact_store: ArtifactStore
    ) -> None:
        """Verify owner can always read their own artifact."""
        artifact = artifact_store.write(
            artifact_id="owner_read_test",
            type="document",
            content="Owner's content",
            owner_id="owner",
            policy={"allow_read": []},  # Empty list - nobody allowed
        )

        # Owner should still be able to read
        assert artifact.can_read("owner") is True

    def test_owner_always_has_access_write(
        self, artifact_store: ArtifactStore
    ) -> None:
        """Verify owner can always write to their own artifact."""
        artifact = artifact_store.write(
            artifact_id="owner_write_test",
            type="document",
            content="Owner's content",
            owner_id="owner",
            policy={"allow_write": []},  # Empty list - nobody allowed
        )

        # Owner should still be able to write
        assert artifact.can_write("owner") is True

    def test_owner_always_has_access_invoke(
        self, artifact_store: ArtifactStore
    ) -> None:
        """Verify owner can always invoke their own executable artifact."""
        artifact = artifact_store.write(
            artifact_id="owner_invoke_test",
            type="executable",
            content="Owner's service",
            owner_id="owner",
            executable=True,
            code="def run(): return 'owner result'",
            policy={"allow_invoke": []},  # Empty list - nobody allowed
        )

        # Owner should still be able to invoke
        assert artifact.can_invoke("owner") is True

    def test_owner_not_in_allow_list_still_allowed(
        self, artifact_store: ArtifactStore
    ) -> None:
        """Verify owner has access even when not explicitly in allow list."""
        artifact = artifact_store.write(
            artifact_id="exclusive_artifact",
            type="document",
            content="Exclusive content",
            owner_id="owner",
            policy={
                "allow_read": ["other_agent"],  # Owner not in list
                "allow_write": ["other_agent"],  # Owner not in list
            },
        )

        # Owner should still have access
        assert artifact.can_read("owner") is True
        assert artifact.can_write("owner") is True


class TestPolicyUpdate:
    """Tests for updating artifact policies."""

    def test_policy_update_on_rewrite(self, artifact_store: ArtifactStore) -> None:
        """Verify policy can be updated when artifact is rewritten."""
        # Initial write with restrictive policy
        artifact_store.write(
            artifact_id="update_test",
            type="document",
            content="Initial content",
            owner_id="owner",
            policy={"allow_read": ["agent1"]},
        )

        initial = artifact_store.get("update_test")
        assert initial is not None
        assert initial.can_read("agent2") is False

        # Update with new policy
        artifact_store.write(
            artifact_id="update_test",
            type="document",
            content="Updated content",
            owner_id="owner",
            policy={"allow_read": ["agent1", "agent2"]},
        )

        updated = artifact_store.get("update_test")
        assert updated is not None
        assert updated.can_read("agent2") is True


class TestPricingBackwardsCompatibility:
    """Tests for backwards compatibility with price parameter."""

    def test_price_param_sets_invoke_price(
        self, artifact_store: ArtifactStore
    ) -> None:
        """Verify price parameter sets invoke_price in policy."""
        artifact = artifact_store.write(
            artifact_id="compat_test",
            type="executable",
            content="Service",
            owner_id="owner",
            executable=True,
            code="def run(): return 1",
            price=50,  # Old-style price parameter
        )

        assert artifact.policy["invoke_price"] == 50
        assert artifact.price == 50

    def test_policy_invoke_price_overrides_price_param(
        self, artifact_store: ArtifactStore
    ) -> None:
        """Verify policy invoke_price takes precedence when both specified."""
        artifact = artifact_store.write(
            artifact_id="override_test",
            type="executable",
            content="Service",
            owner_id="owner",
            executable=True,
            code="def run(): return 1",
            price=50,
            policy={"invoke_price": 100},  # Policy should win
        )

        assert artifact.policy["invoke_price"] == 100
        assert artifact.price == 100
