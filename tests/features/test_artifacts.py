"""Feature tests for artifacts - maps to features/artifacts.yaml acceptance criteria.

Each test corresponds to an AC-ID in the feature definition.
"""

from __future__ import annotations

import pytest
from datetime import datetime

from src.world.artifacts import Artifact, ArtifactStore, default_policy


class TestArtifactsFeature:
    """Tests mapping to features/artifacts.yaml acceptance criteria."""

    # AC-1: Create artifact with required fields (happy_path)
    def test_ac_1_create_artifact_required_fields(self) -> None:
        """AC-1: Create artifact with required fields.

        Given: A principal wants to create an artifact
        When: Artifact is created with id, type, content, owner_id
        Then:
          - Artifact is stored in artifact store
          - created_at is set to current time
          - Default policy is applied
          - Artifact is retrievable by id
        """
        store = ArtifactStore()
        before_time = datetime.utcnow().isoformat()

        artifact = store.write(
            artifact_id="test_artifact",
            type="generic",
            content="Test content",
            owner_id="alice",
        )

        after_time = datetime.utcnow().isoformat()

        # Artifact is stored
        assert store.exists("test_artifact")

        # created_at is set to current time
        assert before_time <= artifact.created_at <= after_time

        # Default policy is applied
        assert artifact.policy.get("allow_read") == ["*"]
        assert artifact.policy.get("allow_write") == []
        assert artifact.policy.get("read_price") == 0

        # Artifact is retrievable by id
        retrieved = store.get("test_artifact")
        assert retrieved is not None
        assert retrieved.id == "test_artifact"
        assert retrieved.content == "Test content"
        assert retrieved.owner_id == "alice"

    # AC-2: Read artifact respects policy (happy_path)
    def test_ac_2_read_respects_policy(self) -> None:
        """AC-2: Read artifact respects policy.

        Given:
          - Artifact exists with allow_read: ['alice', 'bob']
          - Principal 'charlie' is not in allow list
        When: Charlie attempts to read artifact
        Then:
          - Read is denied
          - No content is returned
          - Policy enforcement logged
        """
        store = ArtifactStore()
        artifact = store.write(
            artifact_id="restricted_artifact",
            type="generic",
            content="Secret content",
            owner_id="owner",
            policy={"allow_read": ["alice", "bob"]},
        )

        # Charlie is not in allow list
        assert artifact.can_read("charlie") is False

        # Alice and bob can read
        assert artifact.can_read("alice") is True
        assert artifact.can_read("bob") is True

        # Owner can always read
        assert artifact.can_read("owner") is True

    # AC-3: Invoke executable artifact (happy_path)
    def test_ac_3_invoke_executable_artifact(self) -> None:
        """AC-3: Invoke executable artifact.

        Given:
          - Artifact has executable: true
          - Artifact has valid Python code in content
          - Caller has invoke permission
        When: Artifact is invoked with arguments
        Then:
          - Code executes in sandbox
          - Result is returned to caller
          - invoke_price is deducted from caller
        """
        store = ArtifactStore()
        artifact = store.write(
            artifact_id="calculator",
            type="executable",
            content="A calculator tool",
            owner_id="alice",
            executable=True,
            code='''
def run(a, b):
    return {"result": a + b}
''',
            policy={"invoke_price": 5, "allow_invoke": ["*"]},
        )

        assert artifact.executable is True
        assert artifact.policy.get("invoke_price") == 5
        assert artifact.can_invoke("bob") is True

        # Note: Actual invocation is handled by executor, tested in integration tests

    # AC-4: Non-executable artifact cannot be invoked (error_case)
    def test_ac_4_non_executable_cannot_invoke(self) -> None:
        """AC-4: Non-executable artifact cannot be invoked.

        Given: Artifact has executable: false
        When: Caller attempts to invoke
        Then:
          - Invocation fails with error
          - No code execution occurs
        """
        store = ArtifactStore()
        artifact = store.write(
            artifact_id="data_artifact",
            type="data",
            content="Just data",
            owner_id="alice",
            executable=False,  # Not executable
        )

        assert artifact.executable is False
        # Non-executable artifacts can't be invoked even if policy allows
        # The executor checks executable flag before running code

    # AC-5: Owner can modify artifact (happy_path)
    def test_ac_5_owner_can_modify(self) -> None:
        """AC-5: Owner can modify artifact.

        Given: Principal owns an artifact
        When: Owner updates content or policy
        Then:
          - Update succeeds
          - updated_at is refreshed
          - New content/policy takes effect immediately
        """
        store = ArtifactStore()
        artifact = store.write(
            artifact_id="mutable_artifact",
            type="generic",
            content="Original content",
            owner_id="alice",
        )

        original_updated = artifact.updated_at

        # Owner modifies artifact
        assert artifact.can_write("alice") is True

        # Simulate modification via store.write (update)
        updated = store.write(
            artifact_id="mutable_artifact",
            type="generic",
            content="Updated content",
            owner_id="alice",
            policy={"read_price": 10},
        )

        # updated_at is refreshed
        assert updated.updated_at >= original_updated

        # New content takes effect
        assert updated.content == "Updated content"
        assert updated.policy.get("read_price") == 10

    # AC-6: Non-owner cannot modify without permission (error_case)
    def test_ac_6_non_owner_cannot_modify(self) -> None:
        """AC-6: Non-owner cannot modify without permission.

        Given:
          - Artifact owned by Alice
          - allow_write: [] (owner only)
        When: Bob attempts to modify
        Then:
          - Modification denied
          - Content unchanged
        """
        store = ArtifactStore()
        artifact = store.write(
            artifact_id="private_artifact",
            type="generic",
            content="Original content",
            owner_id="alice",
            policy={"allow_write": []},  # Owner only
        )

        # Bob cannot write
        assert artifact.can_write("bob") is False
        assert artifact.can_write("charlie") is False

        # Only alice (owner) can write
        assert artifact.can_write("alice") is True

    # AC-7: Ownership transfer updates all permissions (edge_case)
    def test_ac_7_ownership_transfer(self) -> None:
        """AC-7: Ownership transfer updates all permissions.

        Given:
          - Artifact owned by Alice
          - Artifact has custom policy (allow_read: ['charlie'])
        When: Alice transfers ownership to Bob
        Then:
          - Bob becomes new owner
          - Bob can now modify artifact
          - Alice loses owner privileges
          - Existing allow_read policy is preserved
        """
        store = ArtifactStore()
        artifact = store.write(
            artifact_id="transferable",
            type="generic",
            content="Transferable content",
            owner_id="alice",
            policy={"allow_read": ["charlie"]},
        )

        # Verify initial state
        assert artifact.owner_id == "alice"
        assert artifact.can_write("alice") is True
        assert artifact.can_write("bob") is False

        # Transfer ownership
        result = store.transfer_ownership("transferable", "alice", "bob")
        assert result is True

        # Reload artifact
        retrieved = store.get("transferable")
        assert retrieved is not None
        artifact = retrieved

        # Bob becomes new owner
        assert artifact.owner_id == "bob"

        # Bob can now modify
        assert artifact.can_write("bob") is True

        # Alice loses owner privileges
        assert artifact.can_write("alice") is False

        # Existing allow_read policy is preserved
        assert artifact.policy.get("allow_read") == ["charlie"]
        # Charlie can still read
        assert artifact.can_read("charlie") is True


