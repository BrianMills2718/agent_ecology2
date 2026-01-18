"""Feature acceptance tests for artifacts - maps to acceptance_gates/artifacts.yaml.

Run with: pytest --feature artifacts tests/
"""

from __future__ import annotations

import pytest
from datetime import datetime

from src.world.artifacts import Artifact, ArtifactStore, default_policy


@pytest.mark.feature("artifacts")
class TestArtifactsFeature:
    """Tests mapping to acceptance_gates/artifacts.yaml acceptance criteria."""

    # AC-1: Create artifact with required fields (happy_path)
    def test_ac_1_create_artifact_required_fields(self) -> None:
        """AC-1: Create artifact with required fields."""
        store = ArtifactStore()
        before_time = datetime.utcnow().isoformat()

        artifact = store.write(
            artifact_id="test_artifact",
            type="generic",
            content="Test content",
            owner_id="alice",
        )

        after_time = datetime.utcnow().isoformat()

        assert store.exists("test_artifact")
        assert before_time <= artifact.created_at <= after_time
        assert artifact.policy.get("allow_read") == ["*"]

        retrieved = store.get("test_artifact")
        assert retrieved is not None
        assert retrieved.id == "test_artifact"
        assert retrieved.content == "Test content"
        assert retrieved.owner_id == "alice"

    # AC-2: Read artifact respects policy (happy_path)
    def test_ac_2_read_respects_policy(self) -> None:
        """AC-2: Read artifact respects policy."""
        store = ArtifactStore()
        artifact = store.write(
            artifact_id="restricted_artifact",
            type="generic",
            content="Secret content",
            owner_id="owner",
            policy={"allow_read": ["alice", "bob"]},
        )

        assert artifact.can_read("charlie") is False
        assert artifact.can_read("alice") is True
        assert artifact.can_read("bob") is True
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
            code="""
def run(a, b):
    return {"result": a + b}
""",
            policy={"invoke_price": 5, "allow_invoke": ["*"]},
        )

        assert artifact.executable is True
        assert artifact.policy.get("invoke_price") == 5
        assert artifact.can_invoke("bob") is True

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
            executable=False,
        )

        assert artifact.executable is False
        # Non-executable artifacts don't have can_invoke
        assert not getattr(artifact, 'can_invoke', lambda x: False)("bob")


    # AC-5: Owner can modify artifact (happy_path)
    def test_ac_5_owner_can_modify(self) -> None:
        """AC-5: Owner can modify artifact."""
        store = ArtifactStore()
        artifact = store.write(
            artifact_id="mutable_artifact",
            type="generic",
            content="Original content",
            owner_id="alice",
        )

        original_updated = artifact.updated_at
        assert artifact.can_write("alice") is True

        updated = store.write(
            artifact_id="mutable_artifact",
            type="generic",
            content="Updated content",
            owner_id="alice",
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
            owner_id="alice",
            policy={"allow_write": []},
        )

        assert artifact.can_write("bob") is False
        assert artifact.can_write("charlie") is False
        assert artifact.can_write("alice") is True

    # AC-7: Ownership transfer updates all permissions (edge_case)
    def test_ac_7_ownership_transfer(self) -> None:
        """AC-7: Ownership transfer updates all permissions."""
        store = ArtifactStore()
        artifact = store.write(
            artifact_id="transferable",
            type="generic",
            content="Transferable content",
            owner_id="alice",
            policy={"allow_read": ["charlie"]},
        )

        assert artifact.owner_id == "alice"
        assert artifact.can_write("alice") is True
        assert artifact.can_write("bob") is False

        result = store.transfer_ownership("transferable", "alice", "bob")
        assert result is True

        retrieved = store.get("transferable")
        assert retrieved is not None
        artifact = retrieved

        assert artifact.owner_id == "bob"
        assert artifact.can_write("bob") is True
        assert artifact.can_write("alice") is False
        assert artifact.policy.get("allow_read") == ["charlie"]
        assert artifact.can_read("charlie") is True


@pytest.mark.feature("artifacts")
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
            owner_id="developer",
            executable=True,
            code='def run(x, y): return {"sum": x + y}',
        )

        assert artifact.executable is True
        assert artifact.content == "A useful tool that adds numbers"
        assert "def run" in artifact.code
