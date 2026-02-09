"""Kernel contracts - built-in access control contracts.

This module provides the five kernel contracts that are available at world
initialization. These contracts cover the most common access patterns:

- FreewareContract: Anyone can read/invoke, only authorized_writer can modify
- TransferableFreewareContract: Same as freeware (both use authorized_writer)
- SelfOwnedContract: Only the artifact itself (or authorized_principal) can access
- PrivateContract: Only authorized_principal can access
- PublicContract: Anyone can do anything (true commons)

Authorization is determined by metadata fields (authorized_writer,
authorized_principal), NOT by created_by. created_by is purely informational
metadata, like created_at. See ADR-0028.

Kernel contracts are immutable and cannot be modified. They are referenced
by their contract_id (e.g., 'kernel_contract_freeware') and are available
without needing to be created as artifacts.

Custom contracts can be created by agents as executable artifacts that
implement the same check_permission interface.

See also:
- contracts.py: Core interfaces (PermissionAction, PermissionResult, AccessContract)
- ADR-0028: created_by is purely informational
"""

# --- GOVERNANCE START (do not edit) ---
# ADR-0001: Everything is an artifact
# ADR-0003: Contracts can do anything
# ADR-0028: created_by is purely informational
#
# Five built-in contracts: freeware, transferable_freeware, self_owned, private, public.
# These are Python classes, not artifacts (current implementation).
# Authorization uses metadata fields (authorized_writer, authorized_principal),
# NEVER created_by. See ADR-0028.
# --- GOVERNANCE END ---
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Optional

from .constants import (
    KERNEL_CONTRACT_FREEWARE,
    KERNEL_CONTRACT_TRANSFERABLE_FREEWARE,
    KERNEL_CONTRACT_SELF_OWNED,
    KERNEL_CONTRACT_PRIVATE,
    KERNEL_CONTRACT_PUBLIC,
)
from .contracts import AccessContract, PermissionAction, PermissionResult


def _get_metadata_field(context: Optional[dict[str, object]], field: str) -> Any:
    """Extract a field from target_metadata in the permission context.

    Returns None if context is missing, target_metadata is missing/not a dict,
    or the field is not present.
    """
    if not context:
        return None
    target_metadata = context.get("target_metadata")
    if isinstance(target_metadata, dict):
        return target_metadata.get(field)
    return None


