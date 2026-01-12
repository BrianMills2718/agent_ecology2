"""Tests for AgentMemory functionality.

Tests the memory wrapper around Mem0. Mocks required because:
- mem0.Memory connects to external Qdrant vector database
- mem0.Memory uses Gemini API for embeddings and LLM operations
- Tests must run without network access or API keys

# mock-ok: Mocking Memory class avoids Gemini/Qdrant API calls - tests focus on AgentMemory wrapper logic
"""

import threading
from typing import Any
from unittest.mock import MagicMock, patch, PropertyMock

import pytest


class TestAgentMemoryAdd:
    """Tests for AgentMemory.add method."""

    @patch("src.agents.memory.Memory")
    def test_add_calls_memory_with_content(self, mock_memory_class: MagicMock) -> None:
        """add() passes content and agent_id to underlying memory."""
        # Reset singleton for fresh test
        from src.agents import memory as memory_module
        memory_module.AgentMemory._instance = None
        memory_module._memory = None

        mock_memory = MagicMock()
        mock_memory.add.return_value = {"results": [{"id": "123"}]}
        mock_memory_class.from_config.return_value = mock_memory

        mem = memory_module.AgentMemory()
        result = mem.add("agent_1", "I learned something new")

        mock_memory.add.assert_called_once_with(
            "I learned something new", user_id="agent_1"
        )
        assert result == {"results": [{"id": "123"}]}

    @patch("src.agents.memory.Memory")
    def test_add_returns_error_on_exception(self, mock_memory_class: MagicMock) -> None:
        """add() returns error dict when underlying memory raises."""
        from src.agents import memory as memory_module
        memory_module.AgentMemory._instance = None
        memory_module._memory = None

        mock_memory = MagicMock()
        mock_memory.add.side_effect = Exception("Connection failed")
        mock_memory_class.from_config.return_value = mock_memory

        mem = memory_module.AgentMemory()
        result = mem.add("agent_1", "test content")

        assert "error" in result
        assert "Connection failed" in result["error"]


class TestAgentMemorySearch:
    """Tests for AgentMemory.search method."""

    @patch("src.agents.memory.Memory")
    def test_search_returns_results(self, mock_memory_class: MagicMock) -> None:
        """search() returns results list from memory."""
        from src.agents import memory as memory_module
        memory_module.AgentMemory._instance = None
        memory_module._memory = None

        mock_memory = MagicMock()
        mock_memory.search.return_value = {
            "results": [
                {"memory": "First memory", "score": 0.9},
                {"memory": "Second memory", "score": 0.8},
            ]
        }
        mock_memory_class.from_config.return_value = mock_memory

        mem = memory_module.AgentMemory()
        results = mem.search("agent_1", "query text", limit=5)

        mock_memory.search.assert_called_once_with(
            "query text", user_id="agent_1", limit=5
        )
        assert len(results) == 2
        assert results[0]["memory"] == "First memory"

    @patch("src.agents.memory.Memory")
    def test_search_uses_default_limit(self, mock_memory_class: MagicMock) -> None:
        """search() defaults to limit=5."""
        from src.agents import memory as memory_module
        memory_module.AgentMemory._instance = None
        memory_module._memory = None

        mock_memory = MagicMock()
        mock_memory.search.return_value = {"results": []}
        mock_memory_class.from_config.return_value = mock_memory

        mem = memory_module.AgentMemory()
        mem.search("agent_1", "query")

        mock_memory.search.assert_called_once_with(
            "query", user_id="agent_1", limit=5
        )

    @patch("src.agents.memory.Memory")
    def test_search_returns_empty_on_exception(self, mock_memory_class: MagicMock) -> None:
        """search() returns empty list on exception."""
        from src.agents import memory as memory_module
        memory_module.AgentMemory._instance = None
        memory_module._memory = None

        mock_memory = MagicMock()
        mock_memory.search.side_effect = Exception("Search failed")
        mock_memory_class.from_config.return_value = mock_memory

        mem = memory_module.AgentMemory()
        results = mem.search("agent_1", "query")

        assert results == []

    @patch("src.agents.memory.Memory")
    def test_search_handles_missing_results_key(self, mock_memory_class: MagicMock) -> None:
        """search() handles response without 'results' key."""
        from src.agents import memory as memory_module
        memory_module.AgentMemory._instance = None
        memory_module._memory = None

        mock_memory = MagicMock()
        mock_memory.search.return_value = {}  # No 'results' key
        mock_memory_class.from_config.return_value = mock_memory

        mem = memory_module.AgentMemory()
        results = mem.search("agent_1", "query")

        assert results == []


