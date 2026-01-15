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

    def list_artifacts_by_owner(self, owner_id: str) -> list[str]:
        """List artifact IDs owned by a principal.

        Args:
            owner_id: The owner to query

        Returns:
            List of artifact IDs (empty if none found)
        """
        return self._world.artifacts.get_artifacts_by_owner(owner_id)

    def get_artifact_metadata(self, artifact_id: str) -> dict[str, Any] | None:
        """Get artifact metadata (not content).

        Args:
            artifact_id: The artifact to query

        Returns:
            Dict with id, type, owner_id, etc. or None if not found
        """
        artifact = self._world.artifacts.get(artifact_id)
        if artifact is None:
            return None

        return {
            "id": artifact.id,
            "type": artifact.type,
            "owner_id": artifact.owner_id,
            "executable": artifact.executable,
            "created_at": artifact.created_at,
            "updated_at": artifact.updated_at,
            "deleted": artifact.deleted,
        }

    def read_artifact(self, artifact_id: str, caller_id: str) -> str | None:
        """Read artifact content (access controlled).

        Args:
            artifact_id: The artifact to read
            caller_id: Who is requesting the read

        Returns:
            Artifact content if access allowed, None otherwise
        """
        artifact = self._world.artifacts.get(artifact_id)
        if artifact is None:
            return None

        # Check access - for now, default is public read
        # TODO: Implement proper access control via artifact policy
        policy = artifact.policy or {}
        allow_read = policy.get("allow_read", True)

        if not allow_read and artifact.owner_id != caller_id:
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

    def write_artifact(
        self,
        caller_id: str,
        artifact_id: str,
        content: str,
        artifact_type: str = "generic",
    ) -> bool:
        """Write or update an artifact owned by caller.

        Args:
            caller_id: Who is writing (must own artifact or create new)
            artifact_id: Artifact to write
            content: New content
            artifact_type: Type if creating new

        Returns:
            True if write succeeded, False otherwise
        """
        existing = self._world.artifacts.get(artifact_id)

        if existing is not None:
            # Update existing - must be owner
            if existing.owner_id != caller_id:
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
        from src.config import get_validated_config

        config = get_validated_config()
        genesis_libs = [lib.lower() for lib in config.libraries.genesis]
        blocked_libs = [lib.lower() for lib in config.libraries.blocked]

        lib_lower = library_name.lower()

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

        # Consume quota
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
            "message": f"Installed '{library_name}' (quota cost: {estimated_size} bytes)",
            "quota_cost": estimated_size,
        }
