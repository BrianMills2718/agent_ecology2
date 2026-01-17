"""
Tests for Plan #63: Artifact Dependencies (Composition)

TDD tests for the depends_on field and validation logic.
These tests define the expected behavior - implementation follows.
"""

import pytest
from datetime import datetime

from src.world.artifacts import Artifact, ArtifactStore


@pytest.mark.plans([63])
class TestArtifactDependsOnField:
    """Tests for the depends_on field on Artifact dataclass."""

    def test_depends_on_field_exists(self) -> None:
        """Artifact dataclass should have a depends_on field (list of artifact IDs)."""
        now = datetime.utcnow().isoformat()
        artifact = Artifact(
            id="test_artifact",
            type="service",
            content="test content",
            owner_id="test_owner",
            created_at=now,
            updated_at=now,
        )

        # depends_on should exist and default to empty list
        assert hasattr(artifact, "depends_on"), "Artifact should have depends_on field"
        assert artifact.depends_on == [], "depends_on should default to empty list"

    def test_create_artifact_with_dependencies(self) -> None:
        """Should be able to create artifact with depends_on set."""
        now = datetime.utcnow().isoformat()
        artifact = Artifact(
            id="pipeline",
            type="service",
            content="pipeline code",
            owner_id="test_owner",
            created_at=now,
            updated_at=now,
            depends_on=["helper_lib", "data_processor"],
        )

        assert artifact.depends_on == ["helper_lib", "data_processor"]

    def test_depends_on_included_in_to_dict(self) -> None:
        """depends_on should be included in to_dict() when non-empty."""
        now = datetime.utcnow().isoformat()
        artifact = Artifact(
            id="pipeline",
            type="service",
            content="test",
            owner_id="owner",
            created_at=now,
            updated_at=now,
            depends_on=["helper"],
        )

        result = artifact.to_dict()
        assert "depends_on" in result
        assert result["depends_on"] == ["helper"]

    def test_depends_on_not_in_dict_when_empty(self) -> None:
        """depends_on should not clutter to_dict() when empty."""
        now = datetime.utcnow().isoformat()
        artifact = Artifact(
            id="simple",
            type="data",
            content="test",
            owner_id="owner",
            created_at=now,
            updated_at=now,
            depends_on=[],
        )

        result = artifact.to_dict()
        # Empty depends_on should not be included (like other optional fields)
        assert "depends_on" not in result


@pytest.mark.plans([63])
class TestArtifactStoreWithDependencies:
    """Tests for ArtifactStore handling depends_on."""

    @pytest.fixture
    def store(self) -> ArtifactStore:
        """Create empty artifact store."""
        return ArtifactStore()

    @pytest.fixture
    def store_with_helper(self, store: ArtifactStore) -> ArtifactStore:
        """Store with a helper artifact pre-created."""
        store.write(
            artifact_id="helper_lib",
            type="library",
            content="def helper(): return 42",
            owner_id="alice",
            executable=True,
            code="def run(): return 42",
        )
        return store

    def test_write_artifact_with_valid_dependency(
        self, store_with_helper: ArtifactStore
    ) -> None:
        """Should successfully create artifact when dependency exists."""
        artifact = store_with_helper.write(
            artifact_id="pipeline",
            type="service",
            content="pipeline using helper",
            owner_id="alice",
            executable=True,
            code="def run(args, context): return context.dependencies['helper_lib'].invoke()",
            depends_on=["helper_lib"],
        )

        assert artifact.depends_on == ["helper_lib"]

    def test_missing_dependency_rejected(self, store: ArtifactStore) -> None:
        """Creating artifact with non-existent dependency should fail."""
        with pytest.raises(ValueError, match="Dependency 'nonexistent' does not exist"):
            store.write(
                artifact_id="pipeline",
                type="service",
                content="broken pipeline",
                owner_id="alice",
                depends_on=["nonexistent"],
            )


