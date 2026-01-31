"""Invoke Handler - Logic for artifact-to-artifact invocation.

Plan #181: Extracted from executor.py to reduce file size and
separate invoke handling from core execution.

This module handles:
- invoke() function logic for nested artifact calls
- Permission checking for invocations
- Cost/payment handling for paid artifacts
- Recursion depth limiting
"""

from __future__ import annotations

import logging
from typing import Any, TYPE_CHECKING

if TYPE_CHECKING:
    from .ledger import Ledger
    from .artifacts import Artifact, ArtifactStore
    from .world import World
    from .contracts import PermissionCache, AccessContract, ExecutableContract

from .contracts import PermissionResult


# Type alias for invoke result
class InvokeResult:
    """Result from an invoke() call within artifact execution.

    Note: This is a class rather than TypedDict for easier construction
    in the extracted module. Compatible with the TypedDict version in executor.py.
    """
    def __init__(
        self,
        success: bool,
        result: Any,
        error: str,
        price_paid: int,
    ):
        self.success = success
        self.result = result
        self.error = error
        self.price_paid = price_paid

    def to_dict(self) -> dict[str, Any]:
        """Convert to dict for compatibility with existing code."""
        return {
            "success": self.success,
            "result": self.result,
            "error": self.error,
            "price_paid": self.price_paid,
        }


def execute_invoke(
    target_artifact_id: str,
    invoke_args: tuple[Any, ...],
    caller_id: str,
    artifact_id: str | None,
    ledger: "Ledger",
    artifact_store: "ArtifactStore",
    current_depth: int,
    max_depth: int,
    world: "World | None",
    check_permission_func: Any,
    check_permission_via_contract_func: Any,
    execute_with_invoke_func: Any,
    use_contracts: bool = True,
) -> dict[str, Any]:
    """Execute an invoke call from one artifact to another.

    This function handles the core logic for artifact-to-artifact invocation,
    including permission checks, cost handling, and recursive execution.

    Args:
        target_artifact_id: ID of artifact to invoke
        invoke_args: Arguments to pass to the artifact's run()
        caller_id: ID of the original caller (pays for invocations)
        artifact_id: ID of the invoking artifact (immediate caller)
        ledger: Ledger instance for transfers
        artifact_store: ArtifactStore for looking up artifacts
        current_depth: Current recursion depth
        max_depth: Maximum allowed recursion depth
        world: World instance for kernel interface injection
        check_permission_func: Function to check permissions (from executor)
        check_permission_via_contract_func: Function to check contract permissions
        execute_with_invoke_func: Function to recursively execute (from executor)
        use_contracts: Whether contract-based permissions are enabled

    Returns:
        Dict with success, result, error, and price_paid
    """
    # Check recursion depth
    if current_depth >= max_depth:
        return {
            "success": False,
            "result": None,
            "error": f"Max invoke depth ({max_depth}) exceeded",
            "price_paid": 0
        }

    # Look up the target artifact
    target = artifact_store.get(target_artifact_id)
    if not target:
        return {
            "success": False,
            "result": None,
            "error": f"Artifact {target_artifact_id} not found",
            "price_paid": 0
        }

    if not target.executable:
        # Plan #160: Suggest alternative - use read_artifact for data/config artifacts
        return {
            "success": False,
            "result": None,
            "error": (
                f"Artifact {target_artifact_id} is not executable (it's a data artifact). "
                f"Use kernel_actions.read_artifact('{target_artifact_id}') to read its content."
            ),
            "price_paid": 0
        }

    # Plan #234: Detect handle_request on target (ADR-0024)
    target_has_handle_request = (
        target.genesis_methods is None
        and target.code
        and "def handle_request(" in target.code
    )

    # Check invoke permission using IMMEDIATE caller (this artifact)
    # ADR-0019: When A→B→C, C's contract sees B as caller, not A
    # artifact_id is the current artifact (immediate caller)
    # caller_id is the original agent (used for billing, not permission)
    immediate_caller = artifact_id if artifact_id else caller_id

    # Plan #234: Skip kernel permission check for handle_request targets.
    # The target artifact handles its own access control.
    if not target_has_handle_request:
        # ADR-0019: pass method ("run") and args in context
        allowed, reason = check_permission_func(
            immediate_caller, "invoke", target, method="run", args=list(invoke_args)
        )
        if not allowed:
            return {
                "success": False,
                "result": None,
                "error": f"Caller {immediate_caller} not allowed to invoke {target_artifact_id}: {reason}",
                "price_paid": 0
            }

    # Determine price: contract cost (if any) + artifact price
    price = target.price
    created_by = target.created_by

    # If using contracts and target has a contract, check for additional cost
    contract_cost = 0
    cost_payer = caller_id  # Default: original caller pays (billing uses original)
    has_contract = hasattr(target, "access_contract_id") and target.access_contract_id is not None
    if use_contracts and has_contract:
        # Use immediate caller for permission/cost check per ADR-0019
        perm_result = check_permission_via_contract_func(
            immediate_caller, "invoke", target, method="run", args=list(invoke_args)
        )
        contract_cost = perm_result.cost
        # Contract can specify alternate payer (Plan #140)
        if perm_result.payer is not None:
            cost_payer = perm_result.payer

    total_cost = price + contract_cost
    if total_cost > 0 and not ledger.can_afford_scrip(cost_payer, total_cost):
        return {
            "success": False,
            "result": None,
            "error": f"Payer {cost_payer} has insufficient scrip for total cost {total_cost}",
            "price_paid": 0
        }

    # Recursively execute the target artifact
    # Plan #234: Use correct entry point for handle_request targets
    nested_result = execute_with_invoke_func(
        code=target.code,
        args=list(invoke_args),
        caller_id=caller_id,
        artifact_id=target_artifact_id,
        ledger=ledger,
        artifact_store=artifact_store,
        current_depth=current_depth + 1,
        max_depth=max_depth,
        world=world,
        entry_point="handle_request" if target_has_handle_request else "run",
        method_name="invoke" if target_has_handle_request else None,
    )

    if nested_result.get("success"):
        # Pay total cost to artifact creator (only on success)
        # Plan #140: Use contract-specified payer instead of hardcoded caller
        if total_cost > 0 and created_by != cost_payer:
            ledger.deduct_scrip(cost_payer, total_cost)
            ledger.credit_scrip(created_by, total_cost)

        return {
            "success": True,
            "result": nested_result.get("result"),
            "error": "",
            "price_paid": total_cost
        }
    else:
        return {
            "success": False,
            "result": None,
            "error": nested_result.get("error", "Unknown error"),
            "price_paid": 0
        }


