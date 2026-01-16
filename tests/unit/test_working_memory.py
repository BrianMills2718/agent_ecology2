"""Tests for agent working memory functionality (Plan #59)."""

import pytest
import json
from unittest.mock import MagicMock, patch

from src.agents.agent import Agent


# mock-ok: Mem0 requires API keys; we're testing working memory logic not memory system
@pytest.fixture(autouse=True)
def mock_memory():
    """Mock the memory system to avoid API key requirements."""
    with patch("src.agents.agent.get_memory") as mock:
        mock.return_value = MagicMock()
        yield mock


class TestWorkingMemoryInjection:
    """Test working memory injection into prompts."""

    @pytest.mark.plans([59])
    def test_working_memory_injection_enabled(self) -> None:
        """Working memory should be injected into prompt when enabled."""
        agent = Agent(
            agent_id="test",
            llm_model="gemini/gemini-3-flash-preview",
            inject_working_memory=True,
        )

        # Set working memory on the agent's artifact content
        agent._working_memory = {
            "current_goal": "Build a price oracle",
            "progress": {"stage": "Planning", "completed": []},
            "lessons": ["Start simple"],
        }

        world_state = {"tick": 1, "balances": {"test": 100}}
        prompt = agent.build_prompt(world_state)

        # Working memory should appear in prompt
        assert "Working Memory" in prompt or "working_memory" in prompt.lower()
        assert "Build a price oracle" in prompt
        assert "Planning" in prompt

    @pytest.mark.plans([59])
    def test_working_memory_injection_disabled(self) -> None:
        """Working memory should NOT be injected when disabled."""
        agent = Agent(
            agent_id="test",
            llm_model="gemini/gemini-3-flash-preview",
            inject_working_memory=False,
        )

        # Set working memory - but it shouldn't appear
        agent._working_memory = {
            "current_goal": "Build a price oracle",
            "progress": {"stage": "Planning"},
        }

        world_state = {"tick": 1, "balances": {"test": 100}}
        prompt = agent.build_prompt(world_state)

        # Working memory should NOT appear in prompt
        assert "Build a price oracle" not in prompt

    @pytest.mark.plans([59])
    def test_working_memory_default_disabled(self) -> None:
        """Working memory injection should be disabled by default."""
        agent = Agent(
            agent_id="test",
            llm_model="gemini/gemini-3-flash-preview",
        )

        # Default should be False (configurable)
        assert agent.inject_working_memory is False


class TestWorkingMemorySizeLimit:
    """Test working memory size constraints."""

    @pytest.mark.plans([59])
    def test_working_memory_size_limit(self) -> None:
        """Large working memory should be truncated to max_size_bytes."""
        max_size = 500  # bytes
        agent = Agent(
            agent_id="test",
            llm_model="gemini/gemini-3-flash-preview",
            inject_working_memory=True,
            working_memory_max_bytes=max_size,
        )

        # Create a large working memory
        large_memory = {
            "current_goal": "A" * 1000,  # Way over limit
            "lessons": ["B" * 500],
        }
        agent._working_memory = large_memory

        # Get the formatted memory for injection
        formatted = agent._format_working_memory()

        # Should be truncated to max size
        assert len(formatted.encode("utf-8")) <= max_size + 50  # Allow some header overhead

    @pytest.mark.plans([59])
    def test_working_memory_small_fits(self) -> None:
        """Small working memory should not be truncated."""
        agent = Agent(
            agent_id="test",
            llm_model="gemini/gemini-3-flash-preview",
            inject_working_memory=True,
            working_memory_max_bytes=2000,
        )

        small_memory = {
            "current_goal": "Test goal",
            "progress": {"stage": "Done"},
        }
        agent._working_memory = small_memory

        formatted = agent._format_working_memory()

        # Should contain the full content
        assert "Test goal" in formatted
        assert "Done" in formatted


class TestWorkingMemoryGracefulHandling:
    """Test graceful handling of missing/invalid working memory."""

    @pytest.mark.plans([59])
    def test_working_memory_missing_graceful(self) -> None:
        """Agent should not crash if working_memory is absent."""
        agent = Agent(
            agent_id="test",
            llm_model="gemini/gemini-3-flash-preview",
            inject_working_memory=True,
        )

        # No working memory set (None)
        assert agent._working_memory is None

        world_state = {"tick": 1, "balances": {"test": 100}}

        # Should not crash
        prompt = agent.build_prompt(world_state)
        assert isinstance(prompt, str)

    @pytest.mark.plans([59])
    def test_working_memory_empty_dict_graceful(self) -> None:
        """Agent should handle empty working memory dict gracefully."""
        agent = Agent(
            agent_id="test",
            llm_model="gemini/gemini-3-flash-preview",
            inject_working_memory=True,
        )

        agent._working_memory = {}

        world_state = {"tick": 1, "balances": {"test": 100}}
        prompt = agent.build_prompt(world_state)

        # Should not crash, prompt should be valid
        assert isinstance(prompt, str)


class TestWorkingMemoryFromArtifact:
    """Test loading working memory from agent artifact."""

    @pytest.mark.plans([59])
    def test_get_working_memory_from_content(self) -> None:
        """Agent should extract working_memory from artifact content."""
        agent = Agent(
            agent_id="test",
            llm_model="gemini/gemini-3-flash-preview",
            inject_working_memory=True,
        )

        # Simulate artifact content with working_memory
        artifact_content = {
            "model": "gemini-3-flash",
            "system_prompt": "You are a trader",
            "working_memory": {
                "current_goal": "Accumulate scrip",
                "progress": {"stage": "Execution"},
            },
        }

        memory = agent._extract_working_memory(artifact_content)

        assert memory is not None
        assert memory["current_goal"] == "Accumulate scrip"

    @pytest.mark.plans([59])
    def test_get_working_memory_missing_key(self) -> None:
        """Should return None if working_memory key is missing."""
        agent = Agent(
            agent_id="test",
            llm_model="gemini/gemini-3-flash-preview",
            inject_working_memory=True,
        )

        artifact_content = {
            "model": "gemini-3-flash",
            "system_prompt": "You are a trader",
            # No working_memory key
        }

        memory = agent._extract_working_memory(artifact_content)
        assert memory is None
