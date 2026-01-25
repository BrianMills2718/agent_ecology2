"""Tests for workflow hooks system (Plan #208).

Tests:
- Hook parsing and validation
- Argument interpolation
- Injection targets
- Error handling (skip/fail)
- Depth limit enforcement
- Subscribed artifacts expansion
"""

import pytest
from unittest.mock import Mock, AsyncMock, MagicMock

from src.agents.hooks import (
    HookDefinition,
    HooksConfig,
    HookExecutor,
    HookTiming,
    HookErrorPolicy,
    HookResult,
    INJECT_PROMPT,
    INJECT_SYSTEM_PROMPT,
    INJECT_NULL,
    expand_subscribed_artifacts,
)


class TestHookDefinition:
    """Tests for HookDefinition dataclass."""

    def test_from_dict_minimal(self):
        """Test creating HookDefinition with minimal config."""
        data = {
            "artifact_id": "my_artifact",
            "method": "search",
        }
        hook = HookDefinition.from_dict(data)

        assert hook.artifact_id == "my_artifact"
        assert hook.method == "search"
        assert hook.args == {}
        assert hook.inject_as is None
        assert hook.on_error == HookErrorPolicy.SKIP
        assert hook.max_retries == 3

    def test_from_dict_full(self):
        """Test creating HookDefinition with full config."""
        data = {
            "artifact_id": "genesis_search",
            "method": "search",
            "args": {"query": "{current_goal}", "limit": 5},
            "inject_as": "search_results",
            "on_error": "fail",
            "max_retries": 5,
        }
        hook = HookDefinition.from_dict(data)

        assert hook.artifact_id == "genesis_search"
        assert hook.method == "search"
        assert hook.args == {"query": "{current_goal}", "limit": 5}
        assert hook.inject_as == "search_results"
        assert hook.on_error == HookErrorPolicy.FAIL
        assert hook.max_retries == 5

    def test_to_dict(self):
        """Test serializing HookDefinition."""
        hook = HookDefinition(
            artifact_id="my_artifact",
            method="run",
            args={"x": 1},
            inject_as="result",
            on_error=HookErrorPolicy.RETRY,
            max_retries=2,
        )
        data = hook.to_dict()

        assert data["artifact_id"] == "my_artifact"
        assert data["method"] == "run"
        assert data["args"] == {"x": 1}
        assert data["inject_as"] == "result"
        assert data["on_error"] == "retry"
        assert data["max_retries"] == 2


class TestHooksConfig:
    """Tests for HooksConfig dataclass."""

    def test_from_dict_empty(self):
        """Test creating HooksConfig from empty/None dict."""
        config = HooksConfig.from_dict(None)
        assert config.is_empty()

        config = HooksConfig.from_dict({})
        assert config.is_empty()

    def test_from_dict_with_hooks(self):
        """Test creating HooksConfig with hooks at each timing."""
        data = {
            "pre_decision": [
                {"artifact_id": "search", "method": "run"}
            ],
            "post_decision": [
                {"artifact_id": "validate", "method": "check"}
            ],
            "post_action": [
                {"artifact_id": "logger", "method": "log"}
            ],
            "on_error": [
                {"artifact_id": "handler", "method": "handle"}
            ],
        }
        config = HooksConfig.from_dict(data)

        assert len(config.pre_decision) == 1
        assert len(config.post_decision) == 1
        assert len(config.post_action) == 1
        assert len(config.on_error) == 1
        assert not config.is_empty()

    def test_merge(self):
        """Test merging two HooksConfigs."""
        config1 = HooksConfig(
            pre_decision=[HookDefinition("a1", "m1")],
            post_action=[HookDefinition("a2", "m2")],
        )
        config2 = HooksConfig(
            pre_decision=[HookDefinition("a3", "m3")],
            on_error=[HookDefinition("a4", "m4")],
        )

        merged = config1.merge(config2)

        assert len(merged.pre_decision) == 2
        assert merged.pre_decision[0].artifact_id == "a1"
        assert merged.pre_decision[1].artifact_id == "a3"
        assert len(merged.post_action) == 1
        assert len(merged.on_error) == 1

    def test_get_hooks(self):
        """Test getting hooks by timing."""
        config = HooksConfig(
            pre_decision=[HookDefinition("a1", "m1")],
            post_decision=[HookDefinition("a2", "m2")],
        )

        assert len(config.get_hooks(HookTiming.PRE_DECISION)) == 1
        assert len(config.get_hooks(HookTiming.POST_DECISION)) == 1
        assert len(config.get_hooks(HookTiming.POST_ACTION)) == 0
        assert len(config.get_hooks(HookTiming.ON_ERROR)) == 0


