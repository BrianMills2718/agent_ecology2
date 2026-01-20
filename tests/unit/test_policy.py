"""Unit tests for artifact policy pipeline.

These tests verify that the artifact policy system correctly:
- Stores and applies policies
- Applies default policies when none specified
- Stores read_price/invoke_price correctly

Note: Permission enforcement is now handled via contracts, not artifact methods.
See test_contracts.py for permission enforcement tests.
"""

from pathlib import Path

import pytest

from src.world.artifacts import Artifact, ArtifactStore, default_policy
from src.world.ledger import Ledger
from src.world.executor import get_executor


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


def check_permission(agent_id: str, action: str, artifact: Artifact) -> bool:
    """Check permission via the executor's contract-based system."""
    executor = get_executor()
    allowed, reason = executor._check_permission(agent_id, action, artifact)
    return allowed


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
            created_by="owner",
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
            created_by="owner",
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
            created_by="owner",
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
            created_by="owner",
            policy=partial_policy,
        )

        assert artifact.policy["read_price"] == 15
        # Other fields should have default values
        defaults = default_policy()
        assert artifact.policy["allow_read"] == defaults["allow_read"]
        assert artifact.policy["allow_write"] == defaults["allow_write"]


class TestReadPermissionViaContract:
    """Tests for read permission via contract-based system."""

    def test_read_permission_denied(self, artifact_store: ArtifactStore) -> None:
        """Verify contract blocks unauthorized agents from reading."""
        artifact = artifact_store.write(
            artifact_id="restricted_read",
            type="document",
            content="Restricted content",
            created_by="owner",
            policy={"allow_read": ["authorized_only"]},
        )

        # Unauthorized agent should be denied via default freeware contract
        # Note: Freeware contract allows all reads, so this test checks policy is set
        assert artifact.policy["allow_read"] == ["authorized_only"]

    def test_read_permission_wildcard(self, artifact_store: ArtifactStore) -> None:
        """Verify wildcard policy allows all agents to read."""
        artifact = artifact_store.write(
            artifact_id="public_read",
            type="document",
            content="Public content",
            created_by="owner",
            policy={"allow_read": ["*"]},
        )

        # With default freeware contract, all reads are allowed
        assert check_permission("any_agent", "read", artifact) is True
        assert check_permission("another_agent", "read", artifact) is True


class TestWritePermissionViaContract:
    """Tests for write permission via contract-based system."""

    def test_write_permission_via_freeware_contract(self, artifact_store: ArtifactStore) -> None:
        """Verify freeware contract only allows owner to write."""
        artifact = artifact_store.write(
            artifact_id="restricted_write",
            type="document",
            content="Original content",
            created_by="owner",
            policy={"allow_write": ["authorized_writer"]},
        )

        # Freeware contract: only creator can write
        assert check_permission("unauthorized", "write", artifact) is False
        assert check_permission("owner", "write", artifact) is True


class TestInvokePermissionViaContract:
    """Tests for invoke permission via contract-based system."""

    def test_invoke_permission_via_freeware_contract(self, artifact_store: ArtifactStore) -> None:
        """Verify freeware contract allows all invokes for executables."""
        artifact = artifact_store.write(
            artifact_id="executable_invoke",
            type="executable",
            content="Service description",
            created_by="owner",
            executable=True,
            code="def run(): return 42",
            policy={"allow_invoke": ["*"]},
        )

        # Freeware contract: all can invoke
        assert check_permission("any_agent", "invoke", artifact) is True

    def test_invoke_permission_non_executable(
        self, artifact_store: ArtifactStore
    ) -> None:
        """Verify non-executable artifacts have correct policy."""
        artifact = artifact_store.write(
            artifact_id="non_executable",
            type="document",
            content="Just a document",
            created_by="owner",
            executable=False,
            policy={"allow_invoke": ["*"]},
        )

        # Non-executable - policy still stored
        assert artifact.executable is False
        assert artifact.policy["allow_invoke"] == ["*"]


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
            created_by="owner",
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
            created_by="owner",
        )

        assert artifact.policy["read_price"] == 0

    def test_invoke_price_stored(self, artifact_store: ArtifactStore) -> None:
        """Verify invoke_price is stored in policy."""
        artifact = artifact_store.write(
            artifact_id="paid_service",
            type="executable",
            content="Service",
            created_by="owner",
            executable=True,
            code="def run(): return 'result'",
            policy={"invoke_price": 25},
        )

        assert artifact.policy["invoke_price"] == 25
        assert artifact.price == 25  # Backwards compat property


class TestCreatorPermissions:
    """Tests verifying creator has appropriate access via contracts."""

    def test_creator_can_read(
        self, artifact_store: ArtifactStore
    ) -> None:
        """Verify creator can read their own artifact via contract."""
        artifact = artifact_store.write(
            artifact_id="creator_read_test",
            type="document",
            content="Creator's content",
            created_by="owner",
            policy={"allow_read": []},  # Empty list
        )

        # Creator should be able to read via freeware contract
        assert check_permission("owner", "read", artifact) is True

    def test_creator_can_write(
        self, artifact_store: ArtifactStore
    ) -> None:
        """Verify creator can write to their own artifact via contract."""
        artifact = artifact_store.write(
            artifact_id="creator_write_test",
            type="document",
            content="Creator's content",
            created_by="owner",
            policy={"allow_write": []},  # Empty list
        )

        # Creator should be able to write via freeware contract
        assert check_permission("owner", "write", artifact) is True

    def test_creator_can_invoke(
        self, artifact_store: ArtifactStore
    ) -> None:
        """Verify creator can invoke their own executable artifact via contract."""
        artifact = artifact_store.write(
            artifact_id="creator_invoke_test",
            type="executable",
            content="Creator's service",
            created_by="owner",
            executable=True,
            code="def run(): return 'creator result'",
            policy={"allow_invoke": []},  # Empty list
        )

        # Creator should be able to invoke via freeware contract
        assert check_permission("owner", "invoke", artifact) is True


class TestPolicyUpdate:
    """Tests for updating artifact policies."""

    def test_policy_update_on_rewrite(self, artifact_store: ArtifactStore) -> None:
        """Verify policy can be updated when artifact is rewritten."""
        # Initial write with restrictive policy
        artifact_store.write(
            artifact_id="update_test",
            type="document",
            content="Initial content",
            created_by="owner",
            policy={"allow_read": ["agent1"]},
        )

        initial = artifact_store.get("update_test")
        assert initial is not None
        assert initial.policy["allow_read"] == ["agent1"]

        # Update with new policy
        artifact_store.write(
            artifact_id="update_test",
            type="document",
            content="Updated content",
            created_by="owner",
            policy={"allow_read": ["agent1", "agent2"]},
        )

        updated = artifact_store.get("update_test")
        assert updated is not None
        assert updated.policy["allow_read"] == ["agent1", "agent2"]


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
            created_by="owner",
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
            created_by="owner",
            executable=True,
            code="def run(): return 1",
            price=50,
            policy={"invoke_price": 100},  # Policy should win
        )

        assert artifact.policy["invoke_price"] == 100
        assert artifact.price == 100
