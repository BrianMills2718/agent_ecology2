"""
Tests for src/world/executor.py

Phase 0 of Plan #53: Verify executor uses ResourceMeasurer and returns cpu_seconds.
"""

import pytest

from src.world.executor import SafeExecutor


class TestSafeExecutorResourceMeasurement:
    """Tests for Phase 0: SafeExecutor should use ResourceMeasurer and return cpu_seconds."""

    @pytest.fixture
    def executor(self) -> SafeExecutor:
        """Create an executor with default settings."""
        return SafeExecutor(timeout=5, use_contracts=False)

    def test_executor_returns_cpu_seconds_not_llm_tokens(self, executor: SafeExecutor) -> None:
        """
        SafeExecutor should return cpu_seconds in resources_consumed, not llm_tokens.

        The _time_to_tokens() hack conflates wall-clock time with LLM tokens.
        After Phase 0, executor should return cpu_seconds from ResourceMeasurer.
        """
        result = executor.execute("def run(): return 42")

        assert result["success"] is True
        assert "resources_consumed" in result

        resources = result["resources_consumed"]

        # Phase 0 requirement: should have cpu_seconds, not llm_tokens
        assert "cpu_seconds" in resources, (
            "SafeExecutor should return cpu_seconds, not llm_tokens. "
            "The _time_to_tokens() hack must be replaced with ResourceMeasurer."
        )
        assert "llm_tokens" not in resources, (
            "SafeExecutor should NOT return llm_tokens for execution time. "
            "LLM tokens are for LLM API calls, not code execution."
        )

        # cpu_seconds should be a non-negative float
        assert isinstance(resources["cpu_seconds"], (int, float))
        assert resources["cpu_seconds"] >= 0

    def test_executor_uses_resource_measurer(self, executor: SafeExecutor) -> None:
        """
        SafeExecutor should use ResourceMeasurer for accurate CPU measurement.

        ResourceMeasurer uses time.process_time() which measures actual CPU time,
        not wall-clock time. This is more accurate for resource accounting.
        """
        # Execute code that does some CPU work
        code = """
def run():
    total = sum(i * i for i in range(10000))
    return total
"""
        result = executor.execute(code)

        assert result["success"] is True
        resources = result["resources_consumed"]

        # Should have cpu_seconds from ResourceMeasurer
        assert "cpu_seconds" in resources
        # CPU time should be positive for non-trivial work
        # (though may be very small on fast machines)
        assert resources["cpu_seconds"] >= 0

    def test_executor_returns_cpu_seconds_on_timeout(self) -> None:
        """Even on timeout, executor should return cpu_seconds not llm_tokens."""
        # Create executor with very short timeout (1ms)
        short_executor = SafeExecutor(timeout=1, use_contracts=False)

        # Code that does a lot of work (will likely timeout)
        code = """
def run():
    total = 0
    for i in range(10000000):
        total += i * i
    return total
"""
        result = short_executor.execute(code)

        # Regardless of success/timeout, resources_consumed should have cpu_seconds
        assert "resources_consumed" in result
        resources = result["resources_consumed"]
        assert "cpu_seconds" in resources
        assert "llm_tokens" not in resources

    def test_executor_returns_cpu_seconds_on_error(self, executor: SafeExecutor) -> None:
        """Even on error, executor should return cpu_seconds not llm_tokens."""
        code = """
def run():
    raise ValueError("intentional error")
"""
        result = executor.execute(code)

        assert result["success"] is False
        assert "resources_consumed" in result
        resources = result["resources_consumed"]
        assert "cpu_seconds" in resources
        assert "llm_tokens" not in resources


