"""Tests for LLM gateway functionality (Plan #255).

Tests the kernel LLM gateway:
- _syscall_llm kernel primitive
- can_call_llm capability check
- kernel_llm_gateway artifact bootstrap
- Budget deduction from caller
"""

import pytest
from unittest.mock import patch, MagicMock

from src.world.world import World
from src.world.executor import create_syscall_llm, LLMSyscallResult
from src.world.llm_client import LLMCallResult


def _mock_call_llm_result(
    content: str = "Hello, world!",
    cost: float = 0.001,
) -> LLMCallResult:
    """Create a mock LLMCallResult for testing."""
    return LLMCallResult(
        content=content,
        usage={"prompt_tokens": 10, "completion_tokens": 5, "total_tokens": 15},
        cost=cost,
        model="gpt-4",
    )


@pytest.mark.plans([255])
class TestKernelLLMGateway:
    """Test kernel_llm_gateway artifact bootstrap."""

    def test_gateway_exists_at_init(self, test_world: World) -> None:
        """kernel_llm_gateway is seeded on World init."""
        artifact = test_world.artifacts.get("kernel_llm_gateway")
        assert artifact is not None
        assert artifact.type == "executable"

    def test_gateway_has_capability(self, test_world: World) -> None:
        """kernel_llm_gateway has can_call_llm capability."""
        artifact = test_world.artifacts.get("kernel_llm_gateway")
        assert artifact is not None
        assert "can_call_llm" in artifact.capabilities

    def test_gateway_is_passive(self, test_world: World) -> None:
        """kernel_llm_gateway has has_loop=False (passive service)."""
        artifact = test_world.artifacts.get("kernel_llm_gateway")
        assert artifact is not None
        assert artifact.has_loop is False

    def test_gateway_has_no_standing(self, test_world: World) -> None:
        """kernel_llm_gateway has has_standing=False (no wallet)."""
        artifact = test_world.artifacts.get("kernel_llm_gateway")
        assert artifact is not None
        assert artifact.has_standing is False

    def test_gateway_has_code(self, test_world: World) -> None:
        """kernel_llm_gateway has executable code."""
        artifact = test_world.artifacts.get("kernel_llm_gateway")
        assert artifact is not None
        assert artifact.code is not None
        assert "def run(" in artifact.code


@pytest.mark.plans([255])
class TestSyscallLLM:
    """Test _syscall_llm kernel primitive."""

    def test_syscall_returns_llm_syscall_result(self, test_world: World) -> None:
        """_syscall_llm returns proper LLMSyscallResult structure."""
        # Create a principal with budget
        test_world.ledger.create_principal("syscall_caller_1", starting_scrip=100)
        test_world.ledger.set_resource("syscall_caller_1", "llm_budget", 10.0)

        syscall = create_syscall_llm(test_world, "syscall_caller_1")

        # mock-ok: LLM calls are external API
        with patch("src.world.llm_client.call_llm", return_value=_mock_call_llm_result()):
            result = syscall("gpt-4", [{"role": "user", "content": "Hi"}])

        assert isinstance(result, dict)
        assert "success" in result
        assert "content" in result
        assert "usage" in result
        assert "cost" in result
        assert "error" in result

    def test_syscall_deducts_budget(self, test_world: World) -> None:
        """_syscall_llm deducts from caller's llm_budget."""
        # Create a principal with budget
        test_world.ledger.create_principal("syscall_caller_2", starting_scrip=100)
        test_world.ledger.set_resource("syscall_caller_2", "llm_budget", 10.0)

        initial_budget = test_world.ledger.get_resource("syscall_caller_2", "llm_budget")

        # mock-ok: LLM calls are external API
        with patch("src.world.llm_client.call_llm", return_value=_mock_call_llm_result(cost=0.005)):
            syscall = create_syscall_llm(test_world, "syscall_caller_2")
            result = syscall("gpt-4", [{"role": "user", "content": "Hi"}])

        assert result["success"] is True
        final_budget = test_world.ledger.get_resource("syscall_caller_2", "llm_budget")
        assert final_budget < initial_budget
        assert final_budget == initial_budget - 0.005

    def test_syscall_rejects_insufficient_budget(self, test_world: World) -> None:
        """_syscall_llm fails if caller has insufficient budget."""
        # Create a principal with tiny budget
        test_world.ledger.create_principal("syscall_caller_3", starting_scrip=100)
        test_world.ledger.set_resource("syscall_caller_3", "llm_budget", 0.0001)  # Very small budget

        syscall = create_syscall_llm(test_world, "syscall_caller_3")

        # No mock needed - should fail before LLM call
        result = syscall("gpt-4", [{"role": "user", "content": "Hi"}])

        assert result["success"] is False
        assert "Budget exhausted" in result["error"] or "cannot afford" in result["error"].lower()

    def test_syscall_handles_llm_error(self, test_world: World) -> None:
        """_syscall_llm handles LLM errors gracefully."""
        # Create a principal with budget
        test_world.ledger.create_principal("syscall_caller_4", starting_scrip=100)
        test_world.ledger.set_resource("syscall_caller_4", "llm_budget", 10.0)

        syscall = create_syscall_llm(test_world, "syscall_caller_4")

        # mock-ok: LLM calls are external API
        with patch("src.world.llm_client.call_llm", side_effect=Exception("API error")):
            result = syscall("gpt-4", [{"role": "user", "content": "Hi"}])

        assert result["success"] is False
        assert "LLM call failed" in result["error"]


