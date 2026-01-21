"""
Prompt Component Loader - Loads and injects modular prompt components.

Components are reusable prompt fragments that can be mixed and matched
to create different agent "genotypes" for experimentation.

Component Types:
- Traits: Behavioral modifiers injected into prompts
- Phases: Reusable workflow step definitions
- Goals: High-level directives that shape behavior

Usage:
    from src.agents.component_loader import ComponentRegistry

    registry = ComponentRegistry()
    registry.load_all()  # Load from default location

    # Get components for an agent
    traits = registry.get_traits(["buy_before_build", "economic_participant"])

    # Inject into workflow config
    workflow_dict = inject_components(workflow_dict, traits=traits)
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml

logger = logging.getLogger(__name__)

# Default components directory
COMPONENTS_DIR = Path(__file__).parent / "_components"


@dataclass
class Component:
    """A prompt component that can be injected into workflows.

    Attributes:
        name: Unique identifier for the component
        component_type: Type of component (trait, phase, goal)
        version: Component version for compatibility
        description: Human-readable description
        inject_into: List of step names where this should be injected
        prompt_fragment: The actual prompt text to inject
        requires_context: List of context variables this component needs
    """

    name: str
    component_type: str  # "trait", "phase", or "goal"
    version: int = 1
    description: str = ""
    inject_into: list[str] = field(default_factory=list)
    prompt_fragment: str = ""
    requires_context: list[str] = field(default_factory=list)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Component:
        """Create Component from dictionary (parsed YAML)."""
        return cls(
            name=data["name"],
            component_type=data["type"],
            version=data.get("version", 1),
            description=data.get("description", ""),
            inject_into=data.get("inject_into", []),
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
        self.traits: dict[str, Component] = {}
        self.phases: dict[str, Component] = {}
        self.goals: dict[str, Component] = {}

    def load_all(self) -> None:
        """Load all components from the components directory."""
        if not self.components_dir.exists():
            logger.warning(f"Components directory not found: {self.components_dir}")
            return

        # Load traits
        traits_dir = self.components_dir / "traits"
        if traits_dir.exists():
            for path in traits_dir.glob("*.yaml"):
                self._load_component(path, "trait")

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
            f"Loaded components: {len(self.traits)} traits, "
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
            if component.component_type == "trait":
                self.traits[component.name] = component
            elif component.component_type == "phase":
                self.phases[component.name] = component
            elif component.component_type == "goal":
                self.goals[component.name] = component
            else:
                logger.warning(f"Unknown component type: {component.component_type}")

            logger.debug(f"Loaded component: {component.name}")

        except Exception as e:
            logger.error(f"Failed to load component {path}: {e}")

    def get_trait(self, name: str) -> Component | None:
        """Get a trait component by name."""
        return self.traits.get(name)

    def get_phase(self, name: str) -> Component | None:
        """Get a phase component by name."""
        return self.phases.get(name)

    def get_goal(self, name: str) -> Component | None:
        """Get a goal component by name."""
        return self.goals.get(name)

    def get_traits(self, names: list[str]) -> list[Component]:
        """Get multiple trait components by name.

        Args:
            names: List of trait names to retrieve

        Returns:
            List of Component objects (missing ones are logged and skipped)
        """
        components = []
        for name in names:
            component = self.traits.get(name)
            if component:
                components.append(component)
            else:
                logger.warning(f"Trait not found: {name}")
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


def inject_components_into_workflow(
    workflow_dict: dict[str, Any],
    traits: list[Component] | None = None,
    goals: list[Component] | None = None,
) -> dict[str, Any]:
    """Inject component prompt fragments into a workflow configuration.

    This modifies the workflow dictionary in place, appending component
    prompt fragments to matching step prompts.

    Args:
        workflow_dict: Workflow configuration dictionary (from agent.yaml)
        traits: List of trait components to inject
        goals: List of goal components to inject

    Returns:
        Modified workflow dictionary
    """
    if not traits and not goals:
        return workflow_dict

    all_components = (traits or []) + (goals or [])

    # Build a map of step_name -> fragments to inject
    injections: dict[str, list[str]] = {}
    for component in all_components:
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


# Global registry singleton
_registry: ComponentRegistry | None = None


def get_registry() -> ComponentRegistry:
    """Get the global component registry (lazy-loaded)."""
    global _registry
    if _registry is None:
        _registry = ComponentRegistry()
        _registry.load_all()
    return _registry


def load_agent_components(
    component_config: dict[str, list[str]] | None,
) -> tuple[list[Component], list[Component]]:
    """Load components specified in an agent's config.

    Args:
        component_config: The 'components' section from agent.yaml, e.g.:
            {"traits": ["buy_before_build"], "goals": ["facilitate_transactions"]}

    Returns:
        Tuple of (traits, goals) component lists
    """
    if not component_config:
        return [], []

    registry = get_registry()

    traits = registry.get_traits(component_config.get("traits", []))
    goals = registry.get_goals(component_config.get("goals", []))

    return traits, goals
