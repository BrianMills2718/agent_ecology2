"""Genesis Memory - Semantic memory operations for memory artifacts (Plan #146)

This genesis artifact provides semantic memory operations:
1. Add entries to memory artifacts with auto-generated embeddings
2. Search memory artifacts using semantic similarity
3. Delete entries from memory artifacts

Memory artifacts store entries as JSON with structure:
{
    "entries": [
        {
            "id": "entry_uuid",
            "text": "The original text",
            "embedding": [0.1, 0.2, ...],
            "metadata": {"key": "value"},
            "created_at": "2024-01-21T00:00:00Z"
        }
    ]
}

This replaces external vector DB dependencies (Qdrant/Mem0) with artifact-based storage,
making memories tradeable and emergent.
"""

from __future__ import annotations

import json
import logging
import math
import uuid
from datetime import datetime, timezone
from typing import Any, TYPE_CHECKING

from ...config import get as config_get
from ...config_schema import GenesisConfig
from ..errors import (
    ErrorCode,
    permission_error,
    resource_error,
    validation_error,
)
from .base import GenesisArtifact

if TYPE_CHECKING:
    from ..artifacts import ArtifactStore

logger = logging.getLogger(__name__)


def cosine_similarity(a: list[float], b: list[float]) -> float:
    """Calculate cosine similarity between two vectors.

    Args:
        a: First vector
        b: Second vector

    Returns:
        Cosine similarity in range [-1, 1]
    """
    if len(a) != len(b):
        return 0.0

    dot_product = sum(x * y for x, y in zip(a, b))
    norm_a = math.sqrt(sum(x * x for x in a))
    norm_b = math.sqrt(sum(x * x for x in b))

    if norm_a == 0 or norm_b == 0:
        return 0.0

    return dot_product / (norm_a * norm_b)


