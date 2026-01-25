"""
Agent Memory - Dual Implementation

Provides persistent memory for each agent across ticks.

Two implementations available:
1. AgentMemory - DEPRECATED: Uses Mem0 with Qdrant for semantic vector search
   Plan #146: Use genesis_memory artifact instead for semantic search
2. ArtifactMemory - Uses artifact store for observable, tradeable memory (CAP-004)

Usage:
    # Artifact-based (recommended - observable, no external deps)
    memory = ArtifactMemory(store)
    memory.add(agent_id, "learned something")  # Stored in artifact content

    # For semantic search, use genesis_memory artifact:
    #   world.invoke("genesis_memory", caller_id, "search",
    #                {"memory_artifact_id": "alice_longterm", "query": "trading"})
"""

import logging
import os
import atexit
import threading
import warnings
from pathlib import Path
from typing import Any, Literal, TypedDict

# Memory tier type - numeric values for easy comparison and boosting
# 0 = pinned (always included), 1 = critical, 2 = important, 3 = normal (default), 4 = low
MemoryTier = Literal[0, 1, 2, 3, 4]
TIER_NAMES: dict[int, str] = {0: "pinned", 1: "critical", 2: "important", 3: "normal", 4: "low"}
TIER_VALUES: dict[str, int] = {v: k for k, v in TIER_NAMES.items()}

# Suppress noisy Pydantic serialization warnings from LiteLLM/mem0
warnings.filterwarnings("ignore", message=".*Pydantic serializer warnings.*")
warnings.filterwarnings("ignore", category=UserWarning, module="pydantic")

logger = logging.getLogger(__name__)

# Conditional import of mem0 - deprecated as of Plan #146
# Use genesis_memory artifact for semantic search instead
_MEM0_AVAILABLE = False
Memory: Any = None  # type: ignore[no-redef]
try:
    from mem0 import Memory as _Memory  # type: ignore[import-untyped,unused-ignore]
    Memory = _Memory
    _MEM0_AVAILABLE = True
    # Reduce mem0 log level to WARNING to suppress JSON parse errors
    logging.getLogger("mem0").setLevel(logging.WARNING)
    logging.getLogger("mem0.memory.main").setLevel(logging.WARNING)
except ImportError:
    # mem0 not installed - AgentMemory will not be available
    # This is expected after Plan #146 deprecation
    pass

from dotenv import load_dotenv

from ..config import get as config_get

load_dotenv()

# Track memory instances for cleanup
_cleanup_list: list["AgentMemory"] = []


class MemoryResult(TypedDict, total=False):
    """Result from memory add operation."""
    error: str
    results: list[dict[str, Any]]


class MemorySearchResult(TypedDict, total=False):
    """Individual memory search result."""
    memory: str
    score: float


class EmbedderConfig(TypedDict):
    """Configuration for embedder."""
    model: str
    api_key: str | None
    embedding_dims: int


class LLMConfig(TypedDict):
    """Configuration for LLM."""
    model: str
    api_key: str | None
    temperature: float


class VectorStoreServerConfig(TypedDict):
    """Configuration for vector store in server mode."""
    collection_name: str
    embedding_model_dims: int
    host: str
    port: int


class VectorStoreLocalConfig(TypedDict):
    """Configuration for vector store in local mode."""
    collection_name: str
    embedding_model_dims: int
    path: str


class EmbedderSection(TypedDict):
    """Embedder section of config."""
    provider: str
    config: EmbedderConfig


class LLMSection(TypedDict):
    """LLM section of config."""
    provider: str
    config: LLMConfig


class VectorStoreSection(TypedDict):
    """Vector store section of config."""
    provider: str
    config: VectorStoreServerConfig | VectorStoreLocalConfig


class MemoryConfig(TypedDict):
    """Full memory configuration."""
    embedder: EmbedderSection
    llm: LLMSection
    vector_store: VectorStoreSection


