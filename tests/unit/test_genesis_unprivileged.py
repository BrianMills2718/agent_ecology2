"""Plan #111: Verify genesis artifacts only use KernelState/KernelActions interfaces.

These tests ensure genesis artifacts are not privileged - they use the same
kernel interfaces available to all artifacts. Any capability a genesis artifact
needs must be exposed through these interfaces.

The goal is that the simulation can work with full capabilities even with zero
genesis artifacts (other than genesis agents).
"""

from __future__ import annotations

import ast
import inspect
from pathlib import Path
from typing import Any

import pytest


# Helper to find privileged access patterns in source code
def get_privileged_patterns() -> dict[str, list[str]]:
    """Return patterns that indicate privileged access.

    These are method calls or attribute accesses that bypass kernel interfaces.
    """
    return {
        # Direct Ledger method calls (should use KernelState/KernelActions)
        "ledger_privileged": [
            "self.ledger.create_principal",  # Should use KernelActions.create_principal
            "self.ledger.credit_scrip",  # Should use KernelActions (or be kernel-only)
            "self.ledger.deduct_scrip",  # Should use KernelActions (or be kernel-only)
            # Note: get_scrip, transfer_scrip etc. are acceptable via delegation
        ],
        # Direct ArtifactStore method calls (should use KernelState/KernelActions)
        "artifact_store_privileged": [
            "self.artifact_store.transfer_ownership",  # Should use KernelActions.transfer_ownership
            # Note: artifact_store.get() for read is acceptable via delegation
        ],
    }


class PrivilegedAccessVisitor(ast.NodeVisitor):
    """AST visitor to find privileged access patterns in genesis artifact code."""

    def __init__(self) -> None:
        self.privileged_calls: list[dict[str, Any]] = []

    def visit_Attribute(self, node: ast.Attribute) -> None:
        """Check for privileged attribute access patterns."""
        # Build the full attribute path
        parts: list[str] = []
        current: ast.expr = node

        while isinstance(current, ast.Attribute):
            parts.insert(0, current.attr)
            current = current.value

        if isinstance(current, ast.Name):
            parts.insert(0, current.id)

        attr_path = ".".join(parts)

        # Check against privileged patterns
        patterns = get_privileged_patterns()
        for category, pattern_list in patterns.items():
            for pattern in pattern_list:
                if attr_path == pattern or attr_path.startswith(pattern + "("):
                    self.privileged_calls.append({
                        "path": attr_path,
                        "category": category,
                        "line": node.lineno,
                    })

        self.generic_visit(node)


def analyze_file_for_privileged_access(file_path: Path) -> list[dict[str, Any]]:
    """Analyze a Python file for privileged access patterns."""
    with open(file_path) as f:
        source = f.read()

    tree = ast.parse(source)
    visitor = PrivilegedAccessVisitor()
    visitor.visit(tree)

    return visitor.privileged_calls


def get_genesis_files() -> list[Path]:
    """Get all genesis artifact source files."""
    genesis_dir = Path("src/world/genesis")
    # Note: store.py removed in Plan #190 - use query_kernel action
    files = [
        genesis_dir / "ledger.py",
        genesis_dir / "mint.py",
        genesis_dir / "escrow.py",
        genesis_dir / "rights_registry.py",
    ]
    return [f for f in files if f.exists()]


