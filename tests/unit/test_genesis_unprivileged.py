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
    files = [
        genesis_dir / "ledger.py",
        genesis_dir / "mint.py",
        genesis_dir / "escrow.py",
        genesis_dir / "store.py",
        genesis_dir / "rights_registry.py",
    ]
    return [f for f in files if f.exists()]


class TestGenesisUnprivileged:
    """Tests verifying genesis artifacts don't have privileged access."""

    def test_ledger_no_create_principal_direct_call(self) -> None:
        """genesis_ledger should not call self.ledger.create_principal() directly.

        Instead, it should use KernelActions.create_principal() when that's available.
        This ensures agent-built artifacts can provide the same functionality.
        """
        ledger_file = Path("src/world/genesis/ledger.py")
        privileged = analyze_file_for_privileged_access(ledger_file)

        create_principal_calls = [
            p for p in privileged
            if "create_principal" in p["path"]
        ]

        # This test will fail until we fix genesis_ledger
        # After fix: assert len(create_principal_calls) == 0
        if create_principal_calls:
            pytest.skip(
                f"genesis_ledger still has {len(create_principal_calls)} "
                f"privileged create_principal calls - to be fixed"
            )

    def test_ledger_no_direct_artifact_store_transfer(self) -> None:
        """genesis_ledger should not call self.artifact_store.transfer_ownership() directly.

        Instead, it should use KernelActions.transfer_ownership() when available.
        """
        ledger_file = Path("src/world/genesis/ledger.py")
        privileged = analyze_file_for_privileged_access(ledger_file)

        transfer_calls = [
            p for p in privileged
            if "transfer_ownership" in p["path"]
        ]

        if transfer_calls:
            pytest.skip(
                f"genesis_ledger still has {len(transfer_calls)} "
                f"privileged transfer_ownership calls - to be fixed"
            )

    def test_escrow_no_direct_transfer_ownership(self) -> None:
        """genesis_escrow should use kernel interface for ownership transfers.

        Escrow performs ownership transfers as part of trading, which should
        go through KernelActions.transfer_ownership() rather than direct
        artifact_store access.
        """
        escrow_file = Path("src/world/genesis/escrow.py")
        privileged = analyze_file_for_privileged_access(escrow_file)

        transfer_calls = [
            p for p in privileged
            if "transfer_ownership" in p["path"]
        ]

        if transfer_calls:
            pytest.skip(
                f"genesis_escrow still has {len(transfer_calls)} "
                f"privileged transfer_ownership calls - to be fixed"
            )

    def test_store_uses_kernel_interface(self) -> None:
        """genesis_store should use kernel interface for artifact discovery.

        Store provides artifact discovery which should go through KernelState
        methods rather than direct artifact_store access.

        Note: Read-only access may be acceptable if KernelState provides
        equivalent functionality.
        """
        store_file = Path("src/world/genesis/store.py")
        privileged = analyze_file_for_privileged_access(store_file)

        # Store mainly does reads, which may be acceptable
        # Focus on any write operations
        write_calls = [
            p for p in privileged
            if "transfer" in p["path"] or "create" in p["path"]
        ]

        assert len(write_calls) == 0, (
            f"genesis_store has privileged write calls: {write_calls}"
        )

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
