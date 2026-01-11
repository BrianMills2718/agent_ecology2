"""Tests for AgentMemory functionality.

Tests the memory wrapper around Mem0. Mocks required because:
- mem0.Memory connects to external Qdrant vector database
- mem0.Memory uses Gemini API for embeddings and LLM operations
- Tests must run without network access or API keys
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
