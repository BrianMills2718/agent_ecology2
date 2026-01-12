"""Contract-based access control system.

This module defines the core interfaces for contract-based access control:
- PermissionAction: Enum of all possible actions on artifacts
- PermissionResult: Dataclass returned by permission checks
- AccessContract: Protocol that all access contracts must implement
- ExecutableContract: A contract with executable code for dynamic permission logic
- ReadOnlyLedger: A read-only wrapper for ledger access in contract code

Contracts replace inline policy dictionaries. Instead of storing access rules
directly in artifacts, artifacts reference a contract by ID. The contract's
check_permission() method determines whether an action is allowed.

This enables:
- Reusable access patterns (freeware, private, public, etc.)
- Contracts as tradeable artifacts
- Custom contracts with complex logic (DAOs, voting, time-based access)
- Decoupling access control from artifact structure
- Dynamic permission logic via executable contract code (CAP-006)

See also:
- genesis_contracts.py: The four built-in genesis contracts
- GAP-GEN-001: Implementation plan for this system
"""

# --- GOVERNANCE START (do not edit) ---
# ADR-0001: Everything is an artifact
# ADR-0003: Contracts can do anything
#
# Permission checks are the hot path - keep them fast.
# Contracts return decisions; kernel applies state changes.
# --- GOVERNANCE END ---
from __future__ import annotations

import builtins
import json
import math
import random
import signal
import time as time_module
from contextlib import contextmanager
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from types import FrameType
from typing import Any, Generator, Optional, Protocol, TYPE_CHECKING, runtime_checkable

if TYPE_CHECKING:
    from .ledger import Ledger


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


class ReadOnlyLedger:
    """Read-only wrapper around Ledger for safe use in contract code.

    Contract code needs access to ledger information (balances, etc.) but
    should NOT be able to modify balances. This wrapper exposes only the
    read methods.

    Usage in contract code:
        if not ledger.can_afford_scrip(caller, 10):
            return {"allowed": False, "reason": "Insufficient scrip", "cost": 0}
    """

    def __init__(self, ledger: "Ledger") -> None:
        """Initialize with a real Ledger instance."""
        self._ledger = ledger

    def get_scrip(self, principal_id: str) -> int:
        """Get scrip balance for a principal."""
        return self._ledger.get_scrip(principal_id)

    def can_afford_scrip(self, principal_id: str, amount: int) -> bool:
        """Check if principal can afford a scrip cost."""
        return self._ledger.can_afford_scrip(principal_id, amount)

    def get_resource(self, principal_id: str, resource: str) -> float:
        """Get balance for a specific resource."""
        return self._ledger.get_resource(principal_id, resource)

    def can_spend_resource(self, principal_id: str, resource: str, amount: float) -> bool:
        """Check if principal has enough of a resource."""
        return self._ledger.can_spend_resource(principal_id, resource, amount)

    def get_all_resources(self, principal_id: str) -> dict[str, float]:
        """Get all resource balances for a principal."""
        return self._ledger.get_all_resources(principal_id)

    def principal_exists(self, principal_id: str) -> bool:
        """Check if a principal exists in the ledger."""
        return self._ledger.principal_exists(principal_id)


class ContractExecutionError(Exception):
    """Error during contract code execution."""
    pass


class ContractTimeoutError(Exception):
    """Contract code execution timed out."""
    pass


def _contract_timeout_handler(signum: int, frame: FrameType | None) -> None:
    """Signal handler for contract execution timeout."""
    raise ContractTimeoutError("Contract execution timed out")


@contextmanager
def _contract_timeout_context(timeout: int) -> Generator[None, None, None]:
    """Context manager for contract code execution timeout.

    On Windows/platforms without signal.alarm, silently does nothing.
    Properly restores the previous signal handler on exit.

    Args:
        timeout: Timeout in seconds

    Yields:
        None - just provides timeout protection for the block

    Raises:
        ContractTimeoutError: If the block takes longer than timeout seconds
    """
    old_handler: Any = None
    try:
        old_handler = signal.signal(signal.SIGALRM, _contract_timeout_handler)
        signal.alarm(timeout)
    except (ValueError, AttributeError):
        # signal.alarm not available (Windows) - skip timeout
        pass

    try:
        yield
    finally:
        try:
            signal.alarm(0)
            if old_handler:
                signal.signal(signal.SIGALRM, old_handler)
        except (ValueError, AttributeError):
            pass


# Modules available to contract code
CONTRACT_ALLOWED_MODULES: dict[str, Any] = {
    "math": math,
    "json": json,
    "random": random,
    "time": time_module,
}


