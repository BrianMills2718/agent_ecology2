"""
Prompt Component Loader - Loads and injects modular prompt components.

Components are reusable prompt fragments that can be mixed and matched
to create different agent "genotypes" for experimentation.

Component Types:
- Behaviors: Behavioral modifiers injected into prompts
- Phases: Reusable workflow step definitions
- Goals: High-level directives that shape behavior

Plan #222 Phase 2: Conditional Injection
Components can specify conditional injection rules that invoke artifacts
to determine whether injection should occur at runtime.

Usage:
    from src.agents.component_loader import ComponentRegistry

    registry = ComponentRegistry()
    registry.load_all()  # Load from default location

    # Get components for an agent
    behaviors = registry.get_behaviors(["buy_before_build", "economic_participant"])

    # Inject into workflow config (with optional invoke resolver for conditionals)
    workflow_dict = inject_components(workflow_dict, behaviors=behaviors, invoke_resolver=resolver)
"""

from __future__ import annotations

import logging
import threading
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable

import yaml

logger = logging.getLogger(__name__)

# Type alias for invoke resolver callback (Plan #222)
InvokeResolver = Callable[[str, str, list[Any], dict[str, Any], Any], Any]

# Default components directory
COMPONENTS_DIR = Path(__file__).parent / "_components"


@dataclass
class InjectionRule:
    """A rule for conditional injection into a workflow step.

    Plan #222 Phase 2: Supports artifact-invoked conditions for injection.

    Attributes:
        step: Name of the step to inject into
        always: If True, always inject (no condition check)
        condition: Optional InvokeSpec dict for conditional injection
    """

    step: str
    always: bool = True
    condition: dict[str, Any] | None = None  # InvokeSpec format

    @classmethod
    def from_value(cls, value: str | dict[str, Any]) -> "InjectionRule":
        """Create InjectionRule from YAML value.

        Supports both simple string format and conditional dict format:
            # Simple: always inject
            inject_into:
              - observe
              - reflect

            # Conditional: check artifact before injecting
            inject_into:
              - step: observe
                always: true
              - step: reflect
                if:
                  invoke: "context_analyzer"
                  method: "needs_guidance"
                  fallback: true
        """
        if isinstance(value, str):
            # Simple format: just step name, always inject
            return cls(step=value, always=True, condition=None)
        elif isinstance(value, dict):
            step = value.get("step", "")
            always = value.get("always", False)
            condition = value.get("if")  # InvokeSpec format
            # If no explicit always and no condition, default to always=True
            if not condition and not value.get("always", None):
                always = True
            return cls(step=step, always=always, condition=condition)
        else:
            raise ValueError(f"Invalid injection rule format: {value}")


@dataclass
class Component:
    """A prompt component that can be injected into workflows.

    Plan #222 Phase 2: Supports conditional injection via InvokeSpec.

    Attributes:
        name: Unique identifier for the component
        component_type: Type of component (behavior, phase, goal)
        version: Component version for compatibility
        description: Human-readable description
        inject_into: List of step names where this should be injected (legacy)
        injection_rules: List of InjectionRules with conditional support (Plan #222)
        prompt_fragment: The actual prompt text to inject
        requires_context: List of context variables this component needs
    """

    name: str
    component_type: str  # "behavior", "phase", or "goal"
    version: int = 1
    description: str = ""
    inject_into: list[str] = field(default_factory=list)  # Legacy simple list
    injection_rules: list[InjectionRule] = field(default_factory=list)  # Plan #222
    prompt_fragment: str = ""
    requires_context: list[str] = field(default_factory=list)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "Component":
        """Create Component from dictionary (parsed YAML).

        Plan #222: Parses both simple inject_into list and conditional rules.
        """
        # Parse inject_into which can be either:
        # - Simple list of strings: ["observe", "reflect"]
        # - List with conditional dicts: [{"step": "observe", "if": {...}}]
        raw_inject = data.get("inject_into", [])
        simple_inject: list[str] = []
        rules: list[InjectionRule] = []

        for item in raw_inject:
            rule = InjectionRule.from_value(item)
            rules.append(rule)
            # Also maintain legacy simple list for backward compatibility
            if rule.always and not rule.condition:
                simple_inject.append(rule.step)

        return cls(
            name=data["name"],
            component_type=data["type"],
            version=data.get("version", 1),
            description=data.get("description", ""),
            inject_into=simple_inject,  # Legacy simple list
            injection_rules=rules,  # Full rules with conditions
            prompt_fragment=data.get("prompt_fragment", ""),
            requires_context=data.get("requires_context", []),
        )