@dataclass
class FreewareContract:
    """Freeware access contract (ADR-0019, ADR-0028).

    Access rules:
    - READ, INVOKE: Anyone can access
    - WRITE, EDIT, DELETE: Only metadata["authorized_writer"] can modify

    Authorization is based on the mutable metadata["authorized_writer"] field,
    NOT on created_by. This field is auto-populated from created_by at artifact
    creation time, but can be changed afterward (e.g., via escrow transfer).

    If no authorized_writer is set in metadata, write access is denied (fail closed).
    """

    contract_id: str = KERNEL_CONTRACT_FREEWARE
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
            context: Should contain 'target_metadata' with 'authorized_writer'

        Returns:
            PermissionResult with decision
        """
        authorized_writer = _get_metadata_field(context, "authorized_writer")

        # Open access actions - anyone can perform these
        if action in (PermissionAction.READ, PermissionAction.INVOKE):
            return PermissionResult(
                allowed=True,
                reason="freeware: open access",
                scrip_recipient=authorized_writer,
            )

        # Authorized-writer-only actions
        if action in (PermissionAction.WRITE, PermissionAction.EDIT, PermissionAction.DELETE):
            if authorized_writer is None:
                return PermissionResult(
                    allowed=False,
                    reason="freeware: no authorized_writer in metadata",
                )
            if caller == authorized_writer:
                return PermissionResult(
                    allowed=True,
                    reason="freeware: authorized writer",
                    scrip_recipient=authorized_writer,
                )
            return PermissionResult(
                allowed=False, reason="freeware: only authorized_writer can modify"
            )

        # Unknown action - fail closed
        return PermissionResult(allowed=False, reason="freeware: unknown action")


@dataclass
class TransferableFreewareContract:
    """Transferable freeware access contract (Plan #213, ADR-0028).

    Write permission is based on metadata["authorized_writer"]. This enables
    artifact trading via escrow:

    1. Creator's authorized_writer is auto-set at creation
    2. When sold, escrow updates metadata["authorized_writer"] = buyer
    3. Buyer can now write (this contract checks authorized_writer)

    Access rules:
    - READ, INVOKE: Anyone can access
    - WRITE, EDIT, DELETE: Only authorized_writer can modify

    If no authorized_writer is set in metadata, write access is denied (fail closed).

    Note: Both freeware and transferable_freeware now use the same authorization
    mechanism (authorized_writer). The distinction is semantic — transferable_freeware
    signals that the artifact is intended to be traded.
    """

    contract_id: str = KERNEL_CONTRACT_TRANSFERABLE_FREEWARE
    contract_type: str = "transferable_freeware"

    def check_permission(
        self,
        caller: str,
        action: PermissionAction,
        target: str,
        context: Optional[dict[str, object]] = None,
    ) -> PermissionResult:
        """Check permission for transferable freeware access pattern.

        Args:
            caller: Principal requesting access
            action: Action being attempted
            target: Artifact being accessed
            context: Should contain 'target_metadata' with 'authorized_writer'

        Returns:
            PermissionResult with decision
        """
        authorized_writer = _get_metadata_field(context, "authorized_writer")

        # Open access actions - anyone can perform these
        if action in (PermissionAction.READ, PermissionAction.INVOKE):
            return PermissionResult(
                allowed=True,
                reason="transferable_freeware: open access",
                scrip_recipient=authorized_writer,
            )

        # Authorized-writer-only actions
        if action in (PermissionAction.WRITE, PermissionAction.EDIT, PermissionAction.DELETE):
            if authorized_writer is None:
                return PermissionResult(
                    allowed=False,
                    reason="transferable_freeware: no authorized_writer in metadata",
                )
            if caller == authorized_writer:
                return PermissionResult(
                    allowed=True,
                    reason="transferable_freeware: authorized writer",
                    scrip_recipient=authorized_writer,
                )
            return PermissionResult(
                allowed=False,
                reason="transferable_freeware: only authorized_writer can modify",
            )

        # Unknown action - fail closed
        return PermissionResult(allowed=False, reason="transferable_freeware: unknown action")


@dataclass
class SelfOwnedContract:
    """Self-owned access contract (ADR-0028).

    Access rules:
    - Self-access: The artifact can access itself (caller == target)
    - Principal-access: metadata["authorized_principal"] can access
    - All others: Denied

    This is used for agent memory, private state, and artifacts that
    should only be accessible to their authorized principal or themselves.

    "Self-access" means the caller's principal_id matches the target's
    artifact_id - useful when artifacts need to read/modify themselves
    during execution.
    """

    contract_id: str = KERNEL_CONTRACT_SELF_OWNED
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
            context: Should contain 'target_metadata' with 'authorized_principal'

        Returns:
            PermissionResult with decision
        """
        authorized_principal = _get_metadata_field(context, "authorized_principal")

        # Self-access: artifact accessing itself
        if caller == target:
            return PermissionResult(
                allowed=True,
                reason="self_owned: self access",
                scrip_recipient=authorized_principal,
            )

        # Authorized principal access
        if authorized_principal is not None and caller == authorized_principal:
            return PermissionResult(
                allowed=True,
                reason="self_owned: authorized principal",
                scrip_recipient=authorized_principal,
            )

        # All others denied
        return PermissionResult(allowed=False, reason="self_owned: access denied")


@dataclass
class PrivateContract:
    """Private access contract (ADR-0028).

    Access rules:
    - Authorized principal: Full access to all actions
    - All others: Denied

    This is the most restrictive contract. Only the authorized principal
    can perform any action. Used for sensitive artifacts that should never
    be shared, even with the artifact itself.

    Unlike SelfOwnedContract, this does NOT allow self-access. An artifact
    with a private contract cannot even access itself - only the authorized
    principal can.
    """

    contract_id: str = KERNEL_CONTRACT_PRIVATE
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
            context: Should contain 'target_metadata' with 'authorized_principal'

        Returns:
            PermissionResult with decision
        """
        authorized_principal = _get_metadata_field(context, "authorized_principal")

        # Only authorized principal has access
        if authorized_principal is not None and caller == authorized_principal:
            return PermissionResult(
                allowed=True,
                reason="private: authorized principal",
                scrip_recipient=authorized_principal,
            )

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

    contract_id: str = KERNEL_CONTRACT_PUBLIC
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


# Registry of kernel contracts - singleton instances
KERNEL_CONTRACTS: dict[str, AccessContract] = {
    "freeware": FreewareContract(),
    "transferable_freeware": TransferableFreewareContract(),
    "self_owned": SelfOwnedContract(),
    "private": PrivateContract(),
    "public": PublicContract(),
}


def get_kernel_contract(contract_type: str) -> AccessContract:
    """Get a kernel contract by type.

    Args:
        contract_type: One of 'freeware', 'self_owned', 'private', 'public'

    Returns:
        The corresponding AccessContract instance

    Raises:
        ValueError: If contract_type is not a valid kernel contract type
    """
    if contract_type not in KERNEL_CONTRACTS:
        valid_types = ", ".join(sorted(KERNEL_CONTRACTS.keys()))
        raise ValueError(
            f"Unknown kernel contract type: '{contract_type}'. "
            f"Valid types: {valid_types}"
        )
    return KERNEL_CONTRACTS[contract_type]


def get_contract_by_id(contract_id: str) -> AccessContract | None:
    """Get a kernel contract by its full contract_id.

    Args:
        contract_id: The contract's unique identifier
                    (e.g., 'kernel_contract_freeware')

    Returns:
        The corresponding AccessContract instance, or None if not found
    """
    for contract in KERNEL_CONTRACTS.values():
        if contract.contract_id == contract_id:
            return contract
    return None


def list_kernel_contracts() -> list[str]:
    """List all available kernel contract types.

    Returns:
        List of contract type names (e.g., ['freeware', 'private', ...])
    """
    return list(KERNEL_CONTRACTS.keys())
