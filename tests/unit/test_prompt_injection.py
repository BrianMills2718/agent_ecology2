"""Unit tests for Plan #197: Configurable Mandatory Prompt Injection.

Tests the prompt injection feature including:
- Injection enabled/disabled behavior
- Scope filtering (none/genesis/all)
- Prefix/suffix positioning
- is_genesis property behavior
"""

import pytest
from unittest.mock import patch, MagicMock

from src.agents.agent import Agent


class TestIsGenesisProperty:
    """Tests for the is_genesis property on agents."""

    def test_is_genesis_default_true(self) -> None:
        """New agents default to is_genesis=True."""
        # Agent constructor requires llm_model, so we mock minimally
        with patch("src.agents.agent.LLMProvider"):
            agent = Agent(
                agent_id="test_agent",
                llm_model="test/model",
                system_prompt="Test prompt",
            )
            assert agent.is_genesis is True

    def test_is_genesis_explicit_false(self) -> None:
        """Agents can be created with is_genesis=False."""
        with patch("src.agents.agent.LLMProvider"):
            agent = Agent(
                agent_id="test_agent",
                llm_model="test/model",
                system_prompt="Test prompt",
                is_genesis=False,
            )
            assert agent.is_genesis is False

    def test_is_genesis_explicit_true(self) -> None:
        """Agents can be explicitly created with is_genesis=True."""
        with patch("src.agents.agent.LLMProvider"):
            agent = Agent(
                agent_id="test_agent",
                llm_model="test/model",
                system_prompt="Test prompt",
                is_genesis=True,
            )
            assert agent.is_genesis is True


class TestFromArtifactIsGenesis:
    """Tests for is_genesis parameter in Agent.from_artifact."""

    def test_from_artifact_default_is_genesis_true(self) -> None:
        """from_artifact defaults to is_genesis=True."""
        # Create mock artifact
        mock_artifact = MagicMock()
        mock_artifact.id = "test_agent"
        mock_artifact.is_agent = True
        mock_artifact.content = '{"llm_model": "test/model", "system_prompt": "Test"}'

        with patch("src.agents.agent.LLMProvider"):
            agent = Agent.from_artifact(mock_artifact)
            assert agent.is_genesis is True

    def test_from_artifact_explicit_is_genesis_false(self) -> None:
        """from_artifact respects is_genesis=False parameter."""
        mock_artifact = MagicMock()
        mock_artifact.id = "test_agent"
        mock_artifact.is_agent = True
        mock_artifact.content = '{"llm_model": "test/model", "system_prompt": "Test"}'

        with patch("src.agents.agent.LLMProvider"):
            agent = Agent.from_artifact(mock_artifact, is_genesis=False)
            assert agent.is_genesis is False


