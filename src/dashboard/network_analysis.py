"""Network analysis metrics for emergence detection.

Calculates graph metrics to detect emergent structures:
- Degree centrality: Who has most connections
- Betweenness centrality: Who bridges groups
- Clustering coefficient: How tightly connected are neighborhoods
- Community detection: Identify distinct groups
"""

from collections import defaultdict
from typing import Any

from src.dashboard.models import Interaction


def _build_adjacency(interactions: list[Interaction]) -> dict[str, set[str]]:
    """Build undirected adjacency list from interactions."""
    adj: dict[str, set[str]] = defaultdict(set)
    for interaction in interactions:
        adj[interaction.from_id].add(interaction.to_id)
        adj[interaction.to_id].add(interaction.from_id)
    return dict(adj)


def calculate_degree_centrality(interactions: list[Interaction]) -> dict[str, float]:
    """Calculate normalized degree centrality for each node.

    Degree centrality = number of connections / (n-1)
    where n is total number of nodes.

    Higher values indicate more connected nodes (hubs).
    """
    if not interactions:
        return {}

    adj = _build_adjacency(interactions)
    n = len(adj)

    if n <= 1:
        return {node: 0.0 for node in adj}

    # Normalize by (n-1), the maximum possible degree
    return {node: len(neighbors) / (n - 1) for node, neighbors in adj.items()}


def calculate_betweenness_centrality(interactions: list[Interaction]) -> dict[str, float]:
    """Calculate betweenness centrality for each node.

    Betweenness = fraction of shortest paths that pass through the node.
    Higher values indicate bridge nodes that connect different groups.

    Uses Brandes' algorithm for efficiency.
    """
    if not interactions:
        return {}

    adj = _build_adjacency(interactions)
    nodes = list(adj.keys())
    n = len(nodes)

    if n <= 2:
        return {node: 0.0 for node in nodes}

    betweenness: dict[str, float] = {node: 0.0 for node in nodes}

    # Brandes' algorithm
    for source in nodes:
        # BFS from source
        stack: list[str] = []
        pred: dict[str, list[str]] = {node: [] for node in nodes}
        sigma: dict[str, int] = {node: 0 for node in nodes}
        sigma[source] = 1
        dist: dict[str, int] = {node: -1 for node in nodes}
        dist[source] = 0

        queue = [source]
        while queue:
            v = queue.pop(0)
            stack.append(v)
            for w in adj.get(v, set()):
                # First visit?
                if dist[w] < 0:
                    queue.append(w)
                    dist[w] = dist[v] + 1
                # Shortest path to w via v?
                if dist[w] == dist[v] + 1:
                    sigma[w] += sigma[v]
                    pred[w].append(v)

        # Accumulation
        delta: dict[str, float] = {node: 0.0 for node in nodes}
        while stack:
            w = stack.pop()
            for v in pred[w]:
                delta[v] += (sigma[v] / sigma[w]) * (1 + delta[w])
            if w != source:
                betweenness[w] += delta[w]

    # Normalize (undirected graph, so divide by 2)
    norm = (n - 1) * (n - 2)
    if norm > 0:
        for node in betweenness:
            betweenness[node] = betweenness[node] / norm

    return betweenness


def calculate_clustering_coefficient(interactions: list[Interaction]) -> dict[str, float]:
    """Calculate local clustering coefficient for each node.

    Clustering = (edges among neighbors) / (possible edges among neighbors)
    Higher values indicate tightly knit neighborhoods.

    Returns 0.0 for nodes with fewer than 2 neighbors.
    """
    if not interactions:
        return {}

    adj = _build_adjacency(interactions)
    clustering: dict[str, float] = {}

    for node, neighbors in adj.items():
        k = len(neighbors)
        if k < 2:
            clustering[node] = 0.0
            continue

        # Count edges among neighbors
        edges_among_neighbors = 0
        neighbor_list = list(neighbors)
        for i, n1 in enumerate(neighbor_list):
            for n2 in neighbor_list[i + 1:]:
                if n2 in adj.get(n1, set()):
                    edges_among_neighbors += 1

        # Maximum possible edges = k*(k-1)/2
        max_edges = k * (k - 1) / 2
        clustering[node] = edges_among_neighbors / max_edges

    return clustering


def detect_communities(interactions: list[Interaction]) -> list[set[str]]:
    """Detect communities using connected components.

    Simple approach: each connected component is a community.
    For more sophisticated detection, could implement label propagation
    or modularity optimization.

    Returns list of sets, where each set contains node IDs in a community.
    """
    if not interactions:
        return []

    adj = _build_adjacency(interactions)
    visited: set[str] = set()
    communities: list[set[str]] = []

    for start_node in adj:
        if start_node in visited:
            continue

        # BFS to find connected component
        community: set[str] = set()
        queue = [start_node]
        while queue:
            node = queue.pop(0)
            if node in visited:
                continue
            visited.add(node)
            community.add(node)
            for neighbor in adj.get(node, set()):
                if neighbor not in visited:
                    queue.append(neighbor)

        communities.append(community)

    return communities


def calculate_network_metrics(interactions: list[Interaction]) -> dict[str, Any]:
    """Calculate all network metrics at once.

    Returns dict with:
    - degree_centrality: {node: float}
    - betweenness_centrality: {node: float}
    - clustering_coefficient: {node: float}
    - communities: list[set[str]]
    - summary: aggregate statistics
    """
    degree = calculate_degree_centrality(interactions)
    betweenness = calculate_betweenness_centrality(interactions)
    clustering = calculate_clustering_coefficient(interactions)
    communities = detect_communities(interactions)

    # Summary statistics
    nodes = list(degree.keys())
    n = len(nodes)

    summary = {
        "node_count": n,
        "community_count": len(communities),
        "avg_degree_centrality": sum(degree.values()) / n if n > 0 else 0,
        "avg_clustering": sum(clustering.values()) / n if n > 0 else 0,
        "max_betweenness_node": max(betweenness.keys(), key=lambda k: betweenness[k]) if betweenness else None,
        "density": _calculate_density(interactions, n),
    }

    return {
        "degree_centrality": degree,
        "betweenness_centrality": betweenness,
        "clustering_coefficient": clustering,
        "communities": [list(c) for c in communities],  # Convert sets for JSON
        "summary": summary,
    }


def _calculate_density(interactions: list[Interaction], n: int) -> float:
    """Calculate network density = actual edges / possible edges."""
    if n <= 1:
        return 0.0

    # Count unique edges
    edges: set[tuple[str, str]] = set()
    for interaction in interactions:
        pair = sorted([interaction.from_id, interaction.to_id])
        edge: tuple[str, str] = (pair[0], pair[1])
        edges.add(edge)

    max_edges = n * (n - 1) / 2
    return len(edges) / max_edges
