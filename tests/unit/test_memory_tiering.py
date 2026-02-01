"""Tests for memory tiering (Plan #196).

Tests that memories can be assigned tiers and that retrieval
prioritizes pinned/critical memories appropriately.
"""
import pytest
from unittest.mock import MagicMock, patch

from src.agents.memory import (
    ArtifactMemory,
    MemoryTier,
    TIER_NAMES,
    TIER_VALUES,
)


class TestMemoryTierConstants:
    """Test tier constants are properly defined."""

    def test_tier_names_mapping(self) -> None:
        """Verify tier name mapping is correct."""
        assert TIER_NAMES[0] == "pinned"
        assert TIER_NAMES[1] == "critical"
        assert TIER_NAMES[2] == "important"
        assert TIER_NAMES[3] == "normal"
        assert TIER_NAMES[4] == "low"

    def test_tier_values_mapping(self) -> None:
        """Verify tier value mapping is reverse of names."""
        assert TIER_VALUES["pinned"] == 0
        assert TIER_VALUES["critical"] == 1
        assert TIER_VALUES["important"] == 2
        assert TIER_VALUES["normal"] == 3
        assert TIER_VALUES["low"] == 4


class TestArtifactMemoryTiering:
    """Test ArtifactMemory with tiering support."""

    @pytest.fixture
    def mock_store(self) -> MagicMock:
        """Create a mock artifact store."""
        store = MagicMock()
        store.artifacts = {}
        # Make get() look up from artifacts dict
        store.get.side_effect = lambda key: store.artifacts.get(key)
        return store

    @pytest.fixture
    def memory(self, mock_store: MagicMock) -> ArtifactMemory:
        """Create an ArtifactMemory instance."""
        return ArtifactMemory(mock_store)

    def test_add_memory_with_default_tier(self, memory: ArtifactMemory) -> None:
        """Adding memory without tier should use normal (3)."""
        result = memory.add("agent1", "test memory")
        assert "results" in result

        # Check tier in stored memory
        content = memory._get_memory_content("agent1")
        assert len(content["history"]) == 1
        assert content["history"][0]["tier"] == 3  # normal

    def test_add_memory_with_pinned_tier(self, memory: ArtifactMemory) -> None:
        """Adding memory with pinned tier should work."""
        result = memory.add("agent1", "important info", tier=0)
        assert "results" in result

        content = memory._get_memory_content("agent1")
        assert content["history"][0]["tier"] == 0  # pinned

    def test_add_memory_with_critical_tier(self, memory: ArtifactMemory) -> None:
        """Adding memory with critical tier should work."""
        result = memory.add("agent1", "critical info", tier=1)
        assert "results" in result

        content = memory._get_memory_content("agent1")
        assert content["history"][0]["tier"] == 1  # critical

    @patch("src.agents.memory.config_get")  # mock-ok: config requires filesystem setup
    def test_pinned_limit_enforced(self, mock_config: MagicMock, memory: ArtifactMemory) -> None:
        """Should reject pinned memories when limit is reached."""
        mock_config.return_value = 2  # max 2 pinned

        # Add 2 pinned memories (should succeed)
        result1 = memory.add("agent1", "pinned 1", tier=0)
        result2 = memory.add("agent1", "pinned 2", tier=0)
        assert "results" in result1
        assert "results" in result2

        # Third pinned should fail
        result3 = memory.add("agent1", "pinned 3", tier=0)
        assert "error" in result3
        assert "Maximum pinned" in result3["error"]

    def test_get_pinned_memories(self, memory: ArtifactMemory) -> None:
        """get_pinned_memories should return only tier 0 memories."""
        # Add mixed tier memories
        memory.add("agent1", "normal memory", tier=3)
        memory.add("agent1", "pinned memory 1", tier=0)
        memory.add("agent1", "critical memory", tier=1)
        memory.add("agent1", "pinned memory 2", tier=0)
        memory.add("agent1", "low memory", tier=4)

        pinned = memory.get_pinned_memories("agent1")
        assert len(pinned) == 2
        assert all(m["tier"] == 0 for m in pinned)
        assert "pinned memory 1" in pinned[0]["memory"]
        assert "pinned memory 2" in pinned[1]["memory"]

    def test_search_tier_boosting(self, memory: ArtifactMemory) -> None:
        """Search should boost scores based on tier.

        Note: ArtifactMemory combines recency score with tier boost.
        This test verifies that tier boosts dominate the ordering
        for pinned and critical memories.
        """
        # Add memories in order: normal, low, critical, pinned
        memory.add("agent1", "normal memory", tier=3)
        memory.add("agent1", "low priority", tier=4)
        memory.add("agent1", "critical info", tier=1)
        memory.add("agent1", "pinned always", tier=0)

        # Search should return them boosted by tier
        results = memory.search("agent1", "anything", limit=4)
        assert len(results) == 4

        # Pinned should be first (highest boosted score: +1.0)
        assert results[0]["tier"] == 0
        # Critical should be second (+0.3 boost)
        assert results[1]["tier"] == 1
        # Low and normal: low has higher recency but -0.1 penalty
        # Since low was added second (index 1, recency=0.25) and normal first (index 0, recency=0),
        # low ends up with 0.25-0.1=0.15 > normal with 0+0=0
        assert results[2]["tier"] == 4
        assert results[3]["tier"] == 3

    def test_get_relevant_memories_includes_pinned_first(self, memory: ArtifactMemory) -> None:
        """get_relevant_memories should always include pinned first."""
        # Add memories
        memory.add("agent1", "normal 1", tier=3)
        memory.add("agent1", "normal 2", tier=3)
        memory.add("agent1", "pinned important", tier=0)
        memory.add("agent1", "normal 3", tier=3)

        result = memory.get_relevant_memories("agent1", "context", limit=2)

        # Should include pinned memory with label
        assert "[pinned]" in result
        assert "pinned important" in result

    def test_get_relevant_memories_tier_labels(self, memory: ArtifactMemory) -> None:
        """Non-normal tiers should have labels in output."""
        memory.add("agent1", "pinned info", tier=0)
        memory.add("agent1", "critical info", tier=1)
        memory.add("agent1", "normal info", tier=3)
        memory.add("agent1", "low info", tier=4)

        result = memory.get_relevant_memories("agent1", "context", limit=10)

        assert "[pinned]" in result
        assert "[critical]" in result
        assert "[low]" in result
        # Normal tier should NOT have a label
        assert "- normal info" in result  # No tier label

    def test_set_memory_tier(self, memory: ArtifactMemory) -> None:
        """Should be able to change tier of existing memory."""
        memory.add("agent1", "test memory", tier=3)

        # Change to critical
        success = memory.set_memory_tier("agent1", 0, tier=1)
        assert success is True

        content = memory._get_memory_content("agent1")
        assert content["history"][0]["tier"] == 1

    def test_set_memory_tier_invalid_index(self, memory: ArtifactMemory) -> None:
        """Setting tier on non-existent memory should fail."""
        memory.add("agent1", "test memory", tier=3)

        success = memory.set_memory_tier("agent1", 99, tier=0)
        assert success is False

    @patch("src.agents.memory.config_get")  # mock-ok: config requires filesystem setup
    def test_set_memory_tier_respects_pinned_limit(
        self, mock_config: MagicMock, memory: ArtifactMemory
    ) -> None:
        """Upgrading to pinned should respect limit."""
        mock_config.return_value = 1  # max 1 pinned

        memory.add("agent1", "already pinned", tier=0)
        memory.add("agent1", "normal memory", tier=3)

        # Try to upgrade second memory to pinned
        success = memory.set_memory_tier("agent1", 1, tier=0)
        assert success is False  # Should fail - limit reached

    def test_record_action_with_tier(self, memory: ArtifactMemory) -> None:
        """record_action should accept tier parameter."""
        result = memory.record_action("agent1", "read_artifact", "test", True, tick=1, tier=1)
        assert "results" in result

        content = memory._get_memory_content("agent1")
        assert content["history"][0]["tier"] == 1

    def test_record_observation_with_tier(self, memory: ArtifactMemory) -> None:
        """record_observation should accept tier parameter."""
        result = memory.record_observation("agent1", "something happened", tick=1, tier=2)
        assert "results" in result

        content = memory._get_memory_content("agent1")
        assert content["history"][0]["tier"] == 2


