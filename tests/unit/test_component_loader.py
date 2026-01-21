"""Tests for the prompt component loader (Plan #150)."""

import pytest
from pathlib import Path
import tempfile
import yaml

from src.agents.component_loader import (
    Component,
    ComponentRegistry,
    inject_components_into_workflow,
    load_agent_components,
)


class TestComponent:
    """Tests for the Component dataclass."""

    def test_from_dict_basic(self) -> None:
        """Component parses from dict correctly."""
        data = {
            "name": "test_trait",
            "type": "trait",
            "version": 1,
            "description": "A test trait",
            "inject_into": ["ideate", "observe"],
            "prompt_fragment": "Test prompt fragment",
            "requires_context": ["balance"],
        }
        component = Component.from_dict(data)

        assert component.name == "test_trait"
        assert component.component_type == "trait"
        assert component.version == 1
        assert component.description == "A test trait"
        assert component.inject_into == ["ideate", "observe"]
        assert component.prompt_fragment == "Test prompt fragment"
        assert component.requires_context == ["balance"]

    def test_from_dict_minimal(self) -> None:
        """Component handles minimal config."""
        data = {"name": "minimal", "type": "goal"}
        component = Component.from_dict(data)

        assert component.name == "minimal"
        assert component.component_type == "goal"
        assert component.version == 1  # default
        assert component.inject_into == []
        assert component.prompt_fragment == ""


class TestComponentRegistry:
    """Tests for the ComponentRegistry."""

    def test_load_trait_component(self, tmp_path: Path) -> None:
        """Registry loads trait components from traits/ directory."""
        # Create a test trait
        traits_dir = tmp_path / "traits"
        traits_dir.mkdir()
        trait_file = traits_dir / "test_trait.yaml"
        trait_file.write_text(
            yaml.dump(
                {
                    "name": "test_trait",
                    "type": "trait",
                    "inject_into": ["ideate"],
                    "prompt_fragment": "Be smart!",
                }
            )
        )

        registry = ComponentRegistry(components_dir=tmp_path)
        registry.load_all()

        assert "test_trait" in registry.traits
        assert registry.traits["test_trait"].prompt_fragment == "Be smart!"

    def test_load_goal_component(self, tmp_path: Path) -> None:
        """Registry loads goal components from goals/ directory."""
        goals_dir = tmp_path / "goals"
        goals_dir.mkdir()
        goal_file = goals_dir / "test_goal.yaml"
        goal_file.write_text(
            yaml.dump(
                {
                    "name": "test_goal",
                    "type": "goal",
                    "inject_into": ["strategic"],
                    "prompt_fragment": "Focus on X!",
                }
            )
        )

        registry = ComponentRegistry(components_dir=tmp_path)
        registry.load_all()

        assert "test_goal" in registry.goals
        assert registry.goals["test_goal"].prompt_fragment == "Focus on X!"

    def test_get_traits_returns_list(self, tmp_path: Path) -> None:
        """get_traits returns list of components."""
        traits_dir = tmp_path / "traits"
        traits_dir.mkdir()

        for name in ["trait_a", "trait_b"]:
            (traits_dir / f"{name}.yaml").write_text(
                yaml.dump({"name": name, "type": "trait", "prompt_fragment": f"{name} content"})
            )

        registry = ComponentRegistry(components_dir=tmp_path)
        registry.load_all()

        traits = registry.get_traits(["trait_a", "trait_b"])
        assert len(traits) == 2
        assert traits[0].name == "trait_a"
        assert traits[1].name == "trait_b"

    def test_get_traits_skips_missing(self, tmp_path: Path) -> None:
        """get_traits logs warning and skips missing components."""
        traits_dir = tmp_path / "traits"
        traits_dir.mkdir()
        (traits_dir / "exists.yaml").write_text(
            yaml.dump({"name": "exists", "type": "trait"})
        )

        registry = ComponentRegistry(components_dir=tmp_path)
        registry.load_all()

        traits = registry.get_traits(["exists", "does_not_exist"])
        assert len(traits) == 1
        assert traits[0].name == "exists"

    def test_empty_directory_no_error(self, tmp_path: Path) -> None:
        """Registry handles empty/missing directories gracefully."""
        registry = ComponentRegistry(components_dir=tmp_path)
        registry.load_all()  # Should not raise

        assert registry.traits == {}
        assert registry.goals == {}


