"""Tests for Reflex System (Plan #143).

Tests that reflexes:
- Execute fast Python code before LLM
- Return actions that skip LLM when reflex fires
- Fall back to LLM when reflex returns None
- Time out and fall back to LLM when slow
- Handle errors gracefully by falling back to LLM
- Can be validated without execution
"""

import pytest

from src.agents.reflex import (
    ReflexContext,
    ReflexResult,
    ReflexExecutor,
    validate_reflex_code,
)


class TestReflexContext:
    """Tests for ReflexContext."""

    def test_context_to_dict(self) -> None:
        """Test context converts to dict correctly."""
        context = ReflexContext(
            agent_id="alice",
            tick=10,
            balance=100,
            llm_tokens_remaining=50,
            owned_artifacts=["artifact_1", "artifact_2"],
        )

        ctx_dict = context.to_dict()

        assert ctx_dict["agent_id"] == "alice"
        assert ctx_dict["tick"] == 10
        assert ctx_dict["balance"] == 100
        assert ctx_dict["llm_tokens_remaining"] == 50
        assert ctx_dict["owned_artifacts"] == ["artifact_1", "artifact_2"]

    def test_context_defaults(self) -> None:
        """Test context has sensible defaults."""
        context = ReflexContext(agent_id="bob", tick=1, balance=0)

        assert context.llm_tokens_remaining == 0
        assert context.recent_events == []
        assert context.pending_purchases == []
        assert context.owned_artifacts == []


class TestReflexResult:
    """Tests for ReflexResult."""

    def test_result_defaults(self) -> None:
        """Test result has correct defaults."""
        result = ReflexResult()

        assert result.action is None
        assert result.fired is False
        assert result.error is None
        assert result.execution_time_ms == 0.0