@pytest.mark.plans([255])
class TestSyscallInjection:
    """Test _syscall_llm capability-based injection."""

    def test_syscall_injected_for_capable_artifact(self, test_world: World) -> None:
        """Artifacts with can_call_llm get _syscall_llm injected."""
        from src.world.executor import SafeExecutor

        # Create an artifact with can_call_llm capability
        # Code must define run() function for execute_with_invoke
        # Check for _syscall_llm in globals() since it's injected there
        test_code = """
def run():
    return '_syscall_llm' in globals()
"""
        test_world.artifacts.write(
            artifact_id="test_capable",
            type="executable",
            content={"description": "test"},
            created_by="SYSTEM",
            executable=True,
            code=test_code,
            capabilities=["can_call_llm"],
        )

        executor = SafeExecutor()
        # execute_with_invoke is the method that injects kernel interfaces and syscalls
        result = executor.execute_with_invoke(
            code=test_code,
            world=test_world,
            caller_id="test_capable",
            artifact_id="test_capable",
            artifact_store=test_world.artifacts,
        )

        # The result should be successful
        assert result.get("success") is True
        # The run() function checks if _syscall_llm is in globals
        assert result.get("result") is True

    def test_syscall_not_injected_without_capability(self, test_world: World) -> None:
        """Artifacts without can_call_llm don't get _syscall_llm."""
        from src.world.executor import SafeExecutor

        # Create an artifact WITHOUT can_call_llm capability
        # Code tries to call _syscall_llm which should not be injected
        test_code = """
def run():
    return _syscall_llm('model', [])
"""
        test_world.artifacts.write(
            artifact_id="test_incapable",
            type="executable",
            content={"description": "test"},
            created_by="SYSTEM",
            executable=True,
            code=test_code,
            capabilities=[],  # No can_call_llm
        )

        executor = SafeExecutor()

        # Try to use _syscall_llm - should fail with NameError
        result = executor.execute_with_invoke(
            code=test_code,
            world=test_world,
            caller_id="test_incapable",
            artifact_id="test_incapable",
            artifact_store=test_world.artifacts,
        )

        # Should fail because _syscall_llm is not defined
        assert result.get("success") is False
        assert "NameError" in result.get("error", "") or "not defined" in result.get("error", "")