class TestGetRelevantMemories:
    """Tests for AgentMemory.get_relevant_memories method."""

    @patch("src.agents.memory.Memory")
    def test_formats_memories_as_list(self, mock_memory_class: MagicMock) -> None:
        """get_relevant_memories() formats memories as bullet list."""
        from src.agents import memory as memory_module
        memory_module.AgentMemory._instance = None
        memory_module._memory = None

        mock_memory = MagicMock()
        mock_memory.search.return_value = {
            "results": [
                {"memory": "First thing I remember"},
                {"memory": "Second thing I remember"},
            ]
        }
        mock_memory_class.from_config.return_value = mock_memory

        mem = memory_module.AgentMemory()
        result = mem.get_relevant_memories("agent_1", "context query")

        assert "- First thing I remember" in result
        assert "- Second thing I remember" in result

    @patch("src.agents.memory.Memory")
    def test_returns_no_memories_message(self, mock_memory_class: MagicMock) -> None:
        """get_relevant_memories() returns placeholder when no memories."""
        from src.agents import memory as memory_module
        memory_module.AgentMemory._instance = None
        memory_module._memory = None

        mock_memory = MagicMock()
        mock_memory.search.return_value = {"results": []}
        mock_memory_class.from_config.return_value = mock_memory

        mem = memory_module.AgentMemory()
        result = mem.get_relevant_memories("agent_1", "context")

        assert result == "(No relevant memories)"

    @patch("src.agents.memory.Memory")
    def test_passes_limit_to_search(self, mock_memory_class: MagicMock) -> None:
        """get_relevant_memories() passes limit parameter."""
        from src.agents import memory as memory_module
        memory_module.AgentMemory._instance = None
        memory_module._memory = None

        mock_memory = MagicMock()
        mock_memory.search.return_value = {"results": []}
        mock_memory_class.from_config.return_value = mock_memory

        mem = memory_module.AgentMemory()
        mem.get_relevant_memories("agent_1", "context", limit=10)

        mock_memory.search.assert_called_once_with(
            "context", user_id="agent_1", limit=10
        )


