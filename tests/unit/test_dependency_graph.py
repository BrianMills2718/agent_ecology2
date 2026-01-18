"""Unit tests for artifact dependency graph construction and metrics.

Tests for Plan #64: Artifact Dependency Graph Visualization.
"""

import pytest
from datetime import datetime, timedelta

from src.dashboard.models import (
    DependencyNode,
    DependencyEdge,
    DependencyGraphData,
    DependencyGraphMetrics,
)
from src.dashboard.dependency_graph import (
    build_dependency_graph,
    compute_graph_metrics,
)


class TestDependencyGraphModels:
    """Test Pydantic models for dependency graph."""

    def test_dependency_node_creation(self) -> None:
        """Test DependencyNode model creation."""
        node = DependencyNode(
            artifact_id="test_artifact",
            name="test_artifact",
            owner="alice",
            artifact_type="code",
            is_genesis=False,
            usage_count=5,
            created_at=datetime.now(),
            depth=2,
        )
        assert node.artifact_id == "test_artifact"
        assert node.owner == "alice"
        assert node.is_genesis is False
        assert node.usage_count == 5
        assert node.depth == 2

    def test_dependency_node_genesis(self) -> None:
        """Test genesis artifact node."""
        node = DependencyNode(
            artifact_id="genesis_ledger",
            name="genesis_ledger",
            owner="system",
            artifact_type="genesis",
            is_genesis=True,
            usage_count=100,
            created_at=datetime.now(),
            depth=0,
        )
        assert node.is_genesis is True
        assert node.depth == 0

    def test_dependency_edge_creation(self) -> None:
        """Test DependencyEdge model creation."""
        edge = DependencyEdge(
            source="child_artifact",
            target="parent_artifact",
        )
        assert edge.source == "child_artifact"
        assert edge.target == "parent_artifact"

    def test_dependency_graph_metrics(self) -> None:
        """Test DependencyGraphMetrics model."""
        metrics = DependencyGraphMetrics(
            max_depth=3,
            avg_fanout=2.5,
            genesis_dependency_ratio=0.4,
            orphan_count=2,
            total_nodes=10,
            total_edges=15,
        )
        assert metrics.max_depth == 3
        assert metrics.avg_fanout == 2.5
        assert metrics.genesis_dependency_ratio == 0.4
        assert metrics.orphan_count == 2

    def test_dependency_graph_data(self) -> None:
        """Test DependencyGraphData model."""
        node = DependencyNode(
            artifact_id="test",
            name="test",
            owner="alice",
            artifact_type="code",
            is_genesis=False,
            usage_count=1,
            created_at=datetime.now(),
            depth=0,
        )
        edge = DependencyEdge(source="a", target="b")
        metrics = DependencyGraphMetrics(
            max_depth=0,
            avg_fanout=0.0,
            genesis_dependency_ratio=0.0,
            orphan_count=1,
            total_nodes=1,
            total_edges=0,
        )
        graph = DependencyGraphData(
            nodes=[node],
            edges=[edge],
            metrics=metrics,
        )
        assert len(graph.nodes) == 1
        assert len(graph.edges) == 1
        assert graph.metrics.total_nodes == 1