class TestAgentMemoryTiering:
    """Test AgentMemory (Mem0-based) with tiering support.

    These tests mock the Mem0 Memory class since we can't run
    actual Mem0/Qdrant in unit tests.
    """

    @pytest.fixture
    def mock_mem0(self) -> MagicMock:
        """Create a mock Mem0 Memory instance."""
        mock = MagicMock()
        mock.add.return_value = {"results": [{"id": "test_id"}]}
        mock.search.return_value = {"results": []}
        return mock

    @patch("src.agents.memory.Memory")  # mock-ok: Mem0 Memory requires external service
    @patch("src.agents.memory.config_get")  # mock-ok: config requires filesystem setup
    def test_add_passes_tier_as_metadata(
        self, mock_config: MagicMock, mock_memory_class: MagicMock, mock_mem0: MagicMock
    ) -> None:
        """Adding memory should pass tier as metadata to Mem0."""
        mock_config.return_value = None
        mock_memory_class.from_config.return_value = mock_mem0

        # Import after mocking to get mocked Memory class
        from src.agents.memory import AgentMemory

        # Clear singleton for test
        AgentMemory._instance = None

        memory = AgentMemory()
        memory.add("agent1", "test content", tier=1)

        # Verify add was called with metadata containing tier
        mock_mem0.add.assert_called_once()
        call_kwargs = mock_mem0.add.call_args
        assert call_kwargs[1]["metadata"]["tier"] == 1
