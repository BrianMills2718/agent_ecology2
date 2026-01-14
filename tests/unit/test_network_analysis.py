"""Tests for network analysis metrics."""

import pytest

from src.dashboard.network_analysis import (
    calculate_degree_centrality,
    calculate_betweenness_centrality,
    calculate_clustering_coefficient,
    detect_communities,
)
from src.dashboard.models import Interaction


def make_interaction(from_id: str, to_id: str, tick: int = 1) -> Interaction:
    """Helper to create test interactions."""
    return Interaction(
        interaction_type="scrip_transfer",
        timestamp="2026-01-14T00:00:00Z",
        tick=tick,
        from_id=from_id,
        to_id=to_id,
        artifact_id=None,
        amount=10,
    )


class TestDegreeCentrality:
    """Test degree centrality calculation."""

    def test_empty_interactions(self) -> None:
        """Empty interactions returns empty dict."""
        result = calculate_degree_centrality([])
        assert result == {}

    def test_single_interaction(self) -> None:
        """Single interaction gives both nodes degree 1."""
        interactions = [make_interaction("A", "B")]
        result = calculate_degree_centrality(interactions)
        # Normalized by (n-1) where n=2, so degree 1/(2-1) = 1.0
        assert result["A"] == 1.0
        assert result["B"] == 1.0

    def test_hub_node(self) -> None:
        """Node connected to many others has highest centrality."""
        # A is connected to B, C, D (hub)
        # B, C, D only connected to A
        interactions = [
            make_interaction("A", "B"),
            make_interaction("A", "C"),
            make_interaction("A", "D"),
        ]
        result = calculate_degree_centrality(interactions)
        # A has degree 3, B/C/D have degree 1
        # n=4, so normalized: A=3/3=1.0, others=1/3=0.333
        assert result["A"] == pytest.approx(1.0)
        assert result["B"] == pytest.approx(1/3, rel=0.01)
        assert result["C"] == pytest.approx(1/3, rel=0.01)
        assert result["D"] == pytest.approx(1/3, rel=0.01)

    def test_bidirectional_counts_once(self) -> None:
        """A->B and B->A should count as one edge for degree."""
        interactions = [
            make_interaction("A", "B"),
            make_interaction("B", "A"),
        ]
        result = calculate_degree_centrality(interactions)
        # Both have degree 1 (one unique neighbor)
        assert result["A"] == 1.0
        assert result["B"] == 1.0


class TestBetweennessCentrality:
    """Test betweenness centrality (bridge detection)."""

    def test_empty_interactions(self) -> None:
        """Empty interactions returns empty dict."""
        result = calculate_betweenness_centrality([])
        assert result == {}

    def test_linear_chain(self) -> None:
        """Middle node in A-B-C has highest betweenness."""
        interactions = [
            make_interaction("A", "B"),
            make_interaction("B", "C"),
        ]
        result = calculate_betweenness_centrality(interactions)
        # B is on the only path between A and C
        assert result["B"] > result["A"]
        assert result["B"] > result["C"]

    def test_bridge_node(self) -> None:
        """Node bridging two clusters has high betweenness."""
        # Cluster 1: A-B, Cluster 2: C-D, Bridge: B-C
        interactions = [
            make_interaction("A", "B"),
            make_interaction("B", "C"),
            make_interaction("C", "D"),
        ]
        result = calculate_betweenness_centrality(interactions)
        # B and C are bridges
        assert result["B"] >= result["A"]
        assert result["C"] >= result["D"]


class TestClusteringCoefficient:
    """Test local clustering coefficient."""

    def test_empty_interactions(self) -> None:
        """Empty interactions returns empty dict."""
        result = calculate_clustering_coefficient([])
        assert result == {}

    def test_triangle(self) -> None:
        """Complete triangle has clustering coefficient 1.0."""
        interactions = [
            make_interaction("A", "B"),
            make_interaction("B", "C"),
            make_interaction("A", "C"),
        ]
        result = calculate_clustering_coefficient(interactions)
        # All neighbors of each node are connected
        assert result["A"] == pytest.approx(1.0)
        assert result["B"] == pytest.approx(1.0)
        assert result["C"] == pytest.approx(1.0)

    def test_star_topology(self) -> None:
        """Star topology has clustering 0 for hub (neighbors don't connect)."""
        interactions = [
            make_interaction("hub", "A"),
            make_interaction("hub", "B"),
            make_interaction("hub", "C"),
        ]
        result = calculate_clustering_coefficient(interactions)
        # Hub's neighbors (A,B,C) don't connect to each other
        assert result["hub"] == pytest.approx(0.0)
        # Leaf nodes only have 1 neighbor, so clustering undefined (0)
        assert result["A"] == pytest.approx(0.0)

    def test_partial_clustering(self) -> None:
        """Node with some neighbor connections has intermediate clustering."""
        # A connected to B, C, D
        # B-C connected, but D isolated
        interactions = [
            make_interaction("A", "B"),
            make_interaction("A", "C"),
            make_interaction("A", "D"),
            make_interaction("B", "C"),  # 1 of 3 possible neighbor edges
        ]
        result = calculate_clustering_coefficient(interactions)
        # A has 3 neighbors, 1 edge among them, max possible = 3
        # clustering = 1/3 = 0.333
        assert result["A"] == pytest.approx(1/3, rel=0.01)


class TestCommunityDetection:
    """Test community/cluster detection."""

    def test_empty_interactions(self) -> None:
        """Empty interactions returns empty list."""
        result = detect_communities([])
        assert result == []

    def test_single_community(self) -> None:
        """Fully connected graph is one community."""
        interactions = [
            make_interaction("A", "B"),
            make_interaction("B", "C"),
            make_interaction("A", "C"),
        ]
        result = detect_communities(interactions)
        assert len(result) == 1
        assert result[0] == {"A", "B", "C"}

    def test_two_disconnected_communities(self) -> None:
        """Disconnected components are separate communities."""
        interactions = [
            make_interaction("A", "B"),  # Community 1
            make_interaction("C", "D"),  # Community 2
        ]
        result = detect_communities(interactions)
        assert len(result) == 2
        communities = [frozenset(c) for c in result]
        assert frozenset({"A", "B"}) in communities
        assert frozenset({"C", "D"}) in communities

    def test_weakly_connected_communities(self) -> None:
        """Weakly connected clusters may be detected as separate."""
        # Two dense clusters with single bridge
        interactions = [
            # Cluster 1
            make_interaction("A", "B"),
            make_interaction("B", "C"),
            make_interaction("A", "C"),
            # Cluster 2
            make_interaction("D", "E"),
            make_interaction("E", "F"),
            make_interaction("D", "F"),
            # Weak bridge
            make_interaction("C", "D"),
        ]
        result = detect_communities(interactions)
        # With simple algorithm, may be 1 or 2 communities
        assert len(result) >= 1
