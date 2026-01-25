"""Tests for Plan #190: Configurable Mandatory Prompt Injection.

These tests verify that the prompt injection feature:
- Is disabled by default (no behavior change)
- Injects prefix/suffix content when enabled
- Respects scope settings (none, genesis, all)
- Correctly identifies genesis vs spawned agents
"""

import pytest
from unittest.mock import patch

from src.agents.agent import Agent


class TestPromptInjectionDisabledByDefault:
    """Test that prompt injection is disabled by default."""

    def test_agent_prompt_unchanged_when_disabled(self) -> None:
        """When prompt_injection.enabled is False, prompt should be unchanged."""
        agent = Agent(
            agent_id="test_agent",
            system_prompt="Original system prompt content",
            is_genesis=True,
        )

        with patch("src.agents.agent.config_get") as mock_config:
            # Configure: disabled by default
            mock_config.side_effect = lambda key: {
                "prompt_injection.enabled": False,
                "prompt_injection.scope": "all",
                "prompt_injection.mandatory_prefix": "INJECTED PREFIX",
                "prompt_injection.mandatory_suffix": "INJECTED SUFFIX",
            }.get(key)

            world_state = {"tick": 1, "balances": {"test_agent": 100}, "artifacts": []}
            prompt = agent.build_prompt(world_state)

            # Original prompt should be present, injections should NOT be present
            assert "Original system prompt content" in prompt
            assert "INJECTED PREFIX" not in prompt
            assert "INJECTED SUFFIX" not in prompt


class TestPromptInjectionAllScope:
    """Test prompt injection with scope='all' (both genesis and spawned)."""

    def test_genesis_agent_gets_injection_with_all_scope(self) -> None:
        """Genesis agents get injection when scope='all'."""
        agent = Agent(
            agent_id="genesis_test",
            system_prompt="Genesis prompt",
            is_genesis=True,
        )

        with patch("src.agents.agent.config_get") as mock_config:
            mock_config.side_effect = lambda key: {
                "prompt_injection.enabled": True,
                "prompt_injection.scope": "all",
                "prompt_injection.mandatory_prefix": "=== MANDATORY DIRECTIVE ===",
                "prompt_injection.mandatory_suffix": "=== END DIRECTIVE ===",
            }.get(key)

            world_state = {"tick": 1, "balances": {"genesis_test": 100}, "artifacts": []}
            prompt = agent.build_prompt(world_state)

            # Both original and injected content should be present
            assert "Genesis prompt" in prompt
            assert "=== MANDATORY DIRECTIVE ===" in prompt
            assert "=== END DIRECTIVE ===" in prompt

    def test_spawned_agent_gets_injection_with_all_scope(self) -> None:
        """Spawned agents get injection when scope='all'."""
        agent = Agent(
            agent_id="spawned_test",
            system_prompt="Spawned prompt",
            is_genesis=False,  # Spawned agent
        )

        with patch("src.agents.agent.config_get") as mock_config:
            mock_config.side_effect = lambda key: {
                "prompt_injection.enabled": True,
                "prompt_injection.scope": "all",
                "prompt_injection.mandatory_prefix": "SPAWNED DIRECTIVE",
                "prompt_injection.mandatory_suffix": "",
            }.get(key)

            world_state = {"tick": 1, "balances": {"spawned_test": 100}, "artifacts": []}
            prompt = agent.build_prompt(world_state)

            assert "Spawned prompt" in prompt
            assert "SPAWNED DIRECTIVE" in prompt


class TestPromptInjectionGenesisScope:
    """Test prompt injection with scope='genesis' (only genesis agents)."""

    def test_genesis_agent_gets_injection_with_genesis_scope(self) -> None:
        """Genesis agents get injection when scope='genesis'."""
        agent = Agent(
            agent_id="genesis_only",
            system_prompt="Genesis only prompt",
            is_genesis=True,
        )

        with patch("src.agents.agent.config_get") as mock_config:
            mock_config.side_effect = lambda key: {
                "prompt_injection.enabled": True,
                "prompt_injection.scope": "genesis",
                "prompt_injection.mandatory_prefix": "GENESIS ONLY PREFIX",
                "prompt_injection.mandatory_suffix": "GENESIS ONLY SUFFIX",
            }.get(key)

            world_state = {"tick": 1, "balances": {"genesis_only": 100}, "artifacts": []}
            prompt = agent.build_prompt(world_state)

            assert "Genesis only prompt" in prompt
            assert "GENESIS ONLY PREFIX" in prompt
            assert "GENESIS ONLY SUFFIX" in prompt

    def test_spawned_agent_no_injection_with_genesis_scope(self) -> None:
        """Spawned agents do NOT get injection when scope='genesis'."""
        agent = Agent(
            agent_id="spawned_excluded",
            system_prompt="Spawned excluded prompt",
            is_genesis=False,  # Spawned agent
        )

        with patch("src.agents.agent.config_get") as mock_config:
            mock_config.side_effect = lambda key: {
                "prompt_injection.enabled": True,
                "prompt_injection.scope": "genesis",
                "prompt_injection.mandatory_prefix": "SHOULD NOT APPEAR",
                "prompt_injection.mandatory_suffix": "SHOULD NOT APPEAR",
            }.get(key)

            world_state = {"tick": 1, "balances": {"spawned_excluded": 100}, "artifacts": []}
            prompt = agent.build_prompt(world_state)

            assert "Spawned excluded prompt" in prompt
            assert "SHOULD NOT APPEAR" not in prompt


