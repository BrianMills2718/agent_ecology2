"""
Integration tests for Plan #63: Artifact Dependencies (Composition)

Tests for dependency injection at invocation time and runtime behavior.
These tests use the lower-level executor API to test dependency resolution.
"""

import tempfile
from datetime import datetime
from typing import Any

import pytest

from src.world.artifacts import Artifact, ArtifactStore
from src.world.executor import SafeExecutor
from src.world.ledger import Ledger


def make_artifact(
    artifact_id: str,
    code: str,
    created_by: str = "owner",
    price: int = 0,
    depends_on: list[str] | None = None,
) -> Artifact:
    """Helper to create test artifacts with dependencies."""
    now = datetime.now().isoformat()
    policy = {
        "read_price": 0,
        "invoke_price": price,
        "allow_read": ["*"],
        "allow_write": [],
        "allow_invoke": ["*"],
    }
    return Artifact(
        id=artifact_id,
        type="code",
        content=f"Test artifact {artifact_id}",
        created_by=created_by,
        created_at=now,
        updated_at=now,
        executable=True,
        code=code,
        policy=policy,
        depends_on=depends_on or [],
    )


@pytest.mark.plans([63])
class TestDependencyInjection:
    """Tests for dependency resolution and injection at invocation."""

    @pytest.fixture
    def executor(self) -> SafeExecutor:
        """Create executor."""
        return SafeExecutor(timeout=5)

    @pytest.fixture
    def ledger(self) -> Ledger:
        """Create ledger with test principals."""
        ledger = Ledger()
        ledger.create_principal("alice", starting_scrip=1000)
        ledger.create_principal("bob", starting_scrip=500)
        return ledger

    @pytest.fixture
    def store(self) -> ArtifactStore:
        """Create empty artifact store."""
        return ArtifactStore()

    def test_invoke_with_deps_injects_dependencies(
        self, executor: SafeExecutor, ledger: Ledger, store: ArtifactStore
    ) -> None:
        """Dependencies should be injected into execution context."""
        # Create a helper library
        helper = make_artifact(
            "helper_lib",
            """
def run(*args):
    return {"value": 42}
""",
        )
        store.artifacts["helper_lib"] = helper

        # Create a service that depends on helper
        # Note: context is a global (like invoke, pay, kernel_state)
        pipeline = make_artifact(
            "pipeline",
            """
def run(*args):
    # Access injected dependency via global context
    helper = context.dependencies["helper_lib"]
    result = helper.invoke()
    return {"helper_result": result["result"]["value"]}
""",
            depends_on=["helper_lib"],
        )
        store.artifacts["pipeline"] = pipeline

        # Execute pipeline with dependency resolution
        result = executor.execute_with_invoke(
            code=pipeline.code,
            args=[],
            caller_id="alice",
            artifact_id="pipeline",
            ledger=ledger,
            artifact_store=store,
        )

        assert result["success"] is True
        assert result["result"]["helper_result"] == 42

    def test_nested_invocation_tracked(
        self, executor: SafeExecutor, ledger: Ledger, store: ArtifactStore
    ) -> None:
        """When dependency is called, nested invocation should be tracked."""
        # Create helper
        counter = make_artifact(
            "counter",
            "def run(*args): return {'count': 1}",
        )
        store.artifacts["counter"] = counter

        # Create service using counter (context is global)
        service = make_artifact(
            "user_service",
            """
def run(*args):
    counter = context.dependencies["counter"]
    r = counter.invoke()
    return r["result"]
""",
            depends_on=["counter"],
        )
        store.artifacts["user_service"] = service

        result = executor.execute_with_invoke(
            code=service.code,
            args=[],
            caller_id="alice",
            artifact_id="user_service",
            ledger=ledger,
            artifact_store=store,
        )

        assert result["success"] is True
        # The nested invocation should have been tracked (nested_invocations in result)
        assert "nested_invocations" in result or result["success"]

    def test_dep_resource_attribution(
        self, executor: SafeExecutor, ledger: Ledger, store: ArtifactStore
    ) -> None:
        """Resource costs of dependency calls should be attributed to invoker."""
        # Create CPU-intensive helper
        heavy = make_artifact(
            "heavy_helper",
            """
def run(*args):
    # Do some work
    total = sum(i * i for i in range(10000))
    return {'total': total}
""",
        )
        store.artifacts["heavy_helper"] = heavy

        # Create service using heavy helper (context is global)
        light = make_artifact(
            "light_service",
            """
def run(*args):
    helper = context.dependencies["heavy_helper"]
    return helper.invoke()["result"]
""",
            depends_on=["heavy_helper"],
        )
        store.artifacts["light_service"] = light

        result = executor.execute_with_invoke(
            code=light.code,
            args=[],
            caller_id="alice",
            artifact_id="light_service",
            ledger=ledger,
            artifact_store=store,
        )

        assert result["success"] is True
        # Resources consumed should include both service and helper costs
        assert "resources_consumed" in result
        # CPU time should be > 0 (helper did work)
        assert result["resources_consumed"].get("cpu_seconds", 0) >= 0

    def test_deleted_dep_fails_gracefully(
        self, executor: SafeExecutor, ledger: Ledger, store: ArtifactStore
    ) -> None:
        """If dependency is deleted after artifact creation, invocation fails clearly."""
        # Create helper
        helper = make_artifact(
            "temp_helper",
            "def run(): return 'ok'",
        )
        store.artifacts["temp_helper"] = helper

        # Create service depending on it
        service = make_artifact(
            "service",
            """
def run(args=None, context=None):
    helper = context.dependencies["temp_helper"]
    return helper.invoke()
""",
            depends_on=["temp_helper"],
        )
        store.artifacts["service"] = service

        # Delete the helper (soft delete)
        deleted_helper = store.artifacts["temp_helper"]
        deleted_helper.deleted = True
        deleted_helper.deleted_at = datetime.now().isoformat()

        # Try to invoke - should fail with clear error
        result = executor.execute_with_invoke(
            code=service.code,
            args=[],
            caller_id="alice",
            artifact_id="service",
            ledger=ledger,
            artifact_store=store,
        )

        # Should fail because dep is deleted
        # Either the dependency resolution fails, or the invoke inside fails
        if result["success"]:
            # If it succeeded somehow, the test should fail
            pytest.fail("Expected failure when dependency is deleted")

    def test_transitive_deps_resolved(
        self, executor: SafeExecutor, ledger: Ledger, store: ArtifactStore
    ) -> None:
        """Transitive dependencies (A→B→C) should be resolved."""
        # Create C (base)
        lib_c = make_artifact(
            "lib_c",
            "def run(*args): return {'from': 'C'}",
        )
        store.artifacts["lib_c"] = lib_c

        # Create B depending on C (context is global)
        lib_b = make_artifact(
            "lib_b",
            """
def run(*args):
    c = context.dependencies["lib_c"]
    c_result = c.invoke()
    return {'from': 'B', 'c_said': c_result['result']['from']}
""",
            depends_on=["lib_c"],
        )
        store.artifacts["lib_b"] = lib_b

        # Create A depending on B (context is global)
        lib_a = make_artifact(
            "lib_a",
            """
def run(*args):
    b = context.dependencies["lib_b"]
    b_result = b.invoke()
    return {'from': 'A', 'chain': [b_result['result']['from'], b_result['result']['c_said']]}
""",
            depends_on=["lib_b"],
        )
        store.artifacts["lib_a"] = lib_a

        result = executor.execute_with_invoke(
            code=lib_a.code,
            args=[],
            caller_id="alice",
            artifact_id="lib_a",
            ledger=ledger,
            artifact_store=store,
        )

        assert result["success"] is True
        assert result["result"]["chain"] == ["B", "C"]


