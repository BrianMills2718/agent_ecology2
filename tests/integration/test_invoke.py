"""Unit tests for execute_with_invoke() artifact composition.

Tests the invoke() capability that allows artifacts to call other artifacts.
"""

from datetime import datetime

import pytest

from src.world.executor import SafeExecutor
from src.world.ledger import Ledger
from src.world.artifacts import Artifact, ArtifactStore


def make_artifact(
    artifact_id: str,
    code: str,
    created_by: str = "owner",
    price: int = 0,
    executable: bool = True,
    allow_invoke: list[str] | None = None,
) -> Artifact:
    """Helper to create test artifacts."""
    now = datetime.now().isoformat()
    policy = {
        "read_price": 0,
        "invoke_price": price,
        "allow_read": ["*"],
        "allow_write": [],
        "allow_invoke": allow_invoke or ["*"],
    }
    return Artifact(
        id=artifact_id,
        type="code",
        content=f"Test artifact {artifact_id}",
        created_by=created_by,
        created_at=now,
        updated_at=now,
        executable=executable,
        code=code,
        policy=policy,
    )


class TestInvokeBasic:
    """Basic invoke() functionality tests."""

    def setup_method(self) -> None:
        """Create fresh executor, ledger, and artifact store for each test."""
        self.executor = SafeExecutor(timeout=5)
        self.ledger = Ledger()
        self.store = ArtifactStore()

        # Create test principals
        self.ledger.create_principal("caller", starting_scrip=100)
        self.ledger.create_principal("owner", starting_scrip=50)

    def test_basic_invoke(self) -> None:
        """Test basic invoke() call to another artifact."""
        # Create a simple target artifact
        target_code = """
def run(*args):
    return {"value": args[0] * 2}
"""
        target = make_artifact("double", target_code, price=0)
        self.store.artifacts["double"] = target

        # Create caller artifact that invokes the target
        caller_code = """
def run(*args):
    result = invoke("double", args[0])
    return result
"""
        result = self.executor.execute_with_invoke(
            code=caller_code,
            args=[5],
            caller_id="caller",
            artifact_id="caller_artifact",
            ledger=self.ledger,
            artifact_store=self.store,
        )

        assert result["success"] is True
        assert result["result"]["success"] is True
        assert result["result"]["result"]["value"] == 10

    def test_invoke_with_price(self) -> None:
        """Test that invoke() charges price to caller."""
        target_code = """
def run(*args):
    return "success"
"""
        target = make_artifact("paid_service", target_code, created_by="owner", price=10)
        self.store.artifacts["paid_service"] = target

        caller_code = """
def run(*args):
    result = invoke("paid_service")
    return result
"""
        initial_caller_scrip = self.ledger.get_scrip("caller")
        initial_owner_scrip = self.ledger.get_scrip("owner")

        result = self.executor.execute_with_invoke(
            code=caller_code,
            args=[],
            caller_id="caller",
            artifact_id="caller_artifact",
            ledger=self.ledger,
            artifact_store=self.store,
        )

        assert result["success"] is True
        assert result["result"]["price_paid"] == 10
        assert self.ledger.get_scrip("caller") == initial_caller_scrip - 10
        assert self.ledger.get_scrip("owner") == initial_owner_scrip + 10

    def test_invoke_artifact_not_found(self) -> None:
        """Test invoke() with non-existent artifact."""
        caller_code = """
def run(*args):
    result = invoke("nonexistent")
    return result
"""
        result = self.executor.execute_with_invoke(
            code=caller_code,
            args=[],
            caller_id="caller",
            artifact_id="caller_artifact",
            ledger=self.ledger,
            artifact_store=self.store,
        )

        assert result["success"] is True
        assert result["result"]["success"] is False
        assert "not found" in result["result"]["error"]

    def test_invoke_not_executable(self) -> None:
        """Test invoke() on non-executable artifact."""
        target = make_artifact("data", "just data", executable=False)
        self.store.artifacts["data"] = target

        caller_code = """
def run(*args):
    result = invoke("data")
    return result
"""
        result = self.executor.execute_with_invoke(
            code=caller_code,
            args=[],
            caller_id="caller",
            artifact_id="caller_artifact",
            ledger=self.ledger,
            artifact_store=self.store,
        )

        assert result["success"] is True
        assert result["result"]["success"] is False
        assert "not executable" in result["result"]["error"]