class TestRecordAction:
    """Tests for AgentMemory.record_action method."""

    @patch("src.agents.memory.Memory")
    def test_records_successful_write_artifact(self, mock_memory_class: MagicMock) -> None:
        """record_action() formats write_artifact success correctly."""
        from src.agents import memory as memory_module
        memory_module.AgentMemory._instance = None
        memory_module._memory = None

        mock_memory = MagicMock()
        mock_memory.add.return_value = {"results": []}
        mock_memory_class.from_config.return_value = mock_memory

        mem = memory_module.AgentMemory()
        mem.record_action("agent_1", "write_artifact", "created tool.py", True)

        call_args = mock_memory.add.call_args
        assert "I created an artifact" in call_args[0][0]
        assert "created tool.py" in call_args[0][0]

    @patch("src.agents.memory.Memory")
    def test_records_successful_read_artifact(self, mock_memory_class: MagicMock) -> None:
        """record_action() formats read_artifact success correctly."""
        from src.agents import memory as memory_module
        memory_module.AgentMemory._instance = None
        memory_module._memory = None

        mock_memory = MagicMock()
        mock_memory.add.return_value = {"results": []}
        mock_memory_class.from_config.return_value = mock_memory

        mem = memory_module.AgentMemory()
        mem.record_action("agent_1", "read_artifact", "read config.yaml", True)

        call_args = mock_memory.add.call_args
        assert "I read an artifact" in call_args[0][0]

    @patch("src.agents.memory.Memory")
    def test_records_successful_transfer(self, mock_memory_class: MagicMock) -> None:
        """record_action() formats transfer success correctly."""
        from src.agents import memory as memory_module
        memory_module.AgentMemory._instance = None
        memory_module._memory = None

        mock_memory = MagicMock()
        mock_memory.add.return_value = {"results": []}
        mock_memory_class.from_config.return_value = mock_memory

        mem = memory_module.AgentMemory()
        mem.record_action("agent_1", "transfer", "50 scrip to agent_2", True)

        call_args = mock_memory.add.call_args
        assert "I transferred credits" in call_args[0][0]

    @patch("src.agents.memory.Memory")
    def test_records_other_action_type(self, mock_memory_class: MagicMock) -> None:
        """record_action() handles unknown action types."""
        from src.agents import memory as memory_module
        memory_module.AgentMemory._instance = None
        memory_module._memory = None

        mock_memory = MagicMock()
        mock_memory.add.return_value = {"results": []}
        mock_memory_class.from_config.return_value = mock_memory

        mem = memory_module.AgentMemory()
        mem.record_action("agent_1", "invoke_artifact", "called tool", True)

        call_args = mock_memory.add.call_args
        assert "I performed invoke_artifact" in call_args[0][0]

    @patch("src.agents.memory.Memory")
    def test_records_failed_action(self, mock_memory_class: MagicMock) -> None:
        """record_action() formats failed actions correctly."""
        from src.agents import memory as memory_module
        memory_module.AgentMemory._instance = None
        memory_module._memory = None

        mock_memory = MagicMock()
        mock_memory.add.return_value = {"results": []}
        mock_memory_class.from_config.return_value = mock_memory

        mem = memory_module.AgentMemory()
        mem.record_action("agent_1", "write_artifact", "permission denied", False)

        call_args = mock_memory.add.call_args
        assert "I tried to write_artifact but failed" in call_args[0][0]
        assert "permission denied" in call_args[0][0]


class TestRecordObservation:
    """Tests for AgentMemory.record_observation method."""

    @patch("src.agents.memory.Memory")
    def test_records_observation(self, mock_memory_class: MagicMock) -> None:
        """record_observation() formats observation correctly."""
        from src.agents import memory as memory_module
        memory_module.AgentMemory._instance = None
        memory_module._memory = None

        mock_memory = MagicMock()
        mock_memory.add.return_value = {"results": []}
        mock_memory_class.from_config.return_value = mock_memory

        mem = memory_module.AgentMemory()
        mem.record_observation("agent_1", "agent_2 created a new tool")

        call_args = mock_memory.add.call_args
        assert call_args[0][0] == "I observed: agent_2 created a new tool"
        assert call_args[1]["user_id"] == "agent_1"


class TestAgentMemorySingleton:
    """Tests for AgentMemory singleton pattern."""

    @patch("src.agents.memory.Memory")
    def test_returns_same_instance(self, mock_memory_class: MagicMock) -> None:
        """AgentMemory() returns same instance on multiple calls."""
        from src.agents import memory as memory_module
        memory_module.AgentMemory._instance = None
        memory_module._memory = None

        mock_memory_class.from_config.return_value = MagicMock()

        mem1 = memory_module.AgentMemory()
        mem2 = memory_module.AgentMemory()

        assert mem1 is mem2

    @patch("src.agents.memory.Memory")
    def test_initializes_only_once(self, mock_memory_class: MagicMock) -> None:
        """AgentMemory only calls Memory.from_config once."""
        from src.agents import memory as memory_module
        memory_module.AgentMemory._instance = None
        memory_module._memory = None

        mock_memory_class.from_config.return_value = MagicMock()

        memory_module.AgentMemory()
        memory_module.AgentMemory()
        memory_module.AgentMemory()

        # from_config should only be called once
        assert mock_memory_class.from_config.call_count == 1


