"""Kernel State and Actions interfaces - Plan #39

These interfaces provide equal access to kernel state for all artifacts,
whether genesis or agent-built. This removes accidental privilege from
genesis artifacts.

Design principles:
- KernelState: Read-only access to public state (balances, resources, metadata)
- KernelActions: Write access verified against caller identity
- Both are injected into artifact sandbox during execution
- Access controls are enforced by the kernel, not by artifacts

Plan #274: Added event logging to KernelActions for observability.
All write operations are now logged to the event system, making
artifact-based agents (BabyAGI loops) as observable as file-based agents.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, cast

if TYPE_CHECKING:
    from src.world.world import World


def _log_kernel_action(
    world: "World",
    action_type: str,
    caller_id: str,
    success: bool,
    data: dict[str, Any],
) -> None:
    """Log a kernel action to the event system (Plan #274).

    This makes artifact-based agents observable in the same way as
    file-based agents that use action_executor.

    Args:
        world: World instance for logging
        action_type: Type of action (e.g., "kernel_write_artifact")
        caller_id: Who performed the action
        success: Whether the action succeeded
        data: Action-specific data to log
    """
    world.logger.log(action_type, {
        "event_number": world.event_number,
        "principal_id": caller_id,
        "success": success,
        **data,
        "scrip_after": world.ledger.get_scrip(caller_id),
    })


class KernelState:
    """Read-only interface to kernel state for artifacts.

    All operations are public - any artifact can query any principal's
    balances, resources, and artifact metadata. Content access may be
    restricted by artifact policies.
    """

    def __init__(self, world: World) -> None:
        """Initialize with reference to world state.

        Args:
            world: The simulation world containing ledger, artifacts, etc.
        """
        self._world = world

    def get_balance(self, principal_id: str) -> int:
        """Get scrip balance for a principal.

        Args:
            principal_id: The principal to query

        Returns:
            Current scrip balance (0 if principal doesn't exist)
        """
        return self._world.ledger.get_scrip(principal_id)

    def get_resource(self, principal_id: str, resource: str) -> float:
        """Get resource amount for a principal.

        Args:
            principal_id: The principal to query
            resource: Resource name (e.g., "llm_tokens", "disk")

        Returns:
            Current resource amount (0.0 if not found)
        """
        return self._world.ledger.get_resource(principal_id, resource)

    def get_llm_budget(self, principal_id: str) -> float:
        """Get LLM budget for a principal.

        Convenience method for get_resource(principal_id, "llm_budget").
        LLM budget is a depletable resource representing dollars available
        for LLM API calls.

        Args:
            principal_id: The principal to query

        Returns:
            Current LLM budget (0.0 if not found)
        """
        return self._world.ledger.get_resource(principal_id, "llm_budget")

    def list_artifacts_by_owner(self, created_by: str) -> list[str]:
        """List artifact IDs owned by a principal.

        Args:
            created_by: The owner to query

        Returns:
            List of artifact IDs (empty if none found)
        """
        return self._world.artifacts.get_artifacts_by_owner(created_by)

    def get_artifact_metadata(self, artifact_id: str) -> dict[str, Any] | None:
        """Get artifact metadata (not content).

        Args:
            artifact_id: The artifact to query

        Returns:
            Dict with id, type, created_by, etc. or None if not found
        """
        artifact = self._world.artifacts.get(artifact_id)
        if artifact is None:
            return None

        return {
            "id": artifact.id,
            "type": artifact.type,
            "created_by": artifact.created_by,
            "executable": artifact.executable,
            "created_at": artifact.created_at,
            "updated_at": artifact.updated_at,
            "deleted": artifact.deleted,
        }

    def read_artifact(self, artifact_id: str, caller_id: str) -> str | None:
        """Read artifact content (access controlled via contracts).

        Args:
            artifact_id: The artifact to read
            caller_id: Who is requesting the read

        Returns:
            Artifact content if access allowed, None otherwise
        """
        from src.world.executor import get_executor

        artifact = self._world.artifacts.get(artifact_id)
        if artifact is None:
            return None

        # Plan #140: Check permission via contract (not hardcoded created_by check)
        executor = get_executor()
        perm_result = executor._check_permission(caller_id, "read", artifact)
        if not perm_result.allowed:
            return None

        # Plan #320: Log sandbox read for observability
        self._world.logger.log("artifact_read", {
            "event_number": self._world.event_number,
            "artifact_id": artifact_id,
            "principal_id": caller_id,
            "artifact_type": artifact.type,
            "read_price_paid": 0,
            "content_size": len(artifact.content) if artifact.content else 0,
        })

        return artifact.content

    # --- Kernel Mint Read Methods (Plan #44) ---

    def get_mint_submissions(self) -> list[dict[str, Any]]:
        """Get all pending mint submissions.

        Public data - any artifact can read pending submissions.

        Returns:
            List of pending mint submissions
        """
        # TypedDict is compatible with dict[str, Any] but needs explicit cast
        submissions = self._world.get_mint_submissions()
        return cast(list[dict[str, Any]], submissions)

    def get_mint_history(self, limit: int = 100) -> list[dict[str, Any]]:
        """Get mint auction history.

        Public data - any artifact can read history.

        Args:
            limit: Maximum number of results

        Returns:
            List of mint results, newest first
        """
        # TypedDict is compatible with dict[str, Any] but needs explicit cast
        history = self._world.get_mint_history(limit=limit)
        return cast(list[dict[str, Any]], history)
    # -------------------------------------------------------------------------
    # Quota Primitives (Plan #42) - Read-only access to kernel quota state
    # -------------------------------------------------------------------------

    def get_quota(self, principal_id: str, resource: str) -> float:
        """Get quota limit for a principal's resource.

        Args:
            principal_id: The principal to query
            resource: Resource name (e.g., "cpu_seconds_per_minute")

        Returns:
            Quota limit, or 0.0 if not set
        """
        return self._world.get_quota(principal_id, resource)

    def get_available_capacity(self, principal_id: str, resource: str) -> float:
        """Get remaining capacity (quota - usage) for a resource.

        Args:
            principal_id: The principal to query
            resource: Resource name

        Returns:
            Remaining capacity, or 0.0 if no quota set
        """
        return self._world.get_available_capacity(principal_id, resource)

    def would_exceed_quota(
        self, principal_id: str, resource: str, amount: float
    ) -> bool:
        """Check if consuming amount would exceed quota.

        Use this for pre-flight checks before attempting actions.

        Args:
            principal_id: The principal to check
            resource: Resource name
            amount: Amount that would be consumed

        Returns:
            True if consumption would exceed quota, False otherwise
        """
        available = self.get_available_capacity(principal_id, resource)
        return amount > available

    def query(
        self, query_type: str, params: dict[str, Any] | None = None, caller_id: str | None = None
    ) -> dict[str, Any]:
        """Execute a kernel query (Plan #273: For code-based agents).

        Delegates to KernelQueryHandler. This provides artifacts with the same
        query capabilities that agents have via query_kernel action.

        Args:
            query_type: Type of query (e.g., "mint_tasks", "artifacts", "balances")
            params: Query parameters
            caller_id: Who is making the query (for logging, Plan #274)

        Returns:
            Query result dict
        """
        from .kernel_queries import KernelQueryHandler
        handler = KernelQueryHandler(self._world)
        result = handler.execute(query_type, params or {})

        # Plan #274: Log query for observability (only if caller_id provided)
        if caller_id is not None:
            self._world.logger.log("kernel_query", {
                "event_number": self._world.event_number,
                "principal_id": caller_id,
                "query_type": query_type,
                "params": params or {},  # Plan #320: Include query params
                "success": result.get("success", True),
            })

        return result

    # -------------------------------------------------------------------------
    # External Capabilities (Plan #300)
    # -------------------------------------------------------------------------

    def has_capability(self, capability_name: str) -> bool:
        """Check if an external capability is available.

        An external capability is available if:
        1. It's configured in external_capabilities
        2. It's enabled (enabled: true)
        3. It has a valid API key

        Args:
            capability_name: Name of capability (e.g., "openai_embeddings")

        Returns:
            True if capability is ready to use
        """
        if not hasattr(self._world, "capability_manager"):
            return False
        manager = self._world.capability_manager
        if manager is None:
            return False
        return manager.is_enabled(capability_name) and manager.get_api_key(capability_name) is not None

    def list_capabilities(self) -> list[dict[str, Any]]:
        """List all configured external capabilities and their status.

        Returns:
            List of capability info dicts with name, enabled, has_api_key, budget info
        """
        if not hasattr(self._world, "capability_manager"):
            return []
        manager = self._world.capability_manager
        if manager is None:
            return []
        return manager.list_capabilities()


class KernelActions:
    """Action interface for artifacts - caller is verified.

    All write operations require caller_id which is verified against
    the actual invoking principal. Artifacts cannot spoof caller identity.
    """

    def __init__(self, world: World) -> None:
        """Initialize with reference to world state.

        Args:
            world: The simulation world containing ledger, artifacts, etc.
        """
        self._world = world

    def transfer_scrip(self, caller_id: str, to: str, amount: int) -> bool:
        """Transfer scrip from caller to recipient.

        Args:
            caller_id: Who is transferring (must be actual caller)
            to: Recipient principal
            amount: Amount to transfer

        Returns:
            True if transfer succeeded, False otherwise
        """
        if amount <= 0:
            _log_kernel_action(self._world, "kernel_transfer_scrip", caller_id, False, {
                "to": to, "amount": amount, "error": "Invalid amount"
            })
            return False

        # Check caller has sufficient balance
        balance = self._world.ledger.get_scrip(caller_id)
        if balance < amount:
            _log_kernel_action(self._world, "kernel_transfer_scrip", caller_id, False, {
                "to": to, "amount": amount, "error": "Insufficient balance"
            })
            return False

        # Perform transfer (atomic)
        self._world.ledger.transfer_scrip(caller_id, to, amount)

        # Plan #274: Log successful transfer
        _log_kernel_action(self._world, "kernel_transfer_scrip", caller_id, True, {
            "to": to, "amount": amount,
        })

        return True

    def transfer_resource(
        self, caller_id: str, to: str, resource: str, amount: float
    ) -> bool:
        """Transfer resource from caller to recipient.

        Args:
            caller_id: Who is transferring (must be actual caller)
            to: Recipient principal
            resource: Resource name (e.g., "llm_tokens")
            amount: Amount to transfer

        Returns:
            True if transfer succeeded, False otherwise
        """
        if amount <= 0:
            _log_kernel_action(self._world, "kernel_transfer_resource", caller_id, False, {
                "to": to, "resource": resource, "amount": amount, "error": "Invalid amount"
            })
            return False

        # Check caller has sufficient resource
        current = self._world.ledger.get_resource(caller_id, resource)
        if current < amount:
            _log_kernel_action(self._world, "kernel_transfer_resource", caller_id, False, {
                "to": to, "resource": resource, "amount": amount, "error": "Insufficient resource"
            })
            return False

        # Perform transfer (ledger uses Decimal arithmetic internally)
        self._world.ledger.transfer_resource(caller_id, to, resource, amount)

        # Plan #276: Log successful transfer
        _log_kernel_action(self._world, "kernel_transfer_resource", caller_id, True, {
            "to": to, "resource": resource, "amount": amount,
        })

        return True

    def transfer_llm_budget(
        self, caller_id: str, to: str, amount: float
    ) -> bool:
        """Transfer LLM budget from caller to recipient.

        Convenience method for transfer_resource(caller_id, to, "llm_budget", amount).
        LLM budget is a depletable resource representing dollars available
        for LLM API calls. Making it tradeable enables budget markets.

        Args:
            caller_id: Who is transferring (must be actual caller)
            to: Recipient principal
            amount: Amount to transfer (in budget units, e.g., dollars)

        Returns:
            True if transfer succeeded, False otherwise
        """
        return self.transfer_resource(caller_id, to, "llm_budget", amount)

    def write_artifact(
        self,
        caller_id: str,
        artifact_id: str,
        content: str,
        artifact_type: str = "generic",
        executable: bool = False,
        code: str | None = None,
        has_standing: bool = False,
        access_contract_id: str | None = None,
    ) -> bool:
        """Write or update an artifact via the unified action executor.

        Routes through ActionExecutor for consistent permission checking,
        disk quota enforcement, code validation, and logging.

        Args:
            caller_id: Who is writing
            artifact_id: Artifact to write
            content: New content
            artifact_type: Type if creating new
            executable: Whether the artifact is executable (Plan #273)
            code: Executable code if creating executable artifact (Plan #273)
            has_standing: If True, create a ledger principal for the artifact
                so it can hold scrip (ADR-0011)
            access_contract_id: Contract governing the artifact (ADR-0019).
                Required for new artifacts. Updates preserve existing contract.

        Returns:
            True if write succeeded, False otherwise
        """
        from src.world.actions import WriteArtifactIntent

        # Preserve existing type/executable on updates (callers don't re-specify)
        existing = self._world.artifacts.get(artifact_id)
        if existing is not None:
            artifact_type = existing.type
            executable = existing.executable

        intent = WriteArtifactIntent(
            principal_id=caller_id,
            artifact_id=artifact_id,
            artifact_type=artifact_type,
            content=content,
            executable=executable,
            code=code or "",
            has_standing=has_standing,
            access_contract_id=access_contract_id,
        )
        result = self._world.execute_action(intent)
        if not result.success:
            raise ValueError(result.message)
        return True

    def submit_to_task(
        self,
        caller_id: str,
        artifact_id: str,
        task_id: str,
    ) -> dict[str, Any]:
        """Submit an artifact as a solution to a mint task (Plan #273).

        This is the kernel interface equivalent of the submit_to_task action.

        Args:
            caller_id: Who is submitting (verified by kernel)
            artifact_id: The artifact being submitted
            task_id: The task to submit to

        Returns:
            {"success": True, "reward": ...} on success
            {"success": False, "error": ...} on failure
        """
        # Check if task-based mint is enabled
        if not hasattr(self._world, "mint_task_manager") or self._world.mint_task_manager is None:
            error_result = {
                "success": False,
                "error": "Task-based mint system is not enabled",
            }
            # Plan #274: Log failed submission
            _log_kernel_action(self._world, "kernel_submit_to_task", caller_id, False, {
                "artifact_id": artifact_id, "task_id": task_id,
                "error": error_result["error"],
            })
            return error_result

        # Submit to task - submit_solution handles all validation
        manager = self._world.mint_task_manager
        result = manager.submit_solution(caller_id, artifact_id, task_id)

        # Convert TaskSubmissionResult to dict
        result_dict = {
            "success": result.success,
            "task_id": result.task_id,
            "artifact_id": result.artifact_id,
            "message": result.message,
            "reward": result.reward_earned,
        }

        # Plan #274: Log submission result
        _log_kernel_action(self._world, "kernel_submit_to_task", caller_id, result.success, {
            "artifact_id": artifact_id, "task_id": task_id,
            "reward": result.reward_earned if result.success else 0,
            "message": result.message,
        })

        return result_dict

    # --- Kernel Mint Action Methods (Plan #44) ---

    def submit_for_mint(
        self, caller_id: str, artifact_id: str, bid: int
    ) -> dict[str, Any]:
        """Submit artifact for mint consideration.

        Caller must own the artifact. Bid is escrowed until auction resolution.

        Args:
            caller_id: Who is submitting (verified by kernel)
            artifact_id: Artifact to submit
            bid: Amount of scrip to bid

        Returns:
            {"success": True, "submission_id": ...} on success
            {"success": False, "error": ...} on failure
        """
        try:
            submission_id = self._world.submit_for_mint(
                principal_id=caller_id,
                artifact_id=artifact_id,
                bid=bid
            )
            # Plan #276: Log successful submission
            _log_kernel_action(self._world, "kernel_submit_for_mint", caller_id, True, {
                "artifact_id": artifact_id, "bid": bid, "submission_id": submission_id,
            })
            return {"success": True, "submission_id": submission_id}
        except ValueError as e:
            # Plan #276: Log failed submission
            _log_kernel_action(self._world, "kernel_submit_for_mint", caller_id, False, {
                "artifact_id": artifact_id, "bid": bid, "error": str(e),
            })
            return {"success": False, "error": str(e)}

    def cancel_mint_submission(self, caller_id: str, submission_id: str) -> bool:
        """Cancel a mint submission and refund the bid.

        Can only cancel your own submissions.

        Args:
            caller_id: Who is cancelling (verified by kernel)
            submission_id: Which submission to cancel

        Returns:
            True if cancelled, False if not allowed
        """
        result = self._world.cancel_mint_submission(caller_id, submission_id)
        # Plan #276: Log cancellation result
        _log_kernel_action(self._world, "kernel_cancel_mint_submission", caller_id, result, {
            "submission_id": submission_id,
        })
        return result

    # -------------------------------------------------------------------------
    # Quota Primitives (Plan #42) - Write access to kernel quota state
    # -------------------------------------------------------------------------

    def transfer_quota(
        self, from_id: str, to_id: str, resource: str, amount: float
    ) -> bool:
        """Atomically transfer quota from one principal to another.

        This transfers the quota *limit*, not usage. Use for trading quotas.

        Args:
            from_id: Principal giving up quota
            to_id: Principal receiving quota
            resource: Resource name
            amount: Quota amount to transfer

        Returns:
            True if transfer succeeded, False if insufficient quota
        """
        if amount <= 0:
            _log_kernel_action(self._world, "kernel_transfer_quota", from_id, False, {
                "to": to_id, "resource": resource, "amount": amount, "error": "Invalid amount"
            })
            return False

        # Check source has sufficient quota
        from_quota = self._world.get_quota(from_id, resource)
        if from_quota < amount:
            _log_kernel_action(self._world, "kernel_transfer_quota", from_id, False, {
                "to": to_id, "resource": resource, "amount": amount, "error": "Insufficient quota"
            })
            return False

        # Perform atomic transfer
        to_quota = self._world.get_quota(to_id, resource)
        self._world.set_quota(from_id, resource, from_quota - amount)
        self._world.set_quota(to_id, resource, to_quota + amount)

        # Plan #276: Log successful transfer
        _log_kernel_action(self._world, "kernel_transfer_quota", from_id, True, {
            "to": to_id, "resource": resource, "amount": amount,
        })

        return True

    def consume_quota(
        self, principal_id: str, resource: str, amount: float
    ) -> bool:
        """Record resource consumption against quota.

        Args:
            principal_id: Principal consuming resources
            resource: Resource name
            amount: Amount consumed

        Returns:
            True if consumption recorded, False if would exceed quota
        """
        result = self._world.consume_quota(principal_id, resource, amount)
        # Plan #276: Log consumption result
        _log_kernel_action(self._world, "kernel_consume_quota", principal_id, result, {
            "resource": resource, "amount": amount,
        })
        return result

    # -------------------------------------------------------------------------
    # Charge Delegation (Plan #236)
    # -------------------------------------------------------------------------

    def grant_charge_delegation(
        self,
        caller_id: str,
        charger_id: str,
        max_per_call: float | None = None,
        max_per_window: float | None = None,
        window_seconds: int = 3600,
        expires_at: str | None = None,
    ) -> bool:
        """Grant permission for *charger_id* to charge *caller_id*'s account.

        Caller IS the payer — can only grant delegations from yourself.
        Creates or updates ``charge_delegation:{caller_id}`` artifact
        (kernel_protected, private).

        Args:
            caller_id: Payer granting the delegation (verified by kernel).
            charger_id: Principal being authorized to charge.
            max_per_call: Max amount per single charge (None = unlimited).
            max_per_window: Max cumulative amount per window (None = unlimited).
            window_seconds: Rolling window duration in seconds.
            expires_at: ISO 8601 expiry (None = no expiry).

        Returns:
            True on success.
        """
        result = self._world.delegation_manager.grant(
            caller_id,
            charger_id,
            max_per_call=max_per_call,
            max_per_window=max_per_window,
            window_seconds=window_seconds,
            expires_at=expires_at,
        )
        # Plan #276: Log delegation grant
        _log_kernel_action(self._world, "kernel_grant_delegation", caller_id, result, {
            "charger_id": charger_id,
            "max_per_call": max_per_call,
            "max_per_window": max_per_window,
            "window_seconds": window_seconds,
        })
        return result

    def revoke_charge_delegation(
        self,
        caller_id: str,
        charger_id: str,
    ) -> bool:
        """Revoke a previously granted charge delegation.

        Args:
            caller_id: Payer revoking (verified by kernel).
            charger_id: Charger whose delegation is being revoked.

        Returns:
            True if found and removed, False otherwise.
        """
        result = self._world.delegation_manager.revoke(caller_id, charger_id)
        # Plan #276: Log delegation revocation
        _log_kernel_action(self._world, "kernel_revoke_delegation", caller_id, result, {
            "charger_id": charger_id,
        })
        return result

    def authorize_charge(
        self,
        charger_id: str,
        payer_id: str,
        amount: float,
    ) -> tuple[bool, str]:
        """Check if *charger_id* is authorized to charge *payer_id*.

        Args:
            charger_id: Who wants to charge.
            payer_id: Whose account would be charged.
            amount: The charge amount.

        Returns:
            ``(True, "ok")`` if authorized, ``(False, reason)`` otherwise.
        """
        authorized, reason = self._world.delegation_manager.authorize_charge(
            charger_id, payer_id, amount
        )
        _log_kernel_action(self._world, "kernel_authorize_charge", charger_id, authorized, {
            "payer_id": payer_id, "amount": amount, "reason": reason,
        })
        return authorized, reason

    # -------------------------------------------------------------------------
    # Library Installation (Plan #29)
    # -------------------------------------------------------------------------

    def install_library(
        self, caller_id: str, library_name: str, version: str | None = None
    ) -> dict[str, Any]:
        """Install a Python library for the calling agent.

        Genesis libraries are pre-installed and free. Other libraries
        cost disk quota based on installed size.

        Args:
            caller_id: Agent requesting installation
            library_name: Package name (e.g., "scikit-learn")
            version: Optional version constraint (e.g., ">=1.0.0")

        Returns:
            {"success": True, "message": "..."} on success
            {"success": False, "error": "...", "error_code": "..."} on failure
        """
        import re
        import subprocess
        import sys
        from src.config import get_validated_config

        config = get_validated_config()
        genesis_libs = [lib.lower() for lib in config.libraries.genesis]
        blocked_libs = [lib.lower() for lib in config.libraries.blocked]

        lib_lower = library_name.lower()

        # Validate library name format (prevent command injection)
        # Allow: letters, numbers, hyphens, underscores, dots, brackets for extras
        if not re.match(r'^[a-zA-Z0-9_\-.\[\]]+$', library_name):
            _log_kernel_action(self._world, "kernel_install_library", caller_id, False, {
                "library": library_name, "error_code": "INVALID_NAME",
            })
            return {
                "success": False,
                "error": f"Invalid library name format: '{library_name}'",
                "error_code": "INVALID_NAME",
            }

        # Check blocklist
        if lib_lower in blocked_libs:
            _log_kernel_action(self._world, "kernel_install_library", caller_id, False, {
                "library": library_name, "error_code": "BLOCKED_PACKAGE",
            })
            return {
                "success": False,
                "error": f"Package '{library_name}' is blocked for security reasons",
                "error_code": "BLOCKED_PACKAGE",
            }

        # Check if genesis library (free, pre-installed)
        if lib_lower in genesis_libs:
            # Don't record - genesis libs are always available
            _log_kernel_action(self._world, "kernel_install_library", caller_id, True, {
                "library": library_name, "is_genesis": True, "quota_cost": 0,
            })
            return {
                "success": True,
                "message": f"Library '{library_name}' is a genesis library (pre-installed)",
                "quota_cost": 0,
            }

        # For non-genesis libraries, estimate size and check quota
        # Default estimate: 5MB per package (conservative)
        estimated_size = 5 * 1024 * 1024  # 5MB in bytes

        # Check disk quota
        available = self._world.get_available_capacity(caller_id, "disk")
        if estimated_size > available:
            _log_kernel_action(self._world, "kernel_install_library", caller_id, False, {
                "library": library_name, "error_code": "QUOTA_EXCEEDED",
            })
            return {
                "success": False,
                "error": f"Insufficient disk quota. Need ~{estimated_size} bytes, have {available}",
                "error_code": "QUOTA_EXCEEDED",
                "required": estimated_size,
                "available": available,
            }

        # Build package spec with optional version
        package_spec = library_name
        if version:
            # Validate version format
            if not re.match(r'^[<>=!~\d.,a-zA-Z*]+$', version):
                _log_kernel_action(self._world, "kernel_install_library", caller_id, False, {
                    "library": library_name, "version": version, "error_code": "INVALID_VERSION",
                })
                return {
                    "success": False,
                    "error": f"Invalid version format: '{version}'",
                    "error_code": "INVALID_VERSION",
                }
            package_spec = f"{library_name}{version}"

        # Actually install the package using pip
        # Use --break-system-packages for externally-managed environments (Debian/Ubuntu)
        try:
            result = subprocess.run(
                [sys.executable, "-m", "pip", "install", "--break-system-packages", "-q", package_spec],
                capture_output=True,
                text=True,
                timeout=120,  # 2 minute timeout for installation
            )

            if result.returncode != 0:
                error_msg = result.stderr.strip() or result.stdout.strip() or "Unknown pip error"
                # Truncate long error messages
                if len(error_msg) > 200:
                    error_msg = error_msg[:200] + "..."
                _log_kernel_action(self._world, "kernel_install_library", caller_id, False, {
                    "library": library_name, "error_code": "PIP_FAILED",
                })
                return {
                    "success": False,
                    "error": f"pip install failed: {error_msg}",
                    "error_code": "PIP_FAILED",
                }

        except subprocess.TimeoutExpired:
            _log_kernel_action(self._world, "kernel_install_library", caller_id, False, {
                "library": library_name, "error_code": "TIMEOUT",
            })
            return {
                "success": False,
                "error": "Package installation timed out (>120s)",
                "error_code": "TIMEOUT",
            }
        except Exception as e:
            _log_kernel_action(self._world, "kernel_install_library", caller_id, False, {
                "library": library_name, "error_code": "INSTALL_ERROR",
            })
            return {
                "success": False,
                "error": f"Installation error: {str(e)}",
                "error_code": "INSTALL_ERROR",
            }

        # Installation succeeded - consume quota and record
        if not self._world.consume_quota(caller_id, "disk", float(estimated_size)):
            _log_kernel_action(self._world, "kernel_install_library", caller_id, False, {
                "library": library_name, "error_code": "QUOTA_CONSUME_FAILED",
            })
            return {
                "success": False,
                "error": "Failed to consume disk quota",
                "error_code": "QUOTA_CONSUME_FAILED",
            }

        # Track installation in world state
        self._world.record_library_install(caller_id, library_name, version)

        # Plan #276: Log successful installation
        _log_kernel_action(self._world, "kernel_install_library", caller_id, True, {
            "library": library_name, "version": version, "quota_cost": estimated_size,
        })

        return {
            "success": True,
            "message": f"Installed '{package_spec}' (quota cost: {estimated_size} bytes)",
            "quota_cost": estimated_size,
        }

    # -------------------------------------------------------------------------
    # Principal Management (Plan #111)
    # -------------------------------------------------------------------------

    def create_principal(
        self, principal_id: str, starting_scrip: int = 0
    ) -> bool:
        """Create a new principal with optional starting resources.

        This is the single atomic operation for principal creation (Plan #231).
        Creates ledger entry, sets has_standing on artifact, and creates
        ResourceManager entry.

        Args:
            principal_id: ID for the new principal (must be unique)
            starting_scrip: Initial scrip balance (default 0)

        Returns:
            True if principal created, False if already exists
        """
        # Check if principal already exists
        if self._world.ledger.principal_exists(principal_id):
            _log_kernel_action(self._world, "kernel_create_principal", principal_id, False, {
                "error": "Principal already exists",
            })
            return False

        # 1. Ledger entry
        self._world.ledger.create_principal(
            principal_id,
            starting_scrip=starting_scrip,
        )

        # 2. Artifact has_standing (Plan #231: ledger <-> has_standing invariant)
        if principal_id in self._world.artifacts.artifacts:
            self._world.artifacts.artifacts[principal_id].has_standing = True

        # 3. ResourceManager entry
        if hasattr(self._world, 'resource_manager'):
            self._world.resource_manager.create_principal(principal_id)

        # Plan #276: Log successful creation
        _log_kernel_action(self._world, "kernel_create_principal", principal_id, True, {
            "starting_scrip": starting_scrip,
        })

        return True

    def update_artifact_metadata(
        self, caller_id: str, artifact_id: str, key: str, value: object
    ) -> bool:
        """Update a single metadata key on an artifact (Plan #213).

        This is the canonical way to update artifact metadata.
        Auth data lives in artifact.state (Plan #311), not metadata.

        Permission checking:
        - Caller must have WRITE permission on the artifact via its contract
        - This enables escrow to update metadata after purchase

        Args:
            caller_id: Principal requesting the update
            artifact_id: Artifact to update
            key: Metadata key to set
            value: Value to set (use None to delete the key)

        Returns:
            True if metadata was updated, False otherwise
        """
        from src.world.executor import get_executor

        artifact = self._world.artifacts.get(artifact_id)
        if artifact is None:
            _log_kernel_action(self._world, "kernel_update_metadata", caller_id, False, {
                "artifact_id": artifact_id, "key": key, "error": "Artifact not found",
            })
            return False

        # Check write permission via contract
        executor = get_executor()
        perm_result = executor._check_permission(caller_id, "write", artifact)
        if not perm_result.allowed:
            _log_kernel_action(self._world, "kernel_update_metadata", caller_id, False, {
                "artifact_id": artifact_id, "key": key, "error": f"Permission denied: {perm_result.reason}",
            })
            return False

        # Update the metadata
        if value is None:
            # Delete key if value is None
            artifact.metadata.pop(key, None)
        else:
            artifact.metadata[key] = value

        # Plan #276: Log successful metadata update
        _log_kernel_action(self._world, "kernel_update_metadata", caller_id, True, {
            "artifact_id": artifact_id, "key": key, "action": "delete" if value is None else "set",
        })

        return True

    def modify_protected_content(
        self,
        artifact_id: str,
        *,
        content: str | None = None,
        code: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> bool:
        """Kernel-only: modify content of a kernel_protected artifact.

        Plan #235 Phase 1: Bypasses kernel_protected checks.
        Only kernel code should call this - it is NOT exposed to artifacts.

        Args:
            artifact_id: The artifact to modify
            content: New content (None = keep existing)
            code: New code (None = keep existing)
            metadata: New metadata (None = keep existing)

        Returns:
            True if modified, False if artifact not found
        """
        try:
            self._world.artifacts.modify_protected_content(
                artifact_id, content=content, code=code, metadata=metadata
            )
            return True
        except KeyError:
            return False

    # -------------------------------------------------------------------------
    # External Capabilities (Plan #300)
    # -------------------------------------------------------------------------

    def request_capability(
        self,
        caller_id: str,
        capability_name: str,
        reason: str,
    ) -> dict[str, Any]:
        """Request access to an external capability.

        Creates a pending request for human review. The human must then:
        1. Add API key to config
        2. Set enabled: true

        Args:
            caller_id: Agent making the request
            capability_name: Capability being requested (e.g., "openai_embeddings")
            reason: Why the agent needs this capability

        Returns:
            {"pending": True, "message": "..."} - Request logged for human review
        """
        # Log the request for human visibility
        _log_kernel_action(self._world, "capability_request", caller_id, True, {
            "capability": capability_name,
            "reason": reason,
            "status": "pending",
        })

        return {
            "pending": True,
            "message": f"Request for '{capability_name}' logged. Waiting for human approval.",
            "capability": capability_name,
            "reason": reason,
        }

    def use_capability(
        self,
        caller_id: str,
        capability_name: str,
        action: str,
        params: dict[str, Any],
    ) -> dict[str, Any]:
        """Use an approved external capability.

        The capability must be:
        1. Configured in external_capabilities
        2. Enabled (enabled: true)
        3. Have a valid API key

        Args:
            caller_id: Agent using the capability
            capability_name: Which capability to use
            action: Capability-specific action (e.g., "embed" for embeddings)
            params: Action parameters

        Returns:
            {"success": True, ...} with capability-specific results
            {"success": False, "error": "...", "error_code": "..."} on failure
        """
        if not hasattr(self._world, "capability_manager") or self._world.capability_manager is None:
            _log_kernel_action(self._world, "capability_use", caller_id, False, {
                "capability": capability_name,
                "action": action,
                "error_code": "NO_MANAGER",
            })
            return {
                "success": False,
                "error": "Capability system not initialized",
                "error_code": "NO_MANAGER",
            }

        manager = self._world.capability_manager

        # Check if enabled
        if not manager.is_enabled(capability_name):
            _log_kernel_action(self._world, "capability_use", caller_id, False, {
                "capability": capability_name,
                "action": action,
                "error_code": "NOT_ENABLED",
            })
            return {
                "success": False,
                "error": f"Capability '{capability_name}' is not enabled. Request it first.",
                "error_code": "NOT_ENABLED",
            }

        # Execute the capability
        result = manager.execute(capability_name, action, params)

        # Track spend if successful and there's a cost
        if result.get("success") and "cost" in result:
            cost = result["cost"]
            if not manager.track_spend(capability_name, cost):
                _log_kernel_action(self._world, "capability_use", caller_id, False, {
                    "capability": capability_name,
                    "action": action,
                    "error_code": "BUDGET_EXCEEDED",
                })
                return {
                    "success": False,
                    "error": f"Capability '{capability_name}' budget exceeded",
                    "error_code": "BUDGET_EXCEEDED",
                }

        # Log the result
        _log_kernel_action(self._world, "capability_use", caller_id, result.get("success", False), {
            "capability": capability_name,
            "action": action,
            "error_code": result.get("error_code") if not result.get("success") else None,
        })

        return result

