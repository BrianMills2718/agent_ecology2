"""Unit tests for safe expression evaluator.

Tests for Plan #123: Replace eval() with safe expression evaluator.
Verifies both functional correctness and security properties.
"""

from __future__ import annotations

import pytest

from src.agents.safe_eval import (
    SafeExpressionError,
    safe_eval_condition,
    try_safe_eval_condition,
)


@pytest.mark.plans([123])
class TestSafeEvalConditionBasic:
    """Tests for basic expression evaluation functionality."""

    def test_simple_comparison_greater_than(self) -> None:
        """Basic > comparison evaluates correctly."""
        assert safe_eval_condition("x > 5", {"x": 10}) is True
        assert safe_eval_condition("x > 5", {"x": 3}) is False

    def test_simple_comparison_equality(self) -> None:
        """Equality comparison evaluates correctly."""
        assert safe_eval_condition("status == 'active'", {"status": "active"}) is True
        assert safe_eval_condition("status == 'active'", {"status": "inactive"}) is False

    def test_logical_and(self) -> None:
        """Logical AND evaluates correctly."""
        context = {"x": 10, "y": 5}
        assert safe_eval_condition("x > 5 and y < 10", context) is True
        assert safe_eval_condition("x > 5 and y > 10", context) is False

    def test_logical_or(self) -> None:
        """Logical OR evaluates correctly."""
        context = {"x": 3, "y": 15}
        assert safe_eval_condition("x > 5 or y > 10", context) is True
        assert safe_eval_condition("x > 5 or y < 10", context) is False

    def test_logical_not(self) -> None:
        """Logical NOT evaluates correctly."""
        assert safe_eval_condition("not x", {"x": False}) is True
        assert safe_eval_condition("not x", {"x": True}) is False

    def test_string_in_operator(self) -> None:
        """String 'in' operator works correctly."""
        assert safe_eval_condition("'foo' in items", {"items": ["foo", "bar"]}) is True
        assert safe_eval_condition("'baz' in items", {"items": ["foo", "bar"]}) is False

    def test_arithmetic_operations(self) -> None:
        """Basic arithmetic in expressions works."""
        assert safe_eval_condition("x + y > 10", {"x": 5, "y": 6}) is True
        assert safe_eval_condition("x * 2 == 10", {"x": 5}) is True

    def test_dict_access(self) -> None:
        """Dictionary key access in expressions works."""
        context = {"data": {"count": 5, "status": "ready"}}
        assert safe_eval_condition("data['count'] > 3", context) is True
        assert safe_eval_condition("data['status'] == 'ready'", context) is True

    def test_list_indexing(self) -> None:
        """List indexing in expressions works."""
        context = {"items": [1, 2, 3, 4, 5]}
        assert safe_eval_condition("items[0] == 1", context) is True
        assert safe_eval_condition("items[-1] == 5", context) is True

    def test_truthy_falsy_values(self) -> None:
        """Truthy/falsy evaluation works correctly."""
        assert safe_eval_condition("items", {"items": [1, 2, 3]}) is True
        assert safe_eval_condition("items", {"items": []}) is False
        assert safe_eval_condition("count", {"count": 0}) is False
        assert safe_eval_condition("count", {"count": 1}) is True