def create_invoke_function(
    caller_id: str,
    artifact_id: str | None,
    ledger: "Ledger",
    artifact_store: "ArtifactStore",
    current_depth: int,
    max_depth: int,
    world: "World | None",
    check_permission_func: Any,
    check_permission_via_contract_func: Any,
    execute_with_invoke_func: Any,
    use_contracts: bool = True,
) -> Any:
    """Create an invoke closure for injection into artifact execution context.

    This factory creates a closure that captures all the context needed for
    artifact-to-artifact invocation, suitable for injection into controlled_globals.

    Args:
        caller_id: ID of the original caller
        artifact_id: ID of this artifact
        ledger: Ledger instance
        artifact_store: ArtifactStore instance
        current_depth: Current recursion depth
        max_depth: Maximum allowed recursion depth
        world: World instance (optional)
        check_permission_func: Permission check function
        check_permission_via_contract_func: Contract permission check function
        execute_with_invoke_func: Recursive execution function
        use_contracts: Whether contracts are enabled

    Returns:
        A callable invoke(target_artifact_id, *args) function
    """
    def invoke(target_artifact_id: str, *invoke_args: Any) -> dict[str, Any]:
        """Invoke another artifact from within this artifact's code.

        The caller (original agent) pays for the invocation.
        Recursion is limited to prevent infinite loops.

        Args:
            target_artifact_id: ID of artifact to invoke
            *invoke_args: Arguments to pass to the artifact's run()

        Returns:
            Dict with success, result, error, and price_paid
        """
        return execute_invoke(
            target_artifact_id=target_artifact_id,
            invoke_args=invoke_args,
            caller_id=caller_id,
            artifact_id=artifact_id,
            ledger=ledger,
            artifact_store=artifact_store,
            current_depth=current_depth,
            max_depth=max_depth,
            world=world,
            check_permission_func=check_permission_func,
            check_permission_via_contract_func=check_permission_via_contract_func,
            execute_with_invoke_func=execute_with_invoke_func,
            use_contracts=use_contracts,
        )

    return invoke
