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

from typing import TYPE_CHECKING, Any

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