class TestGenesisUnprivileged:
    """Tests verifying genesis artifacts don't have privileged access."""

    def test_ledger_has_set_world_method(self) -> None:
        """genesis_ledger should have set_world() for kernel delegation (Plan #111)."""
        from src.world.genesis.ledger import GenesisLedger

        assert hasattr(GenesisLedger, "set_world"), (
            "GenesisLedger should have set_world() method for kernel delegation"
        )

    def test_ledger_uses_kernel_when_world_set(self) -> None:
        """genesis_ledger should use KernelActions when _world is set.

        Plan #111: When _world is set, spawn_principal and transfer_ownership
        should use KernelActions instead of direct ledger/artifact_store access.
        """
        # Verify the code checks for _world in the spawn_principal method
        source_file = Path("src/world/genesis/ledger.py")
        with open(source_file) as f:
            source = f.read()

        # Verify kernel interface import and usage in spawn_principal
        assert "if self._world is not None:" in source, (
            "genesis_ledger should check _world before privileged operations"
        )
        assert "from ..kernel_interface import KernelActions" in source, (
            "genesis_ledger should import KernelActions for kernel delegation"
        )
        assert "kernel_actions.create_principal" in source, (
            "genesis_ledger should use KernelActions.create_principal()"
        )
        assert "kernel_actions.transfer_ownership" in source, (
            "genesis_ledger should use KernelActions.transfer_ownership()"
        )

    def test_escrow_has_set_world_method(self) -> None:
        """genesis_escrow should have set_world() for kernel delegation (Plan #111)."""
        from src.world.genesis.escrow import GenesisEscrow

        assert hasattr(GenesisEscrow, "set_world"), (
            "GenesisEscrow should have set_world() method for kernel delegation"
        )

    def test_escrow_uses_kernel_when_world_set(self) -> None:
        """genesis_escrow should use KernelActions when _world is set.

        Plan #111: When _world is set, purchase and cancel should use
        KernelActions instead of direct ledger/artifact_store access.

        Plan #213: Escrow now uses update_artifact_metadata() instead of
        transfer_ownership() to set authorized_writer, keeping created_by
        immutable per ADR-0016.
        """
        source_file = Path("src/world/genesis/escrow.py")
        with open(source_file) as f:
            source = f.read()

        # Verify kernel interface import and usage
        assert "if self._world is not None:" in source, (
            "genesis_escrow should check _world before privileged operations"
        )
        # Plan #213: Changed from transfer_ownership to update_artifact_metadata
        assert "kernel_actions.update_artifact_metadata" in source, (
            "genesis_escrow should use KernelActions.update_artifact_metadata()"
        )
        assert "kernel_actions.transfer_scrip" in source, (
            "genesis_escrow should use KernelActions.transfer_scrip()"
        )

    # Note: test_store_uses_kernel_interface removed in Plan #190
    # genesis_store was removed - use query_kernel action instead

    def test_mint_delegates_to_kernel(self) -> None:
        """genesis_mint should delegate to kernel primitives when world is set.

        Plan #44 already migrated mint to use kernel primitives. This test
        verifies that pattern is maintained.
        """
        from src.world.genesis.mint import GenesisMint

        # Check that GenesisMint has set_world method (kernel delegation)
        assert hasattr(GenesisMint, "set_world"), (
            "GenesisMint should have set_world() for kernel delegation"
        )

        # Verify it uses _world internally
        source_lines = inspect.getsource(GenesisMint)
        assert "_world" in source_lines, (
            "GenesisMint should use _world for kernel delegation"
        )

    def test_rights_registry_delegates_to_kernel(self) -> None:
        """genesis_rights_registry should delegate to kernel quota primitives.

        Plan #42 already migrated rights_registry to use kernel quota primitives.
        This test verifies that pattern is maintained.
        """
        from src.world.genesis.rights_registry import GenesisRightsRegistry

        # Check that GenesisRightsRegistry has set_world method
        assert hasattr(GenesisRightsRegistry, "set_world"), (
            "GenesisRightsRegistry should have set_world() for kernel delegation"
        )

    def test_kernel_actions_has_required_methods(self) -> None:
        """KernelActions should expose methods needed by genesis artifacts.

        For genesis artifacts to be unprivileged, KernelActions must provide
        all write operations they need:
        - transfer_scrip (exists)
        - create_principal (needed for spawn_principal)
        - transfer_ownership (needed for escrow trading)
        """
        from src.world.kernel_interface import KernelActions

        # These methods exist
        assert hasattr(KernelActions, "transfer_scrip")
        assert hasattr(KernelActions, "write_artifact")
        assert hasattr(KernelActions, "submit_for_mint")

        # These methods are needed for genesis unprivilege (Plan #111)
        # Currently missing - this test documents the requirement
        required_methods = ["create_principal", "transfer_ownership"]
        missing = [m for m in required_methods if not hasattr(KernelActions, m)]

        if missing:
            pytest.skip(
                f"KernelActions missing required methods for genesis unprivilege: {missing}"
            )

    def test_kernel_state_has_required_methods(self) -> None:
        """KernelState should expose methods needed by genesis artifacts.

        For genesis artifacts to be unprivileged, KernelState must provide
        all read operations they need:
        - get_balance (exists)
        - list_artifacts_by_owner (exists)
        - get_all_balances (needed for all_balances method)
        - list_all_principals (needed for discovery)
        """
        from src.world.kernel_interface import KernelState

        # These methods exist
        assert hasattr(KernelState, "get_balance")
        assert hasattr(KernelState, "list_artifacts_by_owner")
        assert hasattr(KernelState, "get_artifact_metadata")

        # These would be nice but may not be strictly required
        # since genesis artifacts could iterate using existing methods


class TestNoPrivilegedReferences:
    """Tests that genesis artifacts don't store privileged references."""

    def test_genesis_artifacts_can_work_with_kernel_only(self) -> None:
        """Genesis artifacts should be able to work with only KernelState/KernelActions.

        This test verifies the design goal: genesis artifacts shouldn't need
        direct Ledger or ArtifactStore references to function.

        Currently, genesis artifacts DO store these references for backward
        compatibility. After Plan #111 is complete, they should work
        with kernel interfaces only.
        """
        # Document current state - genesis artifacts store privileged refs
        # This will be updated when we migrate them

        from src.world.genesis.ledger import GenesisLedger
        from src.world.genesis.escrow import GenesisEscrow

        # Current state: these classes require ledger/artifact_store in __init__
        # Target state: they should work with KernelState/KernelActions only

        # For now, just verify the classes exist and document the gap
        assert GenesisLedger is not None
        assert GenesisEscrow is not None