class TestGetMemory:
    """Tests for get_memory() global function."""

    @patch("src.agents.memory.Memory")
    def test_returns_agent_memory_instance(self, mock_memory_class: MagicMock) -> None:
        """get_memory() returns AgentMemory instance."""
        from src.agents import memory as memory_module
        memory_module.AgentMemory._instance = None
        memory_module._memory = None

        mock_memory_class.from_config.return_value = MagicMock()

        result = memory_module.get_memory()

        assert isinstance(result, memory_module.AgentMemory)

    @patch("src.agents.memory.Memory")
    def test_returns_same_instance(self, mock_memory_class: MagicMock) -> None:
        """get_memory() returns same instance on multiple calls."""
        from src.agents import memory as memory_module
        memory_module.AgentMemory._instance = None
        memory_module._memory = None

        mock_memory_class.from_config.return_value = MagicMock()

        mem1 = memory_module.get_memory()
        mem2 = memory_module.get_memory()

        assert mem1 is mem2


class TestAgentMemoryConfig:
    """Tests for AgentMemory configuration."""

    @patch.dict("os.environ", {"QDRANT_HOST": "localhost", "QDRANT_PORT": "6334"}, clear=False)
    @patch("src.agents.memory.Memory")
    def test_uses_server_mode_config(self, mock_memory_class: MagicMock) -> None:
        """AgentMemory uses server config when QDRANT_HOST set."""
        from src.agents import memory as memory_module
        memory_module.AgentMemory._instance = None
        memory_module._memory = None

        mock_memory_class.from_config.return_value = MagicMock()

        memory_module.AgentMemory()

        call_args = mock_memory_class.from_config.call_args[0][0]
        vector_config = call_args["vector_store"]["config"]
        assert vector_config["host"] == "localhost"
        assert vector_config["port"] == 6334

    @patch.dict("os.environ", {}, clear=False)
    @patch("src.agents.memory.Memory")
    def test_uses_local_mode_config(self, mock_memory_class: MagicMock) -> None:
        """AgentMemory uses local config when QDRANT_HOST not set."""
        from src.agents import memory as memory_module
        memory_module.AgentMemory._instance = None
        memory_module._memory = None

        # Remove QDRANT_HOST if present
        import os
        os.environ.pop("QDRANT_HOST", None)

        mock_memory_class.from_config.return_value = MagicMock()

        memory_module.AgentMemory()

        call_args = mock_memory_class.from_config.call_args[0][0]
        vector_config = call_args["vector_store"]["config"]
        assert "path" in vector_config
        assert "qdrant_data" in vector_config["path"]


class TestCleanupMemories:
    """Tests for _cleanup_memories function."""

    def test_cleanup_handles_missing_attributes(self) -> None:
        """_cleanup_memories handles memories without _client."""
        from src.agents import memory as memory_module

        # Create mock memory without _client
        mock_mem = MagicMock(spec=memory_module.AgentMemory)
        mock_mem.memory = MagicMock()
        del mock_mem.memory._client  # Remove _client attribute

        # Add to cleanup list
        original_list = memory_module._cleanup_list.copy()
        memory_module._cleanup_list.clear()
        memory_module._cleanup_list.append(mock_mem)

        # Should not raise
        memory_module._cleanup_memories()

        # Restore original list
        memory_module._cleanup_list.clear()
        memory_module._cleanup_list.extend(original_list)

    def test_cleanup_handles_close_exception(self) -> None:
        """_cleanup_memories handles exceptions during close."""
        from src.agents import memory as memory_module

        # Create mock memory with failing close
        mock_mem = MagicMock(spec=memory_module.AgentMemory)
        mock_mem.memory = MagicMock()
        mock_mem.memory._client = MagicMock()
        mock_mem.memory._client.close.side_effect = Exception("Close failed")

        # Add to cleanup list
        original_list = memory_module._cleanup_list.copy()
        memory_module._cleanup_list.clear()
        memory_module._cleanup_list.append(mock_mem)

        # Should not raise
        memory_module._cleanup_memories()

        # Restore original list
        memory_module._cleanup_list.clear()
        memory_module._cleanup_list.extend(original_list)