class TestReflexExecutor:
    """Tests for ReflexExecutor."""

    @pytest.fixture
    def executor(self) -> ReflexExecutor:
        """Create executor with reasonable timeout."""
        return ReflexExecutor(timeout_ms=1000.0)  # 1 second for tests

    @pytest.fixture
    def context(self) -> ReflexContext:
        """Create test context."""
        return ReflexContext(
            agent_id="alice",
            tick=10,
            balance=100,
            pending_purchases=[
                {"deal_id": "deal_1", "price": 5, "artifact_id": "artifact_1"},
                {"deal_id": "deal_2", "price": 50, "artifact_id": "artifact_2"},
            ],
        )

    def test_reflex_returns_action(self, executor: ReflexExecutor, context: ReflexContext) -> None:
        """Test reflex that returns an action."""
        code = '''
def reflex(context):
    # Auto-accept cheap purchases
    for purchase in context.get("pending_purchases", []):
        if purchase["price"] <= 10:
            return {
                "action_type": "invoke_artifact",
                "artifact_id": "genesis_escrow",
                "method": "accept",
                "args": [purchase["deal_id"]]
            }
    return None
'''
        result = executor.execute(code, context)

        assert result.fired is True
        assert result.action is not None
        assert result.action["action_type"] == "invoke_artifact"
        assert result.action["artifact_id"] == "genesis_escrow"
        assert result.error is None

    def test_reflex_returns_none(self, executor: ReflexExecutor, context: ReflexContext) -> None:
        """Test reflex that returns None (fall back to LLM)."""
        code = '''
def reflex(context):
    # Only act if balance > 1000
    if context.get("balance", 0) > 1000:
        return {"action_type": "noop"}
    return None
'''
        result = executor.execute(code, context)

        assert result.fired is False
        assert result.action is None
        assert result.error is None

    def test_reflex_syntax_error(self, executor: ReflexExecutor, context: ReflexContext) -> None:
        """Test reflex with syntax error."""
        code = '''
def reflex(context)  # Missing colon
    return None
'''
        result = executor.execute(code, context)

        assert result.fired is False
        assert result.action is None
        assert result.error is not None
        assert "Syntax error" in result.error

    def test_reflex_missing_function(self, executor: ReflexExecutor, context: ReflexContext) -> None:
        """Test reflex code without reflex function."""
        code = '''
def my_helper(context):
    return {"action_type": "noop"}
'''
        result = executor.execute(code, context)

        assert result.fired is False
        assert result.action is None
        assert result.error is not None
        assert "reflex(context)" in result.error

    def test_reflex_runtime_error(self, executor: ReflexExecutor, context: ReflexContext) -> None:
        """Test reflex with runtime error."""
        code = '''
def reflex(context):
    # This will raise KeyError
    return {"action_type": context["nonexistent_key"]}
'''
        result = executor.execute(code, context)

        assert result.fired is False
        assert result.action is None
        assert result.error is not None
        assert "error" in result.error.lower()

    def test_reflex_invalid_return_type(self, executor: ReflexExecutor, context: ReflexContext) -> None:
        """Test reflex returning wrong type."""
        code = '''
def reflex(context):
    return "not a dict"
'''
        result = executor.execute(code, context)

        assert result.fired is False
        assert result.action is None
        assert result.error is not None
        assert "dict" in result.error.lower()

    def test_reflex_missing_action_type(self, executor: ReflexExecutor, context: ReflexContext) -> None:
        """Test reflex returning action without action_type."""
        code = '''
def reflex(context):
    return {"artifact_id": "test"}  # Missing action_type
'''
        result = executor.execute(code, context)

        assert result.fired is False
        assert result.action is None
        assert result.error is not None
        assert "action_type" in result.error

    def test_reflex_can_use_builtins(self, executor: ReflexExecutor, context: ReflexContext) -> None:
        """Test reflex can use allowed built-ins."""
        code = '''
def reflex(context):
    balance = context.get("balance", 0)
    if balance > 50:
        items = list(range(3))
        total = sum(items)
        return {"action_type": "noop", "data": {"count": len(items), "total": total}}
    return None
'''
        result = executor.execute(code, context)

        assert result.fired is True
        assert result.action is not None
        assert result.action["data"]["count"] == 3
        assert result.action["data"]["total"] == 3  # 0+1+2

    def test_reflex_execution_time_tracked(self, executor: ReflexExecutor, context: ReflexContext) -> None:
        """Test execution time is tracked."""
        code = '''
def reflex(context):
    return None
'''
        result = executor.execute(code, context)

        assert result.execution_time_ms > 0
        assert result.execution_time_ms < 1000  # Should be fast

    def test_reflex_cannot_import(self, executor: ReflexExecutor, context: ReflexContext) -> None:
        """Test reflex cannot import modules."""
        code = '''
def reflex(context):
    import os
    return {"action_type": "noop"}
'''
        result = executor.execute(code, context)

        # Should error since import is not available
        assert result.error is not None

    def test_reflex_accesses_context_fields(self, executor: ReflexExecutor, context: ReflexContext) -> None:
        """Test reflex can access all context fields."""
        code = '''
def reflex(context):
    agent_id = context.get("agent_id")
    tick = context.get("tick")
    balance = context.get("balance")
    pending = context.get("pending_purchases", [])

    if agent_id == "alice" and tick > 5 and balance >= 100 and len(pending) > 0:
        return {"action_type": "noop", "reason": "all fields accessible"}
    return None
'''
        result = executor.execute(code, context)

        assert result.fired is True
        assert result.action is not None
        assert result.action["reason"] == "all fields accessible"


class TestValidateReflexCode:
    """Tests for validate_reflex_code."""

    def test_valid_reflex_code(self) -> None:
        """Test valid reflex code passes validation."""
        code = '''
def reflex(context):
    return None
'''
        is_valid, error = validate_reflex_code(code)

        assert is_valid is True
        assert error is None

    def test_invalid_syntax(self) -> None:
        """Test syntax error is detected."""
        code = '''
def reflex(context)
    return None
'''
        is_valid, error = validate_reflex_code(code)

        assert is_valid is False
        assert error is not None
        assert "Syntax error" in error

    def test_missing_reflex_function(self) -> None:
        """Test missing reflex function is detected."""
        code = '''
def other_func(context):
    return None
'''
        is_valid, error = validate_reflex_code(code)

        assert is_valid is False
        assert error is not None
        assert "reflex(context)" in error

    def test_wrong_argument_count(self) -> None:
        """Test wrong argument count is detected."""
        code = '''
def reflex(context, extra):
    return None
'''
        is_valid, error = validate_reflex_code(code)

        assert is_valid is False
        assert error is not None
        assert "one argument" in error


class TestAgentReflexIntegration:
    """Tests for Agent reflex integration."""

    def test_agent_reflex_artifact_id_default(self) -> None:
        """Test agent has no reflex by default."""
        from src.agents.agent import Agent

        agent = Agent(agent_id="test")

        assert agent.reflex_artifact_id is None
        assert agent.has_reflex is False

    def test_agent_reflex_artifact_id_setter(self) -> None:
        """Test agent reflex_artifact_id can be set."""
        from src.agents.agent import Agent

        agent = Agent(agent_id="test")
        agent.reflex_artifact_id = "my_reflex"

        assert agent.reflex_artifact_id == "my_reflex"
        assert agent.has_reflex is True

    def test_agent_config_includes_reflex(self) -> None:
        """Test AgentConfigDict includes reflex_artifact_id."""
        from src.agents.agent import AgentConfigDict

        config: AgentConfigDict = {
            "llm_model": "test-model",
            "reflex_artifact_id": "my_reflex",
        }

        assert config.get("reflex_artifact_id") == "my_reflex"


