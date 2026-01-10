"""Simple artifact store - in-memory dict of artifacts"""

from dataclasses import dataclass, field
from typing import Dict, Optional, Any, List, Union
from datetime import datetime


# Type alias for policy allow fields: either a static list or a contract reference
PolicyAllow = Union[List[str], str]


def is_contract_reference(value: PolicyAllow) -> bool:
    """Check if a policy value is a contract reference (starts with @)"""
    return isinstance(value, str) and value.startswith("@")


def default_policy() -> Dict[str, Any]:
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
        "read_price": 0,        # Scrip cost to read content
        "invoke_price": 0,      # Scrip cost to invoke (for executables)
        "allow_read": ["*"],    # Static list OR "@contract_id"
        "allow_write": [],      # Static list OR "@contract_id" (empty = owner only)
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
    policy: Dict[str, Any] = field(default_factory=default_policy)

    @property
    def price(self) -> int:
        """Backwards compatibility: invoke_price from policy"""
        return self.policy.get("invoke_price", 0)

    def can_read(self, agent_id: str) -> bool:
        """Check if agent can read this artifact

        Raises NotImplementedError if policy uses @contract reference (V2 feature).
        """
        allow = self.policy.get("allow_read", ["*"])

        # V2: Contract-based policy (deferred)
        if is_contract_reference(allow):
            raise NotImplementedError(
                f"Dynamic policy contracts not yet supported. "
                f"Artifact '{self.id}' uses contract '{allow}' for read access. "
                f"V2 will invoke the contract with (requester={agent_id}, action='read', target={self.id})"
            )

        # V1: Static list policy (fast path)
        return "*" in allow or agent_id in allow or agent_id == self.owner_id

    def can_write(self, agent_id: str) -> bool:
        """Check if agent can write to this artifact

        Owner always has write access.
        Raises NotImplementedError if policy uses @contract reference (V2 feature).
        """
        if agent_id == self.owner_id:
            return True

        allow = self.policy.get("allow_write", [])

        # V2: Contract-based policy (deferred)
        if is_contract_reference(allow):
            raise NotImplementedError(
                f"Dynamic policy contracts not yet supported. "
                f"Artifact '{self.id}' uses contract '{allow}' for write access. "
                f"V2 will invoke the contract with (requester={agent_id}, action='write', target={self.id})"
            )

        # V1: Static list policy (fast path)
        return agent_id in allow

    def can_invoke(self, agent_id: str) -> bool:
        """Check if agent can invoke this artifact

        Raises NotImplementedError if policy uses @contract reference (V2 feature).
        """
        if not self.executable:
            return False

        allow = self.policy.get("allow_invoke", ["*"])

        # V2: Contract-based policy (deferred)
        if is_contract_reference(allow):
            raise NotImplementedError(
                f"Dynamic policy contracts not yet supported. "
                f"Artifact '{self.id}' uses contract '{allow}' for invoke access. "
                f"V2 will invoke the contract with (requester={agent_id}, action='invoke', target={self.id})"
            )

        # V1: Static list policy (fast path)
        return "*" in allow or agent_id in allow or agent_id == self.owner_id

    def to_dict(self) -> Dict[str, Any]:
        result = {
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

    def __init__(self):
        self.artifacts: Dict[str, Artifact] = {}

    def exists(self, artifact_id: str) -> bool:
        """Check if artifact exists"""
        return artifact_id in self.artifacts

    def get(self, artifact_id: str) -> Optional[Artifact]:
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
        policy: Dict[str, Any] = None
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
                policy=artifact_policy
            )
            self.artifacts[artifact_id] = artifact

        return artifact

    def get_owner(self, artifact_id: str) -> Optional[str]:
        """Get owner of an artifact"""
        artifact = self.get(artifact_id)
        return artifact.owner_id if artifact else None

    def list_all(self) -> list:
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
        return len(artifact.content.encode('utf-8')) + len(artifact.code.encode('utf-8'))

    def get_owner_usage(self, owner_id: str) -> int:
        """Get total disk usage for an owner in bytes"""
        total = 0
        for artifact in self.artifacts.values():
            if artifact.owner_id == owner_id:
                total += len(artifact.content.encode('utf-8')) + len(artifact.code.encode('utf-8'))
        return total

    def list_by_owner(self, owner_id: str) -> list:
        """List all artifacts owned by a principal"""
        return [
            a.to_dict() for a in self.artifacts.values()
            if a.owner_id == owner_id
        ]
