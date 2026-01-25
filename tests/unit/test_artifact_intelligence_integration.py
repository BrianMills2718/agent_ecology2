"""Tests for Plan #146 Phase 4: Artifact Intelligence Integration.

Tests the integration of personality prompts and long-term memory artifacts
into the agent's build_prompt() method.
"""

from __future__ import annotations

import pytest
from typing import Any
from unittest.mock import MagicMock

from src.agents.agent import Agent


class TestPersonalityPromptArtifactIntegration:
    """Tests for personality prompt artifact integration in build_prompt()."""

    def test_uses_default_system_prompt_when_no_artifact_configured(self) -> None:
        """Agent uses self.system_prompt when no personality_prompt_artifact_id set."""
        agent = Agent(
            agent_id="test_agent",
            llm_model="gpt-4",
            system_prompt="Default system prompt",
        )

        # Build prompt
        world_state: dict[str, Any] = {
            "tick": 1,
            "balances": {"test_agent": 100},
            "artifacts": [],
        }
        prompt = agent.build_prompt(world_state)

        assert "Default system prompt" in prompt

    def test_loads_personality_prompt_from_artifact_when_configured(self) -> None:
        """Agent loads prompt from artifact when personality_prompt_artifact_id is set."""
        # Create mock artifact store
        mock_store = MagicMock()
        mock_artifact = MagicMock()
        mock_artifact.content = "Custom personality from artifact"
        mock_store.get.return_value = mock_artifact

        agent = Agent(
            agent_id="test_agent",
            llm_model="gpt-4",
            system_prompt="Default system prompt",
            artifact_store=mock_store,
        )
        agent.personality_prompt_artifact_id = "my_personality_artifact"

        # Build prompt
        world_state: dict[str, Any] = {
            "tick": 1,
            "balances": {"test_agent": 100},
            "artifacts": [],
        }
        prompt = agent.build_prompt(world_state)

        # Should use artifact prompt, not default
        assert "Custom personality from artifact" in prompt
        assert "Default system prompt" not in prompt
        mock_store.get.assert_called_with("my_personality_artifact")

    def test_falls_back_to_system_prompt_when_artifact_not_found(self) -> None:
        """Agent falls back to system_prompt when artifact not found."""
        # Create mock artifact store that returns None
        mock_store = MagicMock()
        mock_store.get.return_value = None

        agent = Agent(
            agent_id="test_agent",
            llm_model="gpt-4",
            system_prompt="Default system prompt",
            artifact_store=mock_store,
        )
        agent.personality_prompt_artifact_id = "missing_artifact"

        # Build prompt
        world_state: dict[str, Any] = {
            "tick": 1,
            "balances": {"test_agent": 100},
            "artifacts": [],
        }
        prompt = agent.build_prompt(world_state)

        # Should fall back to default
        assert "Default system prompt" in prompt

    def test_handles_dict_content_with_template_field(self) -> None:
        """Agent extracts template from dict content in prompt artifact."""
        mock_store = MagicMock()
        mock_artifact = MagicMock()
        mock_artifact.content = {
            "template": "Template from dict content",
            "variables": ["var1", "var2"],
        }
        mock_store.get.return_value = mock_artifact

        agent = Agent(
            agent_id="test_agent",
            llm_model="gpt-4",
            system_prompt="Default system prompt",
            artifact_store=mock_store,
        )
        agent.personality_prompt_artifact_id = "dict_prompt_artifact"

        world_state: dict[str, Any] = {
            "tick": 1,
            "balances": {"test_agent": 100},
            "artifacts": [],
        }
        prompt = agent.build_prompt(world_state)

        assert "Template from dict content" in prompt