@pytest.mark.plans([123])
class TestSafeEvalConditionSecurity:
    """Security tests - verifies dangerous operations are blocked."""

    def test_blocks_import_statement(self) -> None:
        """Import statements are blocked."""
        with pytest.raises(SafeExpressionError):
            safe_eval_condition("__import__('os')", {})

    def test_blocks_builtin_import(self) -> None:
        """Builtin import function is blocked."""
        with pytest.raises(SafeExpressionError):
            safe_eval_condition("__builtins__['__import__']('os')", {})

    def test_blocks_eval(self) -> None:
        """Nested eval is blocked."""
        with pytest.raises(SafeExpressionError):
            safe_eval_condition("eval('1+1')", {})

    def test_blocks_exec(self) -> None:
        """exec is blocked."""
        with pytest.raises(SafeExpressionError):
            safe_eval_condition("exec('x=1')", {})

    def test_blocks_open_file(self) -> None:
        """File access is blocked."""
        with pytest.raises(SafeExpressionError):
            safe_eval_condition("open('/etc/passwd')", {})

    def test_blocks_dunder_class(self) -> None:
        """Access to __class__ is blocked."""
        with pytest.raises(SafeExpressionError):
            safe_eval_condition("''.__class__", {})

    def test_blocks_dunder_bases(self) -> None:
        """Access to __bases__ is blocked."""
        with pytest.raises(SafeExpressionError):
            safe_eval_condition("''.__class__.__bases__", {})

    def test_blocks_dunder_mro(self) -> None:
        """Access to __mro__ is blocked."""
        with pytest.raises(SafeExpressionError):
            safe_eval_condition("''.__class__.__mro__", {})

    def test_blocks_dunder_subclasses(self) -> None:
        """Access to __subclasses__ is blocked."""
        with pytest.raises(SafeExpressionError):
            safe_eval_condition("''.__class__.__subclasses__()", {})

    def test_blocks_globals_access(self) -> None:
        """Access to __globals__ is blocked."""
        with pytest.raises(SafeExpressionError):
            safe_eval_condition("(lambda: 0).__globals__", {})

    def test_blocks_code_object_access(self) -> None:
        """Access to __code__ is blocked."""
        with pytest.raises(SafeExpressionError):
            safe_eval_condition("(lambda: 0).__code__", {})

    def test_blocks_os_system_via_chain(self) -> None:
        """Complex attack chain to os.system is blocked."""
        # This is a common attack pattern trying to get to os.system
        attack = (
            "''.__class__.__mro__[2].__subclasses__()[40]"
            "('/etc/passwd').read()"
        )
        with pytest.raises(SafeExpressionError):
            safe_eval_condition(attack, {})

    def test_blocks_arbitrary_function_calls(self) -> None:
        """Arbitrary function calls are blocked."""
        # Functions are disabled in the evaluator
        with pytest.raises(SafeExpressionError):
            safe_eval_condition("print('hello')", {})

    def test_blocks_compile(self) -> None:
        """compile() is blocked."""
        with pytest.raises(SafeExpressionError):
            safe_eval_condition("compile('x', '', 'eval')", {})

    def test_blocks_getattr_bypass(self) -> None:
        """getattr bypass attempts are blocked."""
        with pytest.raises(SafeExpressionError):
            safe_eval_condition("getattr(x, '__class__')", {"x": ""})


@pytest.mark.plans([123])
class TestSafeEvalConditionErrors:
    """Tests for error handling."""

    def test_empty_expression_raises(self) -> None:
        """Empty expression raises SafeExpressionError."""
        with pytest.raises(SafeExpressionError, match="Empty expression"):
            safe_eval_condition("", {})

    def test_whitespace_only_raises(self) -> None:
        """Whitespace-only expression raises SafeExpressionError."""
        with pytest.raises(SafeExpressionError, match="Empty expression"):
            safe_eval_condition("   ", {})

    def test_undefined_variable_raises(self) -> None:
        """Undefined variable raises SafeExpressionError."""
        with pytest.raises(SafeExpressionError):
            safe_eval_condition("undefined_var > 5", {})

    def test_invalid_syntax_raises(self) -> None:
        """Invalid syntax raises SafeExpressionError."""
        with pytest.raises(SafeExpressionError):
            safe_eval_condition("x > > 5", {"x": 10})

    def test_type_error_raises(self) -> None:
        """Type errors raise SafeExpressionError."""
        with pytest.raises(SafeExpressionError):
            safe_eval_condition("x + 'string'", {"x": 5})


