"""Permission checking for artifact access.

Extracted from executor.py as part of Plan #181 (Split Large Core Files).

This module provides permission checking logic for:
- Contract-based permission checking (Plan #100)
- Dangling contract fallback handling (ADR-0017)
- TTL-based permission caching

The functions here are used by SafeExecutor to check permissions before
artifact access operations.
"""

from __future__ import annotations

import logging
from dataclasses import replace as dataclass_replace
from typing import TYPE_CHECKING, Any

from ..config import get as config_get, get_validated_config
from .constants import KERNEL_CONTRACT_FREEWARE
from .contracts import (
    AccessContract,
    ExecutableContract,
    PermissionAction,
    PermissionResult,
)
from .kernel_contracts import get_contract_by_id, get_kernel_contract

if TYPE_CHECKING:
    from .artifacts import Artifact
    from .contracts import PermissionCache
    from .ledger import Ledger


def get_max_contract_depth() -> int:
    """Get max recursion depth for contract permission checks from config.

    This limits how deep permission check chains can go to prevent
    infinite recursion. Per Plan #100 and ADR-0018, default is 10.
    """
    return get_validated_config().executor.max_contract_depth


# Legacy constant for backward compatibility
DEFAULT_MAX_CONTRACT_DEPTH = 10


def get_contract_with_fallback_info(
    contract_id: str,
    contract_cache: dict[str, AccessContract | ExecutableContract],
    dangling_count_tracker: list[int],
) -> tuple[AccessContract | ExecutableContract, bool, str | None]:
    """Get contract by ID, with info about whether fallback was used.

    Checks kernel contracts first, then falls back to configurable
    default if not found. Also supports ExecutableContracts registered
    via register_executable_contract().

    Plan #100 Phase 2, ADR-0017: Dangling contracts fail open to default.

    Args:
        contract_id: The contract ID to look up
        contract_cache: Cache dict for contract lookups
        dangling_count_tracker: Single-element list to track dangling count

    Returns:
        Tuple of (contract, is_fallback, original_contract_id)
        - contract: The contract instance (never None)
        - is_fallback: True if this is a fallback due to missing contract
        - original_contract_id: The original ID if fallback occurred, else None
    """
    if contract_id in contract_cache:
        return contract_cache[contract_id], False, None

    # Check kernel contracts
    contract = get_contract_by_id(contract_id)
    if contract:
        contract_cache[contract_id] = contract
        return contract, False, None

    # Contract not found - use configurable default (ADR-0017)
    dangling_count_tracker[0] += 1

    # Log warning for observability
    logger = logging.getLogger(__name__)
    default_contract_id = config_get("contracts.default_on_missing") or KERNEL_CONTRACT_FREEWARE
    logger.warning(
        f"Dangling contract: '{contract_id}' not found, "
        f"falling back to '{default_contract_id}'"
    )

    # Get the default contract
    contract = get_contract_by_id(default_contract_id)
    if not contract:
        contract = get_kernel_contract("freeware")

    # Cache the original ID pointing to fallback contract
    contract_cache[contract_id] = contract
    return contract, True, contract_id


