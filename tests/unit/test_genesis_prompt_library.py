"""Tests for GenesisPromptLibrary (Plan #146 Phase 2)"""

import pytest

from src.world.genesis.prompt_library import GenesisPromptLibrary, DEFAULT_PROMPTS


class TestGenesisPromptLibrary:
    """Test the genesis prompt library artifact."""

    @pytest.fixture
    def library(self) -> GenesisPromptLibrary:
        """Create a prompt library instance."""
        return GenesisPromptLibrary()

    def test_has_correct_id(self, library: GenesisPromptLibrary) -> None:
        """Library has expected artifact ID."""
        assert library.id == "genesis_prompt_library"

    def test_has_correct_type(self, library: GenesisPromptLibrary) -> None:
        """Library is a genesis artifact."""
        assert library.type == "genesis"

    def test_has_registered_methods(self, library: GenesisPromptLibrary) -> None:
        """Library has all expected methods registered."""
        assert "list" in library.methods
        assert "get" in library.methods
        assert "get_template" in library.methods

    def test_methods_are_free(self, library: GenesisPromptLibrary) -> None:
        """All methods should have zero cost."""
        for method in library.methods.values():
            assert method.cost == 0

    def test_list_returns_all_prompts(self, library: GenesisPromptLibrary) -> None:
        """List without filter returns all prompts."""
        result = library._method_list([], "test_caller")
        assert result["success"] is True
        assert result["count"] == len(DEFAULT_PROMPTS)
        assert len(result["prompts"]) == len(DEFAULT_PROMPTS)

    def test_list_with_tag_filter(self, library: GenesisPromptLibrary) -> None:
        """List with tag filter returns matching prompts."""
        result = library._method_list(["observation"], "test_caller")
        assert result["success"] is True
        # observe_base has "observation" tag
        assert result["count"] >= 1
        for prompt in result["prompts"]:
            assert "observation" in prompt["tags"]

    def test_list_with_nonexistent_tag(self, library: GenesisPromptLibrary) -> None:
        """List with unknown tag returns empty list."""
        result = library._method_list(["nonexistent_tag"], "test_caller")
        assert result["success"] is True
        assert result["count"] == 0

    def test_get_existing_prompt(self, library: GenesisPromptLibrary) -> None:
        """Get retrieves existing prompt with full data."""
        result = library._method_get(["observe_base"], "test_caller")
        assert result["success"] is True
        assert result["prompt_id"] == "observe_base"
        assert "template" in result
        assert "description" in result
        assert "tags" in result

    def test_get_nonexistent_prompt(self, library: GenesisPromptLibrary) -> None:
        """Get returns error for nonexistent prompt."""
        result = library._method_get(["nonexistent"], "test_caller")
        assert result["success"] is False
        assert "error" in result
        assert "available" in result  # Shows available prompts

    def test_get_missing_arg(self, library: GenesisPromptLibrary) -> None:
        """Get requires prompt_id argument."""
        result = library._method_get([], "test_caller")
        assert result["success"] is False
        assert "prompt_id required" in result["error"]

    def test_get_template_basic(self, library: GenesisPromptLibrary) -> None:
        """Get template returns just the template text."""
        result = library._method_get_template(["observe_base"], "test_caller")
        assert result["success"] is True
        assert "template" in result
        assert "OBSERVATION PHASE" in result["template"]

    def test_get_template_nonexistent(self, library: GenesisPromptLibrary) -> None:
        """Get template returns error for nonexistent prompt."""
        result = library._method_get_template(["nonexistent"], "test_caller")
        assert result["success"] is False
        assert "error" in result

    def test_get_template_missing_arg(self, library: GenesisPromptLibrary) -> None:
        """Get template requires prompt_id argument."""
        result = library._method_get_template([], "test_caller")
        assert result["success"] is False
        assert "prompt_id required" in result["error"]

    def test_get_interface(self, library: GenesisPromptLibrary) -> None:
        """Get interface returns method descriptions."""
        interface = library.get_interface()
        assert interface["artifact_id"] == "genesis_prompt_library"
        assert "methods" in interface
        assert "list" in interface["methods"]
        assert "get" in interface["methods"]
        assert "get_template" in interface["methods"]
        assert "available_prompts" in interface

    def test_default_prompts_have_required_fields(self) -> None:
        """All default prompts have required fields."""
        for prompt_id, data in DEFAULT_PROMPTS.items():
            assert "description" in data, f"{prompt_id} missing description"
            assert "template" in data, f"{prompt_id} missing template"
            assert "tags" in data, f"{prompt_id} missing tags"
            assert isinstance(data["tags"], list), f"{prompt_id} tags should be list"


class TestAgentPersonalityPromptField:
    """Test agent personality_prompt_artifact_id field (Plan #146 Phase 2)."""

    def test_agent_has_personality_prompt_field(self) -> None:
        """Agent class has personality_prompt_artifact_id field."""
        from src.agents.agent import Agent

        agent = Agent(
            agent_id="test_agent",
            llm_model="test",
            system_prompt="test"
        )

        # Field exists and is initially None
        assert hasattr(agent, "_personality_prompt_artifact_id")
        assert agent.personality_prompt_artifact_id is None

    def test_agent_personality_prompt_property(self) -> None:
        """Agent personality_prompt_artifact_id property works."""
        from src.agents.agent import Agent

        agent = Agent(
            agent_id="test_agent",
            llm_model="test",
            system_prompt="test"
        )

        # Setter works
        agent.personality_prompt_artifact_id = "my_prompt"
        assert agent.personality_prompt_artifact_id == "my_prompt"

        # has_personality_prompt_artifact works
        assert agent.has_personality_prompt_artifact is True

        # Can set back to None
        agent.personality_prompt_artifact_id = None
        assert agent.has_personality_prompt_artifact is False

    def test_agent_config_dict_has_field(self) -> None:
        """AgentConfigDict includes personality_prompt_artifact_id."""
        from src.agents.agent import AgentConfigDict
        import typing

        # Get all fields from TypedDict
        hints = typing.get_type_hints(AgentConfigDict)
        assert "personality_prompt_artifact_id" in hints
