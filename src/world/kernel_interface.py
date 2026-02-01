"""Kernel State and Actions interfaces - Plan #39

These interfaces provide equal access to kernel state for all artifacts,
whether genesis or agent-built. This removes accidental privilege from
genesis artifacts.

Design principles:
- KernelState: Read-only access to public state (balances, resources, metadata)
- KernelActions: Write access verified against caller identity
- Both are injected into artifact sandbox during execution
- Access controls are enforced by the kernel, not by artifacts
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, cast

if TYPE_CHECKING:
    from src.world.world import World


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
        allowed, _reason = executor._check_permission(caller_id, "read", artifact)
        if not allowed:
            return None

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
            return False

        # Check caller has sufficient balance
        balance = self._world.ledger.get_scrip(caller_id)
        if balance < amount:
            return False

        # Perform transfer
        self._world.ledger.deduct_scrip(caller_id, amount)
        self._world.ledger.credit_scrip(to, amount)

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
            return False

        # Check caller has sufficient resource
        current = self._world.ledger.get_resource(caller_id, resource)
        if current < amount:
            return False

        # Perform transfer
        self._world.ledger.spend_resource(caller_id, resource, amount)
        new_recipient = self._world.ledger.get_resource(to, resource) + amount
        self._world.ledger.set_resource(to, resource, new_recipient)

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
    ) -> bool:
        """Write or update an artifact (access controlled via contracts).

        Args:
            caller_id: Who is writing
            artifact_id: Artifact to write
            content: New content
            artifact_type: Type if creating new

        Returns:
            True if write succeeded, False otherwise
        """
        from src.world.executor import get_executor

        existing = self._world.artifacts.get(artifact_id)

        if existing is not None:
            # Update existing - check permission via contract (Plan #140)
            executor = get_executor()
            allowed, _reason = executor._check_permission(caller_id, "write", existing)
            if not allowed:
                return False
            existing.content = content
            return True
        else:
            # Create new
            self._world.artifacts.write(
                artifact_id, artifact_type, content, caller_id
            )
            return True

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
            return {"success": True, "submission_id": submission_id}
        except ValueError as e:
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
        return self._world.cancel_mint_submission(caller_id, submission_id)

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
            return False

        # Check source has sufficient quota
        from_quota = self._world.get_quota(from_id, resource)
        if from_quota < amount:
            return False

        # Perform atomic transfer
        to_quota = self._world.get_quota(to_id, resource)
        self._world.set_quota(from_id, resource, from_quota - amount)
        self._world.set_quota(to_id, resource, to_quota + amount)

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
        return self._world.consume_quota(principal_id, resource, amount)

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
        return self._world.delegation_manager.grant(
            caller_id,
            charger_id,
            max_per_call=max_per_call,
            max_per_window=max_per_window,
            window_seconds=window_seconds,
            expires_at=expires_at,
        )

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
        return self._world.delegation_manager.revoke(caller_id, charger_id)

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
        return self._world.delegation_manager.authorize_charge(
            charger_id, payer_id, amount
        )

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
            return {
                "success": False,
                "error": f"Invalid library name format: '{library_name}'",
                "error_code": "INVALID_NAME",
            }

        # Check blocklist
        if lib_lower in blocked_libs:
            return {
                "success": False,
                "error": f"Package '{library_name}' is blocked for security reasons",
                "error_code": "BLOCKED_PACKAGE",
            }

        # Check if genesis library (free, pre-installed)
        if lib_lower in genesis_libs:
            # Don't record - genesis libs are always available
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
                return {
                    "success": False,
                    "error": f"pip install failed: {error_msg}",
                    "error_code": "PIP_FAILED",
                }

        except subprocess.TimeoutExpired:
            return {
                "success": False,
                "error": "Package installation timed out (>120s)",
                "error_code": "TIMEOUT",
            }
        except Exception as e:
            return {
                "success": False,
                "error": f"Installation error: {str(e)}",
                "error_code": "INSTALL_ERROR",
            }

        # Installation succeeded - consume quota and record
        if not self._world.consume_quota(caller_id, "disk", float(estimated_size)):
            return {
                "success": False,
                "error": "Failed to consume disk quota",
                "error_code": "QUOTA_CONSUME_FAILED",
            }

        # Track installation in world state
        self._world.record_library_install(caller_id, library_name, version)

        return {
            "success": True,
            "message": f"Installed '{package_spec}' (quota cost: {estimated_size} bytes)",
            "quota_cost": estimated_size,
        }

    # -------------------------------------------------------------------------
    # Principal Management (Plan #111)
    # -------------------------------------------------------------------------

    def create_principal(
        self, principal_id: str, starting_scrip: int = 0, starting_compute: int = 0
    ) -> bool:
        """Create a new principal with optional starting resources.

        This is the single atomic operation for principal creation (Plan #231).
        Creates ledger entry, sets has_standing on artifact, and creates
        ResourceManager entry.

        Args:
            principal_id: ID for the new principal (must be unique)
            starting_scrip: Initial scrip balance (default 0)
            starting_compute: Initial compute allocation (default 0)

        Returns:
            True if principal created, False if already exists
        """
        # Check if principal already exists
        if self._world.ledger.principal_exists(principal_id):
            return False

        # 1. Ledger entry
        self._world.ledger.create_principal(
            principal_id,
            starting_scrip=starting_scrip,
            starting_compute=starting_compute
        )

        # 2. Artifact has_standing (Plan #231: ledger <-> has_standing invariant)
        if principal_id in self._world.artifacts.artifacts:
            self._world.artifacts.artifacts[principal_id].has_standing = True

        # 3. ResourceManager entry
        if hasattr(self._world, 'resource_manager'):
            self._world.resource_manager.create_principal(principal_id)

        return True

    def update_artifact_metadata(
        self, caller_id: str, artifact_id: str, key: str, value: object
    ) -> bool:
        """Update a single metadata key on an artifact (Plan #213).

        This is the canonical way to update artifact metadata, including
        "authorized_writer" for transferable_freeware contracts.

        Permission checking:
        - Caller must have WRITE permission on the artifact via its contract
        - This enables escrow to update authorized_writer after purchase

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
            return False

        # Check write permission via contract
        executor = get_executor()
        allowed, _reason = executor._check_permission(caller_id, "write", artifact)
        if not allowed:
            return False

        # Update the metadata
        if value is None:
            # Delete key if value is None
            artifact.metadata.pop(key, None)
        else:
            artifact.metadata[key] = value

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