@pytest.mark.plans([63])
class TestCycleDetection:
    """Tests for cycle detection at artifact creation."""

    @pytest.fixture
    def store(self) -> ArtifactStore:
        """Create artifact store."""
        return ArtifactStore()

    def test_cycle_detection_direct_self_reference(self, store: ArtifactStore) -> None:
        """A→A: Artifact cannot depend on itself."""
        with pytest.raises(ValueError, match="Cycle detected"):
            store.write(
                artifact_id="self_loop",
                type="service",
                content="broken",
                owner_id="alice",
                depends_on=["self_loop"],  # Self-reference
            )

    def test_cycle_detection_indirect_two_nodes(self, store: ArtifactStore) -> None:
        """A→B→A: Two-node cycle should be detected."""
        # Create A first (no deps)
        store.write(
            artifact_id="artifact_a",
            type="service",
            content="a",
            owner_id="alice",
        )

        # Create B depending on A
        store.write(
            artifact_id="artifact_b",
            type="service",
            content="b",
            owner_id="alice",
            depends_on=["artifact_a"],
        )

        # Now update A to depend on B - this creates cycle A→B→A
        with pytest.raises(ValueError, match="Cycle detected"):
            store.write(
                artifact_id="artifact_a",
                type="service",
                content="a updated",
                owner_id="alice",
                depends_on=["artifact_b"],
            )

    def test_cycle_detection_indirect_three_nodes(self, store: ArtifactStore) -> None:
        """A→B→C→A: Three-node cycle should be detected."""
        # Create A, B, C without cycles
        store.write(
            artifact_id="a",
            type="service",
            content="a",
            owner_id="alice",
        )
        store.write(
            artifact_id="b",
            type="service",
            content="b",
            owner_id="alice",
            depends_on=["a"],
        )
        store.write(
            artifact_id="c",
            type="service",
            content="c",
            owner_id="alice",
            depends_on=["b"],
        )

        # Update A to depend on C - creates cycle
        with pytest.raises(ValueError, match="Cycle detected"):
            store.write(
                artifact_id="a",
                type="service",
                content="a updated",
                owner_id="alice",
                depends_on=["c"],
            )

    def test_valid_dag_allowed(self, store: ArtifactStore) -> None:
        """Valid DAG (diamond pattern) should be allowed."""
        # Create diamond: A→B, A→C, B→D, C→D
        #   A
        #  / \
        # B   C
        #  \ /
        #   D

        store.write(artifact_id="d", type="s", content="d", owner_id="alice")
        store.write(
            artifact_id="b", type="s", content="b", owner_id="alice", depends_on=["d"]
        )
        store.write(
            artifact_id="c", type="s", content="c", owner_id="alice", depends_on=["d"]
        )
        # A depends on both B and C (diamond pattern - valid)
        artifact_a = store.write(
            artifact_id="a", type="s", content="a", owner_id="alice", depends_on=["b", "c"]
        )

        assert artifact_a.depends_on == ["b", "c"]


@pytest.mark.plans([63])
class TestDepthLimit:
    """Tests for dependency depth limit enforcement."""

    @pytest.fixture
    def store(self) -> ArtifactStore:
        """Create artifact store."""
        return ArtifactStore()

    def test_depth_limit_enforced(self, store: ArtifactStore) -> None:
        """Creating chain exceeding depth limit should fail."""
        # Default depth limit is 10 (from config)
        # Create chain: a1 → a2 → a3 → ... → a11 (depth 10)

        # Build chain up to depth 10 (should succeed)
        store.write(artifact_id="a1", type="s", content="1", owner_id="alice")
        for i in range(2, 11):
            store.write(
                artifact_id=f"a{i}",
                type="s",
                content=str(i),
                owner_id="alice",
                depends_on=[f"a{i-1}"],
            )

        # Adding a11 depending on a10 would exceed depth limit
        with pytest.raises(ValueError, match="Dependency depth limit"):
            store.write(
                artifact_id="a11",
                type="s",
                content="11",
                owner_id="alice",
                depends_on=["a10"],
            )

    def test_depth_within_limit_allowed(self, store: ArtifactStore) -> None:
        """Chain within depth limit should be allowed."""
        # Create short chain: a → b → c (depth 2)
        store.write(artifact_id="a", type="s", content="a", owner_id="alice")
        store.write(
            artifact_id="b", type="s", content="b", owner_id="alice", depends_on=["a"]
        )
        artifact_c = store.write(
            artifact_id="c", type="s", content="c", owner_id="alice", depends_on=["b"]
        )

        assert artifact_c.depends_on == ["b"]


@pytest.mark.plans([63])
class TestGenesisAsDependency:
    """Tests for using genesis artifacts as dependencies."""

    @pytest.fixture
    def store_with_genesis(self) -> ArtifactStore:
        """Store with genesis artifacts."""
        store = ArtifactStore()
        # Simulate genesis artifacts (normally created by genesis.py)
        store.write(
            artifact_id="genesis_ledger",
            type="genesis",
            content="ledger service",
            owner_id="system",
            executable=True,
        )
        store.write(
            artifact_id="genesis_store",
            type="genesis",
            content="store service",
            owner_id="system",
            executable=True,
        )
        return store

    def test_genesis_as_dependency_allowed(
        self, store_with_genesis: ArtifactStore
    ) -> None:
        """Should be able to depend on genesis artifacts."""
        artifact = store_with_genesis.write(
            artifact_id="my_service",
            type="service",
            content="service using genesis",
            owner_id="alice",
            executable=True,
            code="def run(args, context): return context.dependencies['genesis_ledger'].invoke('get_balance')",
            depends_on=["genesis_ledger"],
        )

        assert "genesis_ledger" in artifact.depends_on

    def test_multiple_genesis_dependencies(
        self, store_with_genesis: ArtifactStore
    ) -> None:
        """Can depend on multiple genesis artifacts."""
        artifact = store_with_genesis.write(
            artifact_id="multi_service",
            type="service",
            content="service using multiple genesis",
            owner_id="alice",
            depends_on=["genesis_ledger", "genesis_store"],
        )

        assert artifact.depends_on == ["genesis_ledger", "genesis_store"]
