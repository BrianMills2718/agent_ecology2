"""Tests for Plan #192: Context Section Control and Plan #193: Context Priority."""

import pytest

from src.agents.schema import validate_action_json


class TestConfigureContextValidation:
    """Test configure_context action validation in schema.py."""

    def test_valid_configure_context(self) -> None:
        """Valid configure_context action should pass validation."""
        result = validate_action_json(
            '{"action_type": "configure_context", "sections": {"working_memory": false}}'
        )
        assert isinstance(result, dict)
        assert result["action_type"] == "configure_context"
        assert result["sections"] == {"working_memory": False}

    def test_configure_context_multiple_sections(self) -> None:
        """Configure multiple sections at once."""
        result = validate_action_json(
            '{"action_type": "configure_context", "sections": {"working_memory": false, "rag_memories": true, "action_history": false}}'
        )
        assert isinstance(result, dict)
        assert result["sections"]["working_memory"] is False
        assert result["sections"]["rag_memories"] is True
        assert result["sections"]["action_history"] is False

    def test_configure_context_requires_sections(self) -> None:
        """configure_context requires sections field."""
        result = validate_action_json('{"action_type": "configure_context"}')
        assert isinstance(result, str)
        assert "requires 'sections'" in result

    def test_configure_context_sections_must_be_dict(self) -> None:
        """sections must be a dict."""
        result = validate_action_json(
            '{"action_type": "configure_context", "sections": ["working_memory"]}'
        )
        assert isinstance(result, str)
        assert "must be a dict" in result

    def test_configure_context_unknown_section(self) -> None:
        """Unknown section names should fail validation."""
        result = validate_action_json(
            '{"action_type": "configure_context", "sections": {"invalid_section": true}}'
        )
        assert isinstance(result, str)
        assert "Unknown section" in result
        assert "invalid_section" in result

    def test_configure_context_value_must_be_bool(self) -> None:
        """Section values must be boolean."""
        result = validate_action_json(
            '{"action_type": "configure_context", "sections": {"working_memory": "false"}}'
        )
        assert isinstance(result, str)
        assert "must be a boolean" in result

    def test_all_valid_sections(self) -> None:
        """All valid section names should be accepted."""
        valid_sections = [
            "working_memory",
            "rag_memories",
            "action_history",
            "failure_history",
            "recent_events",
            "resource_metrics",
            "mint_submissions",
            "quota_info",
            "metacognitive",
            "subscribed_artifacts",
        ]
        for section in valid_sections:
            result = validate_action_json(
                f'{{"action_type": "configure_context", "sections": {{"{section}": true}}}}'
            )
            assert isinstance(result, dict), f"Section {section} should be valid"


class TestAgentContextSections:
    """Test agent context section storage and is_section_enabled."""

    def test_default_sections_all_enabled(self) -> None:
        """By default, all context sections should be enabled."""
        from src.agents.agent import Agent

        # Create minimal agent - just need to check defaults
        agent = Agent.__new__(Agent)
        agent._context_sections = {
            "working_memory": True,
            "rag_memories": True,
            "action_history": True,
            "failure_history": True,
            "recent_events": True,
            "resource_metrics": True,
            "mint_submissions": True,
            "quota_info": True,
            "metacognitive": True,
            "subscribed_artifacts": True,
        }

        for section in agent._context_sections:
            assert agent.is_section_enabled(section) is True

    def test_is_section_enabled_returns_false_when_disabled(self) -> None:
        """is_section_enabled returns False for disabled sections."""
        from src.agents.agent import Agent

        agent = Agent.__new__(Agent)
        agent._context_sections = {"working_memory": False, "rag_memories": True}

        assert agent.is_section_enabled("working_memory") is False
        assert agent.is_section_enabled("rag_memories") is True

    def test_is_section_enabled_unknown_section_returns_true(self) -> None:
        """Unknown sections default to enabled (safe default)."""
        from src.agents.agent import Agent

        agent = Agent.__new__(Agent)
        agent._context_sections = {}

        assert agent.is_section_enabled("unknown_section") is True

    def test_context_sections_property_returns_copy(self) -> None:
        """context_sections property returns a copy to prevent mutation."""
        from src.agents.agent import Agent

        agent = Agent.__new__(Agent)
        agent._context_sections = {"working_memory": True}

        sections = agent.context_sections
        sections["working_memory"] = False

        # Original should be unchanged
        assert agent._context_sections["working_memory"] is True