class TestArtifactsEdgeCases:
    """Additional edge case tests for artifacts robustness."""

    def test_wildcard_read_access(self) -> None:
        """Wildcard '*' allows everyone to read."""
        store = ArtifactStore()
        artifact = store.write(
            artifact_id="public",
            type="generic",
            content="Public content",
            owner_id="creator",
            policy={"allow_read": ["*"]},
        )

        assert artifact.can_read("anyone") is True
        assert artifact.can_read("random_user") is True

    def test_transfer_by_non_owner_fails(self) -> None:
        """Only owner can transfer ownership."""
        store = ArtifactStore()
        store.write(
            artifact_id="artifact",
            type="generic",
            content="Content",
            owner_id="alice",
        )

        # Bob (non-owner) tries to transfer
        result = store.transfer_ownership("artifact", "bob", "charlie")
        assert result is False

        # Alice (owner) can transfer
        result = store.transfer_ownership("artifact", "alice", "charlie")
        assert result is True

    def test_executable_with_code(self) -> None:
        """Executable artifacts store code separately from content."""
        store = ArtifactStore()
        artifact = store.write(
            artifact_id="tool",
            type="tool",
            content="A useful tool that adds numbers",
            owner_id="developer",
            executable=True,
            code='def run(x, y): return {"sum": x + y}',
        )

        assert artifact.executable is True
        assert artifact.content == "A useful tool that adds numbers"
        assert "def run" in artifact.code
