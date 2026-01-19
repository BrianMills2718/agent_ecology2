"""Artifact dependency graph construction and metrics.

Plan #64: Artifact Dependency Graph Visualization.

This module builds a visualization-ready graph from artifact dependency data,
computing metrics that show the emergent capital structure of the simulation.

Key concepts:
- Depth: Distance from root artifacts (no dependencies) - shows capital chain length
- Orphans: Artifacts nothing depends on - dead ends in the capital structure
- Genesis ratio: How much builds on genesis vs. agent-created artifacts
- Lindy score: age × unique_invokers - identifies emergent standards
"""

from __future__ import annotations

from collections import defaultdict
from datetime import datetime, timezone
from typing import Any

from src.dashboard.models import (
    DependencyNode,
    DependencyEdge,
    DependencyGraphData,
    DependencyGraphMetrics,
)


def build_dependency_graph(artifacts: list[dict[str, Any]]) -> DependencyGraphData:
    """Build a dependency graph from artifact data.

    Args:
        artifacts: List of artifact dicts with at minimum:
            - artifact_id: str
            - name: str
            - owner: str
            - artifact_type: str
            - depends_on: list[str]
            - created_at: str (ISO format)
            Optional:
            - unique_invokers: int (for Lindy score calculation)

    Returns:
        DependencyGraphData with nodes, edges, and computed metrics.
    """
    if not artifacts:
        return DependencyGraphData(
            nodes=[],
            edges=[],
            metrics=DependencyGraphMetrics(),
        )

    # Build lookup for artifact IDs
    artifact_ids = {a["artifact_id"] for a in artifacts}

    # Build adjacency list for dependency relationships
    # dependents[X] = list of artifacts that depend on X
    dependents: dict[str, list[str]] = defaultdict(list)

    # Build nodes and collect edges
    nodes: list[DependencyNode] = []
    edges: list[DependencyEdge] = []

    for artifact in artifacts:
        artifact_id = artifact["artifact_id"]
        depends_on = artifact.get("depends_on", [])

        # Create edges (only for valid targets)
        for dep_id in depends_on:
            if dep_id == artifact_id:
                # Skip self-references
                continue
            if dep_id in artifact_ids:
                # Valid dependency - add edge
                edges.append(DependencyEdge(source=artifact_id, target=dep_id))
                dependents[dep_id].append(artifact_id)
            # Dangling references are silently filtered out

    # Calculate depths using BFS from roots
    depths = _calculate_depths(artifacts, artifact_ids)

    # Build nodes with computed values
    now = datetime.now(timezone.utc)
    for artifact in artifacts:
        artifact_id = artifact["artifact_id"]
        created_at_str = artifact.get("created_at", now.isoformat())

        # Parse created_at
        try:
            if isinstance(created_at_str, datetime):
                created_at = created_at_str
            else:
                created_at = datetime.fromisoformat(created_at_str.replace("Z", "+00:00"))
        except (ValueError, AttributeError):
            created_at = now

        # Calculate Lindy score: age_in_days × unique_invokers
        age_days = max(0, (now - created_at).days)
        unique_invokers = artifact.get("unique_invokers", 0)
        lindy_score = age_days * unique_invokers

        # Check if genesis
        artifact_type = artifact.get("artifact_type", "")
        is_genesis = artifact_type == "genesis" or artifact_id.startswith("genesis_")

        nodes.append(DependencyNode(
            artifact_id=artifact_id,
            name=artifact.get("name", artifact_id),
            owner=artifact.get("owner", "unknown"),
            artifact_type=artifact_type,
            is_genesis=is_genesis,
            usage_count=len(dependents.get(artifact_id, [])),
            created_at=created_at,
            depth=depths.get(artifact_id, 0),
            lindy_score=lindy_score,
        ))

    # Compute metrics
    metrics = compute_graph_metrics(nodes, edges)

    return DependencyGraphData(
        nodes=nodes,
        edges=edges,
        metrics=metrics,
    )


