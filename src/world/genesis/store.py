"""Genesis Store - Artifact discovery and registry

Enables agents to programmatically discover artifacts without trial-and-error.
"""

from __future__ import annotations

from typing import Any

from ...config import get_validated_config
from ...config_schema import GenesisConfig
from ..artifacts import ArtifactStore
from .base import GenesisArtifact


class GenesisStore(GenesisArtifact):
    """
    Genesis artifact for artifact discovery and registry.

    Enables agents to programmatically discover artifacts without trial-and-error.
    All methods cost 0 (system-subsidized) to encourage market formation.

    Methods:
    - list: List artifacts with optional filter
    - get: Get single artifact details
    - get_interface: Get interface schema for an artifact (Plan #114)
    - search: Search by content match
    - list_by_type: List artifacts of specific type
    - list_by_owner: List artifacts by owner
    - list_agents: List all agent artifacts
    - list_principals: List all principals (has_standing=True)
    - count: Count artifacts matching filter

    All method costs and descriptions are configurable via config.yaml.
    """

    artifact_store: ArtifactStore

    def __init__(
        self,
        artifact_store: ArtifactStore,
        genesis_config: GenesisConfig | None = None
    ) -> None:
        """
        Args:
            artifact_store: The world's ArtifactStore for artifact lookups
            genesis_config: Optional genesis config (uses global if not provided)
        """
        # Get config (use provided or load from global)
        cfg = genesis_config or get_validated_config().genesis
        store_cfg = cfg.store

        super().__init__(
            artifact_id=store_cfg.id,
            description=store_cfg.description
        )
        self.artifact_store = artifact_store

        # Register methods with costs/descriptions from config
        self.register_method(
            name="list",
            handler=self._list,
            cost=store_cfg.methods.list.cost,
            description=store_cfg.methods.list.description
        )

        self.register_method(
            name="get",
            handler=self._get,
            cost=store_cfg.methods.get.cost,
            description=store_cfg.methods.get.description
        )

        self.register_method(
            name="search",
            handler=self._search,
            cost=store_cfg.methods.search.cost,
            description=store_cfg.methods.search.description
        )

        self.register_method(
            name="list_by_type",
            handler=self._list_by_type,
            cost=store_cfg.methods.list_by_type.cost,
            description=store_cfg.methods.list_by_type.description
        )

        self.register_method(
            name="list_by_owner",
            handler=self._list_by_owner,
            cost=store_cfg.methods.list_by_owner.cost,
            description=store_cfg.methods.list_by_owner.description
        )

        self.register_method(
            name="list_agents",
            handler=self._list_agents,
            cost=store_cfg.methods.list_agents.cost,
            description=store_cfg.methods.list_agents.description
        )

        self.register_method(
            name="list_principals",
            handler=self._list_principals,
            cost=store_cfg.methods.list_principals.cost,
            description=store_cfg.methods.list_principals.description
        )

        self.register_method(
            name="count",
            handler=self._count,
            cost=store_cfg.methods.count.cost,
            description=store_cfg.methods.count.description
        )

        # Plan #114: Interface discovery
        self.register_method(
            name="get_interface",
            handler=self._get_interface,
            cost=store_cfg.methods.get_interface.cost,
            description=store_cfg.methods.get_interface.description
        )

    def _artifact_to_dict(self, artifact: Any) -> dict[str, Any]:
        """Convert an Artifact to a dict representation."""
        result: dict[str, Any] = {
            "id": artifact.id,
            "type": artifact.type,
            "owner_id": artifact.owner_id,
            "content": artifact.content,
            "has_standing": artifact.has_standing,
            "can_execute": artifact.can_execute,
            "executable": artifact.executable,
            "interface": artifact.interface,  # Plan #114: Enable interface discovery
        }
        # Optional fields
        if hasattr(artifact, "memory_artifact_id") and artifact.memory_artifact_id:
            result["memory_artifact_id"] = artifact.memory_artifact_id
        return result

    def _apply_filter(
        self, artifacts: list[Any], filter_dict: dict[str, Any] | None
    ) -> list[Any]:
        """Apply filter criteria to artifact list."""
        if not filter_dict:
            return artifacts

        filtered = artifacts

        # Filter by type
        if "type" in filter_dict:
            filtered = [a for a in filtered if a.type == filter_dict["type"]]

        # Filter by owner
        if "owner" in filter_dict:
            filtered = [a for a in filtered if a.owner_id == filter_dict["owner"]]

        # Filter by has_standing
        if "has_standing" in filter_dict:
            filtered = [a for a in filtered if a.has_standing == filter_dict["has_standing"]]

        # Filter by can_execute
        if "can_execute" in filter_dict:
            filtered = [a for a in filtered if a.can_execute == filter_dict["can_execute"]]

        # Apply offset
        offset = filter_dict.get("offset", 0)
        if offset > 0:
            filtered = filtered[offset:]

        # Apply limit
        limit = filter_dict.get("limit")
        if limit is not None and limit > 0:
            filtered = filtered[:limit]

        return filtered

    def _get_all_artifacts(self) -> list[Any]:
        """Get all artifacts as Artifact objects (not dicts)."""
        return list(self.artifact_store.artifacts.values())

    def _list(self, args: list[Any], invoker_id: str) -> dict[str, Any]:
        """List artifacts with optional filter.

        Args: [filter?] where filter is a dict with optional keys:
        - type: filter by artifact type
        - owner: filter by owner_id
        - has_standing: filter by has_standing (True/False)
        - can_execute: filter by can_execute (True/False)
        - limit: max results to return
        - offset: skip first N results
        """
        filter_dict = args[0] if args and isinstance(args[0], dict) else None

        all_artifacts = self._get_all_artifacts()
        filtered = self._apply_filter(all_artifacts, filter_dict)

        return {
            "success": True,
            "artifacts": [self._artifact_to_dict(a) for a in filtered],
            "count": len(filtered),
        }

    def _get(self, args: list[Any], invoker_id: str) -> dict[str, Any]:
        """Get single artifact details.

        Args: [artifact_id]
        """
        if not args or len(args) < 1:
            return {"success": False, "error": "get requires [artifact_id]"}

        artifact_id: str = str(args[0])
        artifact = self.artifact_store.get(artifact_id)

        if not artifact:
            return {"success": False, "error": f"Artifact '{artifact_id}' not found"}

        return {
            "success": True,
            "artifact": self._artifact_to_dict(artifact),
        }

    def _search(self, args: list[Any], invoker_id: str) -> dict[str, Any]:
        """Search artifacts by content match.

        Args: [query, field?, limit?]
        - query: string to search for
        - field: optional field to search in (default: all)
        - limit: optional max results
        """
        if not args or len(args) < 1:
            return {"success": False, "error": "search requires [query]"}

        query: str = str(args[0]).lower()
        field: str | None = str(args[1]) if len(args) > 1 and args[1] else None
        limit: int | None = int(args[2]) if len(args) > 2 and args[2] else None

        all_artifacts = self._get_all_artifacts()
        matches: list[Any] = []

        for artifact in all_artifacts:
            # Search in content
            content = artifact.content
            matched = False

            if field:
                # Search in specific field
                if isinstance(content, dict) and field in content:
                    if query in str(content[field]).lower():
                        matched = True
            else:
                # Search in all content
                content_str = str(content).lower()
                if query in content_str:
                    matched = True

                # Also search in ID and type
                if query in artifact.id.lower() or query in artifact.type.lower():
                    matched = True

            if matched:
                matches.append(artifact)
                if limit and len(matches) >= limit:
                    break

        return {
            "success": True,
            "artifacts": [self._artifact_to_dict(a) for a in matches],
            "query": query,
        }

    def _list_by_type(self, args: list[Any], invoker_id: str) -> dict[str, Any]:
        """List artifacts of specific type.

        Args: [type]
        """
        if not args or len(args) < 1:
            return {"success": False, "error": "list_by_type requires [type]"}

        artifact_type: str = str(args[0])
        return self._list([{"type": artifact_type}], invoker_id)

    def _list_by_owner(self, args: list[Any], invoker_id: str) -> dict[str, Any]:
        """List artifacts by owner.

        Args: [owner_id]
        """
        if not args or len(args) < 1:
            return {"success": False, "error": "list_by_owner requires [owner_id]"}

        owner_id: str = str(args[0])
        return self._list([{"owner": owner_id}], invoker_id)

    def _list_agents(self, args: list[Any], invoker_id: str) -> dict[str, Any]:
        """List all agent artifacts.

        Agents are artifacts with has_standing=True AND can_execute=True.

        Args: []
        """
        return self._list([{"has_standing": True, "can_execute": True}], invoker_id)

    def _list_principals(self, args: list[Any], invoker_id: str) -> dict[str, Any]:
        """List all principals.

        Principals are artifacts with has_standing=True.
        This includes agents and contracts with standing.

        Args: []
        """
        return self._list([{"has_standing": True}], invoker_id)

    def _count(self, args: list[Any], invoker_id: str) -> dict[str, Any]:
        """Count artifacts matching filter.

        Args: [filter?] - same filter format as list
        """
        filter_dict = args[0] if args and isinstance(args[0], dict) else None

        all_artifacts = self._get_all_artifacts()

        # Don't apply limit/offset for count
        count_filter = dict(filter_dict) if filter_dict else {}
        count_filter.pop("limit", None)
        count_filter.pop("offset", None)

        filtered = self._apply_filter(all_artifacts, count_filter if count_filter else None)

        return {
            "success": True,
            "count": len(filtered),
        }

    def _get_interface(self, args: list[Any], invoker_id: str) -> dict[str, Any]:
        """Get interface schema for an artifact.

        Plan #114: Enable agents to discover artifact interfaces before invoking.

        Args: [artifact_id]
        Returns: {"success": True, "interface": {...}} or {"success": False, "error": "..."}
        """
        if not args or len(args) < 1:
            return {"success": False, "error": "get_interface requires [artifact_id]"}

        artifact_id: str = str(args[0])
        artifact = self.artifact_store.get(artifact_id)

        if not artifact:
            return {"success": False, "error": f"Artifact '{artifact_id}' not found"}

        return {
            "success": True,
            "artifact_id": artifact_id,
            "interface": artifact.interface,
            "executable": artifact.executable,
        }
