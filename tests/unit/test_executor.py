"""
Tests for src/world/executor.py

Phase 0 of Plan #53: Verify executor uses ResourceMeasurer and returns cpu_seconds.
Plan #319: Verify _syscall_llm emits thinking events.
Plan #320: Verify artifact_read and kernel_query events are emitted.
"""

from __future__ import annotations

from typing import Any
from unittest.mock import patch

import pytest

from src.world.executor import SafeExecutor, create_syscall_llm
from src.world.actions import WriteArtifactIntent, ReadArtifactIntent, QueryKernelIntent
from src.world.world import World, ConfigDict


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

    def test_action_read_artifact_without_context(self, executor: SafeExecutor) -> None:
        """Action.read_artifact should return error when artifact_store not available."""
        code = """
def run():
    from actions import Action
    action = Action()
    result = action.read_artifact("some_artifact")
    return result
"""
        result = executor.execute(code)

        assert result["success"] is True
        assert result["result"]["success"] is False
        assert "not available" in result["result"]["error"]


@pytest.mark.plans([319])
class TestSyscallLLMThinkingEvents:
    """Plan #319: Verify _syscall_llm emits thinking/thinking_failed events."""

    @pytest.fixture
    def world(self, tmp_path: Any) -> World:
        """Create a World with a logger for event capture."""
        log_file = tmp_path / "test_thinking.jsonl"
        config: ConfigDict = {
            "world": {},
            "costs": {"per_1k_input_tokens": 1, "per_1k_output_tokens": 3},
            "logging": {"output_file": str(log_file)},
            "principals": [{"id": "test_agent", "starting_scrip": 100}],
            "rights": {"default_llm_tokens_quota": 50, "default_disk_quota": 10000},
            "rate_limiting": {
                "enabled": True,
                "window_seconds": 60.0,
                "resources": {"llm_tokens": {"max_per_window": 1000}},
            },
            "discourse_analyst": {"enabled": False},
            "discourse_analyst_2": {"enabled": False},
            "discourse_analyst_3": {"enabled": False},
            "alpha_prime": {"enabled": False},
        }
        return World(config)

    def test_thinking_event_on_success(self, world: World) -> None:
        """Successful LLM call should emit a 'thinking' event with expected fields."""
        # Give agent LLM budget
        world.ledger.set_resource("test_agent", "llm_budget", 1.0)

        # mock-ok: external LLM API — avoid real API calls in unit tests
        from src.world.llm_client import LLMCallResult

        mock_result = LLMCallResult(
            content='{"action": "noop", "reasoning": "thinking hard"}',
            usage={"prompt_tokens": 100, "completion_tokens": 50, "total_tokens": 150},
            cost=0.001,
            model="test-model",
        )

        syscall = create_syscall_llm(world, "test_agent")

        with patch("src.world.llm_client.call_llm", return_value=mock_result):
            result = syscall("test-model", [{"role": "user", "content": "hello"}])

        assert result["success"] is True

        events = world.logger.read_recent(100)
        thinking_events = [e for e in events if e["event_type"] == "thinking"]
        assert len(thinking_events) == 1

        evt = thinking_events[0]
        assert evt["principal_id"] == "test_agent"
        assert evt["model"] == "test-model"
        assert evt["input_tokens"] == 100
        assert evt["output_tokens"] == 50
        assert evt["api_cost"] == 0.001
        assert "llm_budget_after" in evt
        assert evt["reasoning"] == '{"action": "noop", "reasoning": "thinking hard"}'

    def test_thinking_failed_on_budget_exhaustion(self, world: World) -> None:
        """Budget exhaustion should emit a 'thinking_failed' event."""
        # Set zero LLM budget
        world.ledger.set_resource("test_agent", "llm_budget", 0.0)

        syscall = create_syscall_llm(world, "test_agent")
        result = syscall("test-model", [{"role": "user", "content": "hello"}])

        assert result["success"] is False
        assert "Budget exhausted" in result["error"]

        events = world.logger.read_recent(100)
        failed_events = [e for e in events if e["event_type"] == "thinking_failed"]
        assert len(failed_events) == 1

        evt = failed_events[0]
        assert evt["principal_id"] == "test_agent"
        assert evt["model"] == "test-model"
        assert evt["api_cost"] == 0.0
        assert "Budget exhausted" in evt["reason"]

    def test_thinking_failed_on_llm_error(self, world: World) -> None:
        """LLM exception should emit a 'thinking_failed' event."""
        world.ledger.set_resource("test_agent", "llm_budget", 1.0)

        syscall = create_syscall_llm(world, "test_agent")

        # mock-ok: external LLM API — simulate LLM failure
        with patch(
            "src.world.llm_client.call_llm",
            side_effect=RuntimeError("API timeout"),
        ):
            result = syscall("test-model", [{"role": "user", "content": "hello"}])

        assert result["success"] is False
        assert "API timeout" in result["error"]

        events = world.logger.read_recent(100)
        failed_events = [e for e in events if e["event_type"] == "thinking_failed"]
        assert len(failed_events) == 1

        evt = failed_events[0]
        assert evt["principal_id"] == "test_agent"
        assert evt["model"] == "test-model"
        assert evt["api_cost"] == 0.0
        assert "API timeout" in evt["reason"]

    def test_reasoning_capped_at_2000_chars(self, world: World) -> None:
        """Reasoning field in thinking event should be capped at 2000 chars."""
        world.ledger.set_resource("test_agent", "llm_budget", 1.0)

        from src.world.llm_client import LLMCallResult

        long_content = "x" * 5000
        mock_result = LLMCallResult(
            content=long_content,
            usage={"prompt_tokens": 10, "completion_tokens": 10, "total_tokens": 20},
            cost=0.0001,
            model="test-model",
        )

        syscall = create_syscall_llm(world, "test_agent")

        # mock-ok: external LLM API
        with patch("src.world.llm_client.call_llm", return_value=mock_result):
            result = syscall("test-model", [{"role": "user", "content": "hello"}])

        assert result["success"] is True

        events = world.logger.read_recent(100)
        thinking_events = [e for e in events if e["event_type"] == "thinking"]
        assert len(thinking_events) == 1
        assert len(thinking_events[0]["reasoning"]) == 2000


