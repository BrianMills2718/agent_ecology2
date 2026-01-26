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
            "name": "test_behavior",
            "type": "behavior",
            "version": 1,
            "description": "A test behavior",
            "inject_into": ["ideate", "observe"],
            "prompt_fragment": "Test prompt fragment",
            "requires_context": ["balance"],
        }
        component = Component.from_dict(data)

        assert component.name == "test_behavior"
        assert component.component_type == "behavior"
        assert component.version == 1
        assert component.description == "A test behavior"
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

    def test_load_behavior_component(self, tmp_path: Path) -> None:
        """Registry loads behavior components from behaviors/ directory."""
        # Create a test behavior
        behaviors_dir = tmp_path / "behaviors"
        behaviors_dir.mkdir()
        behavior_file = behaviors_dir / "test_behavior.yaml"
        behavior_file.write_text(
            yaml.dump(
                {
                    "name": "test_behavior",
                    "type": "behavior",
                    "inject_into": ["ideate"],
                    "prompt_fragment": "Be smart!",
                }
            )
        )

        registry = ComponentRegistry(components_dir=tmp_path)
        registry.load_all()

        assert "test_behavior" in registry.behaviors
        assert registry.behaviors["test_behavior"].prompt_fragment == "Be smart!"

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

    def test_get_behaviors_returns_list(self, tmp_path: Path) -> None:
        """get_behaviors returns list of components."""
        behaviors_dir = tmp_path / "behaviors"
        behaviors_dir.mkdir()

        for name in ["behavior_a", "behavior_b"]:
            (behaviors_dir / f"{name}.yaml").write_text(
                yaml.dump({"name": name, "type": "behavior", "prompt_fragment": f"{name} content"})
            )

        registry = ComponentRegistry(components_dir=tmp_path)
        registry.load_all()

        behaviors = registry.get_behaviors(["behavior_a", "behavior_b"])
        assert len(behaviors) == 2
        assert behaviors[0].name == "behavior_a"
        assert behaviors[1].name == "behavior_b"

    def test_get_behaviors_skips_missing(self, tmp_path: Path) -> None:
        """get_behaviors logs warning and skips missing components."""
        behaviors_dir = tmp_path / "behaviors"
        behaviors_dir.mkdir()
        (behaviors_dir / "exists.yaml").write_text(
            yaml.dump({"name": "exists", "type": "behavior"})
        )

        registry = ComponentRegistry(components_dir=tmp_path)
        registry.load_all()

        behaviors = registry.get_behaviors(["exists", "does_not_exist"])
        assert len(behaviors) == 1
        assert behaviors[0].name == "exists"

    def test_empty_directory_no_error(self, tmp_path: Path) -> None:
        """Registry handles empty/missing directories gracefully."""
        registry = ComponentRegistry(components_dir=tmp_path)
        registry.load_all()  # Should not raise

        assert registry.behaviors == {}
        assert registry.goals == {}


class TestInjectComponents:
    """Tests for inject_components_into_workflow."""

    def test_inject_behavior_into_matching_step(self) -> None:
        """Trait prompt fragment is injected into matching step."""
        workflow = {
            "steps": [
                {"name": "ideate", "type": "llm", "prompt": "Original prompt"},
                {"name": "execute", "type": "llm", "prompt": "Execute prompt"},
            ]
        }

        behavior = Component(
            name="test",
            component_type="behavior",
            inject_into=["ideate"],
            prompt_fragment="\nInjected content!",
        )

        result = inject_components_into_workflow(workflow, behaviors=[behavior])

        assert "Injected content!" in result["steps"][0]["prompt"]
        assert "Injected content!" not in result["steps"][1]["prompt"]

    def test_inject_multiple_behaviors(self) -> None:
        """Multiple behaviors are all injected into matching step."""
        workflow = {
            "steps": [{"name": "observe", "type": "llm", "prompt": "Base prompt"}]
        }

        behaviors = [
            Component(
                name="behavior1",
                component_type="behavior",
                inject_into=["observe"],
                prompt_fragment="\nTrait 1 content",
            ),
            Component(
                name="behavior2",
                component_type="behavior",
                inject_into=["observe"],
                prompt_fragment="\nTrait 2 content",
            ),
        ]

        result = inject_components_into_workflow(workflow, behaviors=behaviors)

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

        behavior = Component(
            name="test",
            component_type="behavior",
            inject_into=["ideate"],  # Different from "unrelated"
            prompt_fragment="\nShould not appear",
        )

        result = inject_components_into_workflow(workflow, behaviors=[behavior])

        assert result["steps"][0]["prompt"] == "Original"

    def test_no_components_returns_unchanged(self) -> None:
        """Empty components list returns workflow unchanged."""
        workflow = {"steps": [{"name": "test", "prompt": "Original"}]}

        result = inject_components_into_workflow(workflow, behaviors=[], goals=[])

        assert result == workflow


class TestLoadAgentComponents:
    """Tests for load_agent_components helper."""

    def test_load_from_config(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        """load_agent_components loads specified components."""
        # Create test components
        behaviors_dir = tmp_path / "behaviors"
        behaviors_dir.mkdir()
        (behaviors_dir / "my_behavior.yaml").write_text(
            yaml.dump({"name": "my_behavior", "type": "behavior", "prompt_fragment": "Trait!"})
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

        config = {"behaviors": ["my_behavior"], "goals": ["my_goal"]}
        behaviors, goals = load_agent_components(config)

        assert len(behaviors) == 1
        assert behaviors[0].name == "my_behavior"
        assert len(goals) == 1
        assert goals[0].name == "my_goal"

    def test_empty_config_returns_empty(self) -> None:
        """Empty config returns empty lists."""
        behaviors, goals = load_agent_components(None)
        assert behaviors == []
        assert goals == []

        behaviors, goals = load_agent_components({})
        assert behaviors == []
        assert goals == []
