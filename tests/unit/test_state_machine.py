"""Tests for workflow state machine support.

Tests the state machine integration with the workflow system (Plan #82).
"""

import pytest

from src.agents.state_machine import (
    StateConfig,
    StateTransition,
    WorkflowStateMachine,
)
from src.agents.workflow import WorkflowConfig, WorkflowRunner


@pytest.mark.plans([82])
class TestStateConfig:
    """Tests for StateConfig."""

    def test_from_dict_basic(self) -> None:
        """StateConfig parses states and initial_state."""
        config = StateConfig.from_dict({
            "states": ["idle", "working", "done"],
            "initial_state": "idle",
        })

        assert config.states == ["idle", "working", "done"]
        assert config.initial_state == "idle"
        assert config.transitions == []

    def test_from_dict_with_transitions(self) -> None:
        """StateConfig parses transition definitions."""
        config = StateConfig.from_dict({
            "states": ["idle", "working"],
            "initial_state": "idle",
            "transitions": [
                {"from": "idle", "to": "working"},
                {"from": "working", "to": "idle"},
            ],
        })

        assert len(config.transitions) == 2
        assert config.transitions[0].from_state == "idle"
        assert config.transitions[0].to_state == "working"

    def test_from_dict_shorthand_transitions(self) -> None:
        """StateConfig parses shorthand transition format."""
        config = StateConfig.from_dict({
            "states": ["a", "b", "c"],
            "initial_state": "a",
            "transitions": ["a->b", "b->c", "c->a"],
        })

        assert len(config.transitions) == 3
        assert config.transitions[0].from_state == "a"
        assert config.transitions[0].to_state == "b"

    def test_invalid_initial_state(self) -> None:
        """StateConfig rejects invalid initial state."""
        with pytest.raises(ValueError, match="not in states list"):
            StateConfig(
                states=["idle", "working"],
                initial_state="invalid",
            )


@pytest.mark.plans([82])
class TestWorkflowStateMachine:
    """Tests for WorkflowStateMachine."""

    def test_initial_state(self) -> None:
        """State machine starts in initial state."""
        config = StateConfig(
            states=["idle", "working"],
            initial_state="idle",
        )
        machine = WorkflowStateMachine(config)

        assert machine.current_state == "idle"
        assert machine.history == []

    def test_transition_without_restrictions(self) -> None:
        """State machine allows any transition when no transitions defined."""
        config = StateConfig(
            states=["idle", "working", "done"],
            initial_state="idle",
        )
        machine = WorkflowStateMachine(config)

        # Should allow any transition (permissive mode)
        assert machine.can_transition_to("working")
        assert machine.transition_to("working")
        assert machine.current_state == "working"
        assert machine.history == ["idle"]

    def test_transition_with_restrictions(self) -> None:
        """State machine validates transitions when defined."""
        config = StateConfig(
            states=["idle", "working", "done"],
            initial_state="idle",
            transitions=[
                StateTransition(from_state="idle", to_state="working"),
                StateTransition(from_state="working", to_state="done"),
            ],
        )
        machine = WorkflowStateMachine(config)

        # Valid transition
        assert machine.can_transition_to("working")
        assert machine.transition_to("working")

        # Invalid transition (not defined)
        assert not machine.can_transition_to("idle")  # Can't go back
        assert not machine.transition_to("idle")

        # Valid transition
        assert machine.transition_to("done")
        assert machine.current_state == "done"

    def test_wildcard_transition(self) -> None:
        """State machine supports wildcard source state."""
        config = StateConfig(
            states=["idle", "working", "error"],
            initial_state="idle",
            transitions=[
                StateTransition(from_state="idle", to_state="working"),
                StateTransition(from_state="*", to_state="error"),  # Any -> error
            ],
        )
        machine = WorkflowStateMachine(config)

        # Can go to error from any state
        assert machine.can_transition_to("error")
        machine.transition_to("working")
        assert machine.can_transition_to("error")

    def test_conditional_transition(self) -> None:
        """State machine evaluates transition conditions."""
        config = StateConfig(
            states=["idle", "working"],
            initial_state="idle",
            transitions=[
                StateTransition(
                    from_state="idle",
                    to_state="working",
                    condition="balance > 50",
                ),
            ],
        )
        machine = WorkflowStateMachine(config)

        # Condition not met
        assert not machine.can_transition_to("working", {"balance": 30})

        # Condition met
        assert machine.can_transition_to("working", {"balance": 100})

    def test_in_state(self) -> None:
        """in_state checks current state against multiple options."""
        config = StateConfig(states=["a", "b", "c"], initial_state="a")
        machine = WorkflowStateMachine(config)

        assert machine.in_state("a")
        assert machine.in_state("a", "b")  # Either a or b
        assert not machine.in_state("b", "c")

    def test_restore_from_context(self) -> None:
        """State machine restores from context."""
        config = StateConfig(states=["idle", "working"], initial_state="idle")

        # Simulate saved context
        context = {
            "_state_machine": {
                "current_state": "working",
                "history": ["idle"],
            }
        }

        machine = WorkflowStateMachine(config, context)
        assert machine.current_state == "working"
        assert machine.history == ["idle"]

    def test_to_context(self) -> None:
        """State machine exports to context."""
        config = StateConfig(states=["idle", "working"], initial_state="idle")
        machine = WorkflowStateMachine(config)
        machine.transition_to("working")

        context_data = machine.to_context()
        assert context_data["_state_machine"]["current_state"] == "working"
        assert context_data["_state_machine"]["history"] == ["idle"]

    def test_get_available_transitions(self) -> None:
        """get_available_transitions returns valid targets."""
        config = StateConfig(
            states=["idle", "working", "done"],
            initial_state="idle",
            transitions=[
                StateTransition(from_state="idle", to_state="working"),
                StateTransition(from_state="working", to_state="done"),
                StateTransition(from_state="working", to_state="idle"),
            ],
        )
        machine = WorkflowStateMachine(config)

        assert machine.get_available_transitions() == ["working"]

        machine.transition_to("working")
        assert set(machine.get_available_transitions()) == {"done", "idle"}