def _calculate_depths(
    artifacts: list[dict[str, Any]],
    artifact_ids: set[str],
) -> dict[str, int]:
    """Calculate depth for each artifact using BFS from roots.

    Roots are artifacts with no dependencies (or only dangling dependencies).
    Depth is the longest path from any root to this artifact.

    Handles cycles by visiting each node at most once per path.
    """
    # Build dependency graph: dependencies[X] = what X depends on
    dependencies: dict[str, set[str]] = {}
    for artifact in artifacts:
        artifact_id = artifact["artifact_id"]
        depends_on = artifact.get("depends_on", [])
        # Only keep valid, non-self dependencies
        valid_deps = {d for d in depends_on if d in artifact_ids and d != artifact_id}
        dependencies[artifact_id] = valid_deps

    # Find roots: artifacts with no valid dependencies
    roots = [aid for aid in artifact_ids if not dependencies.get(aid)]

    # BFS from roots to calculate depths
    depths: dict[str, int] = {}
    queue: list[tuple[str, int]] = [(root, 0) for root in roots]
    visited: set[str] = set()

    while queue:
        artifact_id, depth = queue.pop(0)

        # Track maximum depth seen for each artifact
        if artifact_id in depths:
            depths[artifact_id] = max(depths[artifact_id], depth)
        else:
            depths[artifact_id] = depth

        # Find all artifacts that depend on this one
        for other_id, other_deps in dependencies.items():
            if artifact_id in other_deps:
                # Only queue if we haven't fully processed this artifact at this depth
                if other_id not in visited or depths.get(other_id, -1) < depth + 1:
                    queue.append((other_id, depth + 1))

        visited.add(artifact_id)

    # Handle any artifacts not reachable from roots (cycles only)
    for artifact_id in artifact_ids:
        if artifact_id not in depths:
            depths[artifact_id] = 0

    return depths


def compute_graph_metrics(
    nodes: list[DependencyNode],
    edges: list[DependencyEdge],
) -> DependencyGraphMetrics:
    """Compute metrics for the dependency graph.

    Metrics:
    - max_depth: Longest path from any root (shows capital chain length)
    - avg_fanout: Mean dependents per node (shows composition breadth)
    - genesis_dependency_ratio: Genesis deps / total deps
    - orphan_count: Artifacts nothing depends on (dead ends)
    """
    if not nodes:
        return DependencyGraphMetrics()

    # Create node lookup
    node_by_id = {n.artifact_id: n for n in nodes}

    # Count how many edges point to each target (who gets depended on)
    dependent_counts: dict[str, int] = defaultdict(int)
    for edge in edges:
        dependent_counts[edge.target] += 1

    # Max depth
    max_depth = max((n.depth for n in nodes), default=0)

    # Average fanout: mean number of artifacts that depend on each node
    # fanout[X] = count of edges where target == X
    total_fanout = sum(dependent_counts.values())
    avg_fanout = total_fanout / len(nodes) if nodes else 0.0

    # Genesis dependency ratio: edges pointing to genesis / total edges
    genesis_edges = 0
    for edge in edges:
        target_node = node_by_id.get(edge.target)
        if target_node and target_node.is_genesis:
            genesis_edges += 1
    genesis_dependency_ratio = genesis_edges / len(edges) if edges else 0.0

    # Orphan count: nodes with no dependents (nothing points to them)
    # A node is an orphan if no edge has it as target
    targets = {edge.target for edge in edges}
    orphan_count = sum(1 for n in nodes if n.artifact_id not in targets)

    return DependencyGraphMetrics(
        max_depth=max_depth,
        avg_fanout=avg_fanout,
        genesis_dependency_ratio=genesis_dependency_ratio,
        orphan_count=orphan_count,
        total_nodes=len(nodes),
        total_edges=len(edges),
    )
