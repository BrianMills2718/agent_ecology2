"""Unit tests for template injection system.

Tests the template rendering engine for Phase 2 context injection.
Maps to acceptance criteria in acceptance_gates/agent_workflow.yaml (AC-8).

Run with: pytest tests/unit/test_template_injection.py -v
"""

from __future__ import annotations

import pytest


@pytest.mark.feature("agent_workflow")
class TestSimpleVariableReplacement:
    """Test basic {{variable}} replacement."""

    def test_simple_variable_replacement(self) -> None:
        """{{name}} is replaced with value from context."""
        from src.agents.template import render_template

        template = "Hello, {{name}}!"
        context = {"name": "Alice"}
        result = render_template(template, context)
        assert result == "Hello, Alice!"

    def test_multiple_variables(self) -> None:
        """Multiple variables in same template."""
        from src.agents.template import render_template

        template = "{{greeting}}, {{name}}! You have {{count}} messages."
        context = {"greeting": "Hi", "name": "Bob", "count": 5}
        result = render_template(template, context)
        assert result == "Hi, Bob! You have 5 messages."

    def test_variable_with_spaces(self) -> None:
        """Spaces around variable name are trimmed."""
        from src.agents.template import render_template

        template = "Hello, {{ name }}!"
        context = {"name": "Charlie"}
        result = render_template(template, context)
        assert result == "Hello, Charlie!"


@pytest.mark.feature("agent_workflow")
class TestNestedPathReplacement:
    """Test {{nested.path}} replacement."""

    def test_nested_path_replacement(self) -> None:
        """{{user.name}} replaced with nested value."""
        from src.agents.template import render_template

        template = "User: {{user.name}}, Age: {{user.age}}"
        context = {"user": {"name": "Dana", "age": 30}}
        result = render_template(template, context)
        assert result == "User: Dana, Age: 30"

    def test_deeply_nested_path(self) -> None:
        """{{a.b.c.d}} works for deep nesting."""
        from src.agents.template import render_template

        template = "Value: {{a.b.c.d}}"
        context = {"a": {"b": {"c": {"d": "deep"}}}}
        result = render_template(template, context)
        assert result == "Value: deep"

    def test_mixed_simple_and_nested(self) -> None:
        """Mix of simple and nested variables."""
        from src.agents.template import render_template

        template = "{{simple}} and {{nested.value}}"
        context = {"simple": "hello", "nested": {"value": "world"}}
        result = render_template(template, context)
        assert result == "hello and world"


@pytest.mark.feature("agent_workflow")
class TestMissingVariables:
    """Test handling of missing variables."""

    def test_missing_variable_becomes_empty(self) -> None:
        """Missing variable becomes empty string."""
        from src.agents.template import render_template

        template = "Hello, {{name}}!"
        context = {}  # name not provided
        result = render_template(template, context)
        assert result == "Hello, !"

    def test_missing_nested_path_becomes_empty(self) -> None:
        """Missing nested path becomes empty string."""
        from src.agents.template import render_template

        template = "Value: {{user.name}}"
        context = {"user": {}}  # name not in user
        result = render_template(template, context)
        assert result == "Value: "

    def test_missing_intermediate_path_becomes_empty(self) -> None:
        """Missing intermediate in path becomes empty string."""
        from src.agents.template import render_template

        template = "Value: {{a.b.c}}"
        context = {"a": {}}  # b not in a
        result = render_template(template, context)
        assert result == "Value: "


@pytest.mark.feature("agent_workflow")
class TestSafetyAndSecurity:
    """Test that templates are safe and don't execute code."""

    def test_no_code_execution(self) -> None:
        """Template syntax doesn't execute Python code."""
        from src.agents.template import render_template

        # Attempt to inject Python code - pattern won't match due to special chars
        template = "Result: {{__import__('os').system('echo hacked')}}"
        context = {}
        result = render_template(template, context)
        # Should NOT execute - invalid pattern stays as literal text
        # The template contains 'hacked' as literal text, not from execution
        assert result == template  # Template unchanged (no valid variables)

        # Try a simpler injection attempt
        template2 = "Result: {{cmd}}"
        context2 = {"cmd": "__import__('os').system('ls')"}
        result2 = render_template(template2, context2)
        # Value is just a string, not executed
        assert result2 == "Result: __import__('os').system('ls')"

    def test_no_eval_execution(self) -> None:
        """Can't use eval-like syntax."""
        from src.agents.template import render_template

        template = "{{eval('1+1')}}"
        context = {"eval": lambda x: "HACKED"}
        result = render_template(template, context)
        # Should not execute the lambda
        assert "HACKED" not in result

    def test_special_chars_in_value(self) -> None:
        """Values with special chars rendered safely."""
        from src.agents.template import render_template

        template = "Message: {{msg}}"
        context = {"msg": "<script>alert('xss')</script>"}
        result = render_template(template, context)
        # Value should be in output (not escaped for now - templates aren't HTML)
        assert "<script>" in result  # We don't escape - this is a template, not HTML

    def test_braces_in_value(self) -> None:
        """Values containing {{ }} don't cause recursion."""
        from src.agents.template import render_template

        template = "Code: {{code}}"
        context = {"code": "{{nested}}"}
        result = render_template(template, context)
        # Should include the literal braces from the value, not re-process
        assert result == "Code: {{nested}}"


@pytest.mark.feature("agent_workflow")
class TestEdgeCases:
    """Test edge cases and special scenarios."""

    def test_empty_template(self) -> None:
        """Empty template returns empty string."""
        from src.agents.template import render_template

        result = render_template("", {"name": "test"})
        assert result == ""

    def test_no_variables(self) -> None:
        """Template without variables returns as-is."""
        from src.agents.template import render_template

        template = "Hello, world!"
        result = render_template(template, {})
        assert result == "Hello, world!"

    def test_none_value(self) -> None:
        """None value becomes empty string."""
        from src.agents.template import render_template

        template = "Value: {{x}}"
        context = {"x": None}
        result = render_template(template, context)
        assert result == "Value: "

    def test_boolean_value(self) -> None:
        """Boolean values converted to string."""
        from src.agents.template import render_template

        template = "Active: {{active}}"
        context = {"active": True}
        result = render_template(template, context)
        assert result == "Active: True"

    def test_list_value(self) -> None:
        """List values converted to string representation."""
        from src.agents.template import render_template

        template = "Items: {{items}}"
        context = {"items": [1, 2, 3]}
        result = render_template(template, context)
        assert result == "Items: [1, 2, 3]"

    def test_multiline_template(self) -> None:
        """Multiline templates work correctly."""
        from src.agents.template import render_template

        template = """Line 1: {{a}}
Line 2: {{b}}
Line 3: {{c}}"""
        context = {"a": "A", "b": "B", "c": "C"}
        result = render_template(template, context)
        assert result == """Line 1: A
Line 2: B
Line 3: C"""
