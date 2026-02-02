"""Kernel Query Handlers - Plan #184

Provides read-only access to kernel state for agents via the query_kernel action.
"""

from __future__ import annotations

import re
from typing import Any, TYPE_CHECKING

if TYPE_CHECKING:
    from .world import World


# Valid query types and their required/optional parameters
QUERY_SCHEMA: dict[str, dict[str, Any]] = {
    "artifacts": {
        "params": ["owner", "type", "executable", "name_pattern", "limit", "offset"],
        "required": [],
    },
    "artifact": {
        "params": ["artifact_id"],
        "required": ["artifact_id"],
    },
    "principals": {
        "params": ["limit"],
        "required": [],
    },
    "principal": {
        "params": ["principal_id"],
        "required": ["principal_id"],
    },
    "balances": {
        "params": ["principal_id"],
        "required": [],
    },
    "resources": {
        "params": ["principal_id", "resource"],
        "required": ["principal_id"],
    },
    "quotas": {
        "params": ["principal_id", "resource"],
        "required": ["principal_id"],
    },
    "mint": {
        "params": ["status", "history", "limit"],
        "required": [],
    },
    "events": {
        "params": ["limit"],
        "required": [],
    },
    "invocations": {
        "params": ["artifact_id", "invoker_id", "limit"],
        "required": [],
    },
    "frozen": {
        "params": ["agent_id"],
        "required": [],
    },
    "libraries": {
        "params": ["principal_id"],
        "required": ["principal_id"],
    },
    "dependencies": {
        "params": ["artifact_id"],
        "required": ["artifact_id"],
    },
}