# =============================================================================
# CAP-004: ArtifactMemory Tests
# =============================================================================


class TestArtifactMemoryBasics:
    """Tests for ArtifactMemory basic operations."""

    @pytest.fixture
    def store(self) -> Any:
        """Create a fresh artifact store."""
        from src.world.artifacts import ArtifactStore
        return ArtifactStore()

    @pytest.fixture
    def artifact_memory(self, store: Any) -> Any:
        """Create an ArtifactMemory instance."""
        from src.agents.memory import ArtifactMemory
        return ArtifactMemory(store)

    def test_add_creates_memory_artifact(self, store: Any, artifact_memory: Any) -> None:
        """add() creates memory artifact if it doesn't exist."""
        result = artifact_memory.add("agent_1", "I learned something")

        assert "error" not in result
        assert "results" in result
        # Memory artifact should be created
        assert store.exists("agent_1_memory")

    def test_add_stores_content(self, store: Any, artifact_memory: Any) -> None:
        """add() stores memory content in artifact."""
        import json

        artifact_memory.add("agent_1", "First memory")
        artifact_memory.add("agent_1", "Second memory")

        artifact = store.get("agent_1_memory")
        assert artifact is not None
        content = json.loads(artifact.content)
        assert len(content["history"]) == 2
        assert content["history"][0]["content"] == "First memory"
        assert content["history"][1]["content"] == "Second memory"

    def test_add_sets_memory_type(self, store: Any, artifact_memory: Any) -> None:
        """add() sets memory_type to 'custom'."""
        import json

        artifact_memory.add("agent_1", "Custom memory")

        artifact = store.get("agent_1_memory")
        content = json.loads(artifact.content)
        assert content["history"][0]["memory_type"] == "custom"


class TestArtifactMemorySearch:
    """Tests for ArtifactMemory search operations."""

    @pytest.fixture
    def store(self) -> Any:
        """Create a fresh artifact store."""
        from src.world.artifacts import ArtifactStore
        return ArtifactStore()

    @pytest.fixture
    def artifact_memory(self, store: Any) -> Any:
        """Create an ArtifactMemory instance."""
        from src.agents.memory import ArtifactMemory
        return ArtifactMemory(store)

    def test_search_returns_recent_memories(self, artifact_memory: Any) -> None:
        """search() returns most recent memories."""
        # Add several memories
        for i in range(10):
            artifact_memory.add("agent_1", f"Memory {i}")

        results = artifact_memory.search("agent_1", "query", limit=3)

        assert len(results) == 3
        # Should return most recent first
        assert results[0]["memory"] == "Memory 9"
        assert results[1]["memory"] == "Memory 8"
        assert results[2]["memory"] == "Memory 7"

    def test_search_with_no_memories(self, artifact_memory: Any) -> None:
        """search() returns empty list for agent with no memories."""
        results = artifact_memory.search("new_agent", "query")
        assert results == []

    def test_search_default_limit(self, artifact_memory: Any) -> None:
        """search() defaults to limit=5."""
        for i in range(10):
            artifact_memory.add("agent_1", f"Memory {i}")

        results = artifact_memory.search("agent_1", "query")
        assert len(results) == 5