@pytest.mark.plans([123])
class TestTrySafeEvalCondition:
    """Tests for try_safe_eval_condition helper."""

    def test_returns_result_on_success(self) -> None:
        """Returns actual result when evaluation succeeds."""
        assert try_safe_eval_condition("x > 5", {"x": 10}) is True
        assert try_safe_eval_condition("x > 5", {"x": 3}) is False

    def test_returns_default_on_error(self) -> None:
        """Returns default value when evaluation fails."""
        assert try_safe_eval_condition("undefined", {}, default=False) is False
        assert try_safe_eval_condition("undefined", {}, default=True) is True

    def test_returns_false_by_default_on_error(self) -> None:
        """Default value is False when not specified."""
        assert try_safe_eval_condition("undefined", {}) is False

    def test_returns_default_on_security_violation(self) -> None:
        """Returns default on blocked operations instead of raising."""
        assert try_safe_eval_condition("__import__('os')", {}) is False
        assert try_safe_eval_condition("eval('1')", {}) is False


@pytest.mark.plans([123])
class TestWorkflowIntegration:
    """Integration tests for workflow condition evaluation."""

    def test_workflow_condition_with_safe_eval(self) -> None:
        """Workflow step run_if conditions use safe evaluation."""
        from src.agents.workflow import WorkflowRunner, WorkflowStep, StepType

        step = WorkflowStep(
            name="conditional_step",
            step_type=StepType.CODE,
            code="result = 'executed'",
            run_if="count > 5",
        )
        runner = WorkflowRunner()

        # Should run when condition is true
        context_true: dict = {"count": 10}
        result = runner.execute_step(step, context_true)
        assert result["success"] is True
        assert "skipped" not in result or result.get("skipped") is not True

        # Should skip when condition is false
        context_false: dict = {"count": 3}
        result = runner.execute_step(step, context_false)
        assert result.get("skipped") is True

    def test_workflow_blocks_dangerous_condition(self) -> None:
        """Workflow skips step when condition contains dangerous code."""
        from src.agents.workflow import WorkflowRunner, WorkflowStep, StepType

        step = WorkflowStep(
            name="dangerous_step",
            step_type=StepType.CODE,
            code="result = 'should not execute'",
            run_if="__import__('os').system('ls')",
        )
        runner = WorkflowRunner()
        context: dict = {}

        # Should skip (not raise) since workflow catches SafeExpressionError
        result = runner.execute_step(step, context)
        assert result.get("skipped") is True


@pytest.mark.plans([123])
class TestStateMachineIntegration:
    """Integration tests for state machine condition evaluation."""

    def test_state_machine_condition_with_safe_eval(self) -> None:
        """State machine transition conditions use safe evaluation."""
        from src.agents.state_machine import (
            WorkflowStateMachine,
            StateConfig,
            StateTransition,
        )

        config = StateConfig(
            states=["idle", "active"],
            initial_state="idle",
            transitions=[
                StateTransition(
                    from_state="idle",
                    to_state="active",
                    condition="count > 5",
                )
            ],
        )
        machine = WorkflowStateMachine(config)

        # Should allow transition when condition is true
        assert machine.can_transition_to("active", {"count": 10}) is True

        # Should block transition when condition is false
        assert machine.can_transition_to("active", {"count": 3}) is False

    def test_state_machine_blocks_dangerous_condition(self) -> None:
        """State machine blocks transition with dangerous condition."""
        from src.agents.state_machine import (
            WorkflowStateMachine,
            StateConfig,
            StateTransition,
        )

        config = StateConfig(
            states=["idle", "compromised"],
            initial_state="idle",
            transitions=[
                StateTransition(
                    from_state="idle",
                    to_state="compromised",
                    condition="__import__('os').system('ls')",
                )
            ],
        )
        machine = WorkflowStateMachine(config)

        # Should block (return False) since dangerous conditions fail safely
        # Note: Must provide non-empty context for condition to be evaluated
        assert machine.can_transition_to("compromised", {"trigger": True}) is False