class GenesisMemory(GenesisArtifact):
    """
    Genesis artifact for semantic memory operations on memory artifacts.

    Provides:
    - add: Add entry to a memory artifact (generates embedding, costs scrip)
    - search: Semantic search within a memory artifact
    - delete: Remove entry from a memory artifact
    - create: Create a new memory artifact

    This enables agents to build tradeable memories stored as artifacts.
    """

    _artifact_store: ArtifactStore | None
    _embedder: Any  # Reference to genesis_embedder for embedding generation
    _world: Any  # World reference for kernel delegation
    _add_cost: int
    _search_cost: int
    _create_cost: int

    def __init__(
        self,
        artifact_store: ArtifactStore | None = None,
        genesis_config: GenesisConfig | None = None,
        add_cost: int = 1,
        search_cost: int = 0,
        create_cost: int = 5,
    ) -> None:
        """Initialize the memory manager.

        Args:
            artifact_store: ArtifactStore for memory artifact access
            genesis_config: Optional genesis config
            add_cost: Scrip cost to add an entry (default 1)
            search_cost: Scrip cost to search (default 0 - free)
            create_cost: Scrip cost to create a memory artifact (default 5)
        """
        self._artifact_store = artifact_store
        self._embedder = None
        self._world = None
        self._add_cost = add_cost
        self._search_cost = search_cost
        self._create_cost = create_cost

        artifact_id = "genesis_memory"
        description = "Semantic memory operations - add, search, delete entries in memory artifacts"

        super().__init__(
            artifact_id=artifact_id,
            description=description
        )

        # Register methods
        self.register_method(
            name="add",
            handler=self._add_entry,
            cost=add_cost,
            description="Add entry to memory artifact. Args: [memory_artifact_id, text, metadata?]. Generates embedding."
        )

        self.register_method(
            name="search",
            handler=self._search,
            cost=search_cost,
            description="Semantic search in memory artifact. Args: [memory_artifact_id, query, limit?]. Returns similar entries."
        )

        self.register_method(
            name="delete",
            handler=self._delete_entry,
            cost=0,
            description="Delete entry from memory artifact. Args: [memory_artifact_id, entry_id]"
        )

        self.register_method(
            name="create",
            handler=self._create_memory,
            cost=create_cost,
            description="Create new memory artifact. Args: [memory_id?]. Returns new memory artifact ID."
        )

        self.register_method(
            name="list_entries",
            handler=self._list_entries,
            cost=0,
            description="List entries in memory artifact. Args: [memory_artifact_id, limit?]. Returns entries without embeddings."
        )

    def set_world(self, world: Any) -> None:
        """Set world reference for kernel delegation."""
        self._world = world
        # Get embedder reference
        if world and hasattr(world, 'artifacts'):
            embedder = world.artifacts.get("genesis_embedder")
            if embedder:
                self._embedder = embedder

    def set_artifact_store(self, artifact_store: ArtifactStore) -> None:
        """Set artifact store reference."""
        self._artifact_store = artifact_store

    def _get_memory_content(self, artifact_id: str, invoker_id: str) -> tuple[dict[str, Any] | None, str | None]:
        """Get memory artifact content.

        Returns:
            (content_dict, error_message) - content is None if error
        """
        if not self._artifact_store:
            return None, "Artifact store not available"

        artifact = self._artifact_store.get(artifact_id)
        if not artifact:
            return None, f"Memory artifact '{artifact_id}' not found"

        if artifact.type != "memory_store":
            return None, f"Artifact '{artifact_id}' is not a memory_store (type: {artifact.type})"

        try:
            content = json.loads(artifact.content)
            if "entries" not in content:
                content["entries"] = []
            return content, None
        except json.JSONDecodeError:
            return {"entries": []}, None  # Initialize empty if content is invalid

    def _save_memory_content(self, artifact_id: str, content: dict[str, Any]) -> bool:
        """Save memory artifact content.

        Returns:
            True if saved successfully
        """
        if not self._artifact_store:
            return False

        artifact = self._artifact_store.get(artifact_id)
        if not artifact:
            return False

        artifact.content = json.dumps(content)
        artifact.updated_at = datetime.now(timezone.utc).isoformat()
        return True

    def _generate_embedding(self, text: str, invoker_id: str) -> list[float]:
        """Generate embedding for text using genesis_embedder.

        Args:
            text: Text to embed
            invoker_id: Caller ID for cost charging

        Returns:
            Embedding vector
        """
        if not self._world:
            # Fallback: return zero vector
            dims = config_get("memory.embedding_dims") or 768
            return [0.0] * dims

        # Use world executor to invoke genesis_embedder
        result = self._world.executor.invoke(
            artifact_id="genesis_embedder",
            method="embed",
            args={"text": text},
            caller_id=invoker_id,
        )

        if result.success and result.data and "embedding" in result.data:
            return result.data["embedding"]

        # Fallback: return zero vector
        dims = config_get("memory.embedding_dims") or 768
        return [0.0] * dims

    def _add_entry(self, args: list[Any], invoker_id: str) -> dict[str, Any]:
        """Add entry to memory artifact.

        Args format: [memory_artifact_id, text, metadata?]
        """
        if not args or len(args) < 2:
            return validation_error(
                "add requires [memory_artifact_id, text, metadata?]",
                code=ErrorCode.MISSING_ARGUMENT,
                required=["memory_artifact_id", "text"],
            )

        memory_id = str(args[0])
        text = str(args[1])
        metadata = args[2] if len(args) > 2 and isinstance(args[2], dict) else {}

        if not text.strip():
            return validation_error(
                "Text cannot be empty",
                code=ErrorCode.INVALID_ARGUMENT,
                provided="empty string",
            )

        # Get memory content
        content, error = self._get_memory_content(memory_id, invoker_id)
        if error:
            return resource_error(error, code=ErrorCode.NOT_FOUND)

        # Check write permission via contract (ADR-0019: use contracts, not hardcoded checks)
        if self._artifact_store:
            artifact = self._artifact_store.get(memory_id)
            if artifact:
                # Use executor to check permission via target artifact's contract
                from ..executor import get_executor
                executor = get_executor()
                allowed, reason = executor._check_permission(invoker_id, "write", artifact)
                if not allowed:
                    return permission_error(
                        f"Cannot add to memory: {reason}",
                        code=ErrorCode.NOT_AUTHORIZED,
                        invoker=invoker_id,
                    )

        # Generate embedding
        embedding = self._generate_embedding(text, invoker_id)

        # Create entry
        entry_id = str(uuid.uuid4())
        entry = {
            "id": entry_id,
            "text": text,
            "embedding": embedding,
            "metadata": metadata,
            "created_at": datetime.now(timezone.utc).isoformat(),
        }

        # Add to memory
        if content:
            content["entries"].append(entry)

            # Save back
            if not self._save_memory_content(memory_id, content):
                return resource_error(
                    "Failed to save memory artifact",
                    code=ErrorCode.INTERNAL_ERROR,
                )

        return {
            "success": True,
            "entry_id": entry_id,
            "memory_artifact_id": memory_id,
            "embedding_dims": len(embedding),
        }

    def _search(self, args: list[Any], invoker_id: str) -> dict[str, Any]:
        """Semantic search in memory artifact.

        Args format: [memory_artifact_id, query, limit?]
        """
        if not args or len(args) < 2:
            return validation_error(
                "search requires [memory_artifact_id, query, limit?]",
                code=ErrorCode.MISSING_ARGUMENT,
                required=["memory_artifact_id", "query"],
            )

        memory_id = str(args[0])
        query = str(args[1])
        limit = int(args[2]) if len(args) > 2 else 5

        if not query.strip():
            return validation_error(
                "Query cannot be empty",
                code=ErrorCode.INVALID_ARGUMENT,
                provided="empty string",
            )

        # Get memory content
        content, error = self._get_memory_content(memory_id, invoker_id)
        if error:
            return resource_error(error, code=ErrorCode.NOT_FOUND)

        if not content:
            return {"success": True, "results": [], "count": 0}

        entries = content.get("entries", [])
        if not entries:
            return {"success": True, "results": [], "count": 0}

        # Generate query embedding
        query_embedding = self._generate_embedding(query, invoker_id)

        # Calculate similarities
        scored_entries = []
        for entry in entries:
            entry_embedding = entry.get("embedding", [])
            if entry_embedding:
                similarity = cosine_similarity(query_embedding, entry_embedding)
                scored_entries.append({
                    "id": entry.get("id"),
                    "text": entry.get("text"),
                    "metadata": entry.get("metadata", {}),
                    "created_at": entry.get("created_at"),
                    "score": similarity,
                })

        # Sort by similarity (highest first)
        scored_entries.sort(key=lambda x: x["score"], reverse=True)

        # Return top results
        results = scored_entries[:limit]

        return {
            "success": True,
            "results": results,
            "count": len(results),
            "total_entries": len(entries),
            "memory_artifact_id": memory_id,
        }

    def _delete_entry(self, args: list[Any], invoker_id: str) -> dict[str, Any]:
        """Delete entry from memory artifact.

        Args format: [memory_artifact_id, entry_id]
        """
        if not args or len(args) < 2:
            return validation_error(
                "delete requires [memory_artifact_id, entry_id]",
                code=ErrorCode.MISSING_ARGUMENT,
                required=["memory_artifact_id", "entry_id"],
            )

        memory_id = str(args[0])
        entry_id = str(args[1])

        # Get memory content
        content, error = self._get_memory_content(memory_id, invoker_id)
        if error:
            return resource_error(error, code=ErrorCode.NOT_FOUND)

        # Check write permission via contract (ADR-0019: use contracts, not hardcoded checks)
        # Deleting entries is a write operation on the memory artifact
        if self._artifact_store:
            artifact = self._artifact_store.get(memory_id)
            if artifact:
                from ..executor import get_executor
                executor = get_executor()
                allowed, reason = executor._check_permission(invoker_id, "write", artifact)
                if not allowed:
                    return permission_error(
                        f"Cannot delete from memory: {reason}",
                        code=ErrorCode.NOT_AUTHORIZED,
                        invoker=invoker_id,
                    )

        if not content:
            return resource_error(
                f"Entry '{entry_id}' not found",
                code=ErrorCode.NOT_FOUND,
            )

        # Find and remove entry
        entries = content.get("entries", [])
        new_entries = [e for e in entries if e.get("id") != entry_id]

        if len(new_entries) == len(entries):
            return resource_error(
                f"Entry '{entry_id}' not found",
                code=ErrorCode.NOT_FOUND,
            )

        content["entries"] = new_entries

        # Save back
        if not self._save_memory_content(memory_id, content):
            return resource_error(
                "Failed to save memory artifact",
                code=ErrorCode.INTERNAL_ERROR,
            )

        return {
            "success": True,
            "deleted_entry_id": entry_id,
            "memory_artifact_id": memory_id,
            "remaining_entries": len(new_entries),
        }

    def _create_memory(self, args: list[Any], invoker_id: str) -> dict[str, Any]:
        """Create new memory artifact.

        Args format: [memory_id?]
        """
        memory_id = str(args[0]) if args and len(args) > 0 else f"memory_{invoker_id}_{uuid.uuid4().hex[:8]}"

        if not self._artifact_store:
            return resource_error(
                "Artifact store not available",
                code=ErrorCode.INTERNAL_ERROR,
            )

        # Check if ID already exists
        if self._artifact_store.exists(memory_id):
            return validation_error(
                f"Memory artifact '{memory_id}' already exists",
                code=ErrorCode.ALREADY_EXISTS,
            )

        # Create memory artifact with empty entries
        initial_content = json.dumps({"entries": []})

        self._artifact_store.write(
            artifact_id=memory_id,
            type="memory_store",
            content=initial_content,
            created_by=invoker_id,
            executable=False,
        )

        return {
            "success": True,
            "memory_artifact_id": memory_id,
            "created_by": invoker_id,
        }

    def _list_entries(self, args: list[Any], invoker_id: str) -> dict[str, Any]:
        """List entries in memory artifact (without embeddings).

        Args format: [memory_artifact_id, limit?]
        """
        if not args or len(args) < 1:
            return validation_error(
                "list_entries requires [memory_artifact_id, limit?]",
                code=ErrorCode.MISSING_ARGUMENT,
                required=["memory_artifact_id"],
            )

        memory_id = str(args[0])
        limit = int(args[1]) if len(args) > 1 else 20

        # Get memory content
        content, error = self._get_memory_content(memory_id, invoker_id)
        if error:
            return resource_error(error, code=ErrorCode.NOT_FOUND)

        if not content:
            return {"success": True, "entries": [], "count": 0, "total": 0}

        entries = content.get("entries", [])

        # Return entries without embeddings (to reduce response size)
        result_entries = []
        for entry in entries[-limit:]:  # Last N entries (most recent)
            result_entries.append({
                "id": entry.get("id"),
                "text": entry.get("text"),
                "metadata": entry.get("metadata", {}),
                "created_at": entry.get("created_at"),
            })

        return {
            "success": True,
            "entries": result_entries,
            "count": len(result_entries),
            "total": len(entries),
            "memory_artifact_id": memory_id,
        }

    def get_interface(self) -> dict[str, Any]:
        """Get detailed interface schema for genesis_memory (Plan #14)."""
        return {
            "description": self.description,
            "tools": [
                {
                    "name": "add",
                    "description": "Add entry to memory artifact with auto-generated embedding",
                    "cost": self._add_cost,
                    "inputSchema": {
                        "type": "object",
                        "properties": {
                            "memory_artifact_id": {
                                "type": "string",
                                "description": "ID of the memory artifact"
                            },
                            "text": {
                                "type": "string",
                                "description": "Text to store"
                            },
                            "metadata": {
                                "type": "object",
                                "description": "Optional metadata for the entry"
                            }
                        },
                        "required": ["memory_artifact_id", "text"]
                    }
                },
                {
                    "name": "search",
                    "description": "Semantic search in memory artifact",
                    "cost": self._search_cost,
                    "inputSchema": {
                        "type": "object",
                        "properties": {
                            "memory_artifact_id": {
                                "type": "string",
                                "description": "ID of the memory artifact"
                            },
                            "query": {
                                "type": "string",
                                "description": "Search query"
                            },
                            "limit": {
                                "type": "integer",
                                "description": "Maximum results to return (default 5)",
                                "default": 5
                            }
                        },
                        "required": ["memory_artifact_id", "query"]
                    }
                },
                {
                    "name": "delete",
                    "description": "Delete entry from memory artifact",
                    "cost": 0,
                    "inputSchema": {
                        "type": "object",
                        "properties": {
                            "memory_artifact_id": {
                                "type": "string",
                                "description": "ID of the memory artifact"
                            },
                            "entry_id": {
                                "type": "string",
                                "description": "ID of the entry to delete"
                            }
                        },
                        "required": ["memory_artifact_id", "entry_id"]
                    }
                },
                {
                    "name": "create",
                    "description": "Create new memory artifact",
                    "cost": self._create_cost,
                    "inputSchema": {
                        "type": "object",
                        "properties": {
                            "memory_id": {
                                "type": "string",
                                "description": "Optional custom ID for the memory artifact"
                            }
                        }
                    }
                },
                {
                    "name": "list_entries",
                    "description": "List entries in memory artifact (without embeddings)",
                    "cost": 0,
                    "inputSchema": {
                        "type": "object",
                        "properties": {
                            "memory_artifact_id": {
                                "type": "string",
                                "description": "ID of the memory artifact"
                            },
                            "limit": {
                                "type": "integer",
                                "description": "Maximum entries to return (default 20)",
                                "default": 20
                            }
                        },
                        "required": ["memory_artifact_id"]
                    }
                }
            ]
        }