class TestArtifactMemoryGetRelevant:
    """Tests for ArtifactMemory.get_relevant_memories method."""

    @pytest.fixture
    def store(self) -> Any:
        """Create a fresh artifact store."""
        from src.world.artifacts import ArtifactStore
        return ArtifactStore()

    @pytest.fixture
    def artifact_memory(self, store: Any) -> Any:
        """Create an ArtifactMemory instance."""
        from src.agents.memory import ArtifactMemory
        return ArtifactMemory(store)

    def test_formats_as_bullet_list(self, artifact_memory: Any) -> None:
        """get_relevant_memories() formats memories as bullet list."""
        artifact_memory.add("agent_1", "First memory")
        artifact_memory.add("agent_1", "Second memory")

        result = artifact_memory.get_relevant_memories("agent_1", "context")

        assert "- Second memory" in result
        assert "- First memory" in result

    def test_returns_no_memories_message(self, artifact_memory: Any) -> None:
        """get_relevant_memories() returns placeholder when empty."""
        result = artifact_memory.get_relevant_memories("empty_agent", "context")
        assert result == "(No relevant memories)"


class TestArtifactMemoryRecordAction:
    """Tests for ArtifactMemory.record_action method."""

    @pytest.fixture
    def store(self) -> Any:
        """Create a fresh artifact store."""
        from src.world.artifacts import ArtifactStore
        return ArtifactStore()

    @pytest.fixture
    def artifact_memory(self, store: Any) -> Any:
        """Create an ArtifactMemory instance."""
        from src.agents.memory import ArtifactMemory
        return ArtifactMemory(store)

    def test_records_write_artifact_success(self, store: Any, artifact_memory: Any) -> None:
        """record_action() formats write_artifact success correctly."""
        import json

        artifact_memory.record_action("agent_1", "write_artifact", "created tool.py", True)

        artifact = store.get("agent_1_memory")
        content = json.loads(artifact.content)
        assert "I created an artifact" in content["history"][0]["content"]
        assert content["history"][0]["memory_type"] == "action"

    def test_records_failed_action(self, store: Any, artifact_memory: Any) -> None:
        """record_action() formats failed actions correctly."""
        import json

        artifact_memory.record_action("agent_1", "transfer", "no funds", False)

        artifact = store.get("agent_1_memory")
        content = json.loads(artifact.content)
        assert "I tried to transfer but failed" in content["history"][0]["content"]

    def test_records_with_tick(self, store: Any, artifact_memory: Any) -> None:
        """record_action() stores tick number."""
        import json

        artifact_memory.record_action("agent_1", "noop", "did nothing", True, tick=42)

        artifact = store.get("agent_1_memory")
        content = json.loads(artifact.content)
        assert content["history"][0]["tick"] == 42


class TestArtifactMemoryRecordObservation:
    """Tests for ArtifactMemory.record_observation method."""

    @pytest.fixture
    def store(self) -> Any:
        """Create a fresh artifact store."""
        from src.world.artifacts import ArtifactStore
        return ArtifactStore()

    @pytest.fixture
    def artifact_memory(self, store: Any) -> Any:
        """Create an ArtifactMemory instance."""
        from src.agents.memory import ArtifactMemory
        return ArtifactMemory(store)

    def test_records_observation(self, store: Any, artifact_memory: Any) -> None:
        """record_observation() formats observation correctly."""
        import json

        artifact_memory.record_observation("agent_1", "agent_2 created a tool")

        artifact = store.get("agent_1_memory")
        content = json.loads(artifact.content)
        assert content["history"][0]["content"] == "I observed: agent_2 created a tool"
        assert content["history"][0]["memory_type"] == "observation"


class TestArtifactMemoryKnowledge:
    """Tests for ArtifactMemory knowledge storage."""

    @pytest.fixture
    def store(self) -> Any:
        """Create a fresh artifact store."""
        from src.world.artifacts import ArtifactStore
        return ArtifactStore()

    @pytest.fixture
    def artifact_memory(self, store: Any) -> Any:
        """Create an ArtifactMemory instance."""
        from src.agents.memory import ArtifactMemory
        return ArtifactMemory(store)

    def test_set_and_get_knowledge(self, artifact_memory: Any) -> None:
        """set_knowledge() and get_knowledge() work correctly."""
        artifact_memory.set_knowledge("agent_1", "favorite_color", "blue")

        result = artifact_memory.get_knowledge("agent_1", "favorite_color")
        assert result == "blue"

    def test_get_knowledge_default(self, artifact_memory: Any) -> None:
        """get_knowledge() returns default for missing keys."""
        result = artifact_memory.get_knowledge("agent_1", "missing_key", default="unknown")
        assert result == "unknown"

    def test_knowledge_survives_history_add(self, artifact_memory: Any) -> None:
        """Knowledge persists after adding history entries."""
        artifact_memory.set_knowledge("agent_1", "key", "value")
        artifact_memory.add("agent_1", "New memory")

        result = artifact_memory.get_knowledge("agent_1", "key")
        assert result == "value"


