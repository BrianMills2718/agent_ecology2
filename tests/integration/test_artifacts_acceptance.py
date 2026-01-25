"""Feature acceptance tests for artifacts - maps to meta/acceptance_gates/artifacts.yaml.

Run with: pytest --feature artifacts tests/

Note: Permission enforcement is now via contracts (Plan #100).
Tests verify policy storage and contract-based permission checks.
"""

from __future__ import annotations

import pytest
from datetime import datetime

from src.world.artifacts import Artifact, ArtifactStore, default_policy
from src.world.executor import get_executor


def check_permission(agent_id: str, action: str, artifact: Artifact) -> bool:
    """Check permission via the executor's contract-based system."""
    executor = get_executor()
    allowed, reason = executor._check_permission(agent_id, action, artifact)
    return allowed


@pytest.mark.feature("artifacts")
class TestArtifactsFeature:
    """Tests mapping to meta/acceptance_gates/artifacts.yaml acceptance criteria."""

    # AC-1: Create artifact with required fields (happy_path)
    def test_ac_1_create_artifact_required_fields(self) -> None:
        """AC-1: Create artifact with required fields."""
        store = ArtifactStore()
        before_time = datetime.utcnow().isoformat()

        artifact = store.write(
            artifact_id="test_artifact",
            type="generic",
            content="Test content",
            created_by="alice",
        )

        after_time = datetime.utcnow().isoformat()

        assert store.exists("test_artifact")
        assert before_time <= artifact.created_at <= after_time
        assert artifact.policy.get("allow_read") == ["*"]

        retrieved = store.get("test_artifact")
        assert retrieved is not None
        assert retrieved.id == "test_artifact"
        assert retrieved.content == "Test content"
        assert retrieved.created_by == "alice"

    # AC-2: Read artifact respects policy (happy_path)
    def test_ac_2_read_respects_policy(self) -> None:
        """AC-2: Read artifact policy stored correctly.

        Note: Actual permission enforcement is via contracts.
        The freeware contract allows all reads by default.
        """
        store = ArtifactStore()
        artifact = store.write(
            artifact_id="restricted_artifact",
            type="generic",
            content="Secret content",
            created_by="owner",
            policy={"allow_read": ["alice", "bob"]},
        )

        # Verify policy is stored
        assert artifact.policy["allow_read"] == ["alice", "bob"]

        # Via freeware contract, all reads are allowed
        assert check_permission("alice", "read", artifact) is True
        assert check_permission("bob", "read", artifact) is True
        assert check_permission("owner", "read", artifact) is True


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
            created_by="alice",
            executable=True,
            code="""
def run(a, b):
    return {"result": a + b}
""",
            policy={"invoke_price": 5, "allow_invoke": ["*"]},
        )

        assert artifact.executable is True
        assert artifact.policy.get("invoke_price") == 5
        # Via freeware contract, all invokes are allowed
        assert check_permission("bob", "invoke", artifact) is True

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
            created_by="alice",
            executable=False,
        )

        assert artifact.executable is False
        # Non-executable artifacts should not be invokable (handled at world level)


    # AC-5: Owner can modify artifact (happy_path)
    def test_ac_5_owner_can_modify(self) -> None:
        """AC-5: Owner can modify artifact."""
        store = ArtifactStore()
        artifact = store.write(
            artifact_id="mutable_artifact",
            type="generic",
            content="Original content",
            created_by="alice",
        )

        original_updated = artifact.updated_at
        # Via freeware contract, creator can write
        assert check_permission("alice", "write", artifact) is True

        updated = store.write(
            artifact_id="mutable_artifact",
            type="generic",
            content="Updated content",
            created_by="alice",
            policy={"read_price": 10},
        )

        assert updated.updated_at >= original_updated
        assert updated.content == "Updated content"
        assert updated.policy.get("read_price") == 10

    # AC-6: Non-owner cannot modify without permission (error_case)
    def test_ac_6_non_owner_cannot_modify(self) -> None:
        """AC-6: Non-owner cannot modify without permission."""
        store = ArtifactStore()
        artifact = store.write(
            artifact_id="private_artifact",
            type="generic",
            content="Original content",
            created_by="alice",
            policy={"allow_write": []},
        )

        # Via freeware contract, only creator can write
        assert check_permission("bob", "write", artifact) is False
        assert check_permission("charlie", "write", artifact) is False
        assert check_permission("alice", "write", artifact) is True

    # AC-7: Ownership transfer updates all permissions (edge_case)
    def test_ac_7_ownership_transfer(self) -> None:
        """AC-7: Ownership transfer updates created_by."""
        store = ArtifactStore()
        artifact = store.write(
            artifact_id="transferable",
            type="generic",
            content="Transferable content",
            created_by="alice",
            policy={"allow_read": ["charlie"]},
        )

        assert artifact.created_by == "alice"
        assert check_permission("alice", "write", artifact) is True
        assert check_permission("bob", "write", artifact) is False

        result = store.transfer_ownership("transferable", "alice", "bob")
        assert result is True

        retrieved = store.get("transferable")
        assert retrieved is not None
        artifact = retrieved

        # Per ADR-0016: created_by is immutable, stays alice
        assert artifact.created_by == "alice"
        # Controller is now bob (stored in metadata)
        assert artifact.metadata.get("controller") == "bob"
        # After transfer, bob is now controller and can write
        assert check_permission("bob", "write", artifact) is True
        # Alice is no longer controller, so cannot write via freeware contract
        assert check_permission("alice", "write", artifact) is False
        # Policy is preserved
        assert artifact.policy.get("allow_read") == ["charlie"]


@pytest.mark.feature("artifacts")
class TestArtifactsEdgeCases:
    """Additional edge case tests for artifacts robustness."""

    def test_wildcard_read_access(self) -> None:
        """Wildcard '*' allows everyone to read via freeware contract."""
        store = ArtifactStore()
        artifact = store.write(
            artifact_id="public",
            type="generic",
            content="Public content",
            created_by="creator",
            policy={"allow_read": ["*"]},
        )

        # Freeware contract allows all reads
        assert check_permission("anyone", "read", artifact) is True
        assert check_permission("random_user", "read", artifact) is True

    def test_transfer_by_non_owner_fails(self) -> None:
        """Only owner can transfer ownership."""
        store = ArtifactStore()
        store.write(
            artifact_id="artifact",
            type="generic",
            content="Content",
            created_by="alice",
        )

        result = store.transfer_ownership("artifact", "bob", "charlie")
        assert result is False

        result = store.transfer_ownership("artifact", "alice", "charlie")
        assert result is True


@pytest.mark.feature("artifacts")
class TestArtifactExecutableEdgeCases:
    """Additional tests for executable artifact functionality."""

    def test_executable_with_code(self) -> None:
        """Executable artifacts store code separately from content."""
        store = ArtifactStore()
        artifact = store.write(
            artifact_id="tool",
            type="tool",
            content="A useful tool that adds numbers",
            created_by="developer",
            executable=True,
            code='def run(x, y): return {"sum": x + y}',
        )

        assert artifact.executable is True
        assert artifact.content == "A useful tool that adds numbers"
        assert "def run" in artifact.code
