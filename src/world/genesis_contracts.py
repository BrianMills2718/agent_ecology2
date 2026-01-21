"""Genesis contracts - built-in access control contracts.

This module provides the four genesis contracts that are available at world
initialization. These contracts cover the most common access patterns:

- FreewareContract: Anyone can read/execute/invoke, only owner can modify
- SelfOwnedContract: Only the artifact itself (or owner) can access
- PrivateContract: Only owner can access
- PublicContract: Anyone can do anything (true commons)

Genesis contracts are immutable and cannot be modified. They are referenced
by their contract_id (e.g., 'genesis_contract_freeware') and are available
without needing to be created as artifacts.

Custom contracts can be created by agents as executable artifacts that
implement the same check_permission interface.

See also:
- contracts.py: Core interfaces (PermissionAction, PermissionResult, AccessContract)
- GAP-GEN-001: Implementation plan for the contract system
"""

# --- GOVERNANCE START (do not edit) ---
# ADR-0001: Everything is an artifact
# ADR-0003: Contracts can do anything
#
# Four built-in contracts: freeware, self_owned, private, public.
# These are Python classes, not artifacts (current implementation).
# --- GOVERNANCE END ---
from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from .contracts import AccessContract, PermissionAction, PermissionResult


@dataclass
class FreewareContract:
    """Freeware access contract.

    Access rules:
    - READ: Anyone can read
    - EXECUTE: Anyone can execute
    - INVOKE: Anyone can invoke
    - WRITE: Only owner can write
    - DELETE: Only owner can delete
    - TRANSFER: Only owner can transfer

    This is the default contract for shared artifacts. It allows broad
    read access while preserving owner control over modifications.

    The contract name comes from the software licensing world - like
    freeware software, anyone can use it but only the author can change it.
    """

    contract_id: str = "genesis_contract_freeware"
    contract_type: str = "freeware"

    def check_permission(
        self,
        caller: str,
        action: PermissionAction,
        target: str,
        context: Optional[dict[str, object]] = None,
    ) -> PermissionResult:
        """Check permission for freeware access pattern.

        Args:
            caller: Principal requesting access
            action: Action being attempted
            target: Artifact being accessed
            context: Must contain 'created_by' key for write/delete/transfer checks

        Returns:
            PermissionResult with decision
        """
        # ADR-0019: context uses target_created_by (with fallback for legacy)
        owner = context.get("target_created_by") or context.get("created_by") if context else None

        # Open access actions - anyone can perform these
        if action in (
            PermissionAction.READ,
            PermissionAction.EXECUTE,
            PermissionAction.INVOKE,
        ):
            return PermissionResult(allowed=True, reason="freeware: open access")

        # Owner-only actions (ADR-0019: includes EDIT)
        if action in (
            PermissionAction.WRITE,
            PermissionAction.EDIT,
            PermissionAction.DELETE,
            PermissionAction.TRANSFER,
        ):
            if caller == owner:
                return PermissionResult(allowed=True, reason="freeware: owner access")
            return PermissionResult(
                allowed=False, reason="freeware: only owner can modify"
            )

        # Unknown action - fail closed
        return PermissionResult(allowed=False, reason="freeware: unknown action")


@dataclass
class SelfOwnedContract:
    """Self-owned access contract.

    Access rules:
    - Self-access: The artifact can access itself
    - Owner-access: The owner can access the artifact
    - All others: Denied

    This is used for agent memory, private state, and artifacts that
    should only be accessible to their creator or themselves.

    "Self-access" means the caller's principal_id matches the target's
    artifact_id - useful when artifacts need to read/modify themselves
    during execution.
    """

    contract_id: str = "genesis_contract_self_owned"
    contract_type: str = "self_owned"

    def check_permission(
        self,
        caller: str,
        action: PermissionAction,
        target: str,
        context: Optional[dict[str, object]] = None,
    ) -> PermissionResult:
        """Check permission for self-owned access pattern.

        Args:
            caller: Principal requesting access
            action: Action being attempted
            target: Artifact being accessed
            context: Must contain 'target_created_by' key (ADR-0019)

        Returns:
            PermissionResult with decision
        """
        # ADR-0019: context uses target_created_by (with fallback for legacy)
        owner = context.get("target_created_by") or context.get("created_by") if context else None

        # Self-access: artifact accessing itself
        if caller == target:
            return PermissionResult(allowed=True, reason="self_owned: self access")

        # Owner access
        if caller == owner:
            return PermissionResult(allowed=True, reason="self_owned: owner access")

        # All others denied
        return PermissionResult(allowed=False, reason="self_owned: access denied")