class TestArtifactMemoryWithAgentArtifact:
    """Tests for ArtifactMemory linked to agent artifacts."""

    @pytest.fixture
    def store(self) -> Any:
        """Create a fresh artifact store with agent and memory artifacts."""
        from src.world.artifacts import (
            ArtifactStore,
            create_agent_artifact,
            create_memory_artifact,
        )

        store = ArtifactStore()

        # Create memory artifact first
        memory = create_memory_artifact(
            memory_id="agent_1_memory",
            owner_id="agent_1",
        )
        store.artifacts[memory.id] = memory

        # Create agent artifact with memory link
        agent = create_agent_artifact(
            agent_id="agent_1",
            owner_id="agent_1",
            agent_config={},
            memory_artifact_id="agent_1_memory",
        )
        store.artifacts[agent.id] = agent

        return store

    @pytest.fixture
    def artifact_memory(self, store: Any) -> Any:
        """Create an ArtifactMemory instance."""
        from src.agents.memory import ArtifactMemory
        return ArtifactMemory(store)

    def test_uses_linked_memory_artifact(self, store: Any, artifact_memory: Any) -> None:
        """ArtifactMemory uses memory_artifact_id from agent artifact."""
        import json

        artifact_memory.add("agent_1", "Memory via link")

        # Should use the linked memory artifact, not create a new one
        memory = store.get("agent_1_memory")
        assert memory is not None
        content = json.loads(memory.content)
        assert len(content["history"]) == 1
        assert content["history"][0]["content"] == "Memory via link"

    def test_memory_owned_by_agent(self, store: Any) -> None:
        """Memory artifact is owned by the agent."""
        memory = store.get("agent_1_memory")
        assert memory is not None
        assert memory.owner_id == "agent_1"


class TestArtifactMemoryHistoryLimit:
    """Tests for ArtifactMemory history limiting."""

    @pytest.fixture
    def store(self) -> Any:
        """Create a fresh artifact store."""
        from src.world.artifacts import ArtifactStore
        return ArtifactStore()

    def test_trims_history_to_max(self, store: Any) -> None:
        """History is trimmed to max_history entries."""
        import json
        from src.agents.memory import ArtifactMemory

        memory = ArtifactMemory(store, max_history=5)

        # Add more than max_history entries
        for i in range(10):
            memory.add("agent_1", f"Memory {i}")

        artifact = store.get("agent_1_memory")
        content = json.loads(artifact.content)

        # Should only have the last 5 entries
        assert len(content["history"]) == 5
        assert content["history"][0]["content"] == "Memory 5"
        assert content["history"][4]["content"] == "Memory 9"


class TestArtifactMemoryClear:
    """Tests for ArtifactMemory.clear_memories method."""

    @pytest.fixture
    def store(self) -> Any:
        """Create a fresh artifact store."""
        from src.world.artifacts import ArtifactStore
        return ArtifactStore()

    @pytest.fixture
    def artifact_memory(self, store: Any) -> Any:
        """Create an ArtifactMemory instance."""
        from src.agents.memory import ArtifactMemory
        return ArtifactMemory(store)

    def test_clear_removes_all_history(self, store: Any, artifact_memory: Any) -> None:
        """clear_memories() removes all history entries."""
        import json

        artifact_memory.add("agent_1", "Memory 1")
        artifact_memory.add("agent_1", "Memory 2")

        result = artifact_memory.clear_memories("agent_1")

        assert result is True
        artifact = store.get("agent_1_memory")
        content = json.loads(artifact.content)
        assert content["history"] == []

    def test_clear_preserves_knowledge(self, store: Any, artifact_memory: Any) -> None:
        """clear_memories() preserves knowledge."""
        artifact_memory.add("agent_1", "Memory")
        artifact_memory.set_knowledge("agent_1", "key", "value")

        artifact_memory.clear_memories("agent_1")

        result = artifact_memory.get_knowledge("agent_1", "key")
        assert result == "value"