class TestDependencyGraphMetrics:
    """Test graph metrics calculations."""

    def test_empty_graph_metrics(self) -> None:
        """Empty graph should have zero metrics."""
        metrics = compute_graph_metrics(nodes=[], edges=[])
        assert metrics.max_depth == 0
        assert metrics.avg_fanout == 0.0
        assert metrics.genesis_dependency_ratio == 0.0
        assert metrics.orphan_count == 0
        assert metrics.total_nodes == 0
        assert metrics.total_edges == 0

    def test_single_node_metrics(self) -> None:
        """Single node with no edges."""
        node = DependencyNode(
            artifact_id="alone",
            name="alone",
            owner="alice",
            artifact_type="code",
            is_genesis=False,
            usage_count=0,
            created_at=datetime.now(),
            depth=0,
        )
        metrics = compute_graph_metrics(nodes=[node], edges=[])
        assert metrics.max_depth == 0
        assert metrics.orphan_count == 1  # No dependents = orphan
        assert metrics.total_nodes == 1

    def test_chain_depth_calculation(self) -> None:
        """Test depth calculation for a chain: A -> B -> C."""
        now = datetime.now()
        nodes = [
            DependencyNode(
                artifact_id="A",
                name="A",
                owner="alice",
                artifact_type="code",
                is_genesis=False,
                usage_count=2,
                created_at=now,
                depth=0,
            ),
            DependencyNode(
                artifact_id="B",
                name="B",
                owner="bob",
                artifact_type="code",
                is_genesis=False,
                usage_count=1,
                created_at=now,
                depth=1,
            ),
            DependencyNode(
                artifact_id="C",
                name="C",
                owner="charlie",
                artifact_type="code",
                is_genesis=False,
                usage_count=0,
                created_at=now,
                depth=2,
            ),
        ]
        edges = [
            DependencyEdge(source="B", target="A"),  # B depends on A
            DependencyEdge(source="C", target="B"),  # C depends on B
        ]
        metrics = compute_graph_metrics(nodes=nodes, edges=edges)
        assert metrics.max_depth == 2
        assert metrics.total_edges == 2

    def test_genesis_dependency_ratio(self) -> None:
        """Test ratio of genesis deps to total deps."""
        now = datetime.now()
        nodes = [
            DependencyNode(
                artifact_id="genesis_ledger",
                name="genesis_ledger",
                owner="system",
                artifact_type="genesis",
                is_genesis=True,
                usage_count=3,
                created_at=now,
                depth=0,
            ),
            DependencyNode(
                artifact_id="user_lib",
                name="user_lib",
                owner="alice",
                artifact_type="code",
                is_genesis=False,
                usage_count=2,
                created_at=now,
                depth=1,
            ),
            DependencyNode(
                artifact_id="app",
                name="app",
                owner="bob",
                artifact_type="code",
                is_genesis=False,
                usage_count=0,
                created_at=now,
                depth=2,
            ),
        ]
        # app depends on user_lib and genesis_ledger
        # user_lib depends on genesis_ledger
        edges = [
            DependencyEdge(source="user_lib", target="genesis_ledger"),
            DependencyEdge(source="app", target="genesis_ledger"),
            DependencyEdge(source="app", target="user_lib"),
        ]
        metrics = compute_graph_metrics(nodes=nodes, edges=edges)
        # 2 edges point to genesis, 3 total edges
        assert metrics.genesis_dependency_ratio == pytest.approx(2 / 3)

    def test_orphan_count(self) -> None:
        """Orphans are artifacts with no dependents (nothing depends on them)."""
        now = datetime.now()
        nodes = [
            DependencyNode(
                artifact_id="root",
                name="root",
                owner="alice",
                artifact_type="code",
                is_genesis=False,
                usage_count=1,
                created_at=now,
                depth=0,
            ),
            DependencyNode(
                artifact_id="leaf1",
                name="leaf1",
                owner="bob",
                artifact_type="code",
                is_genesis=False,
                usage_count=0,
                created_at=now,
                depth=1,
            ),
            DependencyNode(
                artifact_id="leaf2",
                name="leaf2",
                owner="charlie",
                artifact_type="code",
                is_genesis=False,
                usage_count=0,
                created_at=now,
                depth=1,
            ),
        ]
        edges = [
            DependencyEdge(source="leaf1", target="root"),
            DependencyEdge(source="leaf2", target="root"),
        ]
        metrics = compute_graph_metrics(nodes=nodes, edges=edges)
        # leaf1 and leaf2 are orphans (nothing depends on them)
        assert metrics.orphan_count == 2

    def test_avg_fanout(self) -> None:
        """Average fanout = mean children per node."""
        now = datetime.now()
        nodes = [
            DependencyNode(
                artifact_id="root",
                name="root",
                owner="alice",
                artifact_type="code",
                is_genesis=False,
                usage_count=2,
                created_at=now,
                depth=0,
            ),
            DependencyNode(
                artifact_id="child1",
                name="child1",
                owner="bob",
                artifact_type="code",
                is_genesis=False,
                usage_count=0,
                created_at=now,
                depth=1,
            ),
            DependencyNode(
                artifact_id="child2",
                name="child2",
                owner="charlie",
                artifact_type="code",
                is_genesis=False,
                usage_count=0,
                created_at=now,
                depth=1,
            ),
        ]
        edges = [
            DependencyEdge(source="child1", target="root"),
            DependencyEdge(source="child2", target="root"),
        ]
        metrics = compute_graph_metrics(nodes=nodes, edges=edges)
        # root has 2 dependents, child1 and child2 have 0
        # avg = (2 + 0 + 0) / 3 = 0.67
        assert metrics.avg_fanout == pytest.approx(2 / 3)


