"""Workflow state machine support.

Implements state machine behavior for agent workflows, allowing agents to
have explicit states with validated transitions.

Usage:
    from src.agents.state_machine import WorkflowStateMachine, StateConfig

    config = StateConfig(
        states=["idle", "planning", "executing"],
        initial_state="idle",
        transitions=[
            {"from": "idle", "to": "planning"},
            {"from": "planning", "to": "executing"},
            {"from": "executing", "to": "idle"},
        ]
    )

    machine = WorkflowStateMachine(config)
    machine.transition_to("planning")  # OK
    machine.transition_to("executing")  # Fails - not adjacent
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any

logger = logging.getLogger(__name__)


@dataclass
class StateTransition:
    """A valid state transition.

    Attributes:
        from_state: Source state (or "*" for any state)
        to_state: Target state
        condition: Optional condition expression (evaluated with context)
    """

    from_state: str
    to_state: str
    condition: str | None = None


@dataclass
class StateConfig:
    """Configuration for a workflow state machine.

    Attributes:
        states: List of valid state names
        initial_state: Starting state (must be in states list)
        transitions: List of valid transitions between states
    """

    states: list[str] = field(default_factory=list)
    initial_state: str = ""
    transitions: list[StateTransition] = field(default_factory=list)

    def __post_init__(self) -> None:
        """Validate state configuration."""
        if self.states and self.initial_state and self.initial_state not in self.states:
            raise ValueError(
                f"Initial state '{self.initial_state}' not in states list: {self.states}"
            )

    @classmethod
    def from_dict(cls, config: dict[str, Any]) -> StateConfig:
        """Create StateConfig from dictionary.

        Args:
            config: Dictionary with state machine configuration

        Returns:
            StateConfig instance
        """
        states = config.get("states", [])
        initial_state = config.get("initial_state", states[0] if states else "")

        transitions: list[StateTransition] = []
        for t in config.get("transitions", []):
            if isinstance(t, dict):
                transitions.append(StateTransition(
                    from_state=t.get("from", "*"),
                    to_state=t["to"],
                    condition=t.get("condition"),
                ))
            elif isinstance(t, str):
                # Simple format: "from->to"
                if "->" in t:
                    from_state, to_state = t.split("->", 1)
                    transitions.append(StateTransition(
                        from_state=from_state.strip(),
                        to_state=to_state.strip(),
                    ))

        return cls(
            states=states,
            initial_state=initial_state,
            transitions=transitions,
        )


class WorkflowStateMachine:
    """Manages state transitions for a workflow.

    The state machine validates transitions and tracks state history.
    State is stored in the workflow context for persistence.

    Attributes:
        config: State machine configuration
        current_state: Current state name
        history: List of past states (most recent last)
    """

    def __init__(
        self,
        config: StateConfig,
        initial_context: dict[str, Any] | None = None,
    ) -> None:
        """Initialize state machine.

        Args:
            config: State machine configuration
            initial_context: Optional context to restore state from
        """
        self.config = config
        self.history: list[str] = []

        # Restore state from context if available
        if initial_context and "_state_machine" in initial_context:
            sm_data = initial_context["_state_machine"]
            self.current_state = sm_data.get("current_state", config.initial_state)
            self.history = sm_data.get("history", [])
        else:
            self.current_state = config.initial_state

    def can_transition_to(
        self,
        target_state: str,
        context: dict[str, Any] | None = None,
    ) -> bool:
        """Check if transition to target state is valid.

        Args:
            target_state: State to transition to
            context: Optional context for evaluating conditions

        Returns:
            True if transition is valid
        """
        # Check if target state exists
        if self.config.states and target_state not in self.config.states:
            return False

        # Check if transition is defined
        for transition in self.config.transitions:
            if transition.to_state != target_state:
                continue

            # Check source state matches
            if transition.from_state != "*" and transition.from_state != self.current_state:
                continue

            # Check condition if present
            if transition.condition and context:
                try:
                    if not eval(transition.condition, {}, context):  # noqa: S307
                        continue
                except Exception:
                    continue

            return True

        # No valid transition found
        # If no transitions defined, allow any state change (permissive mode)
        if not self.config.transitions:
            return True

        return False

    def transition_to(
        self,
        target_state: str,
        context: dict[str, Any] | None = None,
    ) -> bool:
        """Attempt to transition to target state.

        Args:
            target_state: State to transition to
            context: Optional context for evaluating conditions

        Returns:
            True if transition succeeded
        """
        if not self.can_transition_to(target_state, context):
            logger.warning(
                f"Invalid transition from '{self.current_state}' to '{target_state}'"
            )
            return False

        # Record history
        if self.current_state:
            self.history.append(self.current_state)

        # Update state
        old_state = self.current_state
        self.current_state = target_state

        logger.debug(f"State transition: {old_state} -> {target_state}")
        return True

    def in_state(self, *states: str) -> bool:
        """Check if current state is one of the given states.

        Args:
            *states: State names to check

        Returns:
            True if current state matches any of the given states
        """
        return self.current_state in states

    def to_context(self) -> dict[str, Any]:
        """Export state machine data for context storage.

        Returns:
            Dictionary with state machine data
        """
        return {
            "_state_machine": {
                "current_state": self.current_state,
                "history": self.history.copy(),
                "states": self.config.states,
            }
        }

    def get_available_transitions(self) -> list[str]:
        """Get list of states that can be transitioned to.

        Returns:
            List of valid target state names
        """
        available: list[str] = []

        for transition in self.config.transitions:
            if transition.from_state == "*" or transition.from_state == self.current_state:
                if transition.to_state not in available:
                    available.append(transition.to_state)

        # If no transitions defined, all states are available
        if not self.config.transitions and self.config.states:
            return [s for s in self.config.states if s != self.current_state]

        return available