def _cleanup_memories() -> None:
    """Cleanup handler to close qdrant clients properly"""
    for mem in _cleanup_list:
        try:
            if hasattr(mem, 'memory') and hasattr(mem.memory, '_client'):
                mem.memory._client.close()
        except Exception as e:
            logger.debug("Error closing qdrant client during cleanup: %s", e)

atexit.register(_cleanup_memories)


class AgentMemory:
    """DEPRECATED: Shared memory manager for all agents using Mem0.

    Plan #146 Deprecation Notice:
    This class is deprecated. Use genesis_memory artifact for semantic search:

        # Create a memory artifact
        world.invoke("genesis_memory", caller_id, "create", {"memory_id": "alice_longterm"})

        # Add memories with auto-generated embeddings
        world.invoke("genesis_memory", caller_id, "add",
                     {"memory_artifact_id": "alice_longterm", "text": "learned something"})

        # Semantic search
        world.invoke("genesis_memory", caller_id, "search",
                     {"memory_artifact_id": "alice_longterm", "query": "trading"})

    For non-semantic memory, use ArtifactMemory class directly.
    """

    _instance: "AgentMemory | None" = None
    _lock: threading.Lock = threading.Lock()
    _initialized: bool
    memory: Any  # Memory type when available

    def __new__(cls) -> "AgentMemory":
        if not _MEM0_AVAILABLE:
            raise ImportError(
                "mem0 is not installed. AgentMemory is deprecated - use genesis_memory "
                "artifact for semantic search or ArtifactMemory for simple storage. "
                "See Plan #146 for migration guide."
            )
        # Double-checked locking pattern for thread-safe singleton
        if cls._instance is None:
            with cls._lock:
                # Re-check after acquiring lock
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._initialized = False
        return cls._instance

    def __init__(self) -> None:
        if self._initialized:
            return

        # Emit deprecation warning
        warnings.warn(
            "AgentMemory is deprecated as of Plan #146. "
            "Use genesis_memory artifact for semantic search or ArtifactMemory for simple storage.",
            DeprecationWarning,
            stacklevel=2
        )

        api_key: str | None = os.getenv('GEMINI_API_KEY')

        # Get memory config values (with fallbacks to schema defaults)
        llm_model: str = config_get("memory.llm_model") or "gemini-3-flash-preview"
        embedding_model: str = config_get("memory.embedding_model") or "models/text-embedding-004"
        embedding_dims: int = config_get("memory.embedding_dims") or 768
        temperature: float = config_get("memory.temperature") or 0.1
        collection_name: str = config_get("memory.collection_name") or "agent_memories"

        # Check if running with qdrant server (Docker) or local mode
        qdrant_host: str | None = os.getenv('QDRANT_HOST')
        qdrant_port: int = int(os.getenv('QDRANT_PORT', '6333'))

        vector_store_config: VectorStoreSection
        if qdrant_host:
            # Server mode (Docker)
            vector_store_config = {
                'provider': 'qdrant',
                'config': {
                    'collection_name': collection_name,
                    'embedding_model_dims': embedding_dims,
                    'host': qdrant_host,
                    'port': qdrant_port
                }
            }
        else:
            # Local mode (fallback)
            project_root: Path = Path(__file__).parent.parent.parent
            qdrant_path: Path = project_root / 'qdrant_data'
            qdrant_path.mkdir(exist_ok=True)
            vector_store_config = {
                'provider': 'qdrant',
                'config': {
                    'collection_name': collection_name,
                    'embedding_model_dims': embedding_dims,
                    'path': str(qdrant_path)
                }
            }

        config: MemoryConfig = {
            'embedder': {
                'provider': 'gemini',
                'config': {
                    'model': embedding_model,
                    'api_key': api_key,
                    'embedding_dims': embedding_dims
                }
            },
            'llm': {
                'provider': 'gemini',
                'config': {
                    'model': llm_model,
                    'api_key': api_key,
                    'temperature': temperature
                }
            },
            'vector_store': vector_store_config
        }

        self.memory = Memory.from_config(config)
        self._initialized = True
        _cleanup_list.append(self)

    def add(self, agent_id: str, content: str, tier: MemoryTier = 3) -> dict[str, Any]:
        """Add a memory for an agent with optional tier.

        Args:
            agent_id: The agent's ID
            content: The memory content
            tier: Memory tier (0=pinned, 1=critical, 2=important, 3=normal, 4=low)

        Returns:
            Result dict with memory ID on success, or error on failure
        """
        try:
            # Pass tier as metadata to Mem0
            result: Any = self.memory.add(
                content,
                user_id=agent_id,
                metadata={"tier": tier}
            )
            return result  # type: ignore[no-any-return]
        except Exception as e:
            return {"error": str(e)}

    def search(self, agent_id: str, query: str, limit: int = 5) -> list[dict[str, Any]]:
        """Search memories for an agent with tier boosting.

        Results are boosted based on tier:
        - Tier 0 (pinned): +1.0 boost
        - Tier 1 (critical): +0.3 boost
        - Tier 2 (important): +0.15 boost
        - Tier 3 (normal): no boost
        - Tier 4 (low): -0.1 penalty
        """
        try:
            # Fetch more results than needed for tier boosting
            results: Any = self.memory.search(query, user_id=agent_id, limit=limit * 3)
            memories = results.get('results', [])

            # Apply tier boost to scores
            tier_boosts = {0: 1.0, 1: 0.3, 2: 0.15, 3: 0.0, 4: -0.1}
            for mem in memories:
                tier = mem.get('metadata', {}).get('tier', 3)  # Default: normal
                original_score = mem.get('score', 0.5)
                mem['boosted_score'] = original_score + tier_boosts.get(tier, 0.0)

            # Re-sort by boosted score
            memories.sort(key=lambda m: m.get('boosted_score', 0), reverse=True)
            return memories[:limit]  # type: ignore[no-any-return]
        except Exception as e:
            logger.warning("Memory search failed for agent %s: %s", agent_id, e)
            return []

    def get_pinned_memories(self, agent_id: str) -> list[dict[str, Any]]:
        """Get all pinned memories for an agent (tier 0).

        Pinned memories are always included in context regardless of query relevance.
        """
        try:
            # Search with filter for pinned tier
            results: Any = self.memory.search(
                query="",  # Empty query - we want all pinned
                user_id=agent_id,
                limit=config_get("memory.max_pinned") or 5,
                filters={"tier": 0}
            )
            return results.get('results', [])  # type: ignore[no-any-return]
        except Exception as e:
            logger.warning("Failed to get pinned memories for agent %s: %s", agent_id, e)
            return []

    def get_relevant_memories(self, agent_id: str, context: str, limit: int = 5) -> str:
        """Get relevant memories formatted as a string for prompt injection.

        Pinned memories (tier 0) are always included first, then remaining
        slots are filled with tier-boosted search results.
        """
        # 1. Always include pinned memories first
        pinned = self.get_pinned_memories(agent_id)
        pinned_ids = {m.get('id') for m in pinned}

        # 2. Get remaining with tier-boosted search
        remaining_limit = max(0, limit - len(pinned))
        search_results: list[dict[str, Any]] = []
        if remaining_limit > 0:
            all_results = self.search(agent_id, context, limit=remaining_limit + len(pinned))
            # Exclude pinned memories from search results (already included)
            search_results = [m for m in all_results if m.get('id') not in pinned_ids][:remaining_limit]

        # 3. Combine: pinned first, then search results
        memories = pinned + search_results

        if not memories:
            return "(No relevant memories)"

        lines: list[str] = []
        for m in memories:
            memory_text: Any = m.get('memory', '')
            tier = m.get('metadata', {}).get('tier', 3)
            tier_label = TIER_NAMES.get(tier, "normal")
            # Only show tier label for non-normal tiers
            if tier != 3:
                lines.append(f"- [{tier_label}] {memory_text}")
            else:
                lines.append(f"- {memory_text}")

        return "\n".join(lines)

    def record_action(self, agent_id: str, action_type: str, details: str, success: bool) -> dict[str, Any]:
        """Record an action as a memory"""
        # Use simpler format for better memory extraction by Mem0's LLM
        memory: str
        if success:
            if action_type == "write_artifact":
                memory = f"I created an artifact with details: {details}"
            elif action_type == "read_artifact":
                memory = f"I read an artifact: {details}"
            elif action_type == "transfer":
                memory = f"I transferred credits: {details}"
            else:
                memory = f"I performed {action_type}: {details}"
        else:
            memory = f"I tried to {action_type} but failed: {details}"
        return self.add(agent_id, memory)

    def record_observation(self, agent_id: str, observation: str) -> dict[str, Any]:
        """Record an observation as a memory"""
        memory: str = f"I observed: {observation}"
        return self.add(agent_id, memory)