class TestJSONArgParsing:
    """Tests for Plan #112: Auto-parse JSON string arguments.

    LLMs often generate JSON strings for dict arguments. The executor
    should auto-convert them to proper Python types before passing to run().
    """

    @pytest.fixture
    def executor(self) -> SafeExecutor:
        """Create an executor with default settings."""
        return SafeExecutor(timeout=5, use_contracts=False)

    def test_json_string_arg_parsed_to_dict(self, executor: SafeExecutor) -> None:
        """JSON dict string '{"a": 1}' should be parsed to {"a": 1}."""
        code = """
def run(data):
    # If data is a string, this would fail with AttributeError
    return data.get("a")
"""
        result = executor.execute(code, args=['{"a": 1}'])

        assert result["success"] is True, f"Failed: {result.get('error')}"
        assert result["result"] == 1

    def test_json_string_list_parsed(self, executor: SafeExecutor) -> None:
        """JSON list string '[1, 2, 3]' should be parsed to [1, 2, 3]."""
        code = """
def run(items):
    # If items is a string, len() would return character count, not list length
    return len(items)
"""
        result = executor.execute(code, args=['[1, 2, 3]'])

        assert result["success"] is True, f"Failed: {result.get('error')}"
        assert result["result"] == 3

    def test_plain_string_unchanged(self, executor: SafeExecutor) -> None:
        """Plain string 'hello' should remain 'hello', not parsed."""
        code = """
def run(message):
    return message
"""
        result = executor.execute(code, args=['hello'])

        assert result["success"] is True, f"Failed: {result.get('error')}"
        assert result["result"] == "hello"

    def test_mixed_args_parsed(self, executor: SafeExecutor) -> None:
        """Mixed args: plain string + JSON string should be handled correctly."""
        code = """
def run(action, data):
    # action should be 'register' (string)
    # data should be {"id": "x"} (dict)
    return f"{action}:{data.get('id')}"
"""
        result = executor.execute(code, args=['register', '{"id": "x"}'])

        assert result["success"] is True, f"Failed: {result.get('error')}"
        assert result["result"] == "register:x"

    def test_nested_json_parsed(self, executor: SafeExecutor) -> None:
        """Nested JSON structures should be fully parsed."""
        code = """
def run(data):
    return data["outer"]["inner"]
"""
        result = executor.execute(code, args=['{"outer": {"inner": "value"}}'])

        assert result["success"] is True, f"Failed: {result.get('error')}"
        assert result["result"] == "value"

    def test_json_with_array_parsed(self, executor: SafeExecutor) -> None:
        """JSON with arrays should be fully parsed."""
        code = """
def run(data):
    return data["items"][1]
"""
        result = executor.execute(code, args=['{"items": [10, 20, 30]}'])

        assert result["success"] is True, f"Failed: {result.get('error')}"
        assert result["result"] == 20

    def test_non_string_args_unchanged(self, executor: SafeExecutor) -> None:
        """Non-string args (int, dict, list) should pass through unchanged."""
        code = """
def run(num, data, items):
    return num + data["a"] + items[0]
"""
        result = executor.execute(code, args=[10, {"a": 5}, [3]])

        assert result["success"] is True, f"Failed: {result.get('error')}"
        assert result["result"] == 18

    def test_json_number_string_unchanged(self, executor: SafeExecutor) -> None:
        """'123' should stay string, not become int. Only dict/list JSON is converted."""
        code = """
def run(data):
    return {"type": type(data).__name__, "value": data}
"""
        result = executor.execute(code, args=['123'])

        assert result["success"] is True, f"Failed: {result.get('error')}"
        assert result["result"]["type"] == "str"
        assert result["result"]["value"] == "123"

    def test_json_boolean_string_unchanged(self, executor: SafeExecutor) -> None:
        """'true' and 'false' should stay as strings, not become Python bools."""
        code = """
def run(data):
    return {"type": type(data).__name__, "value": data}
"""
        result = executor.execute(code, args=['true'])

        assert result["success"] is True, f"Failed: {result.get('error')}"
        assert result["result"]["type"] == "str"
        assert result["result"]["value"] == "true"


@pytest.mark.plans([140])
class TestActionsModule:
    """Tests for Plan #140: Support 'from actions import Action' pattern.

    Agents naturally write code like:
        from actions import Action
        action = Action()
        result = action.invoke_artifact("target")

    The executor should inject an 'actions' module with an Action class
    that wraps the bare functions.
    """

    @pytest.fixture
    def executor(self) -> SafeExecutor:
        """Create an executor with default settings."""
        return SafeExecutor(timeout=5, use_contracts=False)

    def test_actions_module_available(self, executor: SafeExecutor) -> None:
        """'from actions import Action' should work without error."""
        code = """
def run():
    from actions import Action
    action = Action()
    return type(action).__name__
"""
        result = executor.execute(code)

        assert result["success"] is True, f"Failed: {result.get('error')}"
        assert result["result"] == "Action"

    def test_action_class_available_directly(self, executor: SafeExecutor) -> None:
        """Action class should also be available directly without import."""
        code = """
def run():
    action = Action()
    return type(action).__name__
"""
        result = executor.execute(code)

        assert result["success"] is True, f"Failed: {result.get('error')}"
        assert result["result"] == "Action"

    def test_action_invoke_artifact_without_context(self, executor: SafeExecutor) -> None:
        """Action.invoke_artifact should return error when invoke not available."""
        code = """
def run():
    from actions import Action
    action = Action()
    result = action.invoke_artifact("nonexistent")
    return result
"""
        # Without full context (no artifact_store), invoke is not available
        result = executor.execute(code)

        assert result["success"] is True
        # The invoke call should return an error dict since invoke not available
        assert result["result"]["success"] is False
        assert "invoke not available" in result["result"]["error"]

    def test_action_pay_without_context(self, executor: SafeExecutor) -> None:
        """Action.pay should return error when pay not available."""
        code = """
def run():
    from actions import Action
    action = Action()
    result = action.pay("someone", 10)
    return result
"""
        result = executor.execute(code)

        assert result["success"] is True
        assert result["result"]["success"] is False
        assert "pay not available" in result["result"]["error"]

    def test_action_get_balance_without_context(self, executor: SafeExecutor) -> None:
        """Action.get_balance should return 0 when get_balance not available."""
        code = """
def run():
    from actions import Action
    action = Action()
    return action.get_balance()
"""
        result = executor.execute(code)

        assert result["success"] is True
        assert result["result"] == 0

    def test_action_methods_match_original_agent_code(self, executor: SafeExecutor) -> None:
        """The Action class API should match what agents naturally wrote.

        Agents wrote code like:
            from actions import Action
            action = Action()
            result = action.invoke_artifact(artifact_id='target', method='run', args=[])
        """
        code = """
def run():
    from actions import Action
    action = Action()
    # Check that the methods exist with expected signatures
    import inspect
    sig = inspect.signature(action.invoke_artifact)
    params = list(sig.parameters.keys())
    return params
"""
        result = executor.execute(code)

        assert result["success"] is True, f"Failed: {result.get('error')}"
        # Should have artifact_id, method, args parameters
        assert "artifact_id" in result["result"]
        assert "method" in result["result"]
        assert "args" in result["result"]