class ComponentRegistry:
    """Registry of all available prompt components.

    Loads components from the _components directory and provides
    lookup by name and type.
    """

    def __init__(self, components_dir: Path | None = None) -> None:
        """Initialize the registry.

        Args:
            components_dir: Directory containing component YAML files.
                           Defaults to src/agents/_components/
        """
        self.components_dir = components_dir or COMPONENTS_DIR
        self.behaviors: dict[str, Component] = {}
        self.phases: dict[str, Component] = {}
        self.goals: dict[str, Component] = {}

    def load_all(self) -> None:
        """Load all components from the components directory."""
        if not self.components_dir.exists():
            logger.warning(f"Components directory not found: {self.components_dir}")
            return

        # Load behaviors
        behaviors_dir = self.components_dir / "behaviors"
        if behaviors_dir.exists():
            for path in behaviors_dir.glob("*.yaml"):
                self._load_component(path, "behavior")

        # Load phases
        phases_dir = self.components_dir / "phases"
        if phases_dir.exists():
            for path in phases_dir.glob("*.yaml"):
                self._load_component(path, "phase")

        # Load goals
        goals_dir = self.components_dir / "goals"
        if goals_dir.exists():
            for path in goals_dir.glob("*.yaml"):
                self._load_component(path, "goal")

        logger.info(
            f"Loaded components: {len(self.behaviors)} behaviors, "
            f"{len(self.phases)} phases, {len(self.goals)} goals"
        )

    def _load_component(self, path: Path, expected_type: str) -> None:
        """Load a single component from a YAML file."""
        try:
            with open(path) as f:
                data = yaml.safe_load(f)

            if not data:
                logger.warning(f"Empty component file: {path}")
                return

            component = Component.from_dict(data)

            # Validate type matches directory
            if component.component_type != expected_type:
                logger.warning(
                    f"Component {path} has type '{component.component_type}' "
                    f"but is in '{expected_type}' directory"
                )

            # Store in appropriate registry
            if component.component_type == "behavior":
                self.behaviors[component.name] = component
            elif component.component_type == "phase":
                self.phases[component.name] = component
            elif component.component_type == "goal":
                self.goals[component.name] = component
            else:
                logger.warning(f"Unknown component type: {component.component_type}")

            logger.debug(f"Loaded component: {component.name}")

        except Exception as e:
            logger.error(f"Failed to load component {path}: {e}")

    def get_behavior(self, name: str) -> Component | None:
        """Get a behavior component by name."""
        return self.behaviors.get(name)

    def get_phase(self, name: str) -> Component | None:
        """Get a phase component by name."""
        return self.phases.get(name)

    def get_goal(self, name: str) -> Component | None:
        """Get a goal component by name."""
        return self.goals.get(name)

    def get_behaviors(self, names: list[str]) -> list[Component]:
        """Get multiple behavior components by name.

        Args:
            names: List of behavior names to retrieve

        Returns:
            List of Component objects (missing ones are logged and skipped)
        """
        components = []
        for name in names:
            component = self.behaviors.get(name)
            if component:
                components.append(component)
            else:
                logger.warning(f"Behavior not found: {name}")
        return components

    def get_goals(self, names: list[str]) -> list[Component]:
        """Get multiple goal components by name."""
        components = []
        for name in names:
            component = self.goals.get(name)
            if component:
                components.append(component)
            else:
                logger.warning(f"Goal not found: {name}")
        return components


def _evaluate_injection_condition(
    condition: dict[str, Any],
    invoke_resolver: InvokeResolver | None,
    context: dict[str, Any],
) -> bool:
    """Evaluate an injection condition using the invoke resolver.

    Plan #222 Phase 2: Supports InvokeSpec format for conditional injection.

    Args:
        condition: InvokeSpec dict with "invoke", "method", "args", "fallback"
        invoke_resolver: Callback to resolve artifact invocations
        context: Runtime context for condition evaluation

    Returns:
        True if injection should occur, False otherwise
    """
    if invoke_resolver is None:
        # No resolver available, use fallback value
        fallback = condition.get("fallback", True)
        logger.debug(
            f"No invoke_resolver, using fallback={fallback} for condition: {condition}"
        )
        return bool(fallback)

    # Extract InvokeSpec fields
    artifact_id = condition.get("invoke", "")
    method = condition.get("method", "")
    args = condition.get("args", [])
    kwargs = condition.get("kwargs", {})
    fallback = condition.get("fallback", True)

    try:
        result = invoke_resolver(artifact_id, method, args, kwargs, fallback)
        return bool(result)
    except Exception as e:
        logger.warning(
            f"Error evaluating injection condition for {artifact_id}.{method}: {e}. "
            f"Using fallback={fallback}"
        )
        return bool(fallback)