class TestInjectComponents:
    """Tests for inject_components_into_workflow."""

    def test_inject_trait_into_matching_step(self) -> None:
        """Trait prompt fragment is injected into matching step."""
        workflow = {
            "steps": [
                {"name": "ideate", "type": "llm", "prompt": "Original prompt"},
                {"name": "execute", "type": "llm", "prompt": "Execute prompt"},
            ]
        }

        trait = Component(
            name="test",
            component_type="trait",
            inject_into=["ideate"],
            prompt_fragment="\nInjected content!",
        )

        result = inject_components_into_workflow(workflow, traits=[trait])

        assert "Injected content!" in result["steps"][0]["prompt"]
        assert "Injected content!" not in result["steps"][1]["prompt"]

    def test_inject_multiple_traits(self) -> None:
        """Multiple traits are all injected into matching step."""
        workflow = {
            "steps": [{"name": "observe", "type": "llm", "prompt": "Base prompt"}]
        }

        traits = [
            Component(
                name="trait1",
                component_type="trait",
                inject_into=["observe"],
                prompt_fragment="\nTrait 1 content",
            ),
            Component(
                name="trait2",
                component_type="trait",
                inject_into=["observe"],
                prompt_fragment="\nTrait 2 content",
            ),
        ]

        result = inject_components_into_workflow(workflow, traits=traits)

        assert "Trait 1 content" in result["steps"][0]["prompt"]
        assert "Trait 2 content" in result["steps"][0]["prompt"]

    def test_inject_goal(self) -> None:
        """Goal prompt fragment is injected into matching step."""
        workflow = {
            "steps": [{"name": "strategic", "type": "llm", "prompt": "Strategy prompt"}]
        }

        goal = Component(
            name="test_goal",
            component_type="goal",
            inject_into=["strategic"],
            prompt_fragment="\nGoal: Do X!",
        )

        result = inject_components_into_workflow(workflow, goals=[goal])

        assert "Goal: Do X!" in result["steps"][0]["prompt"]

    def test_no_injection_if_no_match(self) -> None:
        """Workflow unchanged if no steps match component inject_into."""
        workflow = {
            "steps": [{"name": "unrelated", "type": "llm", "prompt": "Original"}]
        }

        trait = Component(
            name="test",
            component_type="trait",
            inject_into=["ideate"],  # Different from "unrelated"
            prompt_fragment="\nShould not appear",
        )

        result = inject_components_into_workflow(workflow, traits=[trait])

        assert result["steps"][0]["prompt"] == "Original"

    def test_no_components_returns_unchanged(self) -> None:
        """Empty components list returns workflow unchanged."""
        workflow = {"steps": [{"name": "test", "prompt": "Original"}]}

        result = inject_components_into_workflow(workflow, traits=[], goals=[])

        assert result == workflow


class TestLoadAgentComponents:
    """Tests for load_agent_components helper."""

    def test_load_from_config(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        """load_agent_components loads specified components."""
        # Create test components
        traits_dir = tmp_path / "traits"
        traits_dir.mkdir()
        (traits_dir / "my_trait.yaml").write_text(
            yaml.dump({"name": "my_trait", "type": "trait", "prompt_fragment": "Trait!"})
        )

        goals_dir = tmp_path / "goals"
        goals_dir.mkdir()
        (goals_dir / "my_goal.yaml").write_text(
            yaml.dump({"name": "my_goal", "type": "goal", "prompt_fragment": "Goal!"})
        )

        # Patch the global registry
        import src.agents.component_loader as cl
        monkeypatch.setattr(cl, "_registry", None)
        monkeypatch.setattr(cl, "COMPONENTS_DIR", tmp_path)

        config = {"traits": ["my_trait"], "goals": ["my_goal"]}
        traits, goals = load_agent_components(config)

        assert len(traits) == 1
        assert traits[0].name == "my_trait"
        assert len(goals) == 1
        assert goals[0].name == "my_goal"

    def test_empty_config_returns_empty(self) -> None:
        """Empty config returns empty lists."""
        traits, goals = load_agent_components(None)
        assert traits == []
        assert goals == []

        traits, goals = load_agent_components({})
        assert traits == []
        assert goals == []