class TestLongtermMemoryArtifactIntegration:
    """Tests for long-term memory artifact integration in build_prompt()."""

    def test_no_longterm_memory_section_when_not_configured(self) -> None:
        """No long-term memory section when longterm_memory_artifact_id not set."""
        agent = Agent(
            agent_id="test_agent",
            llm_model="gpt-4",
            system_prompt="Test prompt",
        )

        world_state: dict[str, Any] = {
            "tick": 1,
            "balances": {"test_agent": 100},
            "artifacts": [],
        }
        prompt = agent.build_prompt(world_state)

        assert "Long-term Memory" not in prompt

    def test_searches_longterm_memory_artifact_when_configured(self) -> None:
        """Agent searches longterm memory artifact and includes results in prompt."""
        mock_store = MagicMock()
        mock_memory_artifact = MagicMock()
        # Entries must contain keywords that will be in the search query
        # Search query is built from: agent_id, tick, balance, last_action_info
        # So entries should match "test_agent", "tick", "balance", etc.
        mock_memory_artifact.content = {
            "entries": [
                {
                    "text": "At tick 5, I increased my balance by trading",
                    "tags": ["tick", "balance"],
                },
                {
                    "text": "test_agent strategy: focus on building artifacts",
                    "tags": ["strategy"],
                },
            ]
        }
        mock_store.get.return_value = mock_memory_artifact

        agent = Agent(
            agent_id="test_agent",
            llm_model="gpt-4",
            system_prompt="Test prompt",
            artifact_store=mock_store,
        )
        agent.longterm_memory_artifact_id = "test_agent_longterm_memory"

        world_state: dict[str, Any] = {
            "tick": 1,
            "balances": {"test_agent": 100},
            "artifacts": [],
        }
        prompt = agent.build_prompt(world_state)

        # Should include long-term memory section with matching entries
        assert "Long-term Memory" in prompt

    def test_keyword_matching_finds_relevant_memories(self) -> None:
        """Memory search finds entries matching query keywords."""
        mock_store = MagicMock()
        mock_memory_artifact = MagicMock()
        mock_memory_artifact.content = {
            "entries": [
                {"text": "Trading with beta is profitable", "tags": ["trading"]},
                {"text": "Unrelated entry about weather", "tags": ["weather"]},
                {"text": "Scrip balance increased after trading", "tags": ["trading"]},
            ]
        }
        mock_store.get.return_value = mock_memory_artifact

        agent = Agent(
            agent_id="test_agent",
            llm_model="gpt-4",
            system_prompt="Test prompt",
            artifact_store=mock_store,
        )
        agent.longterm_memory_artifact_id = "test_memory"

        # Test the search method directly
        results = agent._search_longterm_memory_artifact("trading scrip", limit=5)

        # Should find entries with "trading" or "scrip" keywords
        assert len(results) >= 2
        texts = [r["text"] for r in results]
        assert any("trading" in t.lower() for t in texts)

    def test_empty_memory_returns_no_section(self) -> None:
        """No section when memory artifact has no entries."""
        mock_store = MagicMock()
        mock_memory_artifact = MagicMock()
        mock_memory_artifact.content = {"entries": []}
        mock_store.get.return_value = mock_memory_artifact

        agent = Agent(
            agent_id="test_agent",
            llm_model="gpt-4",
            system_prompt="Test prompt",
            artifact_store=mock_store,
        )
        agent.longterm_memory_artifact_id = "empty_memory"

        world_state: dict[str, Any] = {
            "tick": 1,
            "balances": {"test_agent": 100},
            "artifacts": [],
        }
        prompt = agent.build_prompt(world_state)

        # Should not include long-term memory section when empty
        assert "Long-term Memory" not in prompt