class TestInvokeRecursion:
    """Tests for recursive invoke() and depth limiting."""

    def setup_method(self) -> None:
        """Create fresh executor, ledger, and artifact store for each test."""
        self.executor = SafeExecutor(timeout=5)
        self.ledger = Ledger()
        self.store = ArtifactStore()

        self.ledger.create_principal("caller", starting_scrip=100)
        self.ledger.create_principal("owner", starting_scrip=50)

    def test_nested_invoke(self) -> None:
        """Test A calls B calls C (depth=2)."""
        # C: leaf artifact
        c_code = """
def run(*args):
    return {"from": "C", "value": args[0]}
"""
        self.store.artifacts["artifact_c"] = make_artifact("artifact_c", c_code)

        # B: calls C
        b_code = """
def run(*args):
    c_result = invoke("artifact_c", args[0])
    return {"from": "B", "c_result": c_result}
"""
        self.store.artifacts["artifact_b"] = make_artifact("artifact_b", b_code)

        # A: calls B
        a_code = """
def run(*args):
    b_result = invoke("artifact_b", args[0])
    return {"from": "A", "b_result": b_result}
"""
        result = self.executor.execute_with_invoke(
            code=a_code,
            args=[42],
            caller_id="caller",
            artifact_id="artifact_a",
            ledger=self.ledger,
            artifact_store=self.store,
        )

        assert result["success"] is True
        # Check nested structure
        a_result = result["result"]
        assert a_result["from"] == "A"
        assert a_result["b_result"]["success"] is True
        b_result = a_result["b_result"]["result"]
        assert b_result["from"] == "B"
        assert b_result["c_result"]["success"] is True
        assert b_result["c_result"]["result"]["from"] == "C"
        assert b_result["c_result"]["result"]["value"] == 42

    def test_max_depth_exceeded(self) -> None:
        """Test that exceeding max depth returns error."""
        # Create self-referencing artifact (would loop forever without limit)
        loop_code = """
def run(*args):
    depth = args[0] if args else 0
    result = invoke("looper", depth + 1)
    return {"depth": depth, "inner": result}
"""
        self.store.artifacts["looper"] = make_artifact("looper", loop_code)

        result = self.executor.execute_with_invoke(
            code=loop_code,
            args=[0],
            caller_id="caller",
            artifact_id="starter",
            ledger=self.ledger,
            artifact_store=self.store,
            max_depth=3,
        )

        # Should succeed but inner invoke should fail at max depth
        assert result["success"] is True
        # Drill down to find the depth limit error
        inner = result["result"]
        while inner.get("inner", {}).get("success", False):
            inner = inner["inner"]["result"]

        # At some point, invoke should have failed with max depth error
        assert "Max invoke depth" in inner.get("inner", {}).get("error", "")