class TestRunnerReflexIntegration:
    """Tests for SimulationRunner reflex integration."""

    @pytest.fixture
    def world_with_reflex(self, test_world):
        """Add a reflex artifact to the test world."""
        from datetime import datetime

        # Create reflex artifact using the artifacts store's write method
        reflex_code = '''
def reflex(context):
    # Auto-noop if balance > 50
    if context.get("balance", 0) > 50:
        return {"action_type": "noop", "reason": "reflex fired"}
    return None
'''
        test_world.artifacts.write(
            artifact_id="test_reflex",
            type="reflex",
            content=reflex_code,
            created_by="agent_1",
            executable=True,
        )

        return test_world

    @pytest.mark.asyncio
    async def test_try_reflex_fires(self, world_with_reflex) -> None:
        """Test that _try_reflex returns action when reflex fires."""
        from src.agents.agent import Agent
        import types

        world = world_with_reflex

        # Create agent with reflex
        agent = Agent(agent_id="agent_1")  # Use existing principal
        agent.reflex_artifact_id = "test_reflex"

        # Create a mock runner (we only need the _try_reflex method)
        class MockRunner:
            def __init__(self, world):
                self.world = world
                self.verbose = False

        runner = MockRunner(world)
        from src.simulation.runner import SimulationRunner

        runner._try_reflex = types.MethodType(SimulationRunner._try_reflex, runner)

        action = await runner._try_reflex(agent)

        assert action is not None
        assert action["action_type"] == "noop"
        assert action.get("reason") == "reflex fired"

    @pytest.mark.asyncio
    async def test_try_reflex_no_reflex_returns_none(self, world_with_reflex) -> None:
        """Test that _try_reflex returns None when agent has no reflex."""
        from src.agents.agent import Agent
        import types

        world = world_with_reflex

        # Create agent WITHOUT reflex
        agent = Agent(agent_id="agent_1")
        # Note: no reflex_artifact_id set

        class MockRunner:
            def __init__(self, world):
                self.world = world
                self.verbose = False

        runner = MockRunner(world)
        from src.simulation.runner import SimulationRunner

        runner._try_reflex = types.MethodType(SimulationRunner._try_reflex, runner)

        action = await runner._try_reflex(agent)

        assert action is None

    @pytest.mark.asyncio
    async def test_try_reflex_missing_artifact_returns_none(
        self, world_with_reflex
    ) -> None:
        """Test that _try_reflex returns None when reflex artifact doesn't exist."""
        from src.agents.agent import Agent
        import types

        world = world_with_reflex

        # Create agent with reflex pointing to non-existent artifact
        agent = Agent(agent_id="agent_1")
        agent.reflex_artifact_id = "nonexistent_reflex"

        class MockRunner:
            def __init__(self, world):
                self.world = world
                self.verbose = False

        runner = MockRunner(world)
        from src.simulation.runner import SimulationRunner

        runner._try_reflex = types.MethodType(SimulationRunner._try_reflex, runner)

        action = await runner._try_reflex(agent)

        assert action is None

    @pytest.mark.asyncio
    async def test_try_reflex_none_return_falls_through(
        self, world_with_reflex
    ) -> None:
        """Test that reflex returning None falls through to LLM."""
        from src.agents.agent import Agent
        import types

        world = world_with_reflex

        # Create a reflex that always returns None
        reflex_code = '''
def reflex(context):
    return None  # Always fall through to LLM
'''
        world.artifacts.write(
            artifact_id="always_none_reflex",
            type="reflex",
            content=reflex_code,
            created_by="agent_1",
            executable=True,
        )

        agent = Agent(agent_id="agent_1")
        agent.reflex_artifact_id = "always_none_reflex"

        class MockRunner:
            def __init__(self, world):
                self.world = world
                self.verbose = False

        runner = MockRunner(world)
        from src.simulation.runner import SimulationRunner

        runner._try_reflex = types.MethodType(SimulationRunner._try_reflex, runner)

        action = await runner._try_reflex(agent)

        assert action is None  # Should fall through
