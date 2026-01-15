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