class TestDependencyGraphConstruction:
    """Test graph construction from artifact data."""

    def test_build_empty_graph(self) -> None:
        """Empty artifact list produces empty graph."""
        graph = build_dependency_graph(artifacts=[])
        assert len(graph.nodes) == 0
        assert len(graph.edges) == 0

    def test_build_single_artifact_no_deps(self) -> None:
        """Single artifact with no dependencies."""
        artifact_data = {
            "artifact_id": "lonely",
            "name": "lonely",
            "owner": "alice",
            "artifact_type": "code",
            "depends_on": [],
            "created_at": datetime.now().isoformat(),
        }
        graph = build_dependency_graph(artifacts=[artifact_data])
        assert len(graph.nodes) == 1
        assert len(graph.edges) == 0
        assert graph.nodes[0].artifact_id == "lonely"

    def test_build_with_dependencies(self) -> None:
        """Artifacts with dependencies create edges."""
        now = datetime.now()
        artifacts = [
            {
                "artifact_id": "parent",
                "name": "parent",
                "owner": "alice",
                "artifact_type": "code",
                "depends_on": [],
                "created_at": now.isoformat(),
            },
            {
                "artifact_id": "child",
                "name": "child",
                "owner": "bob",
                "artifact_type": "code",
                "depends_on": ["parent"],
                "created_at": now.isoformat(),
            },
        ]
        graph = build_dependency_graph(artifacts=artifacts)
        assert len(graph.nodes) == 2
        assert len(graph.edges) == 1
        assert graph.edges[0].source == "child"
        assert graph.edges[0].target == "parent"

    def test_build_identifies_genesis(self) -> None:
        """Genesis artifacts are marked correctly."""
        now = datetime.now()
        artifacts = [
            {
                "artifact_id": "genesis_ledger",
                "name": "genesis_ledger",
                "owner": "system",
                "artifact_type": "genesis",
                "depends_on": [],
                "created_at": now.isoformat(),
            },
            {
                "artifact_id": "user_artifact",
                "name": "user_artifact",
                "owner": "alice",
                "artifact_type": "code",
                "depends_on": ["genesis_ledger"],
                "created_at": now.isoformat(),
            },
        ]
        graph = build_dependency_graph(artifacts=artifacts)
        genesis_node = next(n for n in graph.nodes if n.artifact_id == "genesis_ledger")
        user_node = next(n for n in graph.nodes if n.artifact_id == "user_artifact")
        assert genesis_node.is_genesis is True
        assert user_node.is_genesis is False

    def test_build_calculates_depth(self) -> None:
        """Depth is calculated from root artifacts."""
        now = datetime.now()
        artifacts = [
            {
                "artifact_id": "root",
                "name": "root",
                "owner": "alice",
                "artifact_type": "code",
                "depends_on": [],
                "created_at": now.isoformat(),
            },
            {
                "artifact_id": "level1",
                "name": "level1",
                "owner": "bob",
                "artifact_type": "code",
                "depends_on": ["root"],
                "created_at": now.isoformat(),
            },
            {
                "artifact_id": "level2",
                "name": "level2",
                "owner": "charlie",
                "artifact_type": "code",
                "depends_on": ["level1"],
                "created_at": now.isoformat(),
            },
        ]
        graph = build_dependency_graph(artifacts=artifacts)
        root_node = next(n for n in graph.nodes if n.artifact_id == "root")
        level1_node = next(n for n in graph.nodes if n.artifact_id == "level1")
        level2_node = next(n for n in graph.nodes if n.artifact_id == "level2")
        assert root_node.depth == 0
        assert level1_node.depth == 1
        assert level2_node.depth == 2


class TestEmptyAndEdgeCases:
    """Test edge cases and error handling."""

    def test_missing_dependency_target(self) -> None:
        """Artifact depends on non-existent artifact (dangling reference)."""
        now = datetime.now()
        artifacts = [
            {
                "artifact_id": "orphan_child",
                "name": "orphan_child",
                "owner": "alice",
                "artifact_type": "code",
                "depends_on": ["non_existent"],
                "created_at": now.isoformat(),
            },
        ]
        # Should handle gracefully - edge points to missing node
        graph = build_dependency_graph(artifacts=artifacts)
        assert len(graph.nodes) == 1
        # Edge to missing target should be omitted or handled
        assert len(graph.edges) == 0  # Dangling refs are filtered out

    def test_circular_dependency(self) -> None:
        """Circular dependencies don't cause infinite loops."""
        now = datetime.now()
        artifacts = [
            {
                "artifact_id": "A",
                "name": "A",
                "owner": "alice",
                "artifact_type": "code",
                "depends_on": ["B"],
                "created_at": now.isoformat(),
            },
            {
                "artifact_id": "B",
                "name": "B",
                "owner": "bob",
                "artifact_type": "code",
                "depends_on": ["A"],
                "created_at": now.isoformat(),
            },
        ]
        # Should complete without hanging
        graph = build_dependency_graph(artifacts=artifacts)
        assert len(graph.nodes) == 2
        assert len(graph.edges) == 2

    def test_self_dependency(self) -> None:
        """Artifact depends on itself."""
        now = datetime.now()
        artifacts = [
            {
                "artifact_id": "narcissist",
                "name": "narcissist",
                "owner": "alice",
                "artifact_type": "code",
                "depends_on": ["narcissist"],
                "created_at": now.isoformat(),
            },
        ]
        graph = build_dependency_graph(artifacts=artifacts)
        assert len(graph.nodes) == 1
        # Self-edges should be filtered or handled
        assert len(graph.edges) == 0  # Self-refs are filtered

    def test_lindy_score_in_node(self) -> None:
        """Nodes include Lindy score (age × unique_invokers)."""
        now = datetime.now()
        created_30_days_ago = now - timedelta(days=30)
        artifact_data = {
            "artifact_id": "mature_lib",
            "name": "mature_lib",
            "owner": "alice",
            "artifact_type": "code",
            "depends_on": [],
            "created_at": created_30_days_ago.isoformat(),
            "unique_invokers": 5,
        }
        graph = build_dependency_graph(artifacts=[artifact_data])
        node = graph.nodes[0]
        # Lindy score = age_in_days × unique_invokers
        # 30 days × 5 invokers = 150
        assert hasattr(node, "lindy_score")
        assert node.lindy_score == pytest.approx(150, rel=0.1)