@dataclass
class PrivateContract:
    """Private access contract.

    Access rules:
    - Owner: Full access to all actions
    - All others: Denied

    This is the most restrictive contract. Only the owner can perform
    any action. Used for sensitive artifacts that should never be
    shared, even with the artifact itself.

    Unlike SelfOwnedContract, this does NOT allow self-access. An artifact
    with a private contract cannot even access itself - only the owner can.
    """

    contract_id: str = "genesis_contract_private"
    contract_type: str = "private"

    def check_permission(
        self,
        caller: str,
        action: PermissionAction,
        target: str,
        context: Optional[dict[str, object]] = None,
    ) -> PermissionResult:
        """Check permission for private access pattern.

        Args:
            caller: Principal requesting access
            action: Action being attempted
            target: Artifact being accessed
            context: Must contain 'target_created_by' key (ADR-0019)

        Returns:
            PermissionResult with decision
        """
        # ADR-0019: context uses target_created_by (with fallback for legacy)
        owner = context.get("target_created_by") or context.get("created_by") if context else None

        # Only owner has access
        if caller == owner:
            return PermissionResult(allowed=True, reason="private: owner access")

        # All others denied (including the artifact itself)
        return PermissionResult(allowed=False, reason="private: access denied")


@dataclass
class PublicContract:
    """Public access contract.

    Access rules:
    - ALL actions: Anyone can perform any action

    This is a true commons - completely open access. Anyone can read,
    write, execute, invoke, delete, or transfer.

    Use with caution! This allows anyone to modify or delete the artifact.
    Appropriate for:
    - Shared workspaces
    - Collaborative artifacts
    - Public resources that should be freely modifiable

    WARNING: An artifact with public contract can be deleted or transferred
    by anyone. If you want open read/execute but protected ownership,
    use freeware instead.
    """

    contract_id: str = "genesis_contract_public"
    contract_type: str = "public"

    def check_permission(
        self,
        caller: str,
        action: PermissionAction,
        target: str,
        context: Optional[dict[str, object]] = None,
    ) -> PermissionResult:
        """Check permission for public access pattern.

        Args:
            caller: Principal requesting access
            action: Action being attempted (ignored - all allowed)
            target: Artifact being accessed (ignored - all allowed)
            context: Optional context (ignored - all allowed)

        Returns:
            PermissionResult allowing the action
        """
        return PermissionResult(allowed=True, reason="public: open access")


# Registry of genesis contracts - singleton instances
GENESIS_CONTRACTS: dict[str, AccessContract] = {
    "freeware": FreewareContract(),
    "self_owned": SelfOwnedContract(),
    "private": PrivateContract(),
    "public": PublicContract(),
}


def get_genesis_contract(contract_type: str) -> AccessContract:
    """Get a genesis contract by type.

    Args:
        contract_type: One of 'freeware', 'self_owned', 'private', 'public'

    Returns:
        The corresponding AccessContract instance

    Raises:
        ValueError: If contract_type is not a valid genesis contract type
    """
    if contract_type not in GENESIS_CONTRACTS:
        valid_types = ", ".join(sorted(GENESIS_CONTRACTS.keys()))
        raise ValueError(
            f"Unknown genesis contract type: '{contract_type}'. "
            f"Valid types: {valid_types}"
        )
    return GENESIS_CONTRACTS[contract_type]


def get_contract_by_id(contract_id: str) -> AccessContract | None:
    """Get a genesis contract by its full contract_id.

    Args:
        contract_id: The contract's unique identifier
                    (e.g., 'genesis_contract_freeware')

    Returns:
        The corresponding AccessContract instance, or None if not found
    """
    for contract in GENESIS_CONTRACTS.values():
        if contract.contract_id == contract_id:
            return contract
    return None


def list_genesis_contracts() -> list[str]:
    """List all available genesis contract types.

    Returns:
        List of contract type names (e.g., ['freeware', 'private', ...])
    """
    return list(GENESIS_CONTRACTS.keys())