def check_permission_via_contract(
    caller: str,
    action: str,
    artifact: "Artifact",
    contract_cache: dict[str, AccessContract | ExecutableContract],
    permission_cache: "PermissionCache",
    dangling_count_tracker: list[int],
    ledger: "Ledger | None",
    max_contract_depth: int,
    contract_depth: int = 0,
    method: str | None = None,
    args: list[Any] | None = None,
) -> PermissionResult:
    """Check permission using artifact's access contract.

    Supports both kernel contracts (static logic) and executable
    contracts (dynamic code). Executable contracts receive read-only
    ledger access for balance checks.

    Plan #100 Phase 2: Supports TTL-based caching for contracts with
    cache_policy. Caching is opt-in - contracts without cache_policy
    are never cached.

    Args:
        caller: The principal requesting access
        action: The action being attempted (read, write, invoke, etc.)
        artifact: The artifact being accessed
        contract_cache: Cache dict for contract lookups
        permission_cache: TTL-based permission result cache
        dangling_count_tracker: Single-element list to track dangling count
        ledger: Ledger for executable contract balance checks
        max_contract_depth: Maximum permission check recursion depth
        contract_depth: Current depth of permission check chain (default 0).
            Per Plan #100, prevents infinite recursion in permission checks.
        method: Method name for invoke actions
        args: Arguments for invoke actions

    Returns:
        PermissionResult with allowed, reason, and optional cost
    """
    # Check depth limit (Plan #100: prevent infinite recursion)
    if contract_depth >= max_contract_depth:
        return PermissionResult(
            allowed=False,
            reason=f"Contract permission check depth exceeded (depth={contract_depth}, limit={max_contract_depth})"
        )

    # Get contract ID from artifact
    contract_id = artifact.access_contract_id
    contract, is_fallback, original_contract_id = get_contract_with_fallback_info(
        contract_id, contract_cache, dangling_count_tracker
    )

    # Convert action string to PermissionAction
    try:
        perm_action = PermissionAction(action)
    except ValueError:
        return PermissionResult(
            allowed=False,
            reason=f"Unknown action: {action}"
        )

    # Plan #100 Phase 2: Check permission cache for ExecutableContracts with cache_policy
    cache_key = None
    cache_policy = None
    if isinstance(contract, ExecutableContract) and contract.cache_policy is not None:
        cache_policy = contract.cache_policy
        # Cache key: (artifact_id, action, requester_id, contract_version)
        # Contract version is "v1" for now (versioning to be added later)
        contract_version = getattr(contract, "version", "v1")
        cache_key = (artifact.id, action, caller, contract_version)

        # Check cache
        cached_result = permission_cache.get(cache_key)
        if cached_result is not None:
            return cached_result

    # Build context for contract (ADR-0019: minimal context)
    context: dict[str, object] = {
        "target_created_by": artifact.created_by,  # Informational only (ADR-0028)
        "target_metadata": artifact.metadata if hasattr(artifact, "metadata") and artifact.metadata else {},
    }
    # Add method and args for invoke actions (ADR-0019)
    if action == "invoke":
        context["method"] = method
        context["args"] = args if args is not None else []

    # ExecutableContracts need ledger access for balance checks
    if isinstance(contract, ExecutableContract):
        result = contract.check_permission(
            caller=caller,
            action=perm_action,
            target=artifact.id,
            context=context,
            ledger=ledger,
        )

        # Store in cache if cache_policy is set
        if cache_key is not None and cache_policy is not None:
            ttl_seconds = cache_policy.get("ttl_seconds", 0)
            if ttl_seconds > 0:
                permission_cache.put(cache_key, result, ttl_seconds)
    else:
        # Kernel/static contracts use standard interface
        result = contract.check_permission(
            caller=caller,
            action=perm_action,
            target=artifact.id,
            context=context,
        )

    # Plan #100 ADR-0017: Add dangling contract info to conditions for observability
    if is_fallback and original_contract_id is not None:
        # Merge with existing conditions if any
        new_conditions: dict[str, object] = dict(result.conditions or {})
        new_conditions["dangling_contract"] = True
        new_conditions["original_contract_id"] = original_contract_id
        result = dataclass_replace(result, conditions=new_conditions)

    return result


