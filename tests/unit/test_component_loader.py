"""Tests for the prompt component loader (Plan #150, Plan #222 Phase 2)."""

import pytest
from pathlib import Path
from typing import Any
import yaml

from src.agents.component_loader import (
    Component,
    ComponentRegistry,
    InjectionRule,
    _evaluate_injection_condition,
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
        """Behavior prompt fragment is injected into matching step."""
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
                prompt_fragment="\nBehavior 1 content",
            ),
            Component(
                name="behavior2",
                component_type="behavior",
                inject_into=["observe"],
                prompt_fragment="\nBehavior 2 content",
            ),
        ]

        result = inject_components_into_workflow(workflow, behaviors=behaviors)

        assert "Behavior 1 content" in result["steps"][0]["prompt"]
        assert "Behavior 2 content" in result["steps"][0]["prompt"]

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
            yaml.dump({"name": "my_behavior", "type": "behavior", "prompt_fragment": "Behavior!"})
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


# Plan #222 Phase 2: Conditional Injection Tests


class TestInjectionRule:
    """Tests for InjectionRule dataclass (Plan #222 Phase 2)."""

    def test_from_value_simple_string(self) -> None:
        """Simple string format creates always-inject rule."""
        rule = InjectionRule.from_value("observe")

        assert rule.step == "observe"
        assert rule.always is True
        assert rule.condition is None

    def test_from_value_dict_always_true(self) -> None:
        """Dict format with always=true."""
        rule = InjectionRule.from_value({"step": "observe", "always": True})

        assert rule.step == "observe"
        assert rule.always is True
        assert rule.condition is None

    def test_from_value_dict_with_condition(self) -> None:
        """Dict format with if condition."""
        rule = InjectionRule.from_value(
            {
                "step": "reflect",
                "if": {
                    "invoke": "context_analyzer",
                    "method": "needs_guidance",
                    "fallback": True,
                },
            }
        )

        assert rule.step == "reflect"
        assert rule.always is False
        assert rule.condition is not None
        assert rule.condition["invoke"] == "context_analyzer"
        assert rule.condition["method"] == "needs_guidance"
        assert rule.condition["fallback"] is True

    def test_from_value_dict_no_condition_defaults_always(self) -> None:
        """Dict with just step defaults to always=True."""
        rule = InjectionRule.from_value({"step": "observe"})

        assert rule.step == "observe"
        assert rule.always is True
        assert rule.condition is None

    def test_from_value_invalid_type(self) -> None:
        """Invalid type raises ValueError."""
        with pytest.raises(ValueError, match="Invalid injection rule format"):
            InjectionRule.from_value(123)  # type: ignore


class TestComponentWithInjectionRules:
    """Tests for Component with injection_rules (Plan #222 Phase 2)."""

    def test_from_dict_simple_inject_into(self) -> None:
        """Simple inject_into list creates matching rules."""
        data = {
            "name": "test_behavior",
            "type": "behavior",
            "inject_into": ["observe", "reflect"],
            "prompt_fragment": "Test content",
        }
        component = Component.from_dict(data)

        # Both legacy inject_into and injection_rules populated
        assert component.inject_into == ["observe", "reflect"]
        assert len(component.injection_rules) == 2
        assert component.injection_rules[0].step == "observe"
        assert component.injection_rules[0].always is True
        assert component.injection_rules[1].step == "reflect"

    def test_from_dict_mixed_inject_into(self) -> None:
        """Mixed simple and conditional inject_into."""
        data = {
            "name": "test_behavior",
            "type": "behavior",
            "inject_into": [
                "observe",  # Simple
                {
                    "step": "reflect",
                    "if": {"invoke": "analyzer", "method": "check", "fallback": True},
                },  # Conditional
            ],
            "prompt_fragment": "Test content",
        }
        component = Component.from_dict(data)

        # Legacy inject_into only includes always-inject rules
        assert component.inject_into == ["observe"]

        # injection_rules includes all
        assert len(component.injection_rules) == 2
        assert component.injection_rules[0].step == "observe"
        assert component.injection_rules[0].always is True
        assert component.injection_rules[1].step == "reflect"
        assert component.injection_rules[1].always is False
        assert component.injection_rules[1].condition is not None


class TestEvaluateInjectionCondition:
    """Tests for _evaluate_injection_condition (Plan #222 Phase 2)."""

    def test_no_resolver_uses_fallback_true(self) -> None:
        """Without resolver, uses fallback value (default True)."""
        condition = {"invoke": "artifact", "method": "check", "fallback": True}
        result = _evaluate_injection_condition(condition, None, {})

        assert result is True

    def test_no_resolver_uses_fallback_false(self) -> None:
        """Without resolver, respects explicit fallback=False."""
        condition = {"invoke": "artifact", "method": "check", "fallback": False}
        result = _evaluate_injection_condition(condition, None, {})

        assert result is False

    def test_resolver_returns_true(self) -> None:
        """Resolver returning True allows injection."""

        def mock_resolver(
            artifact_id: str,
            method: str,
            args: list[Any],
            kwargs: dict[str, Any],
            fallback: Any,
        ) -> bool:
            return True

        condition = {"invoke": "artifact", "method": "check", "fallback": False}
        result = _evaluate_injection_condition(condition, mock_resolver, {})

        assert result is True

    def test_resolver_returns_false(self) -> None:
        """Resolver returning False blocks injection."""

        def mock_resolver(
            artifact_id: str,
            method: str,
            args: list[Any],
            kwargs: dict[str, Any],
            fallback: Any,
        ) -> bool:
            return False

        condition = {"invoke": "artifact", "method": "check", "fallback": True}
        result = _evaluate_injection_condition(condition, mock_resolver, {})

        assert result is False

    def test_resolver_exception_uses_fallback(self) -> None:
        """Resolver exception falls back to fallback value."""

        def failing_resolver(
            artifact_id: str,
            method: str,
            args: list[Any],
            kwargs: dict[str, Any],
            fallback: Any,
        ) -> bool:
            raise RuntimeError("Artifact not found")

        condition = {"invoke": "artifact", "method": "check", "fallback": True}
        result = _evaluate_injection_condition(condition, failing_resolver, {})

        assert result is True  # Uses fallback=True


