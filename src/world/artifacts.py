"""Simple artifact store - in-memory dict of artifacts"""

# --- GOVERNANCE START (do not edit) ---
# ADR-0001: Everything is an artifact
#
# Core artifact storage and management.
# Everything is an artifact - agents, contracts, data.
# --- GOVERNANCE END ---
from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, TypedDict, TYPE_CHECKING

if TYPE_CHECKING:
    from .genesis import GenesisMethod
    from .id_registry import IDRegistry


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
    interface: dict[str, Any]  # Plan #14: JSON Schema for discoverability


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
        Fail-closed on errors.
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

    Principal capabilities (GAP-AGENT-001 Unified Ontology):
    - has_standing=True: Can own things, be party to contracts (principals)
    - can_execute=True: Can execute code autonomously (agents)
    - memory_artifact_id: Link to separate memory artifact (for agents)

    Interface schema (Plan #14 Artifact Interface Schema):
    - interface: Optional JSON Schema describing inputs/outputs
    - Enables discoverability - agents can learn how to invoke without reading code
    - Uses MCP-compatible format (but not strict MCP protocol)

    Use is_principal property to check if artifact can own things.
    Use is_agent property to check if artifact is an autonomous agent.
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
    # Principal capabilities (GAP-AGENT-001)
    has_standing: bool = False  # Can own things, be party to contracts
    can_execute: bool = False  # Can execute code autonomously
    # For agents: link to memory artifact
    memory_artifact_id: str | None = None
    # Soft deletion fields (Plan #18: Dangling Reference Handling)
    deleted: bool = False
    deleted_at: str | None = None
    deleted_by: str | None = None
    # Interface schema for discoverability (Plan #14: Artifact Interface Schema)
    # JSON Schema format (MCP-compatible but not strict MCP)
    # Optional - only useful for executable artifacts
    interface: dict[str, Any] | None = None
    # Genesis method dispatch (Plan #15: invoke() Genesis Support)
    # If set, this artifact uses method dispatch instead of code execution
    # Enables unified invoke path for genesis and user artifacts
    genesis_methods: dict[str, "GenesisMethod"] | None = None

    @property
    def price(self) -> int:
        """Backwards compatibility: invoke_price from policy"""
        invoke_price = self.policy.get("invoke_price", 0)
        if isinstance(invoke_price, int):
            return invoke_price
        return 0

    @property
    def is_principal(self) -> bool:
        """Can this artifact own things and enter contracts?

        Principals are artifacts with has_standing=True. They can:
        - Own other artifacts
        - Hold scrip balances
        - Be party to contracts
        - Have ledger entries

        Examples: agents, DAOs, escrow contracts
        """
        return self.has_standing

    @property
    def is_agent(self) -> bool:
        """Is this an autonomous agent?

        Agents are artifacts with both has_standing=True AND can_execute=True.
        They are principals that can also:
        - Execute code autonomously
        - Make decisions via LLM
        - Take actions in the world

        A principal without can_execute (e.g., a DAO) can own things but
        cannot act autonomously - it requires external invocation.
        """
        return self.has_standing and self.can_execute

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
        # Include principal capabilities if set (GAP-AGENT-001)
        if self.has_standing:
            result["has_standing"] = True
        if self.can_execute:
            result["can_execute"] = True
        if self.memory_artifact_id is not None:
            result["memory_artifact_id"] = self.memory_artifact_id
        # Include deletion fields if deleted (Plan #18)
        if self.deleted:
            result["deleted"] = True
            result["deleted_at"] = self.deleted_at
            result["deleted_by"] = self.deleted_by
        # Include interface if set (Plan #14)
        if self.interface is not None:
            result["interface"] = self.interface
        return result


def create_agent_artifact(
    agent_id: str,
    owner_id: str,
    agent_config: dict[str, Any],
    memory_artifact_id: str | None = None,
    access_contract_id: str = "genesis_contract_self_owned",
) -> Artifact:
    """Factory function to create an agent artifact.

    Creates an artifact configured as an autonomous agent with:
    - has_standing=True: Can own things, enter contracts
    - can_execute=True: Can execute code autonomously
    - artifact_type="agent"
    - Self-owned access contract by default

    Args:
        agent_id: Unique ID for the agent
        owner_id: Who owns this agent (can be self-owned: owner_id == agent_id)
        agent_config: Agent configuration stored as content (model, prompt, etc.)
        memory_artifact_id: Optional linked memory artifact
        access_contract_id: Access control contract (default: self_owned)

    Returns:
        Artifact configured as an agent

    Example:
        >>> agent = create_agent_artifact(
        ...     agent_id="agent_001",
        ...     owner_id="agent_001",  # Self-owned
        ...     agent_config={"model": "gpt-4", "system_prompt": "You are helpful."}
        ... )
        >>> agent.is_agent
        True
        >>> agent.is_principal
        True
    """
    now = datetime.utcnow().isoformat()

    # Build policy based on access contract
    # Note: This is a simple mapping - full contract integration comes later
    artifact_policy = default_policy()
    if access_contract_id == "genesis_contract_self_owned":
        # Self-owned: only owner/self can access
        artifact_policy["allow_read"] = []
        artifact_policy["allow_write"] = []
        artifact_policy["allow_invoke"] = []
    elif access_contract_id == "genesis_contract_private":
        # Private: only owner can access
        artifact_policy["allow_read"] = []
        artifact_policy["allow_write"] = []
        artifact_policy["allow_invoke"] = []
    elif access_contract_id == "genesis_contract_public":
        # Public: anyone can access
        artifact_policy["allow_read"] = ["*"]
        artifact_policy["allow_write"] = ["*"]
        artifact_policy["allow_invoke"] = ["*"]
    # freeware is default: read/invoke open, write owner-only

    # Serialize config to string for content field
    content = json.dumps(agent_config)

    return Artifact(
        id=agent_id,
        type="agent",
        content=content,
        owner_id=owner_id,
        created_at=now,
        updated_at=now,
        executable=False,  # Agents don't use the executable code path
        code="",
        policy=artifact_policy,
        has_standing=True,
        can_execute=True,
        memory_artifact_id=memory_artifact_id,
    )


def create_memory_artifact(
    memory_id: str,
    owner_id: str,
    initial_content: dict[str, Any] | None = None,
) -> Artifact:
    """Factory function to create a memory artifact.

    Creates an artifact for storing agent memory with:
    - artifact_type="memory"
    - Self-owned access contract (private by default)
    - has_standing=False: Memory cannot own things
    - can_execute=False: Memory is passive storage

    Memory is private by default because it often contains:
    - Agent reasoning traces
    - Private knowledge
    - Internal state

    Args:
        memory_id: Unique ID for the memory artifact
        owner_id: Who owns this memory (usually the agent)
        initial_content: Initial memory content (default: empty history/knowledge)

    Returns:
        Artifact configured as memory storage

    Example:
        >>> memory = create_memory_artifact(
        ...     memory_id="agent_001_memory",
        ...     owner_id="agent_001",
        ... )
        >>> memory.is_agent
        False
        >>> memory.is_principal
        False
    """
    now = datetime.utcnow().isoformat()

    # Default memory structure
    if initial_content is None:
        initial_content = {"history": [], "knowledge": {}}

    # Self-owned policy: only owner can access
    artifact_policy = default_policy()
    artifact_policy["allow_read"] = []
    artifact_policy["allow_write"] = []
    artifact_policy["allow_invoke"] = []

    # Serialize content to string
    content = json.dumps(initial_content)

    return Artifact(
        id=memory_id,
        type="memory",
        content=content,
        owner_id=owner_id,
        created_at=now,
        updated_at=now,
        executable=False,
        code="",
        policy=artifact_policy,
        has_standing=False,
        can_execute=False,
        memory_artifact_id=None,
    )


class ArtifactStore:
    """In-memory artifact storage
    
    Args:
        id_registry: Optional IDRegistry for global ID collision prevention (Plan #7).
                     When provided, new artifact IDs are registered and collisions 
                     raise IDCollisionError.
    """

    artifacts: dict[str, Artifact]
    id_registry: "IDRegistry | None"

    def __init__(self, id_registry: "IDRegistry | None" = None) -> None:
        self.artifacts = {}
        self.id_registry = id_registry

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
            # Create new - register with ID registry if available (Plan #7)
            if self.id_registry is not None:
                # Import here to avoid circular imports at module level
                from .id_registry import IDCollisionError, EntityType
                # Determine entity type for registry
                entity_type: EntityType = "genesis" if type == "genesis" else "artifact"
                self.id_registry.register(artifact_id, entity_type)
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

    def list_all(self, include_deleted: bool = False) -> list[dict[str, Any]]:
        """List all artifacts.

        Args:
            include_deleted: If True, include deleted artifacts (Plan #18)
        """
        if include_deleted:
            return [a.to_dict() for a in self.artifacts.values()]
        return [a.to_dict() for a in self.artifacts.values() if not a.deleted]

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

    def get_artifacts_by_owner(
        self, owner_id: str, include_deleted: bool = False
    ) -> list[str]:
        """Get artifact IDs owned by a principal.

        Args:
            owner_id: Principal ID to query
            include_deleted: If True, include deleted artifacts (Plan #18)

        Returns:
            List of artifact IDs owned by the principal
        """
        result = []
        for artifact_id, artifact in self.artifacts.items():
            if artifact.owner_id == owner_id:
                if include_deleted or not artifact.deleted:
                    result.append(artifact_id)
        return result

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