class TestLoadPersonalityPromptFromArtifact:
    """Direct tests for _load_personality_prompt_from_artifact method."""

    def test_returns_none_when_no_artifact_id(self) -> None:
        """Returns None when personality_prompt_artifact_id not set."""
        agent = Agent(
            agent_id="test_agent",
            llm_model="gpt-4",
            system_prompt="Test",
        )
        result = agent._load_personality_prompt_from_artifact()
        assert result is None

    def test_returns_none_when_no_artifact_store(self) -> None:
        """Returns None when no artifact_store available."""
        agent = Agent(
            agent_id="test_agent",
            llm_model="gpt-4",
            system_prompt="Test",
        )
        agent._personality_prompt_artifact_id = "some_artifact"
        # No artifact_store set
        result = agent._load_personality_prompt_from_artifact()
        assert result is None

    def test_returns_string_content_directly(self) -> None:
        """Returns string content directly from artifact."""
        mock_store = MagicMock()
        mock_artifact = MagicMock()
        mock_artifact.content = "Direct string prompt"
        mock_store.get.return_value = mock_artifact

        agent = Agent(
            agent_id="test_agent",
            llm_model="gpt-4",
            system_prompt="Test",
            artifact_store=mock_store,
        )
        agent._personality_prompt_artifact_id = "prompt_artifact"

        result = agent._load_personality_prompt_from_artifact()
        assert result == "Direct string prompt"

    def test_extracts_template_from_dict_content(self) -> None:
        """Extracts 'template' field from dict content."""
        mock_store = MagicMock()
        mock_artifact = MagicMock()
        mock_artifact.content = {
            "template": "Template content here",
            "other_field": "ignored",
        }
        mock_store.get.return_value = mock_artifact

        agent = Agent(
            agent_id="test_agent",
            llm_model="gpt-4",
            system_prompt="Test",
            artifact_store=mock_store,
        )
        agent._personality_prompt_artifact_id = "prompt_artifact"

        result = agent._load_personality_prompt_from_artifact()
        assert result == "Template content here"


class TestSearchLongtermMemoryArtifact:
    """Direct tests for _search_longterm_memory_artifact method."""

    def test_returns_empty_when_no_artifact_id(self) -> None:
        """Returns empty list when longterm_memory_artifact_id not set."""
        agent = Agent(
            agent_id="test_agent",
            llm_model="gpt-4",
            system_prompt="Test",
        )
        results = agent._search_longterm_memory_artifact("query")
        assert results == []

    def test_returns_empty_when_artifact_not_found(self) -> None:
        """Returns empty list when artifact not found in store."""
        mock_store = MagicMock()
        mock_store.get.return_value = None

        agent = Agent(
            agent_id="test_agent",
            llm_model="gpt-4",
            system_prompt="Test",
            artifact_store=mock_store,
        )
        agent._longterm_memory_artifact_id = "missing"

        results = agent._search_longterm_memory_artifact("query")
        assert results == []

    def test_respects_limit_parameter(self) -> None:
        """Returns at most 'limit' number of results."""
        mock_store = MagicMock()
        mock_artifact = MagicMock()
        mock_artifact.content = {
            "entries": [
                {"text": f"Entry about trading {i}", "tags": []} for i in range(10)
            ]
        }
        mock_store.get.return_value = mock_artifact

        agent = Agent(
            agent_id="test_agent",
            llm_model="gpt-4",
            system_prompt="Test",
            artifact_store=mock_store,
        )
        agent._longterm_memory_artifact_id = "memory"

        results = agent._search_longterm_memory_artifact("trading", limit=3)
        assert len(results) <= 3

    def test_includes_tags_in_results(self) -> None:
        """Results include tags from entries."""
        mock_store = MagicMock()
        mock_artifact = MagicMock()
        mock_artifact.content = {
            "entries": [
                {"text": "Trading entry", "tags": ["trading", "success"]},
            ]
        }
        mock_store.get.return_value = mock_artifact

        agent = Agent(
            agent_id="test_agent",
            llm_model="gpt-4",
            system_prompt="Test",
            artifact_store=mock_store,
        )
        agent._longterm_memory_artifact_id = "memory"

        results = agent._search_longterm_memory_artifact("trading", limit=5)
        assert len(results) == 1
        assert results[0]["tags"] == ["trading", "success"]