class KernelQueryHandler:
    """Handles kernel state queries.

    Provides read-only access to kernel state including artifacts,
    principals, balances, resources, and more.
    """

    def __init__(self, world: "World") -> None:
        self._world = world

    def execute(self, query_type: str, params: dict[str, Any]) -> dict[str, Any]:
        """Execute a kernel query.

        Args:
            query_type: Type of query (artifacts, balances, etc.)
            params: Query parameters

        Returns:
            Query result dict with success, data, and optional error info
        """
        # Validate query type
        if query_type not in QUERY_SCHEMA:
            valid_types = ", ".join(sorted(QUERY_SCHEMA.keys()))
            return {
                "success": False,
                "error": f"Unknown query_type '{query_type}'. Valid types: {valid_types}",
                "error_code": "invalid_query_type",
            }

        schema = QUERY_SCHEMA[query_type]

        # Validate unknown params
        for param in params:
            if param not in schema["params"]:
                valid_params = ", ".join(schema["params"])
                return {
                    "success": False,
                    "error": f"Unknown param '{param}' for {query_type} query. Valid params: {valid_params}",
                    "error_code": "invalid_param",
                }

        # Validate required params
        for required in schema["required"]:
            if required not in params:
                return {
                    "success": False,
                    "error": f"Query '{query_type}' requires '{required}' param",
                    "error_code": "missing_param",
                }

        # Dispatch to handler
        handler = getattr(self, f"_query_{query_type}", None)
        if handler is None:
            return {
                "success": False,
                "error": f"Query handler for '{query_type}' not implemented",
                "error_code": "not_implemented",
            }

        return handler(params)

    def _query_artifacts(self, params: dict[str, Any]) -> dict[str, Any]:
        """Query artifacts with filters."""
        owner = params.get("owner")
        artifact_type = params.get("type")
        executable = params.get("executable")
        name_pattern = params.get("name_pattern")
        limit = params.get("limit", 50)
        offset = params.get("offset", 0)

        # Validate param types
        if limit is not None and not isinstance(limit, int):
            return {
                "success": False,
                "error": f"Param 'limit' must be an integer, got '{type(limit).__name__}'",
                "error_code": "invalid_param_type",
            }
        if offset is not None and not isinstance(offset, int):
            return {
                "success": False,
                "error": f"Param 'offset' must be an integer, got '{type(offset).__name__}'",
                "error_code": "invalid_param_type",
            }

        # Build filtered results
        results = []
        for artifact_id, artifact in self._world.artifacts.artifacts.items():
            if artifact.deleted:
                continue
            if owner and artifact.created_by != owner:
                continue
            if artifact_type and artifact.type != artifact_type:
                continue
            if executable is not None and artifact.executable != executable:
                continue
            if name_pattern:
                try:
                    if not re.search(name_pattern, artifact_id):
                        continue
                except re.error:
                    return {
                        "success": False,
                        "error": f"Invalid regex pattern: '{name_pattern}'",
                        "error_code": "invalid_pattern",
                    }
            # Handle content preview - content can be str or dict
            content_preview = ""
            if artifact.content:
                if isinstance(artifact.content, str):
                    content_preview = artifact.content[:100]
                else:
                    # Dict or other type - stringify first
                    content_preview = str(artifact.content)[:100]
            results.append({
                "id": artifact.id,
                "type": artifact.type,
                "created_by": artifact.created_by,
                "executable": artifact.executable,
                "content_preview": content_preview,
            })

        total = len(results)
        results = results[offset:offset + limit]

        return {
            "success": True,
            "query_type": "artifacts",
            "total": total,
            "returned": len(results),
            "results": results,
        }

    def _query_artifact(self, params: dict[str, Any]) -> dict[str, Any]:
        """Get single artifact metadata."""
        artifact_id = params["artifact_id"]
        artifact = self._world.artifacts.get(artifact_id)

        if artifact is None:
            return {
                "success": False,
                "error": f"Artifact '{artifact_id}' not found",
                "error_code": "not_found",
            }

        return {
            "success": True,
            "query_type": "artifact",
            "result": artifact.to_dict(),
        }

    def _query_principals(self, params: dict[str, Any]) -> dict[str, Any]:
        """List all principals."""
        limit = params.get("limit", 100)
        principals = list(self._world.ledger.scrip.keys())[:limit]

        return {
            "success": True,
            "query_type": "principals",
            "total": len(self._world.ledger.scrip),
            "returned": len(principals),
            "results": principals,
        }

    def _query_principal(self, params: dict[str, Any]) -> dict[str, Any]:
        """Get principal existence and info."""
        principal_id = params["principal_id"]
        exists = principal_id in self._world.ledger.scrip

        if not exists:
            return {
                "success": True,
                "query_type": "principal",
                "exists": False,
                "principal_id": principal_id,
            }

        return {
            "success": True,
            "query_type": "principal",
            "exists": True,
            "principal_id": principal_id,
            "scrip": self._world.ledger.get_scrip(principal_id),
        }

    def _query_balances(self, params: dict[str, Any]) -> dict[str, Any]:
        """Get balances for one or all principals."""
        principal_id = params.get("principal_id")

        if principal_id:
            if principal_id not in self._world.ledger.scrip:
                return {
                    "success": False,
                    "error": f"Principal '{principal_id}' not found",
                    "error_code": "not_found",
                }
            return {
                "success": True,
                "query_type": "balances",
                "principal_id": principal_id,
                "scrip": self._world.ledger.get_scrip(principal_id),
            }

        # All balances
        balances = {
            pid: self._world.ledger.get_scrip(pid)
            for pid in self._world.ledger.scrip
        }
        return {
            "success": True,
            "query_type": "balances",
            "balances": balances,
        }

    def _query_resources(self, params: dict[str, Any]) -> dict[str, Any]:
        """Get resources for a principal."""
        principal_id = params["principal_id"]
        resource = params.get("resource")

        if not self._world.resource_manager:
            return {
                "success": False,
                "error": "Resource manager not available",
                "error_code": "not_available",
            }

        # Get all resources for this principal
        resources: dict[str, Any] = {}

        # Check disk usage via rights registry if available
        if self._world.rights_registry:
            disk_used = self._world.rights_registry.get_disk_used(principal_id)
            disk_quota = self._world.rights_registry.get_disk_quota(principal_id)
            resources["disk"] = {"used": disk_used, "quota": disk_quota}

        # Filter to specific resource if requested
        if resource and resource in resources:
            return {
                "success": True,
                "query_type": "resources",
                "principal_id": principal_id,
                "resource": resource,
                "data": resources[resource],
            }
        elif resource and resource not in resources:
            return {
                "success": False,
                "error": f"Resource '{resource}' not found. Available: {list(resources.keys())}",
                "error_code": "not_found",
            }

        return {
            "success": True,
            "query_type": "resources",
            "principal_id": principal_id,
            "resources": resources,
        }

    def _query_quotas(self, params: dict[str, Any]) -> dict[str, Any]:
        """Get quota limits and usage for a principal."""
        principal_id = params["principal_id"]
        resource = params.get("resource")

        quotas: dict[str, Any] = {}

        if self._world.rights_registry:
            disk_quota = self._world.rights_registry.get_disk_quota(principal_id)
            disk_used = self._world.rights_registry.get_disk_used(principal_id)
            quotas["disk"] = {
                "quota": disk_quota,
                "used": disk_used,
                "available": disk_quota - disk_used,
            }

        if resource and resource in quotas:
            return {
                "success": True,
                "query_type": "quotas",
                "principal_id": principal_id,
                "resource": resource,
                "data": quotas[resource],
            }
        elif resource and resource not in quotas:
            return {
                "success": False,
                "error": f"Quota for '{resource}' not found",
                "error_code": "not_found",
            }

        return {
            "success": True,
            "query_type": "quotas",
            "principal_id": principal_id,
            "quotas": quotas,
        }

    def _query_mint(self, params: dict[str, Any]) -> dict[str, Any]:
        """Get mint status or history."""
        show_status = params.get("status", False)
        show_history = params.get("history", False)
        limit = params.get("limit", 10)

        result: dict[str, Any] = {
            "success": True,
            "query_type": "mint",
        }

        if show_status or (not show_status and not show_history):
            # Get current auction status
            if self._world.mint_auction:
                result["current_auction"] = {
                    "pending_submissions": len(self._world.mint_auction._submissions),
                }

        if show_history:
            # Get recent auction results - this would need to be implemented
            # in MintAuction if not already available
            result["history"] = []  # Placeholder

        return result

    def _query_events(self, params: dict[str, Any]) -> dict[str, Any]:
        """Get recent events."""
        limit = params.get("limit", 20)

        events = self._world.logger.read_recent(limit)

        return {
            "success": True,
            "query_type": "events",
            "returned": len(events),
            "events": events,
        }

    def _query_invocations(self, params: dict[str, Any]) -> dict[str, Any]:
        """Get invocation stats/history."""
        artifact_id = params.get("artifact_id")
        invoker_id = params.get("invoker_id")
        limit = params.get("limit", 20)

        if not self._world.invocation_registry:
            return {
                "success": False,
                "error": "Invocation registry not available",
                "error_code": "not_available",
            }

        if artifact_id:
            records = self._world.invocation_registry.get_by_artifact(artifact_id, limit)
        elif invoker_id:
            records = self._world.invocation_registry.get_by_invoker(invoker_id, limit)
        else:
            # Return summary stats
            records = []

        return {
            "success": True,
            "query_type": "invocations",
            "returned": len(records),
            "records": [r.to_dict() for r in records] if records else [],
        }

    def _query_frozen(self, params: dict[str, Any]) -> dict[str, Any]:
        """Get frozen agent status."""
        agent_id = params.get("agent_id")

        if agent_id:
            is_frozen = self._world.is_agent_frozen(agent_id)
            return {
                "success": True,
                "query_type": "frozen",
                "agent_id": agent_id,
                "frozen": is_frozen,
            }

        # All frozen agents
        frozen = self._world.get_frozen_agents()
        return {
            "success": True,
            "query_type": "frozen",
            "frozen_agents": frozen,
        }

    def _query_libraries(self, params: dict[str, Any]) -> dict[str, Any]:
        """Get installed libraries for a principal."""
        principal_id = params["principal_id"]

        libraries = self._world.get_installed_libraries(principal_id)

        return {
            "success": True,
            "query_type": "libraries",
            "principal_id": principal_id,
            "libraries": [{"name": name, "version": version} for name, version in libraries],
        }

    def _query_dependencies(self, params: dict[str, Any]) -> dict[str, Any]:
        """Get artifact dependencies."""
        artifact_id = params["artifact_id"]

        artifact = self._world.artifacts.get(artifact_id)
        if artifact is None:
            return {
                "success": False,
                "error": f"Artifact '{artifact_id}' not found",
                "error_code": "not_found",
            }

        # Get dependencies from artifact field (not metadata)
        depends_on = artifact.depends_on

        # Compute reverse dependencies (artifacts that depend on this one)
        dependents = [
            a.id for a in self._world.artifacts.artifacts.values()
            if not a.deleted and artifact_id in a.depends_on
        ]

        return {
            "success": True,
            "query_type": "dependencies",
            "artifact_id": artifact_id,
            "depends_on": depends_on,
            "dependents": dependents,
        }