class TestPromptInjectionNoneScope:
    """Test prompt injection with scope='none' (no agents)."""

    def test_no_injection_with_none_scope(self) -> None:
        """No agents get injection when scope='none', even when enabled."""
        agent = Agent(
            agent_id="none_scope_test",
            system_prompt="None scope prompt",
            is_genesis=True,
        )

        with patch("src.agents.agent.config_get") as mock_config:
            mock_config.side_effect = lambda key: {
                "prompt_injection.enabled": True,
                "prompt_injection.scope": "none",
                "prompt_injection.mandatory_prefix": "SHOULD NOT APPEAR",
                "prompt_injection.mandatory_suffix": "SHOULD NOT APPEAR",
            }.get(key)

            world_state = {"tick": 1, "balances": {"none_scope_test": 100}, "artifacts": []}
            prompt = agent.build_prompt(world_state)

            assert "None scope prompt" in prompt
            assert "SHOULD NOT APPEAR" not in prompt


class TestPromptInjectionContentPositioning:
    """Test that prefix appears before and suffix appears after system prompt."""

    def test_prefix_before_suffix_after_system_prompt(self) -> None:
        """Prefix should appear before system prompt, suffix after."""
        agent = Agent(
            agent_id="position_test",
            system_prompt="MIDDLE_CONTENT",
            is_genesis=True,
        )

        with patch("src.agents.agent.config_get") as mock_config:
            mock_config.side_effect = lambda key: {
                "prompt_injection.enabled": True,
                "prompt_injection.scope": "all",
                "prompt_injection.mandatory_prefix": "START_PREFIX",
                "prompt_injection.mandatory_suffix": "END_SUFFIX",
            }.get(key)

            world_state = {"tick": 1, "balances": {"position_test": 100}, "artifacts": []}
            prompt = agent.build_prompt(world_state)

            # Find positions of each component
            prefix_pos = prompt.find("START_PREFIX")
            middle_pos = prompt.find("MIDDLE_CONTENT")
            suffix_pos = prompt.find("END_SUFFIX")

            # Verify ordering
            assert prefix_pos != -1, "Prefix not found in prompt"
            assert middle_pos != -1, "System prompt not found in prompt"
            assert suffix_pos != -1, "Suffix not found in prompt"
            assert prefix_pos < middle_pos < suffix_pos, "Content not in correct order"


class TestAgentIsGenesisProperty:
    """Test the is_genesis property on Agent."""

    def test_default_is_genesis_true(self) -> None:
        """Agents default to is_genesis=True."""
        agent = Agent(agent_id="default_test", system_prompt="test")
        assert agent.is_genesis is True

    def test_explicit_is_genesis_true(self) -> None:
        """is_genesis=True can be set explicitly."""
        agent = Agent(agent_id="explicit_true", system_prompt="test", is_genesis=True)
        assert agent.is_genesis is True

    def test_explicit_is_genesis_false(self) -> None:
        """is_genesis=False marks spawned agents."""
        agent = Agent(agent_id="explicit_false", system_prompt="test", is_genesis=False)
        assert agent.is_genesis is False

    def test_from_artifact_default_is_genesis_true(self) -> None:
        """Agent.from_artifact defaults to is_genesis=True."""
        from src.world.artifacts import create_agent_artifact

        artifact = create_agent_artifact(
            agent_id="artifact_agent",
            created_by="artifact_agent",
            agent_config={"system_prompt": "test", "llm_model": "test/model"},
        )
        agent = Agent.from_artifact(artifact)
        assert agent.is_genesis is True

    def test_from_artifact_explicit_is_genesis_false(self) -> None:
        """Agent.from_artifact can set is_genesis=False for spawned agents."""
        from src.world.artifacts import create_agent_artifact

        artifact = create_agent_artifact(
            agent_id="spawned_artifact",
            created_by="spawned_artifact",
            agent_config={"system_prompt": "test", "llm_model": "test/model"},
        )
        agent = Agent.from_artifact(artifact, is_genesis=False)
        assert agent.is_genesis is False
