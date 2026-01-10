"""
Agent Memory using Mem0

Provides persistent memory for each agent across ticks.
"""

import os
import atexit
from pathlib import Path
from dotenv import load_dotenv
from mem0 import Memory

load_dotenv()

# Track memory instances for cleanup
_cleanup_list = []

def _cleanup_memories():
    """Cleanup handler to close qdrant clients properly"""
    for mem in _cleanup_list:
        try:
            if hasattr(mem, 'memory') and hasattr(mem.memory, '_client'):
                mem.memory._client.close()
        except Exception:
            pass

atexit.register(_cleanup_memories)


class AgentMemory:
    """Shared memory manager for all agents using Mem0"""

    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if self._initialized:
            return

        api_key = os.getenv('GEMINI_API_KEY')

        # Check if running with qdrant server (Docker) or local mode
        qdrant_host = os.getenv('QDRANT_HOST')
        qdrant_port = int(os.getenv('QDRANT_PORT', '6333'))

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
            project_root = Path(__file__).parent.parent.parent
            qdrant_path = project_root / 'qdrant_data'
            qdrant_path.mkdir(exist_ok=True)
            vector_store_config = {
                'provider': 'qdrant',
                'config': {
                    'collection_name': 'agent_memories',
                    'embedding_model_dims': 768,
                    'path': str(qdrant_path)
                }
            }

        config = {
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
                    'model': 'gemini-2.0-flash',
                    'api_key': api_key,
                    'temperature': 0.1
                }
            },
            'vector_store': vector_store_config
        }

        self.memory = Memory.from_config(config)
        self._initialized = True
        _cleanup_list.append(self)

    def add(self, agent_id: str, content: str) -> dict:
        """Add a memory for an agent"""
        try:
            result = self.memory.add(content, user_id=agent_id)
            return result
        except Exception as e:
            return {"error": str(e)}

    def search(self, agent_id: str, query: str, limit: int = 5) -> list:
        """Search memories for an agent"""
        try:
            results = self.memory.search(query, user_id=agent_id, limit=limit)
            return results.get('results', [])
        except Exception as e:
            return []

    def get_relevant_memories(self, agent_id: str, context: str, limit: int = 5) -> str:
        """Get relevant memories formatted as a string for prompt injection"""
        memories = self.search(agent_id, context, limit=limit)

        if not memories:
            return "(No relevant memories)"

        lines = []
        for m in memories:
            memory_text = m.get('memory', '')
            lines.append(f"- {memory_text}")

        return "\n".join(lines)

    def record_action(self, agent_id: str, action_type: str, details: str, success: bool):
        """Record an action as a memory"""
        # Use simpler format for better memory extraction by Mem0's LLM
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

    def record_observation(self, agent_id: str, observation: str):
        """Record an observation as a memory"""
        memory = f"I observed: {observation}"
        return self.add(agent_id, memory)


# Global instance
_memory = None


def get_memory() -> AgentMemory:
    """Get the global memory instance"""
    global _memory
    if _memory is None:
        _memory = AgentMemory()
    return _memory