# Global instance
_memory: AgentMemory | None = None


def get_memory() -> AgentMemory:
    """DEPRECATED: Get the global memory instance.

    Plan #146 Deprecation Notice:
    This function is deprecated. Use genesis_memory artifact instead:

        # Semantic search via genesis_memory
        world.invoke("genesis_memory", caller_id, "search",
                     {"memory_artifact_id": "alice_longterm", "query": "trading"})

    Or use ArtifactMemory for simple non-semantic memory storage.
    """
    global _memory
    if _memory is None:
        _memory = AgentMemory()
    return _memory


# =============================================================================
# CAP-004: Artifact-Backed Memory
# =============================================================================


class MemoryEntry(TypedDict, total=False):
    """A single memory entry stored in artifact content."""
    tick: int
    timestamp: str
    content: str
    memory_type: str  # "action", "observation", "custom"
    tier: int  # 0=pinned, 1=critical, 2=important, 3=normal, 4=low (default: 3)


class ArtifactMemoryContent(TypedDict):
    """Structure of memory artifact content."""
    history: list[MemoryEntry]
    knowledge: dict[str, Any]


class ArtifactMemory:
    """Memory manager that stores memories in artifact content.

    CAP-004: Memory as Separate Artifact

    This implementation stores memories directly in the artifact store,
    making them observable and potentially tradeable. Unlike AgentMemory
    (which uses Mem0 for semantic search), this stores memories as a
    simple list in artifact content.

    Memory is stored in the artifact's content field as JSON:
    {
        "history": [
            {"tick": 1, "timestamp": "...", "content": "...", "memory_type": "action"},
            ...
        ],
        "knowledge": {...}  # Reserved for structured knowledge
    }

    Differences from AgentMemory:
    - No semantic search (returns most recent memories by default)
    - Fully observable (anyone with read access can see all memories)
    - Tradeable (memory artifact can be transferred)
    - No external dependencies (no Qdrant, no embedding API)

    Args:
        store: The artifact store containing memory artifacts
        max_history: Maximum number of history entries to keep (default: 100)
    """

    def __init__(
        self,
        store: "ArtifactStore",
        max_history: int = 100,
    ) -> None:
        from ..world.artifacts import ArtifactStore
        self._store: ArtifactStore = store
        # max_history can be passed directly or defaults to 100
        # Note: We don't use config_get here to avoid requiring config during tests
        self._max_history: int = max_history

    def _get_memory_artifact_id(self, agent_id: str) -> str:
        """Get the memory artifact ID for an agent.

        First checks if the agent artifact has a memory_artifact_id link.
        Falls back to convention: {agent_id}_memory
        """
        agent_artifact = self._store.get(agent_id)
        if agent_artifact and agent_artifact.memory_artifact_id:
            return agent_artifact.memory_artifact_id
        return f"{agent_id}_memory"

    def _get_memory_content(self, agent_id: str) -> ArtifactMemoryContent:
        """Load memory content from artifact, creating if needed."""
        import json
        from datetime import datetime
        from ..world.artifacts import create_memory_artifact

        memory_id = self._get_memory_artifact_id(agent_id)
        artifact = self._store.get(memory_id)

        if artifact is None:
            # Create memory artifact if it doesn't exist
            memory_artifact = create_memory_artifact(
                memory_id=memory_id,
                created_by=agent_id,
            )
            self._store.artifacts[memory_id] = memory_artifact
            return {"history": [], "knowledge": {}}

        # Parse existing content
        try:
            content: ArtifactMemoryContent = json.loads(artifact.content)
            # Ensure required keys exist
            if "history" not in content:
                content["history"] = []
            if "knowledge" not in content:
                content["knowledge"] = {}
            return content
        except (json.JSONDecodeError, TypeError):
            return {"history": [], "knowledge": {}}

    def _save_memory_content(self, agent_id: str, content: ArtifactMemoryContent) -> None:
        """Save memory content to artifact."""
        import json
        from datetime import datetime, timezone

        memory_id = self._get_memory_artifact_id(agent_id)
        artifact = self._store.get(memory_id)

        if artifact is None:
            # This shouldn't happen if _get_memory_content was called first
            from ..world.artifacts import create_memory_artifact
            artifact = create_memory_artifact(
                memory_id=memory_id,
                created_by=agent_id,
            )
            self._store.artifacts[memory_id] = artifact

        # Trim history if needed
        if len(content["history"]) > self._max_history:
            content["history"] = content["history"][-self._max_history:]

        # Update artifact content
        artifact.content = json.dumps(content)
        artifact.updated_at = datetime.now(timezone.utc).isoformat()

    def add(self, agent_id: str, content_text: str, tick: int = 0, tier: MemoryTier = 3) -> dict[str, Any]:
        """Add a memory for an agent with optional tier.

        Args:
            agent_id: The agent's ID
            content_text: The memory content
            tick: Current simulation tick (default 0)
            tier: Memory tier (0=pinned, 1=critical, 2=important, 3=normal, 4=low)

        Returns:
            Result dict with "results" key on success, or "error" key on failure
        """
        from datetime import datetime, timezone

        try:
            content = self._get_memory_content(agent_id)

            # Check pinned limit if tier is pinned
            if tier == 0:
                max_pinned = config_get("memory.max_pinned") or 5
                pinned_count = sum(1 for e in content["history"] if e.get("tier", 3) == 0)
                if pinned_count >= max_pinned:
                    return {"error": f"Maximum pinned memories ({max_pinned}) reached"}

            entry: MemoryEntry = {
                "tick": tick,
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "content": content_text,
                "memory_type": "custom",
                "tier": tier,
            }
            content["history"].append(entry)
            self._save_memory_content(agent_id, content)
            return {"results": [{"id": f"{agent_id}_{len(content['history'])}"}]}
        except Exception as e:
            logger.warning("Failed to add memory for agent %s: %s", agent_id, e)
            return {"error": str(e)}

    def search(self, agent_id: str, query: str, limit: int = 5) -> list[dict[str, Any]]:
        """Search memories for an agent with tier boosting.

        Note: This implementation does NOT do semantic search.
        It returns memories sorted by tier boost + recency.

        For semantic search, use AgentMemory (Mem0-based).

        Args:
            agent_id: The agent's ID
            query: Search query (currently ignored - returns most recent)
            limit: Maximum number of results

        Returns:
            List of memory dicts with "memory", "score", and "tier" keys
        """
        try:
            content = self._get_memory_content(agent_id)
            history = content.get("history", [])

            if not history:
                return []

            # Calculate boosted scores based on tier and recency
            tier_boosts = {0: 1.0, 1: 0.3, 2: 0.15, 3: 0.0, 4: -0.1}
            scored_entries = []
            for i, entry in enumerate(history):
                tier = entry.get("tier", 3)  # Default: normal
                # Recency score: newer = higher (0.0 to 1.0)
                recency_score = i / max(len(history), 1)
                # Boosted score combines recency and tier
                boosted_score = recency_score + tier_boosts.get(tier, 0.0)
                scored_entries.append({
                    "memory": entry["content"],
                    "score": recency_score,
                    "boosted_score": boosted_score,
                    "tier": tier,
                    "id": f"{agent_id}_{i}",
                    "metadata": {"tier": tier},
                })

            # Sort by boosted score (highest first)
            scored_entries.sort(key=lambda m: m["boosted_score"], reverse=True)
            return scored_entries[:limit]
        except Exception as e:
            logger.warning("Memory search failed for agent %s: %s", agent_id, e)
            return []

    def get_pinned_memories(self, agent_id: str) -> list[dict[str, Any]]:
        """Get all pinned memories for an agent (tier 0).

        Pinned memories are always included in context regardless of query relevance.
        """
        try:
            content = self._get_memory_content(agent_id)
            history = content.get("history", [])

            pinned = [
                {
                    "memory": entry["content"],
                    "score": 1.0,
                    "tier": 0,
                    "id": f"{agent_id}_{i}",
                    "metadata": {"tier": 0},
                }
                for i, entry in enumerate(history)
                if entry.get("tier", 3) == 0
            ]

            max_pinned = config_get("memory.max_pinned") or 5
            return pinned[:max_pinned]
        except Exception as e:
            logger.warning("Failed to get pinned memories for agent %s: %s", agent_id, e)
            return []

    def get_relevant_memories(self, agent_id: str, context: str, limit: int = 5) -> str:
        """Get relevant memories formatted as a string for prompt injection.

        Pinned memories (tier 0) are always included first, then remaining
        slots are filled with tier-boosted results.

        Args:
            agent_id: The agent's ID
            context: Context for search (currently ignored - returns most recent)
            limit: Maximum number of memories to return

        Returns:
            Formatted string of memories for prompt injection
        """
        # 1. Always include pinned memories first
        pinned = self.get_pinned_memories(agent_id)
        pinned_ids = {m.get('id') for m in pinned}

        # 2. Get remaining with tier-boosted search
        remaining_limit = max(0, limit - len(pinned))
        search_results: list[dict[str, Any]] = []
        if remaining_limit > 0:
            all_results = self.search(agent_id, context, limit=remaining_limit + len(pinned))
            # Exclude pinned memories from search results (already included)
            search_results = [m for m in all_results if m.get('id') not in pinned_ids][:remaining_limit]

        # 3. Combine: pinned first, then search results
        memories = pinned + search_results

        if not memories:
            return "(No relevant memories)"

        lines: list[str] = []
        for m in memories:
            memory_text = m.get("memory", "")
            tier = m.get("tier", 3)
            tier_label = TIER_NAMES.get(tier, "normal")
            # Only show tier label for non-normal tiers
            if tier != 3:
                lines.append(f"- [{tier_label}] {memory_text}")
            else:
                lines.append(f"- {memory_text}")

        return "\n".join(lines)

    def record_action(
        self, agent_id: str, action_type: str, details: str, success: bool, tick: int = 0, tier: MemoryTier = 3
    ) -> dict[str, Any]:
        """Record an action as a memory.

        Args:
            agent_id: The agent's ID
            action_type: Type of action performed
            details: Details about the action
            success: Whether the action succeeded
            tick: Current simulation tick
            tier: Memory tier (0=pinned, 1=critical, 2=important, 3=normal, 4=low)

        Returns:
            Result dict with "results" key on success, or "error" key on failure
        """
        from datetime import datetime, timezone

        try:
            content = self._get_memory_content(agent_id)

            # Format memory text (same as AgentMemory)
            memory_text: str
            if success:
                if action_type == "write_artifact":
                    memory_text = f"I created an artifact with details: {details}"
                elif action_type == "read_artifact":
                    memory_text = f"I read an artifact: {details}"
                elif action_type == "transfer":
                    memory_text = f"I transferred credits: {details}"
                else:
                    memory_text = f"I performed {action_type}: {details}"
            else:
                memory_text = f"I tried to {action_type} but failed: {details}"

            entry: MemoryEntry = {
                "tick": tick,
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "content": memory_text,
                "memory_type": "action",
                "tier": tier,
            }
            content["history"].append(entry)
            self._save_memory_content(agent_id, content)
            return {"results": [{"id": f"{agent_id}_{len(content['history'])}"}]}
        except Exception as e:
            logger.warning("Failed to record action for agent %s: %s", agent_id, e)
            return {"error": str(e)}

    def record_observation(self, agent_id: str, observation: str, tick: int = 0, tier: MemoryTier = 3) -> dict[str, Any]:
        """Record an observation as a memory.

        Args:
            agent_id: The agent's ID
            observation: The observation content
            tick: Current simulation tick
            tier: Memory tier (0=pinned, 1=critical, 2=important, 3=normal, 4=low)

        Returns:
            Result dict with "results" key on success, or "error" key on failure
        """
        from datetime import datetime, timezone

        try:
            content = self._get_memory_content(agent_id)
            memory_text = f"I observed: {observation}"
            entry: MemoryEntry = {
                "tick": tick,
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "content": memory_text,
                "memory_type": "observation",
                "tier": tier,
            }
            content["history"].append(entry)
            self._save_memory_content(agent_id, content)
            return {"results": [{"id": f"{agent_id}_{len(content['history'])}"}]}
        except Exception as e:
            logger.warning("Failed to record observation for agent %s: %s", agent_id, e)
            return {"error": str(e)}

    def set_memory_tier(self, agent_id: str, memory_index: int, tier: MemoryTier) -> bool:
        """Set the tier of an existing memory.

        Args:
            agent_id: The agent's ID
            memory_index: Index of the memory in history (0-based)
            tier: New tier (0=pinned, 1=critical, 2=important, 3=normal, 4=low)

        Returns:
            True if successful, False otherwise
        """
        try:
            content = self._get_memory_content(agent_id)
            history = content.get("history", [])

            if memory_index < 0 or memory_index >= len(history):
                return False

            # Check pinned limit if upgrading to pinned
            if tier == 0 and history[memory_index].get("tier", 3) != 0:
                max_pinned = config_get("memory.max_pinned") or 5
                pinned_count = sum(1 for e in history if e.get("tier", 3) == 0)
                if pinned_count >= max_pinned:
                    return False

            history[memory_index]["tier"] = tier
            self._save_memory_content(agent_id, content)
            return True
        except Exception:
            return False

    def get_all_memories(self, agent_id: str) -> list[MemoryEntry]:
        """Get all memories for an agent (full history).

        Args:
            agent_id: The agent's ID

        Returns:
            List of all memory entries
        """
        content = self._get_memory_content(agent_id)
        return content.get("history", [])

    def clear_memories(self, agent_id: str) -> bool:
        """Clear all memories for an agent.

        Args:
            agent_id: The agent's ID

        Returns:
            True if successful, False otherwise
        """
        try:
            content = self._get_memory_content(agent_id)
            content["history"] = []
            self._save_memory_content(agent_id, content)
            return True
        except Exception:
            return False

    def set_knowledge(self, agent_id: str, key: str, value: Any) -> bool:
        """Store structured knowledge for an agent.

        Unlike history (which is append-only), knowledge is a key-value store.

        Args:
            agent_id: The agent's ID
            key: Knowledge key
            value: Knowledge value (must be JSON-serializable)

        Returns:
            True if successful, False otherwise
        """
        try:
            content = self._get_memory_content(agent_id)
            content["knowledge"][key] = value
            self._save_memory_content(agent_id, content)
            return True
        except Exception:
            return False

    def get_knowledge(self, agent_id: str, key: str, default: Any = None) -> Any:
        """Retrieve structured knowledge for an agent.

        Args:
            agent_id: The agent's ID
            key: Knowledge key
            default: Default value if key not found

        Returns:
            The stored value, or default if not found
        """
        content = self._get_memory_content(agent_id)
        return content.get("knowledge", {}).get(key, default)


# Type alias for forward reference
if False:  # TYPE_CHECKING equivalent that works at runtime
    from ..world.artifacts import ArtifactStore
