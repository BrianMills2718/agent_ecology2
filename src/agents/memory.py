"""
Agent Memory using Mem0

Provides persistent memory for each agent across ticks.
"""

import logging
import os
import atexit
import threading
from pathlib import Path
from typing import Any, TypedDict

logger = logging.getLogger(__name__)

from dotenv import load_dotenv
from mem0 import Memory  # type: ignore[import-untyped,unused-ignore]

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
    """Shared memory manager for all agents using Mem0"""

    _instance: "AgentMemory | None" = None
    _lock: threading.Lock = threading.Lock()
    _initialized: bool
    memory: Memory

    def __new__(cls) -> "AgentMemory":
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

        api_key: str | None = os.getenv('GEMINI_API_KEY')

        # Check if running with qdrant server (Docker) or local mode
        qdrant_host: str | None = os.getenv('QDRANT_HOST')
        qdrant_port: int = int(os.getenv('QDRANT_PORT', '6333'))

        vector_store_config: VectorStoreSection
        if qdrant_host:
            # Server mode (Docker)
            vector_store_config = {
                'provider': 'qdrant',
                'config': {
                    'collection_name': 'agent_memories',
                    'embedding_model_dims': 768,
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
                    'collection_name': 'agent_memories',
                    'embedding_model_dims': 768,
                    'path': str(qdrant_path)
                }
            }

        config: MemoryConfig = {
            'embedder': {
                'provider': 'gemini',
                'config': {
                    'model': 'models/text-embedding-004',
                    'api_key': api_key,
                    'embedding_dims': 768
                }
            },
            'llm': {
                'provider': 'gemini',
                'config': {
                    'model': 'gemini-3-flash-preview',
                    'api_key': api_key,
                    'temperature': 0.1
                }
            },
            'vector_store': vector_store_config
        }

        self.memory = Memory.from_config(config)
        self._initialized = True
        _cleanup_list.append(self)

    def add(self, agent_id: str, content: str) -> dict[str, Any]:
        """Add a memory for an agent"""
        try:
            result: Any = self.memory.add(content, user_id=agent_id)
            return result  # type: ignore[no-any-return]
        except Exception as e:
            return {"error": str(e)}

    def search(self, agent_id: str, query: str, limit: int = 5) -> list[dict[str, Any]]:
        """Search memories for an agent"""
        try:
            results: Any = self.memory.search(query, user_id=agent_id, limit=limit)
            return results.get('results', [])  # type: ignore[no-any-return]
        except Exception as e:
            logger.warning("Memory search failed for agent %s: %s", agent_id, e)
            return []

    def get_relevant_memories(self, agent_id: str, context: str, limit: int = 5) -> str:
        """Get relevant memories formatted as a string for prompt injection"""
        memories: list[dict[str, Any]] = self.search(agent_id, context, limit=limit)

        if not memories:
            return "(No relevant memories)"

        lines: list[str] = []
        for m in memories:
            memory_text: Any = m.get('memory', '')
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
    """Get the global memory instance"""
    global _memory
    if _memory is None:
        _memory = AgentMemory()
    return _memory