def check_permission_legacy(
    caller: str,
    action: str,
    artifact: "Artifact",
) -> tuple[bool, str]:
    """Legacy permission check using freeware contract.

    DEPRECATED: Legacy mode is deprecated. All artifacts should use
    access_contract_id for permission checking. When an artifact lacks
    the access_contract_id attribute, falls back to freeware semantics:
    - READ, INVOKE: Anyone can access
    - WRITE, EDIT, DELETE: Only authorized_writer can access

    Args:
        caller: The principal requesting access
        action: The action being attempted
        artifact: The artifact being accessed

    Returns:
        PermissionResult with decision
    """
    import warnings
    warnings.warn(
        "Legacy permission checking is deprecated. Set access_contract_id "
        "on artifacts to use contract-based permissions.",
        DeprecationWarning,
        stacklevel=3,
    )

    # CAP-003: No special bypass. Delegate to freeware contract
    # which checks authorized_writer from metadata.
    freeware = get_kernel_contract("freeware")

    # Convert action string to PermissionAction
    try:
        perm_action = PermissionAction(action)
    except ValueError:
        return PermissionResult(allowed=False, reason=f"legacy: unknown action {action}")

    # ADR-0019/ADR-0028: context with metadata for authorization
    context: dict[str, object] = {
        "target_created_by": artifact.created_by,  # Informational only (ADR-0028)
        "target_metadata": artifact.metadata if hasattr(artifact, "metadata") and artifact.metadata else {},
    }

    result = freeware.check_permission(
        caller=caller,
        action=perm_action,
        target=artifact.id,
        context=context,
    )
    return dataclass_replace(result, reason=f"legacy (freeware): {result.reason}")


def check_permission(
    caller: str,
    action: str,
    artifact: "Artifact",
    contract_cache: dict[str, AccessContract | ExecutableContract],
    permission_cache: "PermissionCache",
    dangling_count_tracker: list[int],
    ledger: "Ledger | None",
    max_contract_depth: int,
    use_contracts: bool,
    method: str | None = None,
    args: list[Any] | None = None,
) -> PermissionResult:
    """Check if caller has permission for action on artifact.

    Permission checking follows ADR-0019:
    1. If access_contract_id is set: use that contract
    2. If access_contract_id is NULL: use configurable default (creator_only or freeware)
    3. If access_contract_id points to deleted contract: use default_on_missing

    Args:
        caller: The principal requesting access
        action: The action being attempted
        artifact: The artifact being accessed
        contract_cache: Cache dict for contract lookups
        permission_cache: TTL-based permission result cache
        dangling_count_tracker: Single-element list to track dangling count
        ledger: Ledger for executable contract balance checks
        max_contract_depth: Maximum permission check recursion depth
        use_contracts: Whether to use contract-based checking
        method: Method name (for invoke actions, per ADR-0019)
        args: Arguments (for invoke actions, per ADR-0019)

    Returns:
        PermissionResult with allowed, reason, cost, recipient, etc.
    """
    # Get artifact's access_contract_id (always present on Artifact dataclass)
    contract_id = artifact.access_contract_id

    # Case 1: Artifact has a non-null contract - use contract-based checking
    if use_contracts and contract_id is not None:
        return check_permission_via_contract(
            caller=caller,
            action=action,
            artifact=artifact,
            contract_cache=contract_cache,
            permission_cache=permission_cache,
            dangling_count_tracker=dangling_count_tracker,
            ledger=ledger,
            max_contract_depth=max_contract_depth,
            method=method,
            args=args,
        )

    # Case 2: Artifact has NULL contract (ADR-0019)
    # Delegate to private contract with proper context (including metadata).
    # "creator_only" config is honored by checking authorized_principal metadata.
    if contract_id is None:
        default_behavior = config_get("contracts.default_when_null")
        if default_behavior is None:
            default_behavior = "creator_only"  # ADR-0019 default

        if default_behavior == "creator_only":
            # Delegate to private contract (authorized_principal from metadata)
            private = get_kernel_contract("private")
            try:
                perm_action = PermissionAction(action)
            except ValueError:
                return PermissionResult(allowed=False, reason=f"null contract: unknown action {action}")
            context: dict[str, object] = {
                "target_created_by": artifact.created_by,  # Informational only (ADR-0028)
                "target_metadata": artifact.metadata if hasattr(artifact, "metadata") and artifact.metadata else {},
            }
            result = private.check_permission(
                caller=caller,
                action=perm_action,
                target=artifact.id,
                context=context,
            )
            return dataclass_replace(result, reason=f"null contract: {result.reason}")
        # else: fall through to legacy/freeware behavior

    # Legacy policy-based check (for backward compatibility or freeware default)
    return check_permission_legacy(caller, action, artifact)