@pytest.mark.plans([320])
class TestReadAndQueryEvents:
    """Plan #320: Verify artifact_read and kernel_query events are emitted."""

    @pytest.fixture
    def world(self, tmp_path: Any) -> World:
        """Create a World with agents for read/query testing."""
        log_file = tmp_path / "test_read_query.jsonl"
        config: ConfigDict = {
            "world": {},
            "costs": {"per_1k_input_tokens": 1, "per_1k_output_tokens": 3},
            "logging": {"output_file": str(log_file)},
            "principals": [
                {"id": "alice", "starting_scrip": 1000},
                {"id": "bob", "starting_scrip": 500},
            ],
            "rights": {"default_llm_tokens_quota": 50, "default_disk_quota": 10000},
            "rate_limiting": {
                "enabled": True,
                "window_seconds": 60.0,
                "resources": {"llm_tokens": {"max_per_window": 1000}},
            },
            "discourse_analyst": {"enabled": False},
            "discourse_analyst_2": {"enabled": False},
            "discourse_analyst_3": {"enabled": False},
            "discourse_v2": {"enabled": False},
            "discourse_v2_2": {"enabled": False},
            "discourse_v2_3": {"enabled": False},
            "alpha_prime": {"enabled": False},
        }
        w = World(config)
        w.increment_event_counter()
        return w

    def test_artifact_read_event_on_success(self, world: World) -> None:
        """Successful read should emit an 'artifact_read' event."""
        # Create an artifact first
        write_intent = WriteArtifactIntent(
            principal_id="alice",
            artifact_id="test_doc",
            artifact_type="json",
            content='{"data": "hello"}',
            access_contract_id="kernel_contract_freeware",
        )
        write_result = world.execute_action(write_intent)
        assert write_result.success, f"Setup write failed: {write_result.message}"

        # Read it
        read_intent = ReadArtifactIntent(
            principal_id="alice",
            artifact_id="test_doc",
        )
        read_result = world.execute_action(read_intent)
        assert read_result.success, f"Read failed: {read_result.message}"

        # Check for artifact_read event
        events = world.logger.read_recent(100)
        read_events = [e for e in events if e["event_type"] == "artifact_read"]
        assert len(read_events) == 1

        evt = read_events[0]
        assert evt["artifact_id"] == "test_doc"
        assert evt["principal_id"] == "alice"
        assert evt["artifact_type"] == "json"
        assert evt["read_price_paid"] == 0
        assert evt["content_size"] == len('{"data": "hello"}')

    def test_kernel_query_includes_params(self, world: World) -> None:
        """kernel_query events should include query params."""
        query_intent = QueryKernelIntent(
            principal_id="alice",
            query_type="artifacts",
            params={"name_pattern": "test_*"},
        )
        world.execute_action(query_intent)

        events = world.logger.read_recent(100)
        query_events = [e for e in events if e["event_type"] == "kernel_query"]
        assert len(query_events) >= 1

        evt = query_events[-1]
        assert evt["principal_id"] == "alice"
        assert evt["query_type"] == "artifacts"
        assert evt["params"] == {"name_pattern": "test_*"}

    def test_no_artifact_read_event_on_not_found(self, world: World) -> None:
        """Failed read (not found) should NOT emit artifact_read event."""
        read_intent = ReadArtifactIntent(
            principal_id="alice",
            artifact_id="nonexistent",
        )
        read_result = world.execute_action(read_intent)
        assert not read_result.success

        events = world.logger.read_recent(100)
        read_events = [e for e in events if e["event_type"] == "artifact_read"]
        assert len(read_events) == 0