def inject_components_into_workflow(
    workflow_dict: dict[str, Any],
    behaviors: list[Component] | None = None,
    goals: list[Component] | None = None,
    invoke_resolver: InvokeResolver | None = None,
    context: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Inject component prompt fragments into a workflow configuration.

    This modifies the workflow dictionary in place, appending component
    prompt fragments to matching step prompts.

    Plan #222 Phase 2: Supports conditional injection via InjectionRules.
    Components can specify conditions that are evaluated at runtime using
    artifact invocations to determine whether injection should occur.

    Args:
        workflow_dict: Workflow configuration dictionary (from agent.yaml)
        behaviors: List of behavior components to inject
        goals: List of goal components to inject
        invoke_resolver: Optional callback to resolve artifact conditions (Plan #222)
        context: Optional runtime context for condition evaluation (Plan #222)

    Returns:
        Modified workflow dictionary
    """
    if not behaviors and not goals:
        return workflow_dict

    all_components = (behaviors or []) + (goals or [])
    ctx = context or {}

    # Build a map of step_name -> fragments to inject
    # Plan #222: Use injection_rules with conditional evaluation
    injections: dict[str, list[str]] = {}

    for component in all_components:
        # Use injection_rules if available (Plan #222), fallback to inject_into
        if component.injection_rules:
            for rule in component.injection_rules:
                should_inject = True

                if not rule.always and rule.condition:
                    # Evaluate the condition
                    should_inject = _evaluate_injection_condition(
                        rule.condition, invoke_resolver, ctx
                    )

                if should_inject:
                    if rule.step not in injections:
                        injections[rule.step] = []
                    injections[rule.step].append(component.prompt_fragment)
                    logger.debug(
                        f"Component '{component.name}' will inject into step '{rule.step}'"
                    )
                else:
                    logger.debug(
                        f"Component '{component.name}' skipped for step '{rule.step}' "
                        "(condition evaluated to false)"
                    )
        else:
            # Legacy: use simple inject_into list (always inject)
            for step_name in component.inject_into:
                if step_name not in injections:
                    injections[step_name] = []
                injections[step_name].append(component.prompt_fragment)

    # Inject into matching steps
    steps = workflow_dict.get("steps", [])
    for step in steps:
        step_name = step.get("name", "")
        if step_name in injections and step.get("prompt"):
            # Append all fragments to the prompt
            fragments = "\n".join(injections[step_name])
            step["prompt"] = step["prompt"] + "\n" + fragments
            logger.debug(
                f"Injected {len(injections[step_name])} component(s) into step '{step_name}'"
            )

    return workflow_dict


# Global registry singleton with thread-safe initialization (Plan #213 fix)
_registry: ComponentRegistry | None = None
_registry_lock = threading.Lock()


def get_registry() -> ComponentRegistry:
    """Get the global component registry (lazy-loaded, thread-safe).

    Uses double-checked locking pattern to avoid lock contention after
    initialization while ensuring thread-safety during first access.
    """
    global _registry
    # Fast path: registry already initialized
    if _registry is not None:
        return _registry

    # Slow path: need to initialize with lock
    with _registry_lock:
        # Double-check after acquiring lock (another thread may have initialized)
        if _registry is None:
            registry = ComponentRegistry()
            registry.load_all()
            _registry = registry  # Assign only after fully loaded
    return _registry


def load_agent_components(
    component_config: dict[str, list[str]] | None,
) -> tuple[list[Component], list[Component]]:
    """Load components specified in an agent's config.

    Args:
        component_config: The 'components' section from agent.yaml, e.g.:
            {"behaviors": ["buy_before_build"], "goals": ["facilitate_transactions"]}

    Returns:
        Tuple of (behaviors, goals) component lists
    """
    if not component_config:
        return [], []

    registry = get_registry()

    behaviors = registry.get_behaviors(component_config.get("behaviors", []))
    goals = registry.get_goals(component_config.get("goals", []))

    return behaviors, goals
