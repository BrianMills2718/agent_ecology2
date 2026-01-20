"""Safe expression evaluation for workflow conditions.

This module provides a secure alternative to Python's eval() for evaluating
workflow condition expressions. It uses simpleeval to prevent arbitrary code
execution while allowing common comparison and logical operations.

Plan #123: Replace eval() with safe expression evaluator.
"""

import logging
from typing import Any

from simpleeval import EvalWithCompoundTypes, InvalidExpression

logger = logging.getLogger(__name__)


class SafeExpressionError(Exception):
    """Raised when a safe expression evaluation fails."""

    pass


def safe_eval_condition(expression: str, context: dict[str, Any]) -> bool:
    """Safely evaluate a condition expression.

    This function evaluates simple boolean expressions without the security
    risks of Python's eval(). It supports:
    - Basic comparisons: ==, !=, <, >, <=, >=
    - Logical operators: and, or, not
    - Arithmetic: +, -, *, /, %
    - String operations: in, not in
    - Attribute access on allowed types (dict, list)

    It blocks:
    - Import statements
    - Function calls to dangerous builtins
    - Attribute access to dunder methods
    - Arbitrary code execution

    Args:
        expression: A string expression to evaluate (e.g., "x > 5 and y == 'active'")
        context: A dictionary of variable names to their values

    Returns:
        The boolean result of evaluating the expression

    Raises:
        SafeExpressionError: If the expression is invalid or uses disallowed operations

    Example:
        >>> safe_eval_condition("count > 10 and status == 'ready'", {"count": 15, "status": "ready"})
        True
        >>> safe_eval_condition("items", {"items": []})  # Empty list is falsy
        False
    """
    if not expression or not expression.strip():
        raise SafeExpressionError("Empty expression")

    try:
        # EvalWithCompoundTypes allows dict/list literals and indexing
        evaluator = EvalWithCompoundTypes(names=context)

        # Remove dangerous functions that might still be accessible
        evaluator.functions = {}  # No function calls allowed

        result = evaluator.eval(expression)
        return bool(result)

    except InvalidExpression as e:
        raise SafeExpressionError(f"Invalid expression '{expression}': {e}") from e
    except (KeyError, TypeError, AttributeError) as e:
        raise SafeExpressionError(
            f"Error evaluating '{expression}': {e}"
        ) from e
    except Exception as e:
        # Catch any other evaluation errors
        raise SafeExpressionError(
            f"Unexpected error evaluating '{expression}': {e}"
        ) from e


def try_safe_eval_condition(
    expression: str, context: dict[str, Any], default: bool = False
) -> bool:
    """Safely evaluate a condition, returning a default on failure.

    This is a convenience wrapper around safe_eval_condition that catches
    SafeExpressionError and returns a default value instead of raising.

    Args:
        expression: A string expression to evaluate
        context: A dictionary of variable names to their values
        default: Value to return if evaluation fails (default: False)

    Returns:
        The boolean result, or the default value on error
    """
    try:
        return safe_eval_condition(expression, context)
    except SafeExpressionError as e:
        logger.warning(f"Safe eval failed: {e}")
        return default