@pytest.mark.plans([255])
class TestArtifactLoopManager:
    """Test ArtifactLoopManager for has_loop artifacts."""

    def test_manager_creation(self, test_world: World) -> None:
        """ArtifactLoopManager can be created."""
        from src.simulation.artifact_loop import ArtifactLoopManager

        manager = ArtifactLoopManager(test_world, test_world.rate_tracker)
        assert manager is not None
        assert manager.loop_count == 0

    def test_discover_loops_finds_has_loop_artifacts(self, test_world: World) -> None:
        """discover_loops() finds artifacts with has_loop=True."""
        from src.simulation.artifact_loop import ArtifactLoopManager

        # Create a has_loop artifact (V4 style - artifact with has_standing creates principal)
        # First create artifact, which registers in id_registry as 'artifact'
        test_world.artifacts.write(
            artifact_id="loop_artifact_test",
            type="executable",
            content={"description": "test loop"},
            created_by="SYSTEM",
            executable=True,
            code="pass",
            has_standing=True,
            has_loop=True,
        )
        # Ensure principal exists in ledger for resource tracking
        test_world.ledger.ensure_principal("loop_artifact_test")
        test_world.ledger.credit_scrip("loop_artifact_test", 100)

        manager = ArtifactLoopManager(test_world, test_world.rate_tracker)
        discovered = manager.discover_loops()

        assert "loop_artifact_test" in discovered
        assert manager.loop_count >= 1

    def test_discover_loops_ignores_passive_artifacts(self, test_world: World) -> None:
        """discover_loops() ignores artifacts with has_loop=False."""
        from src.simulation.artifact_loop import ArtifactLoopManager

        # kernel_llm_gateway has has_loop=False
        manager = ArtifactLoopManager(test_world, test_world.rate_tracker)
        discovered = manager.discover_loops()

        assert "kernel_llm_gateway" not in discovered

    def test_create_loop_validates_has_loop(self, test_world: World) -> None:
        """create_loop() raises error if artifact doesn't have has_loop=True."""
        from src.simulation.artifact_loop import ArtifactLoopManager

        manager = ArtifactLoopManager(test_world, test_world.rate_tracker)

        # kernel_llm_gateway is passive (has_loop=False)
        with pytest.raises(ValueError, match="has_loop"):
            manager.create_loop("kernel_llm_gateway")


@pytest.mark.plans([255])
class TestArtifactLoop:
    """Test ArtifactLoop execution."""

    def test_loop_config_validation(self) -> None:
        """ArtifactLoopConfig validates values."""
        from src.simulation.artifact_loop import ArtifactLoopConfig

        # Valid config
        config = ArtifactLoopConfig(min_loop_delay=0.1, max_loop_delay=10.0)
        assert config.min_loop_delay == 0.1

        # Invalid: negative delay
        with pytest.raises(ValueError):
            ArtifactLoopConfig(min_loop_delay=-1.0)

        # Invalid: max < min
        with pytest.raises(ValueError):
            ArtifactLoopConfig(min_loop_delay=5.0, max_loop_delay=1.0)

    def test_loop_state_transitions(self, test_world: World) -> None:
        """ArtifactLoop transitions through states correctly."""
        from src.simulation.artifact_loop import ArtifactLoop, ArtifactState

        # Create a has_loop artifact (V4 style)
        test_world.artifacts.write(
            artifact_id="loop_test_artifact",
            type="executable",
            content={"description": "test"},
            created_by="SYSTEM",
            executable=True,
            code="pass",
            has_standing=True,
            has_loop=True,
        )
        # Ensure principal exists for resource tracking
        test_world.ledger.ensure_principal("loop_test_artifact")
        test_world.ledger.credit_scrip("loop_test_artifact", 100)

        loop = ArtifactLoop(
            artifact_id="loop_test_artifact",
            world=test_world,
            rate_tracker=test_world.rate_tracker,
        )

        assert loop.state == ArtifactState.STOPPED
        assert loop.is_running is False