class TestPromptInjection:
    """Tests for prompt injection in build_prompt."""

    @pytest.fixture
    def mock_agent(self) -> Agent:
        """Create a mock agent for testing."""
        with patch("src.agents.agent.LLMProvider"):
            agent = Agent(
                agent_id="test_agent",
                llm_model="test/model",
                system_prompt="Original system prompt",
            )
            # Initialize memory to avoid errors
            agent._memories = []
            agent._action_history = []
            agent._failures = []
            return agent

    @pytest.fixture
    def minimal_world_state(self) -> dict:
        """Minimal world state for build_prompt."""
        return {
            "tick": 1,
            "balances": {"test_agent": 100},
            "artifacts": [],
            "other_agents": [],
            "simulation_duration_seconds": 60.0,
            "simulation_start_time": 0.0,
        }

    def test_injection_disabled_by_default(
        self, mock_agent: Agent, minimal_world_state: dict
    ) -> None:
        """No injection when enabled=false."""
        with patch("src.agents.agent.config_get") as mock_config:
            # Default: disabled
            mock_config.side_effect = lambda key: {
                "prompt_injection.enabled": False,
            }.get(key)

            prompt = mock_agent.build_prompt(minimal_world_state)

            # Original prompt should be present unchanged
            assert "Original system prompt" in prompt

    def test_injection_all_scope(
        self, mock_agent: Agent, minimal_world_state: dict
    ) -> None:
        """All agents get injection with scope='all'."""
        with patch("src.agents.agent.config_get") as mock_config:
            mock_config.side_effect = lambda key: {
                "prompt_injection.enabled": True,
                "prompt_injection.scope": "all",
                "prompt_injection.mandatory_prefix": "PREFIX_CONTENT",
                "prompt_injection.mandatory_suffix": "SUFFIX_CONTENT",
            }.get(key)

            prompt = mock_agent.build_prompt(minimal_world_state)

            assert "PREFIX_CONTENT" in prompt
            assert "SUFFIX_CONTENT" in prompt

    def test_injection_genesis_scope_for_genesis_agent(
        self, mock_agent: Agent, minimal_world_state: dict
    ) -> None:
        """Genesis agents get injection with scope='genesis'."""
        assert mock_agent.is_genesis is True  # Default

        with patch("src.agents.agent.config_get") as mock_config:
            mock_config.side_effect = lambda key: {
                "prompt_injection.enabled": True,
                "prompt_injection.scope": "genesis",
                "prompt_injection.mandatory_prefix": "GENESIS_PREFIX",
                "prompt_injection.mandatory_suffix": "GENESIS_SUFFIX",
            }.get(key)

            prompt = mock_agent.build_prompt(minimal_world_state)

            assert "GENESIS_PREFIX" in prompt
            assert "GENESIS_SUFFIX" in prompt

    def test_injection_genesis_scope_skips_spawned_agent(
        self, minimal_world_state: dict
    ) -> None:
        """Spawned agents (is_genesis=False) don't get injection with scope='genesis'."""
        with patch("src.agents.agent.LLMProvider"):
            spawned_agent = Agent(
                agent_id="spawned_agent",
                llm_model="test/model",
                system_prompt="Spawned prompt",
                is_genesis=False,
            )
            spawned_agent._memories = []
            spawned_agent._action_history = []
            spawned_agent._failures = []

        with patch("src.agents.agent.config_get") as mock_config:
            mock_config.side_effect = lambda key: {
                "prompt_injection.enabled": True,
                "prompt_injection.scope": "genesis",
                "prompt_injection.mandatory_prefix": "GENESIS_ONLY",
                "prompt_injection.mandatory_suffix": "GENESIS_SUFFIX",
            }.get(key)

            # Update world state for spawned agent
            world_state = minimal_world_state.copy()
            world_state["balances"] = {"spawned_agent": 50}

            prompt = spawned_agent.build_prompt(world_state)

            # Injection should NOT be present for spawned agents
            assert "GENESIS_ONLY" not in prompt
            assert "GENESIS_SUFFIX" not in prompt
            assert "Spawned prompt" in prompt

    def test_injection_none_scope(
        self, mock_agent: Agent, minimal_world_state: dict
    ) -> None:
        """No injection with scope='none'."""
        with patch("src.agents.agent.config_get") as mock_config:
            mock_config.side_effect = lambda key: {
                "prompt_injection.enabled": True,
                "prompt_injection.scope": "none",
                "prompt_injection.mandatory_prefix": "SHOULD_NOT_APPEAR",
                "prompt_injection.mandatory_suffix": "SHOULD_NOT_APPEAR",
            }.get(key)

            prompt = mock_agent.build_prompt(minimal_world_state)

            assert "SHOULD_NOT_APPEAR" not in prompt
            assert "Original system prompt" in prompt

    def test_prefix_before_prompt(
        self, mock_agent: Agent, minimal_world_state: dict
    ) -> None:
        """Prefix appears before system prompt in output."""
        with patch("src.agents.agent.config_get") as mock_config:
            mock_config.side_effect = lambda key: {
                "prompt_injection.enabled": True,
                "prompt_injection.scope": "all",
                "prompt_injection.mandatory_prefix": "PREFIX_MARKER",
                "prompt_injection.mandatory_suffix": "",
            }.get(key)

            prompt = mock_agent.build_prompt(minimal_world_state)

            # Find positions
            prefix_pos = prompt.find("PREFIX_MARKER")
            original_pos = prompt.find("Original system prompt")

            assert prefix_pos != -1, "Prefix not found in prompt"
            assert original_pos != -1, "Original prompt not found"
            assert prefix_pos < original_pos, "Prefix should appear before original prompt"

    def test_suffix_after_prompt(
        self, mock_agent: Agent, minimal_world_state: dict
    ) -> None:
        """Suffix appears after system prompt in output."""
        with patch("src.agents.agent.config_get") as mock_config:
            mock_config.side_effect = lambda key: {
                "prompt_injection.enabled": True,
                "prompt_injection.scope": "all",
                "prompt_injection.mandatory_prefix": "",
                "prompt_injection.mandatory_suffix": "SUFFIX_MARKER",
            }.get(key)

            prompt = mock_agent.build_prompt(minimal_world_state)

            # Find positions
            original_pos = prompt.find("Original system prompt")
            suffix_pos = prompt.find("SUFFIX_MARKER")

            assert original_pos != -1, "Original prompt not found"
            assert suffix_pos != -1, "Suffix not found in prompt"
            assert suffix_pos > original_pos, "Suffix should appear after original prompt"

    def test_prefix_and_suffix_together(
        self, mock_agent: Agent, minimal_world_state: dict
    ) -> None:
        """Both prefix and suffix work together correctly."""
        with patch("src.agents.agent.config_get") as mock_config:
            mock_config.side_effect = lambda key: {
                "prompt_injection.enabled": True,
                "prompt_injection.scope": "all",
                "prompt_injection.mandatory_prefix": "START_INJECT",
                "prompt_injection.mandatory_suffix": "END_INJECT",
            }.get(key)

            prompt = mock_agent.build_prompt(minimal_world_state)

            prefix_pos = prompt.find("START_INJECT")
            original_pos = prompt.find("Original system prompt")
            suffix_pos = prompt.find("END_INJECT")

            assert prefix_pos < original_pos < suffix_pos, (
                "Order should be: prefix, original, suffix"
            )

    def test_empty_prefix_suffix_no_effect(
        self, mock_agent: Agent, minimal_world_state: dict
    ) -> None:
        """Empty prefix/suffix values don't change prompt."""
        with patch("src.agents.agent.config_get") as mock_config:
            mock_config.side_effect = lambda key: {
                "prompt_injection.enabled": True,
                "prompt_injection.scope": "all",
                "prompt_injection.mandatory_prefix": "",
                "prompt_injection.mandatory_suffix": "",
            }.get(key)

            prompt = mock_agent.build_prompt(minimal_world_state)

            # Original prompt should be present normally
            assert "Original system prompt" in prompt