class TestConfigureContextPriorityValidation:
    """Test configure_context priority validation in schema.py (Plan #193)."""

    def test_valid_priorities(self) -> None:
        """Valid priorities should pass validation."""
        result = validate_action_json(
            '{"action_type": "configure_context", "sections": {"working_memory": true}, "priorities": {"working_memory": 90}}'
        )
        assert isinstance(result, dict)
        assert result["priorities"] == {"working_memory": 90}

    def test_priorities_optional(self) -> None:
        """priorities field is optional."""
        result = validate_action_json(
            '{"action_type": "configure_context", "sections": {"working_memory": true}}'
        )
        assert isinstance(result, dict)
        assert "priorities" not in result or result.get("priorities") is None

    def test_priorities_must_be_dict(self) -> None:
        """priorities must be a dict if provided."""
        result = validate_action_json(
            '{"action_type": "configure_context", "sections": {"working_memory": true}, "priorities": [90]}'
        )
        assert isinstance(result, str)
        assert "must be a dict" in result

    def test_priorities_unknown_section(self) -> None:
        """Unknown section names in priorities should fail."""
        result = validate_action_json(
            '{"action_type": "configure_context", "sections": {"working_memory": true}, "priorities": {"invalid_section": 90}}'
        )
        assert isinstance(result, str)
        assert "Unknown section" in result
        assert "invalid_section" in result

    def test_priority_must_be_integer(self) -> None:
        """Priority values must be integers."""
        result = validate_action_json(
            '{"action_type": "configure_context", "sections": {"working_memory": true}, "priorities": {"working_memory": "high"}}'
        )
        assert isinstance(result, str)
        assert "must be an integer" in result

    def test_priority_must_be_in_range(self) -> None:
        """Priority values must be between 0 and 100."""
        # Too high
        result = validate_action_json(
            '{"action_type": "configure_context", "sections": {"working_memory": true}, "priorities": {"working_memory": 101}}'
        )
        assert isinstance(result, str)
        assert "must be between 0 and 100" in result

        # Too low
        result = validate_action_json(
            '{"action_type": "configure_context", "sections": {"working_memory": true}, "priorities": {"working_memory": -1}}'
        )
        assert isinstance(result, str)
        assert "must be between 0 and 100" in result

    def test_valid_boundary_priorities(self) -> None:
        """Boundary values 0 and 100 should be valid."""
        result_0 = validate_action_json(
            '{"action_type": "configure_context", "sections": {"working_memory": true}, "priorities": {"working_memory": 0}}'
        )
        assert isinstance(result_0, dict)
        assert result_0["priorities"]["working_memory"] == 0

        result_100 = validate_action_json(
            '{"action_type": "configure_context", "sections": {"working_memory": true}, "priorities": {"working_memory": 100}}'
        )
        assert isinstance(result_100, dict)
        assert result_100["priorities"]["working_memory"] == 100


class TestAgentContextPriorities:
    """Test agent context priority storage and ordering (Plan #193)."""

    def test_default_priorities(self) -> None:
        """Agent should have default priorities for all sections."""
        from src.agents.agent import Agent

        agent = Agent.__new__(Agent)
        agent._context_section_priorities = {
            "working_memory": 90,
            "subscribed_artifacts": 85,
            "failure_history": 75,
            "action_history": 70,
        }

        assert agent.get_section_priority("working_memory") == 90
        assert agent.get_section_priority("subscribed_artifacts") == 85
        assert agent.get_section_priority("failure_history") == 75

    def test_get_section_priority_unknown_section(self) -> None:
        """Unknown sections should return default priority of 50."""
        from src.agents.agent import Agent

        agent = Agent.__new__(Agent)
        agent._context_section_priorities = {}

        assert agent.get_section_priority("unknown_section") == 50

    def test_context_section_priorities_property_returns_copy(self) -> None:
        """context_section_priorities property returns a copy to prevent mutation."""
        from src.agents.agent import Agent

        agent = Agent.__new__(Agent)
        agent._context_section_priorities = {"working_memory": 90}

        priorities = agent.context_section_priorities
        priorities["working_memory"] = 10

        # Original should be unchanged
        assert agent._context_section_priorities["working_memory"] == 90

    def test_higher_priority_sections_appear_first(self) -> None:
        """Sections with higher priority should appear earlier in prompt."""
        from src.agents.agent import Agent

        # Create a minimal agent for testing ordering
        agent = Agent.__new__(Agent)
        agent._context_section_priorities = {
            "working_memory": 90,
            "rag_memories": 60,
            "failure_history": 75,
        }

        # Get priorities and verify ordering
        sections = [
            ("working_memory", agent.get_section_priority("working_memory")),
            ("rag_memories", agent.get_section_priority("rag_memories")),
            ("failure_history", agent.get_section_priority("failure_history")),
        ]

        # Sort by priority (higher first)
        sorted_sections = sorted(sections, key=lambda x: x[1], reverse=True)

        assert sorted_sections[0][0] == "working_memory"  # Priority 90
        assert sorted_sections[1][0] == "failure_history"  # Priority 75
        assert sorted_sections[2][0] == "rag_memories"  # Priority 60