@dataclass
class ExecutableContract:
    """A contract with executable code for dynamic permission logic.

    Unlike genesis contracts which have hardcoded logic, executable contracts
    run user-provided code in a sandboxed environment to determine permissions.

    The code must define a check_permission function with signature:
        def check_permission(caller, action, target, context, ledger):
            # Return dict with: allowed (bool), reason (str), cost (int)
            return {"allowed": True, "reason": "Access granted", "cost": 0}

    Contract code has access to:
        - caller: str - Principal requesting access
        - action: str - The action being attempted (read, write, invoke, etc.)
        - target: str - Artifact ID being accessed
        - context: dict - Additional context (owner, artifact_type, tick, etc.)
        - ledger: ReadOnlyLedger - Read-only ledger for balance checks

    Available modules in contract code:
        - math, json, random, time

    Example:
        ExecutableContract(
            contract_id="pay_per_use",
            code='''
def check_permission(caller, action, target, context, ledger):
    price = 10
    if not ledger.can_afford_scrip(caller, price):
        return {"allowed": False, "reason": "Insufficient scrip", "cost": 0}
    return {"allowed": True, "reason": "Paid access", "cost": price}
'''
        )

    Attributes:
        contract_id: Unique identifier for this contract
        contract_type: Always "executable" for this contract type
        code: Python code defining check_permission function
        timeout: Maximum execution time in seconds (default: 1)
    """

    contract_id: str
    code: str
    contract_type: str = "executable"
    timeout: int = 1  # 1 second default timeout for contract execution

    def _validate_code(self) -> tuple[bool, str]:
        """Validate that code can be compiled and has check_permission function.

        Returns:
            (valid, error_message)
        """
        if not self.code or not self.code.strip():
            return False, "Empty contract code"

        # Check for check_permission function definition
        if "def check_permission(" not in self.code:
            return False, "Contract code must define a check_permission() function"

        # Try to compile
        try:
            compile(self.code, '<contract_code>', 'exec')
            return True, ""
        except SyntaxError as e:
            return False, f"Syntax error in contract code: {e}"
        except Exception as e:
            return False, f"Contract code compilation failed: {e}"

    def _execute_contract_code(
        self,
        caller: str,
        action: PermissionAction,
        target: str,
        context: Optional[dict[str, object]],
        ledger: Optional["Ledger"],
    ) -> PermissionResult:
        """Execute the contract code in a sandboxed environment.

        Args:
            caller: Principal requesting access
            action: Action being attempted
            target: Artifact being accessed
            context: Additional context
            ledger: Ledger instance (will be wrapped as read-only)

        Returns:
            PermissionResult from the contract code execution
        """
        # Validate code first
        valid, error = self._validate_code()
        if not valid:
            return PermissionResult(
                allowed=False,
                reason=f"Invalid contract code: {error}"
            )

        # Compile the code
        try:
            compiled = compile(self.code, '<contract_code>', 'exec')
        except Exception as e:
            return PermissionResult(
                allowed=False,
                reason=f"Contract compilation failed: {e}"
            )

        # Build controlled globals with safe builtins
        controlled_builtins = dict(vars(builtins))
        # Remove potentially dangerous builtins
        dangerous_builtins = [
            'open', 'exec', 'eval', 'compile', '__import__',
            'input', 'breakpoint', 'exit', 'quit'
        ]
        for name in dangerous_builtins:
            controlled_builtins.pop(name, None)

        controlled_globals: dict[str, Any] = {
            "__builtins__": controlled_builtins,
            "__name__": "__contract__",
        }

        # Add allowed modules
        for name, module in CONTRACT_ALLOWED_MODULES.items():
            controlled_globals[name] = module

        # Execute the code definition (creates the check_permission function)
        try:
            with _contract_timeout_context(self.timeout):
                exec(compiled, controlled_globals)
        except ContractTimeoutError:
            return PermissionResult(
                allowed=False,
                reason="Contract code definition timed out"
            )
        except Exception as e:
            return PermissionResult(
                allowed=False,
                reason=f"Contract code execution error: {type(e).__name__}: {e}"
            )

        # Check that check_permission was defined
        if "check_permission" not in controlled_globals:
            return PermissionResult(
                allowed=False,
                reason="Contract code did not define check_permission() function"
            )

        check_func = controlled_globals["check_permission"]
        if not callable(check_func):
            return PermissionResult(
                allowed=False,
                reason="check_permission is not callable"
            )

        # Prepare arguments for check_permission
        action_str = action.value if isinstance(action, PermissionAction) else str(action)
        ctx = context if context else {}
        readonly_ledger = ReadOnlyLedger(ledger) if ledger else None

        # Call check_permission with contract context
        try:
            with _contract_timeout_context(self.timeout):
                result = check_func(caller, action_str, target, ctx, readonly_ledger)
        except ContractTimeoutError:
            return PermissionResult(
                allowed=False,
                reason="Contract check_permission execution timed out"
            )
        except Exception as e:
            return PermissionResult(
                allowed=False,
                reason=f"Contract check_permission error: {type(e).__name__}: {e}"
            )

        # Validate and convert result
        if not isinstance(result, dict):
            return PermissionResult(
                allowed=False,
                reason=f"Contract returned invalid result type: {type(result).__name__}"
            )

        allowed = result.get("allowed", False)
        reason = result.get("reason", "No reason provided")
        cost = result.get("cost", 0)

        # Validate types
        if not isinstance(allowed, bool):
            return PermissionResult(
                allowed=False,
                reason=f"Contract 'allowed' must be bool, got {type(allowed).__name__}"
            )
        if not isinstance(reason, str):
            reason = str(reason)
        if not isinstance(cost, int):
            try:
                cost = int(cost)
            except (TypeError, ValueError):
                cost = 0

        return PermissionResult(
            allowed=allowed,
            reason=reason,
            cost=max(0, cost),  # Ensure non-negative
        )

    def check_permission(
        self,
        caller: str,
        action: PermissionAction,
        target: str,
        context: Optional[dict[str, object]] = None,
        ledger: Optional["Ledger"] = None,
    ) -> PermissionResult:
        """Check permission by executing the contract code.

        This method executes the contract's code in a sandboxed environment
        and returns the result.

        Args:
            caller: Principal requesting access
            action: Action being attempted
            target: Artifact being accessed
            context: Additional context about the access attempt
            ledger: Optional ledger for balance checks (will be read-only)

        Returns:
            PermissionResult from the contract code execution
        """
        return self._execute_contract_code(caller, action, target, context, ledger)
