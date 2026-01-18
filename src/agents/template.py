"""Safe template rendering for agent workflow context injection.

Implements ADR-0013 Phase 2: Declarative Context Injection.

This module provides a simple, safe template engine that supports
{{variable}} and {{nested.path}} syntax without code execution.

Usage:
    from src.agents.template import render_template

    template = "Hello, {{user.name}}! You have {{count}} messages."
    context = {"user": {"name": "Alice"}, "count": 5}
    result = render_template(template, context)
    # Result: "Hello, Alice! You have 5 messages."

Security:
    - No code execution (no eval, exec, or similar)
    - No function calls from templates
    - Values are converted to strings directly
    - Recursive template processing is prevented
"""

from __future__ import annotations

import re
from typing import Any


# Pattern matches {{variable}} or {{ variable }} (with optional spaces)
# Also matches {{nested.path.here}}
VARIABLE_PATTERN = re.compile(r"\{\{\s*([a-zA-Z_][a-zA-Z0-9_]*(?:\.[a-zA-Z_][a-zA-Z0-9_]*)*)\s*\}\}")


def render_template(template: str, context: dict[str, Any]) -> str:
    """Render a template with context values.

    Replaces {{variable}} placeholders with values from context.
    Supports nested paths like {{user.name}}.

    Args:
        template: Template string with {{variable}} placeholders
        context: Dictionary of values to substitute

    Returns:
        Rendered template with placeholders replaced

    Examples:
        >>> render_template("Hello, {{name}}!", {"name": "World"})
        'Hello, World!'

        >>> render_template("{{user.name}}", {"user": {"name": "Alice"}})
        'Alice'

        >>> render_template("{{missing}}", {})
        ''
    """
    if not template:
        return ""

    def replace_variable(match: re.Match[str]) -> str:
        """Replace a single variable match with its value."""
        path = match.group(1)
        value = _resolve_path(path, context)
        return _to_string(value)

    return VARIABLE_PATTERN.sub(replace_variable, template)


def _resolve_path(path: str, context: dict[str, Any]) -> Any:
    """Resolve a dotted path in the context.

    Args:
        path: Dotted path like "user.name" or simple "name"
        context: Context dictionary

    Returns:
        Resolved value, or None if path not found
    """
    parts = path.split(".")
    current: Any = context

    for part in parts:
        if isinstance(current, dict) and part in current:
            current = current[part]
        else:
            return None

    return current


def _to_string(value: Any) -> str:
    """Convert a value to string for template substitution.

    Args:
        value: Any value to convert

    Returns:
        String representation
    """
    if value is None:
        return ""
    return str(value)