class TestAgentWithArtifactMemory:
    """Tests for Agent using artifact-backed memory.

    These tests need to mock config_get since Agent.__init__ calls it.
    """

    @pytest.fixture
    def store(self) -> Any:
        """Create a fresh artifact store."""
        from src.world.artifacts import ArtifactStore
        return ArtifactStore()

    @pytest.fixture
    def mock_config(self) -> Any:
        """Mock config_get to avoid loading config.yaml."""
        with patch("src.agents.agent.config_get") as mock:
            mock.return_value = None  # Use defaults
            yield mock

    @pytest.fixture
    def mock_mem0(self) -> Any:
        """Mock Mem0 Memory to avoid external dependencies."""
        with patch("src.agents.memory.Memory") as mock:
            mock.from_config.return_value = MagicMock()
            yield mock

    def test_agent_uses_artifact_memory_when_store_provided(
        self, store: Any, mock_config: Any, mock_mem0: Any
    ) -> None:
        """Agent uses ArtifactMemory when artifact_store is provided."""
        from src.agents.agent import Agent
        from src.agents.memory import ArtifactMemory

        agent = Agent(
            agent_id="test_agent",
            llm_model="test-model",
            artifact_store=store,
        )

        assert agent.uses_artifact_memory is True
        assert isinstance(agent.memory, ArtifactMemory)

    def test_agent_uses_mem0_when_no_store(
        self, mock_config: Any, mock_mem0: Any
    ) -> None:
        """Agent uses AgentMemory (Mem0) when no artifact_store."""
        # Reset singleton for fresh test
        from src.agents import memory as memory_module
        memory_module.AgentMemory._instance = None
        memory_module._memory = None

        from src.agents.agent import Agent

        agent = Agent(
            agent_id="test_agent",
            llm_model="test-model",
        )

        assert agent.uses_artifact_memory is False

    def test_agent_memory_artifact_created(
        self, store: Any, mock_config: Any, mock_mem0: Any
    ) -> None:
        """Agent's memory artifact is created on first use."""
        from src.agents.agent import Agent

        agent = Agent(
            agent_id="test_agent",
            llm_model="test-model",
            artifact_store=store,
        )

        # Trigger memory creation
        agent.memory.add("test_agent", "Test memory")

        assert store.exists("test_agent_memory")

    def test_agent_from_artifact_uses_artifact_memory(
        self, store: Any, mock_config: Any, mock_mem0: Any
    ) -> None:
        """Agent.from_artifact uses ArtifactMemory when store provided."""
        from src.agents.agent import Agent
        from src.agents.memory import ArtifactMemory
        from src.world.artifacts import create_agent_artifact, create_memory_artifact

        # Create memory first
        memory = create_memory_artifact(
            memory_id="linked_agent_memory",
            owner_id="linked_agent",
        )
        store.artifacts[memory.id] = memory

        # Create agent with memory link
        artifact = create_agent_artifact(
            agent_id="linked_agent",
            owner_id="linked_agent",
            agent_config={"llm_model": "test-model"},
            memory_artifact_id="linked_agent_memory",
        )
        store.artifacts[artifact.id] = artifact

        agent = Agent.from_artifact(artifact, store=store)

        assert agent.uses_artifact_memory is True
        assert isinstance(agent.memory, ArtifactMemory)
        assert agent.memory_artifact_id == "linked_agent_memory"