class TestConditionalInjection:
    """Tests for inject_components_into_workflow with conditionals (Plan #222 Phase 2)."""

    def test_inject_with_always_rule(self) -> None:
        """Component with always=True rule is injected."""
        workflow = {
            "steps": [{"name": "observe", "type": "llm", "prompt": "Base prompt"}]
        }

        behavior = Component(
            name="test",
            component_type="behavior",
            inject_into=[],  # Empty legacy
            injection_rules=[InjectionRule(step="observe", always=True)],
            prompt_fragment="\nInjected!",
        )

        result = inject_components_into_workflow(workflow, behaviors=[behavior])

        assert "Injected!" in result["steps"][0]["prompt"]

    def test_inject_with_condition_true(self) -> None:
        """Component with condition evaluating to True is injected."""

        def mock_resolver(
            artifact_id: str,
            method: str,
            args: list[Any],
            kwargs: dict[str, Any],
            fallback: Any,
        ) -> bool:
            return True

        workflow = {
            "steps": [{"name": "reflect", "type": "llm", "prompt": "Base prompt"}]
        }

        behavior = Component(
            name="test",
            component_type="behavior",
            inject_into=[],
            injection_rules=[
                InjectionRule(
                    step="reflect",
                    always=False,
                    condition={"invoke": "analyzer", "method": "check", "fallback": False},
                )
            ],
            prompt_fragment="\nConditional content!",
        )

        result = inject_components_into_workflow(
            workflow, behaviors=[behavior], invoke_resolver=mock_resolver
        )

        assert "Conditional content!" in result["steps"][0]["prompt"]

    def test_skip_with_condition_false(self) -> None:
        """Component with condition evaluating to False is skipped."""

        def mock_resolver(
            artifact_id: str,
            method: str,
            args: list[Any],
            kwargs: dict[str, Any],
            fallback: Any,
        ) -> bool:
            return False

        workflow = {
            "steps": [{"name": "reflect", "type": "llm", "prompt": "Base prompt"}]
        }

        behavior = Component(
            name="test",
            component_type="behavior",
            inject_into=[],
            injection_rules=[
                InjectionRule(
                    step="reflect",
                    always=False,
                    condition={"invoke": "analyzer", "method": "check", "fallback": False},
                )
            ],
            prompt_fragment="\nShould NOT appear!",
        )

        result = inject_components_into_workflow(
            workflow, behaviors=[behavior], invoke_resolver=mock_resolver
        )

        assert "Should NOT appear!" not in result["steps"][0]["prompt"]
        assert result["steps"][0]["prompt"] == "Base prompt"

    def test_mixed_always_and_conditional(self) -> None:
        """Mix of always and conditional rules handled correctly."""

        def mock_resolver(
            artifact_id: str,
            method: str,
            args: list[Any],
            kwargs: dict[str, Any],
            fallback: Any,
        ) -> bool:
            # Only allow if method is "allowed"
            return method == "allowed"

        workflow = {
            "steps": [{"name": "observe", "type": "llm", "prompt": "Base"}]
        }

        behavior1 = Component(
            name="always_inject",
            component_type="behavior",
            inject_into=[],
            injection_rules=[InjectionRule(step="observe", always=True)],
            prompt_fragment="\nAlways here!",
        )

        behavior2 = Component(
            name="conditional_allowed",
            component_type="behavior",
            inject_into=[],
            injection_rules=[
                InjectionRule(
                    step="observe",
                    always=False,
                    condition={"invoke": "x", "method": "allowed", "fallback": False},
                )
            ],
            prompt_fragment="\nConditional allowed!",
        )

        behavior3 = Component(
            name="conditional_blocked",
            component_type="behavior",
            inject_into=[],
            injection_rules=[
                InjectionRule(
                    step="observe",
                    always=False,
                    condition={"invoke": "x", "method": "blocked", "fallback": False},
                )
            ],
            prompt_fragment="\nConditional blocked!",
        )

        result = inject_components_into_workflow(
            workflow, behaviors=[behavior1, behavior2, behavior3], invoke_resolver=mock_resolver
        )

        assert "Always here!" in result["steps"][0]["prompt"]
        assert "Conditional allowed!" in result["steps"][0]["prompt"]
        assert "Conditional blocked!" not in result["steps"][0]["prompt"]

    def test_fallback_to_legacy_inject_into(self) -> None:
        """Component without injection_rules uses legacy inject_into."""
        workflow = {
            "steps": [{"name": "ideate", "type": "llm", "prompt": "Base"}]
        }

        # Component with inject_into but no injection_rules
        behavior = Component(
            name="legacy",
            component_type="behavior",
            inject_into=["ideate"],
            injection_rules=[],  # Empty - fall back to inject_into
            prompt_fragment="\nLegacy injection!",
        )

        result = inject_components_into_workflow(workflow, behaviors=[behavior])

        assert "Legacy injection!" in result["steps"][0]["prompt"]