class TestHookResult:
    """Tests for HookResult dataclass."""

    def test_should_inject_success_with_target(self):
        """Test should_inject for successful result with target."""
        result = HookResult(success=True, result="data", inject_as="key")
        assert result.should_inject

    def test_should_inject_success_null_target(self):
        """Test should_inject for null injection target."""
        result = HookResult(success=True, result="data", inject_as=INJECT_NULL)
        assert not result.should_inject

    def test_should_inject_failure(self):
        """Test should_inject for failed result."""
        result = HookResult(success=False, error="error", inject_as="key")
        assert not result.should_inject

    def test_should_inject_no_target(self):
        """Test should_inject with no injection target."""
        result = HookResult(success=True, result="data", inject_as=None)
        assert not result.should_inject


class TestHookExecutor:
    """Tests for HookExecutor class."""

    def test_interpolate_args_simple(self):
        """Test simple variable interpolation."""
        executor = HookExecutor(
            artifact_store=Mock(),
            invoker=Mock(),
        )
        args = {"query": "{current_goal}", "agent": "{agent_id}"}
        context = {"current_goal": "build oracle", "agent_id": "alice"}

        result = executor.interpolate_args(args, context)

        assert result["query"] == "build oracle"
        assert result["agent"] == "alice"

    def test_interpolate_args_missing_var(self):
        """Test interpolation with missing variable keeps placeholder."""
        executor = HookExecutor(
            artifact_store=Mock(),
            invoker=Mock(),
        )
        args = {"query": "{missing_var}"}
        context = {}

        result = executor.interpolate_args(args, context)

        assert result["query"] == "{missing_var}"

    def test_interpolate_args_nested(self):
        """Test interpolation in nested dicts."""
        executor = HookExecutor(
            artifact_store=Mock(),
            invoker=Mock(),
        )
        args = {"outer": {"inner": "{value}"}}
        context = {"value": "test"}

        result = executor.interpolate_args(args, context)

        assert result["outer"]["inner"] == "test"

    def test_interpolate_args_non_string(self):
        """Test interpolation preserves non-string values."""
        executor = HookExecutor(
            artifact_store=Mock(),
            invoker=Mock(),
        )
        args = {"limit": 5, "enabled": True}
        context = {}

        result = executor.interpolate_args(args, context)

        assert result["limit"] == 5
        assert result["enabled"] is True

    @pytest.mark.asyncio
    async def test_execute_hook_artifact_not_found(self):
        """Test hook execution when artifact doesn't exist."""
        store = Mock()
        store.get.return_value = None

        executor = HookExecutor(
            artifact_store=store,
            invoker=Mock(),
        )
        hook = HookDefinition("missing", "run")

        result = await executor.execute_hook(hook, "agent1", {})

        assert not result.success
        assert "not found" in result.error

    @pytest.mark.asyncio
    async def test_execute_hook_success(self):
        """Test successful hook execution."""
        artifact = Mock()
        store = Mock()
        store.get.return_value = artifact

        mock_executor = Mock()
        mock_executor.invoke_artifact.return_value = {
            "success": True,
            "data": {"result": "data"},
            "message": "OK",
        }

        executor = HookExecutor(
            artifact_store=store,
            invoker=mock_executor,
        )
        hook = HookDefinition("my_artifact", "run", inject_as="output")

        result = await executor.execute_hook(hook, "agent1", {})

        assert result.success
        assert result.result == {"result": "data"}
        assert result.inject_as == "output"

    @pytest.mark.asyncio
    async def test_execute_hook_depth_limit(self):
        """Test depth limit prevents infinite loops."""
        executor = HookExecutor(
            artifact_store=Mock(),
            invoker=Mock(),
            max_depth=2,
        )
        # Simulate nested calls
        executor._current_depth = 2

        hook = HookDefinition("artifact", "run")
        result = await executor.execute_hook(hook, "agent1", {})

        assert not result.success
        assert "depth limit" in result.error.lower()

    @pytest.mark.asyncio
    async def test_execute_hooks_skip_on_error(self):
        """Test hooks with skip policy continue on error."""
        store = Mock()
        store.get.return_value = None  # Will cause "not found" error

        executor = HookExecutor(
            artifact_store=store,
            invoker=Mock(),
        )
        hooks = [
            HookDefinition("missing1", "run", on_error=HookErrorPolicy.SKIP),
            HookDefinition("missing2", "run", on_error=HookErrorPolicy.SKIP),
        ]

        context, should_continue = await executor.execute_hooks(
            hooks, HookTiming.PRE_DECISION, "agent1", {}
        )

        # Should continue despite errors
        assert should_continue

    @pytest.mark.asyncio
    async def test_execute_hooks_fail_on_error(self):
        """Test hooks with fail policy abort on error."""
        store = Mock()
        store.get.return_value = None

        executor = HookExecutor(
            artifact_store=store,
            invoker=Mock(),
        )
        hooks = [
            HookDefinition("missing", "run", on_error=HookErrorPolicy.FAIL),
        ]

        context, should_continue = await executor.execute_hooks(
            hooks, HookTiming.PRE_DECISION, "agent1", {}
        )

        # Should not continue due to fail policy
        assert not should_continue

    @pytest.mark.asyncio
    async def test_execute_hooks_injection(self):
        """Test hook results are injected into context."""
        artifact = Mock()
        store = Mock()
        store.get.return_value = artifact

        mock_executor = Mock()
        mock_executor.invoke_artifact.return_value = {
            "success": True,
            "data": "injected_value",
            "message": "OK",
        }

        executor = HookExecutor(
            artifact_store=store,
            invoker=mock_executor,
        )
        hooks = [
            HookDefinition("artifact", "run", inject_as="my_key"),
        ]

        context, _ = await executor.execute_hooks(
            hooks, HookTiming.PRE_DECISION, "agent1", {}
        )

        assert context["my_key"] == "injected_value"


class TestExpandSubscribedArtifacts:
    """Tests for subscribed artifacts to hooks expansion."""

    def test_expand_empty(self):
        """Test expanding empty list."""
        config = expand_subscribed_artifacts([])
        assert config.is_empty()

    def test_expand_single(self):
        """Test expanding single subscription."""
        config = expand_subscribed_artifacts(["my_handbook"])

        assert len(config.pre_decision) == 1
        hook = config.pre_decision[0]
        assert hook.artifact_id == "my_handbook"
        assert hook.method == "read_content"
        assert hook.inject_as == "subscribed_my_handbook"
        assert hook.on_error == HookErrorPolicy.SKIP

    def test_expand_multiple(self):
        """Test expanding multiple subscriptions."""
        config = expand_subscribed_artifacts(["handbook", "sop", "guide"])

        assert len(config.pre_decision) == 3
        assert config.pre_decision[0].artifact_id == "handbook"
        assert config.pre_decision[1].artifact_id == "sop"
        assert config.pre_decision[2].artifact_id == "guide"
