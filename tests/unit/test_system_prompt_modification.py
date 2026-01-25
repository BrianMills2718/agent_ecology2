"""Tests for Plan #194: Self-Modifying System Prompt."""

import pytest

from src.agents.schema import validate_action_json


class TestModifySystemPromptValidation:
    """Test modify_system_prompt action validation in schema.py."""

    def test_valid_append(self) -> None:
        """Valid append operation should pass validation."""
        result = validate_action_json(
            '{"action_type": "modify_system_prompt", "operation": "append", "content": "New instruction"}'
        )
        assert isinstance(result, dict)
        assert result["action_type"] == "modify_system_prompt"
        assert result["operation"] == "append"
        assert result["content"] == "New instruction"

    def test_valid_prepend(self) -> None:
        """Valid prepend operation should pass validation."""
        result = validate_action_json(
            '{"action_type": "modify_system_prompt", "operation": "prepend", "content": "First instruction"}'
        )
        assert isinstance(result, dict)
        assert result["operation"] == "prepend"

    def test_valid_replace_section(self) -> None:
        """Valid replace_section operation should pass validation."""
        result = validate_action_json(
            '{"action_type": "modify_system_prompt", "operation": "replace_section", "section_marker": "## Goals", "content": "## Goals\\n1. New goal"}'
        )
        assert isinstance(result, dict)
        assert result["operation"] == "replace_section"
        assert result["section_marker"] == "## Goals"

    def test_valid_reset(self) -> None:
        """Valid reset operation should pass validation."""
        result = validate_action_json(
            '{"action_type": "modify_system_prompt", "operation": "reset"}'
        )
        assert isinstance(result, dict)
        assert result["operation"] == "reset"

    def test_requires_operation(self) -> None:
        """modify_system_prompt requires operation field."""
        result = validate_action_json('{"action_type": "modify_system_prompt"}')
        assert isinstance(result, str)
        assert "requires 'operation'" in result

    def test_unknown_operation(self) -> None:
        """Unknown operation should fail validation."""
        result = validate_action_json(
            '{"action_type": "modify_system_prompt", "operation": "delete"}'
        )
        assert isinstance(result, str)
        assert "Unknown operation" in result

    def test_append_requires_content(self) -> None:
        """append operation requires content field."""
        result = validate_action_json(
            '{"action_type": "modify_system_prompt", "operation": "append"}'
        )
        assert isinstance(result, str)
        assert "requires 'content'" in result

    def test_prepend_requires_content(self) -> None:
        """prepend operation requires content field."""
        result = validate_action_json(
            '{"action_type": "modify_system_prompt", "operation": "prepend"}'
        )
        assert isinstance(result, str)
        assert "requires 'content'" in result

    def test_replace_section_requires_marker(self) -> None:
        """replace_section operation requires section_marker field."""
        result = validate_action_json(
            '{"action_type": "modify_system_prompt", "operation": "replace_section", "content": "new"}'
        )
        assert isinstance(result, str)
        assert "requires 'section_marker'" in result

    def test_replace_section_requires_content(self) -> None:
        """replace_section operation requires content field."""
        result = validate_action_json(
            '{"action_type": "modify_system_prompt", "operation": "replace_section", "section_marker": "## Goals"}'
        )
        assert isinstance(result, str)
        assert "requires 'content'" in result


class TestAgentOriginalSystemPrompt:
    """Test agent's original_system_prompt tracking."""

    def test_original_prompt_initialized(self) -> None:
        """Original system prompt should be set on initialization."""
        from src.agents.agent import Agent

        agent = Agent.__new__(Agent)
        agent._system_prompt = "Test prompt"
        agent._original_system_prompt = "Test prompt"

        assert agent.original_system_prompt == "Test prompt"

    def test_original_prompt_preserved_after_modification(self) -> None:
        """Original system prompt should be preserved when prompt is modified."""
        from src.agents.agent import Agent

        agent = Agent.__new__(Agent)
        agent._system_prompt = "Modified prompt"
        agent._original_system_prompt = "Original prompt"

        assert agent.system_prompt == "Modified prompt"
        assert agent.original_system_prompt == "Original prompt"