class TestInvokePermissions:
    """Tests for invoke() permission checking."""

    def setup_method(self) -> None:
        """Create fresh executor, ledger, and artifact store for each test."""
        self.executor = SafeExecutor(timeout=5)
        self.ledger = Ledger()
        self.store = ArtifactStore()

        self.ledger.create_principal("caller", starting_scrip=100)
        self.ledger.create_principal("owner", starting_scrip=50)
        self.ledger.create_principal("allowed", starting_scrip=50)

    def test_invoke_permission_denied(self) -> None:
        """Test invoke() when caller doesn't have permission.

        Per CAP-003, permissions are contract-based. This test uses the
        'private' contract which only allows owner access.
        """
        target_code = """
def run(*args):
    return "secret"
"""
        target = make_artifact(
            "restricted",
            target_code,
            created_by="owner",  # Only owner can invoke
        )
        # Use private contract - only owner can access
        target.access_contract_id = "kernel_contract_private"  # type: ignore[attr-defined]
        self.store.artifacts["restricted"] = target

        caller_code = """
def run(*args):
    result = invoke("restricted")
    return result
"""
        result = self.executor.execute_with_invoke(
            code=caller_code,
            args=[],
            caller_id="caller",  # Not the owner
            artifact_id="caller_artifact",
            ledger=self.ledger,
            artifact_store=self.store,
        )

        assert result["success"] is True
        assert result["result"]["success"] is False
        # Private contract denies access with "access denied" or "private"
        assert "denied" in result["result"]["error"].lower() or "private" in result["result"]["error"].lower()

    def test_invoke_insufficient_scrip(self) -> None:
        """Test invoke() when caller can't afford price."""
        target_code = """
def run(*args):
    return "expensive"
"""
        target = make_artifact("expensive", target_code, price=1000)  # Very expensive
        self.store.artifacts["expensive"] = target

        caller_code = """
def run(*args):
    result = invoke("expensive")
    return result
"""
        result = self.executor.execute_with_invoke(
            code=caller_code,
            args=[],
            caller_id="caller",  # Only has 100 scrip
            artifact_id="caller_artifact",
            ledger=self.ledger,
            artifact_store=self.store,
        )

        assert result["success"] is True
        assert result["result"]["success"] is False
        assert "insufficient scrip" in result["result"]["error"]


class TestInvokeErrorPropagation:
    """Tests for error handling in invoke() chains."""

    def setup_method(self) -> None:
        """Create fresh executor, ledger, and artifact store for each test."""
        self.executor = SafeExecutor(timeout=5)
        self.ledger = Ledger()
        self.store = ArtifactStore()

        self.ledger.create_principal("caller", starting_scrip=100)
        self.ledger.create_principal("owner", starting_scrip=50)

    def test_error_in_invoked_artifact(self) -> None:
        """Test that errors in invoked artifact propagate correctly."""
        target_code = """
def run(*args):
    raise ValueError("Something went wrong")
"""
        self.store.artifacts["error_artifact"] = make_artifact("error_artifact", target_code)

        caller_code = """
def run(*args):
    result = invoke("error_artifact")
    return result
"""
        result = self.executor.execute_with_invoke(
            code=caller_code,
            args=[],
            caller_id="caller",
            artifact_id="caller_artifact",
            ledger=self.ledger,
            artifact_store=self.store,
        )

        assert result["success"] is True
        assert result["result"]["success"] is False
        assert "ValueError" in result["result"]["error"]

    def test_no_payment_on_failure(self) -> None:
        """Test that price is not paid when invoked artifact fails."""
        target_code = """
def run(*args):
    raise RuntimeError("Fail!")
"""
        target = make_artifact("failing", target_code, created_by="owner", price=50)
        self.store.artifacts["failing"] = target

        caller_code = """
def run(*args):
    result = invoke("failing")
    return result
"""
        initial_caller_scrip = self.ledger.get_scrip("caller")
        initial_owner_scrip = self.ledger.get_scrip("owner")

        result = self.executor.execute_with_invoke(
            code=caller_code,
            args=[],
            caller_id="caller",
            artifact_id="caller_artifact",
            ledger=self.ledger,
            artifact_store=self.store,
        )

        assert result["success"] is True
        assert result["result"]["success"] is False
        assert result["result"]["price_paid"] == 0
        # Scrip should not have changed
        assert self.ledger.get_scrip("caller") == initial_caller_scrip
        assert self.ledger.get_scrip("owner") == initial_owner_scrip
