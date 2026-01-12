"""Contract-based access control system.

This module defines the core interfaces for contract-based access control:
- PermissionAction: Enum of all possible actions on artifacts
- PermissionResult: Dataclass returned by permission checks
- AccessContract: Protocol that all access contracts must implement

Contracts replace inline policy dictionaries. Instead of storing access rules
directly in artifacts, artifacts reference a contract by ID. The contract's
check_permission() method determines whether an action is allowed.

This enables:
- Reusable access patterns (freeware, private, public, etc.)
- Contracts as tradeable artifacts
- Custom contracts with complex logic (DAOs, voting, time-based access)
- Decoupling access control from artifact structure

See also:
- genesis_contracts.py: The four built-in genesis contracts
- GAP-GEN-001: Implementation plan for this system
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Optional, Protocol, runtime_checkable


class PermissionAction(str, Enum):
    """Actions that can be performed on artifacts.

    All artifact operations map to one of these actions for permission checking.
    Using str, Enum allows JSON serialization and string comparison.
    """

    READ = "read"
    """Read the artifact's content."""

    WRITE = "write"
    """Modify the artifact's content or metadata."""

    EXECUTE = "execute"
    """Execute artifact code (for executable artifacts)."""

    INVOKE = "invoke"
    """Invoke an artifact's service interface."""

    DELETE = "delete"
    """Delete the artifact entirely."""

    TRANSFER = "transfer"
    """Transfer ownership to another principal."""


@dataclass
class PermissionResult:
    """Result of a permission check.

    Returned by AccessContract.check_permission() to indicate whether
    an action is allowed and provide additional context.

    Attributes:
        allowed: Whether the action is permitted.
        reason: Human-readable explanation of the decision.
        cost: Scrip cost to perform the action (0 = free).
        conditions: Optional additional conditions or metadata.
    """

    allowed: bool
    reason: str
    cost: int = 0
    conditions: Optional[dict[str, object]] = field(default=None)

    def __post_init__(self) -> None:
        """Validate the result after initialization."""
        if self.cost < 0:
            raise ValueError(f"cost cannot be negative: {self.cost}")


# Use runtime_checkable so we can use isinstance() checks
@runtime_checkable
class AccessContract(Protocol):
    """Protocol for access control contracts.

    All access contracts must implement this interface. Contracts are
    invoked by the executor when checking permissions on artifact access.

    Contracts can be:
    - Genesis contracts (built-in, immutable)
    - Custom contracts (agent-created, artifact-based)

    The check_permission method receives full context about the access
    attempt and returns a PermissionResult indicating the decision.
    """

    @property
    def contract_id(self) -> str:
        """Unique identifier for this contract.

        For genesis contracts, this is a fixed string like 'genesis_contract_freeware'.
        For custom contracts, this is the artifact ID of the contract artifact.
        """
        ...

    @property
    def contract_type(self) -> str:
        """Contract type identifier.

        Standard types: 'freeware', 'self_owned', 'private', 'public', 'custom'.
        Custom contracts may define their own types.
        """
        ...

    def check_permission(
        self,
        caller: str,
        action: PermissionAction,
        target: str,
        context: Optional[dict[str, object]] = None,
    ) -> PermissionResult:
        """Check if caller has permission to perform action on target.

        This is the core method that determines access. It receives full
        context about the access attempt and returns a decision.

        Args:
            caller: The principal (agent/artifact) requesting access.
                   This is the principal_id of whoever initiated the action.
            action: The action being attempted (read, write, invoke, etc.).
            target: The artifact_id being accessed.
            context: Optional additional context about the access attempt.
                    Standard context keys:
                    - 'owner': Current owner of the target artifact
                    - 'artifact_type': Type of the target artifact
                    - 'caller_type': Type of the calling principal
                    - 'tick': Current simulation tick
                    - Additional keys may be added by specific contracts

        Returns:
            PermissionResult with:
            - allowed: True if access is permitted, False otherwise
            - reason: Explanation of the decision
            - cost: Optional scrip cost for the action
            - conditions: Optional additional conditions
        """
        ...