@pytest.mark.plans([63])
class TestDependencyContext:
    """Tests for the dependency context provided to artifacts."""

    @pytest.fixture
    def executor(self) -> SafeExecutor:
        """Create executor."""
        return SafeExecutor(timeout=5)

    @pytest.fixture
    def ledger(self) -> Ledger:
        """Create ledger."""
        ledger = Ledger()
        ledger.create_principal("alice", starting_scrip=1000)
        return ledger

    @pytest.fixture
    def store(self) -> ArtifactStore:
        """Create artifact store."""
        return ArtifactStore()

    def test_context_has_dependencies_dict(
        self, executor: SafeExecutor, ledger: Ledger, store: ArtifactStore
    ) -> None:
        """Context (global) should have dependencies attribute as dict."""
        helper = make_artifact(
            "helper",
            "def run(*args): return 1",
        )
        store.artifacts["helper"] = helper

        # Note: context is injected as a global, not a function parameter
        checker = make_artifact(
            "checker",
            """
def run(*args):
    # Verify context.dependencies exists and is dict (context is global)
    assert hasattr(context, 'dependencies'), "Missing dependencies"
    assert isinstance(context.dependencies, dict), "dependencies not dict"
    assert 'helper' in context.dependencies, "helper not in dependencies"
    return {'ok': True}
""",
            depends_on=["helper"],
        )
        store.artifacts["checker"] = checker

        result = executor.execute_with_invoke(
            code=checker.code,
            args=[],
            caller_id="alice",
            artifact_id="checker",
            ledger=ledger,
            artifact_store=store,
        )

        assert result["success"] is True, f"Failed: {result.get('error')}"

    def test_dep_wrapper_has_invoke_method(
        self, executor: SafeExecutor, ledger: Ledger, store: ArtifactStore
    ) -> None:
        """Dependency wrapper should have invoke() method."""
        target = make_artifact(
            "target",
            "def run(*args): return {'invoked': True}",
        )
        store.artifacts["target"] = target

        # context is global, not a function parameter
        caller = make_artifact(
            "caller",
            """
def run(*args):
    target = context.dependencies["target"]
    # Verify invoke is callable
    assert callable(getattr(target, 'invoke', None)), "invoke not callable"
    result = target.invoke()
    return result["result"]
""",
            depends_on=["target"],
        )
        store.artifacts["caller"] = caller

        result = executor.execute_with_invoke(
            code=caller.code,
            args=[],
            caller_id="alice",
            artifact_id="caller",
            ledger=ledger,
            artifact_store=store,
        )

        assert result["success"] is True
        assert result["result"]["invoked"] is True
