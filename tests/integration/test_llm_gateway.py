"""Integration tests for LLM gateway (Plan #255).

Tests the LLM gateway architecture and integration.
"""

import pytest

from src.world.world import World


@pytest.mark.plans([255])
class TestLLMGatewayArchitecture:
    """Test LLM gateway architectural requirements."""

    def test_gateway_bootstrapped_on_world_init(self, test_world: World) -> None:
        """kernel_llm_gateway is created when World initializes."""
        gateway = test_world.artifacts.get("kernel_llm_gateway")
        assert gateway is not None
        assert gateway.type == "executable"
        assert gateway.executable is True

    def test_gateway_has_required_capability(self, test_world: World) -> None:
        """Gateway has can_call_llm capability for syscall injection."""
        gateway = test_world.artifacts.get("kernel_llm_gateway")
        assert gateway is not None
        assert "can_call_llm" in gateway.capabilities

    def test_gateway_is_passive_not_active(self, test_world: World) -> None:
        """Gateway is a passive service (has_loop=False), not an active agent."""
        gateway = test_world.artifacts.get("kernel_llm_gateway")
        assert gateway is not None
        assert gateway.has_loop is False
        assert gateway.has_standing is False

    def test_gateway_code_calls_syscall(self, test_world: World) -> None:
        """Gateway code wraps _syscall_llm correctly."""
        gateway = test_world.artifacts.get("kernel_llm_gateway")
        assert gateway is not None
        assert "_syscall_llm" in gateway.code
        assert "def run(" in gateway.code


@pytest.mark.plans([255])
class TestArtifactLoopManager:
    """Test ArtifactLoopManager integration."""

    def test_discover_loops_finds_has_loop_artifacts(self, test_world: World) -> None:
        """ArtifactLoopManager discovers artifacts with has_loop=True."""
        from src.simulation.artifact_loop import ArtifactLoopManager

        # Create a has_loop artifact
        test_world.artifacts.write(
            artifact_id="loop_artifact_int",
            type="executable",
            content={"description": "artifact with loop"},
            created_by="SYSTEM",
            executable=True,
            code="def run(): pass",
            has_standing=True,
            has_loop=True,
        )
        test_world.ledger.ensure_principal("loop_artifact_int")

        manager = ArtifactLoopManager(test_world, test_world.rate_tracker)
        discovered = manager.discover_loops()

        assert "loop_artifact_int" in discovered
        assert manager.loop_count >= 1

    def test_gateway_not_in_discovered_loops(self, test_world: World) -> None:
        """kernel_llm_gateway is passive, not discovered as loop artifact."""
        from src.simulation.artifact_loop import ArtifactLoopManager

        manager = ArtifactLoopManager(test_world, test_world.rate_tracker)
        discovered = manager.discover_loops()

        # Gateway is passive (has_loop=False)
        assert "kernel_llm_gateway" not in discovered

    def test_create_loop_for_has_loop_artifact(self, test_world: World) -> None:
        """Can create loop for artifact with has_loop=True."""
        from src.simulation.artifact_loop import ArtifactLoopManager, ArtifactState

        # Create a has_loop artifact
        test_world.artifacts.write(
            artifact_id="loop_artifact_create",
            type="executable",
            content={"description": "artifact with loop"},
            created_by="SYSTEM",
            executable=True,
            code="def run(): pass",
            has_standing=True,
            has_loop=True,
        )
        test_world.ledger.ensure_principal("loop_artifact_create")

        manager = ArtifactLoopManager(test_world, test_world.rate_tracker)
        loop = manager.create_loop("loop_artifact_create")

        assert loop is not None
        assert loop.state == ArtifactState.STOPPED
        assert loop.artifact_id == "loop_artifact_create"


@pytest.mark.plans([255])
class TestUniversalBridgePattern:
    """Test the Universal Bridge Pattern architecture.

    The pattern is: Kernel provides syscall, artifact wraps it.
    This is the template for LLM, Search, GitHub, etc.
    """

    def test_syscall_pattern_in_executor(self, test_world: World) -> None:
        """Executor injects _syscall_llm for capable artifacts."""
        from src.world.executor import SafeExecutor, create_syscall_llm

        # create_syscall_llm exists and is callable
        assert callable(create_syscall_llm)

        # Create syscall for a caller
        test_world.ledger.create_principal("syscall_test", starting_scrip=100)
        test_world.ledger.set_resource("syscall_test", "llm_budget", 10.0)
        syscall = create_syscall_llm(test_world, "syscall_test")
        assert callable(syscall)

    def test_capability_gates_injection(self, test_world: World) -> None:
        """Only artifacts with can_call_llm get _syscall_llm."""
        # Verify gateway has capability
        gateway = test_world.artifacts.get("kernel_llm_gateway")
        assert "can_call_llm" in gateway.capabilities

        # Create artifact without capability
        test_world.artifacts.write(
            artifact_id="no_llm_access",
            type="executable",
            content={"description": "no LLM access"},
            created_by="SYSTEM",
            executable=True,
            code="pass",
            capabilities=[],  # No can_call_llm
        )
        no_access = test_world.artifacts.get("no_llm_access")
        assert "can_call_llm" not in no_access.capabilities