@pytest.mark.plans([82])
class TestWorkflowWithStateMachine:
    """Tests for workflow execution with state machine."""

    def test_workflow_with_state_machine(self) -> None:
        """Workflow executes with state machine tracking."""
        config = WorkflowConfig.from_dict({
            "state_machine": {
                "states": ["init", "processing", "complete"],
                "initial_state": "init",
                "transitions": ["init->processing", "processing->complete"],
            },
            "steps": [
                {
                    "name": "setup",
                    "type": "code",
                    "code": "result = 'ready'",
                    "transition_to": "processing",
                },
                {
                    "name": "process",
                    "type": "code",
                    "code": "output = 'done'",
                    "transition_to": "complete",
                },
            ],
        })

        runner = WorkflowRunner()
        context: dict = {}
        result = runner.run_workflow(config, context)

        assert result["success"]
        assert result["state"] == "complete"
        assert context["result"] == "ready"
        assert context["output"] == "done"

    def test_step_in_state_condition(self) -> None:
        """Steps with in_state only run in matching state."""
        config = WorkflowConfig.from_dict({
            "state_machine": {
                "states": ["idle", "active"],
                "initial_state": "idle",
            },
            "steps": [
                {
                    "name": "idle_step",
                    "type": "code",
                    "code": "idle_ran = True",
                    "in_state": "idle",
                },
                {
                    "name": "active_step",
                    "type": "code",
                    "code": "active_ran = True",
                    "in_state": "active",
                },
            ],
        })

        runner = WorkflowRunner()
        context: dict = {}
        result = runner.run_workflow(config, context)

        assert result["success"]
        assert context.get("idle_ran") is True
        assert context.get("active_ran") is None  # Skipped - wrong state

    def test_step_in_state_list(self) -> None:
        """Steps with in_state as list run in any matching state."""
        config = WorkflowConfig.from_dict({
            "state_machine": {
                "states": ["a", "b", "c"],
                "initial_state": "b",
            },
            "steps": [
                {
                    "name": "ab_step",
                    "type": "code",
                    "code": "ab_ran = True",
                    "in_state": ["a", "b"],  # List of states
                },
            ],
        })

        runner = WorkflowRunner()
        context: dict = {}
        result = runner.run_workflow(config, context)

        assert result["success"]
        assert context.get("ab_ran") is True  # Ran because in state 'b'

    def test_state_transition_after_step(self) -> None:
        """Step transition_to triggers state change."""
        config = WorkflowConfig.from_dict({
            "state_machine": {
                "states": ["start", "middle", "end"],
                "initial_state": "start",
                "transitions": ["start->middle", "middle->end"],
            },
            "steps": [
                {
                    "name": "first",
                    "type": "code",
                    "code": "x = 1",
                    "transition_to": "middle",
                },
                {
                    "name": "second",
                    "type": "code",
                    "code": "y = _current_state",  # Access current state
                },
            ],
        })

        runner = WorkflowRunner()
        context: dict = {}
        result = runner.run_workflow(config, context)

        assert result["success"]
        assert context["y"] == "middle"  # State was updated

    def test_invalid_transition_logged(self) -> None:
        """Invalid transition is logged but doesn't fail workflow."""
        config = WorkflowConfig.from_dict({
            "state_machine": {
                "states": ["a", "b", "c"],
                "initial_state": "a",
                "transitions": ["a->c"],  # Only a->c allowed, not a->b
            },
            "steps": [
                {
                    "name": "attempt_transition",
                    "type": "code",
                    "code": "x = 1",
                    "transition_to": "b",  # Will fail - not in transitions
                },
            ],
        })

        runner = WorkflowRunner()
        context: dict = {}
        result = runner.run_workflow(config, context)

        # Workflow succeeds but transition failed
        assert result["success"]
        assert result["state"] == "a"  # Still in original state

    def test_state_persisted_in_context(self) -> None:
        """State machine data is saved in context."""
        config = WorkflowConfig.from_dict({
            "state_machine": {
                "states": ["idle", "active"],
                "initial_state": "idle",
            },
            "steps": [
                {
                    "name": "activate",
                    "type": "code",
                    "code": "pass",
                    "transition_to": "active",
                },
            ],
        })

        runner = WorkflowRunner()
        context: dict = {}
        runner.run_workflow(config, context)

        # State machine data in context
        assert "_state_machine" in context
        assert context["_state_machine"]["current_state"] == "active"
        assert context["_state_machine"]["history"] == ["idle"]

    def test_workflow_without_state_machine(self) -> None:
        """Workflow without state_machine still works."""
        config = WorkflowConfig.from_dict({
            "steps": [
                {
                    "name": "simple",
                    "type": "code",
                    "code": "result = 42",
                },
            ],
        })

        runner = WorkflowRunner()
        context: dict = {}
        result = runner.run_workflow(config, context)

        assert result["success"]
        assert result["state"] is None  # No state machine
        assert context["result"] == 42
