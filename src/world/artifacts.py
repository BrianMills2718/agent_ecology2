"""Simple artifact store - in-memory dict of artifacts"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, TypedDict


# Type alias for policy allow fields: either a static list or a contract reference
PolicyAllow = list[str] | str


class PolicyDict(TypedDict, total=False):
    """Type for artifact policy dictionary."""

    read_price: int
    invoke_price: int
    allow_read: PolicyAllow
    allow_write: PolicyAllow
    allow_invoke: PolicyAllow


class ArtifactDict(TypedDict, total=False):
    """Type for artifact dictionary representation."""

    id: str
    type: str
    content: str
    owner_id: str
    created_at: str
    updated_at: str
    executable: bool
    price: int
    has_code: bool
    policy: PolicyDict


class WriteResult(TypedDict):
    """Result of an artifact write operation."""

    success: bool
    message: str
    data: dict[str, Any] | None


def is_contract_reference(value: PolicyAllow) -> bool:
    """Check if a policy value is a contract reference (starts with @)"""
    return isinstance(value, str) and value.startswith("@")


def default_policy() -> dict[str, Any]:
    """Default policy: public read, owner-only write, no invoke cost

    Policy allow fields support two formats (Hybrid Policy Schema):
    - Static list: ["*"] for everyone, ["alice", "bob"] for specific agents
    - Contract reference: "@contract_id" - defers decision to executable artifact

    Contract references enable:
    - DAOs and voting mechanisms
    - Complex conditional access (time-based, balance-based, etc.)
    - Contracts governing contracts (recursive governance)

    V1: Only static lists are enforced. Contract references raise NotImplementedError.
    V2: Contract references will invoke the artifact with (requester_id, action, target_id).
        Requester pays gas for policy check execution. Fail-closed on errors.
    """
    return {
        "read_price": 0,  # Scrip cost to read content
        "invoke_price": 0,  # Scrip cost to invoke (for executables)
        "allow_read": ["*"],  # Static list OR "@contract_id"
        "allow_write": [],  # Static list OR "@contract_id" (empty = owner only)
        "allow_invoke": ["*"],  # Static list OR "@contract_id"
    }


@dataclass
class Artifact:
    """An artifact in the world

    For executable artifacts:
    - executable=True enables invocation
    - policy["invoke_price"] is the service fee paid to owner
    - code contains the Python code with a run() function

    Policy dict controls access and pricing:
    - read_price: scrip cost to read this artifact
    - invoke_price: scrip cost to invoke (paid to owner)
    - allow_read: List or "@contract_id" - who can read
    - allow_write: List or "@contract_id" - who can modify (owner always can)
    - allow_invoke: List or "@contract_id" - who can invoke

    Hybrid Policy Schema:
    - Static lists (["*"], ["alice"]) are enforced by kernel (fast path)
    - Contract refs ("@dao_vote") defer to executable artifact (slow path, V2)
    """

    id: str
    type: str
    content: str
    owner_id: str
    created_at: str
    updated_at: str
    # Executable artifact fields
    executable: bool = False
    code: str = ""  # Python code (must define run() function)
    # Policy for access control and pricing
    policy: dict[str, Any] = field(default_factory=default_policy)

    @property
    def price(self) -> int:
        """Backwards compatibility: invoke_price from policy"""
        invoke_price = self.policy.get("invoke_price", 0)
        if isinstance(invoke_price, int):
            return invoke_price
        return 0

    def can_read(self, agent_id: str) -> bool:
        """Check if agent can read this artifact

        Raises NotImplementedError if policy uses @contract reference (V2 feature).
        """
        allow: PolicyAllow = self.policy.get("allow_read", ["*"])

        # V2: Contract-based policy (deferred)
        if is_contract_reference(allow):
            raise NotImplementedError(
                f"Dynamic policy contracts not yet supported. "
                f"Artifact '{self.id}' uses contract '{allow}' for read access. "
                f"V2 will invoke the contract with (requester={agent_id}, action='read', target={self.id})"
            )

        # V1: Static list policy (fast path)
        if isinstance(allow, list):
            return "*" in allow or agent_id in allow or agent_id == self.owner_id
        return agent_id == self.owner_id

    def can_write(self, agent_id: str) -> bool:
        """Check if agent can write to this artifact

        Owner always has write access.
        Raises NotImplementedError if policy uses @contract reference (V2 feature).
        """
        if agent_id == self.owner_id:
            return True

        allow: PolicyAllow = self.policy.get("allow_write", [])

        # V2: Contract-based policy (deferred)
        if is_contract_reference(allow):
            raise NotImplementedError(
                f"Dynamic policy contracts not yet supported. "
                f"Artifact '{self.id}' uses contract '{allow}' for write access. "
                f"V2 will invoke the contract with (requester={agent_id}, action='write', target={self.id})"
            )

        # V1: Static list policy (fast path)
        if isinstance(allow, list):
            return agent_id in allow
        return False

    def can_invoke(self, agent_id: str) -> bool:
        """Check if agent can invoke this artifact

        Raises NotImplementedError if policy uses @contract reference (V2 feature).
        """
        if not self.executable:
            return False

        allow: PolicyAllow = self.policy.get("allow_invoke", ["*"])

        # V2: Contract-based policy (deferred)
        if is_contract_reference(allow):
            raise NotImplementedError(
                f"Dynamic policy contracts not yet supported. "
                f"Artifact '{self.id}' uses contract '{allow}' for invoke access. "
                f"V2 will invoke the contract with (requester={agent_id}, action='invoke', target={self.id})"
            )

        # V1: Static list policy (fast path)
        if isinstance(allow, list):
            return "*" in allow or agent_id in allow or agent_id == self.owner_id
        return agent_id == self.owner_id

    def to_dict(self) -> dict[str, Any]:
        result: dict[str, Any] = {
            "id": self.id,
            "type": self.type,
            "content": self.content,
            "owner_id": self.owner_id,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
        }
        if self.executable:
            result["executable"] = True
            result["price"] = self.price
            # Don't include full code in listing - just indicate it exists
            result["has_code"] = bool(self.code)
        # Include policy if non-default
        if self.policy != default_policy():
            result["policy"] = self.policy
        return result


class ArtifactStore:
    """In-memory artifact storage"""

    artifacts: dict[str, Artifact]

    def __init__(self) -> None:
        self.artifacts = {}

    def exists(self, artifact_id: str) -> bool:
        """Check if artifact exists"""
        return artifact_id in self.artifacts

    def get(self, artifact_id: str) -> Artifact | None:
        """Get an artifact by ID"""
        return self.artifacts.get(artifact_id)

    def write(
        self,
        artifact_id: str,
        type: str,
        content: str,
        owner_id: str,
        executable: bool = False,
        price: int = 0,
        code: str = "",
        policy: dict[str, Any] | None = None,
    ) -> Artifact:
        """Create or update an artifact. Returns the artifact.

        For executable artifacts, set executable=True and provide:
        - price: Service fee paid to owner on invocation (or use policy["invoke_price"])
        - code: Python code containing a run() function

        Policy dict controls access:
        - read_price: cost to read
        - invoke_price: cost to invoke (overrides price param)
        - allow_read, allow_write, allow_invoke: access lists
        """
        now = datetime.utcnow().isoformat()

        # Build policy - start with defaults, apply overrides
        artifact_policy = default_policy()
        if policy:
            artifact_policy.update(policy)
        # Backwards compat: if price is set but invoke_price isn't, use price
        if price > 0 and artifact_policy.get("invoke_price", 0) == 0:
            artifact_policy["invoke_price"] = price

        if artifact_id in self.artifacts:
            # Update existing
            artifact = self.artifacts[artifact_id]
            artifact.content = content
            artifact.type = type
            artifact.updated_at = now
            artifact.executable = executable
            artifact.code = code
            artifact.policy = artifact_policy
        else:
            # Create new
            artifact = Artifact(
                id=artifact_id,
                type=type,
                content=content,
                owner_id=owner_id,
                created_at=now,
                updated_at=now,
                executable=executable,
                code=code,
                policy=artifact_policy,
            )
            self.artifacts[artifact_id] = artifact

        return artifact

    def get_owner(self, artifact_id: str) -> str | None:
        """Get owner of an artifact"""
        artifact = self.get(artifact_id)
        return artifact.owner_id if artifact else None

    def list_all(self) -> list[dict[str, Any]]:
        """List all artifacts"""
        return [a.to_dict() for a in self.artifacts.values()]

    def count(self) -> int:
        """Count total artifacts"""
        return len(self.artifacts)

    def get_artifact_size(self, artifact_id: str) -> int:
        """Get size of an artifact in bytes (content + code)"""
        artifact = self.get(artifact_id)
        if not artifact:
            return 0
        return len(artifact.content.encode("utf-8")) + len(
            artifact.code.encode("utf-8")
        )

    def get_owner_usage(self, owner_id: str) -> int:
        """Get total disk usage for an owner in bytes"""
        total = 0
        for artifact in self.artifacts.values():
            if artifact.owner_id == owner_id:
                total += len(artifact.content.encode("utf-8")) + len(
                    artifact.code.encode("utf-8")
                )
        return total

    def list_by_owner(self, owner_id: str) -> list[dict[str, Any]]:
        """List all artifacts owned by a principal"""
        return [a.to_dict() for a in self.artifacts.values() if a.owner_id == owner_id]

    def transfer_ownership(
        self, artifact_id: str, from_id: str, to_id: str
    ) -> bool:
        """Transfer ownership of an artifact.

        Args:
            artifact_id: The artifact to transfer
            from_id: Current owner (must match artifact.owner_id)
            to_id: New owner

        Returns:
            True if transfer succeeded, False otherwise
        """
        artifact = self.get(artifact_id)
        if not artifact:
            return False

        # Verify from_id is the current owner
        if artifact.owner_id != from_id:
            return False

        # Transfer ownership
        artifact.owner_id = to_id
        return True

    def write_artifact(
        self,
        artifact_id: str,
        artifact_type: str,
        content: str,
        owner_id: str,
        executable: bool = False,
        price: int = 0,
        code: str = "",
        policy: dict[str, Any] | None = None,
    ) -> WriteResult:
        """Write an artifact and return a standardized result.

        This is a higher-level wrapper around write() that returns a WriteResult
        with success status, message, and data. Used to deduplicate write logic
        in the world kernel.

        Args:
            artifact_id: Unique identifier for the artifact
            artifact_type: Type of artifact (e.g., "generic", "code")
            content: The artifact content
            owner_id: Owner principal ID
            executable: Whether the artifact is executable
            price: Service fee for invocation (for executables)
            code: Python code with run() function (for executables)
            policy: Optional access control policy

        Returns:
            WriteResult with success=True and artifact data, or success=False on error
        """
        self.write(
            artifact_id=artifact_id,
            type=artifact_type,
            content=content,
            owner_id=owner_id,
            executable=executable,
            price=price,
            code=code,
            policy=policy,
        )

        if executable:
            return {
                "success": True,
                "message": f"Wrote executable artifact {artifact_id} (price: {price})",
                "data": {"artifact_id": artifact_id, "executable": True, "price": price},
            }
        else:
            return {
                "success": True,
                "message": f"Wrote artifact {artifact_id}",
                "data": {"artifact_id": artifact_id},
            }
