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
from datetime import datetime, timezone
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
    created_by: str
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
    created_by: str
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
    # Declared dependencies (Plan #63: Artifact Dependencies)
    # List of artifact IDs this artifact depends on
    # Dependencies are resolved and injected at invocation time
    depends_on: list[str] = field(default_factory=list)
    # Access contract for permission checking (Plan #100: Contract System Overhaul)
    # All permissions are checked via contracts - no hardcoded owner bypass
    access_contract_id: str = "genesis_contract_freeware"

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

    def to_dict(self) -> dict[str, Any]:
        result: dict[str, Any] = {
            "id": self.id,
            "type": self.type,
            "content": self.content,
            "created_by": self.created_by,
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
        # Include dependencies if any (Plan #63)
        if self.depends_on:
            result["depends_on"] = self.depends_on
        return result

    def __getattr__(self, name: str) -> Any:
        """Plan #161: Provide helpful error messages for common attribute typos.

        This is called when an attribute doesn't exist. We suggest correct
        attribute names to help agents learn from their mistakes.
        """
        # Common typos and their corrections
        suggestions: dict[str, str] = {
            "artifact_type": "type",
            "artifact_id": "id",
            "owner": "created_by",
            "creator": "created_by",
            "name": "id",
        }

        available = ["id", "type", "content", "created_by", "executable", "interface", "policy"]

        if name in suggestions:
            correct = suggestions[name]
            raise AttributeError(
                f"'{type(self).__name__}' has no attribute '{name}'. "
                f"Did you mean '{correct}'? Available: {available}"
            )

        raise AttributeError(
            f"'{type(self).__name__}' has no attribute '{name}'. "
            f"Available: {available}"
        )


def create_agent_artifact(
    agent_id: str,
    created_by: str,
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
        created_by: Who owns this agent (can be self-owned: created_by == agent_id)
        agent_config: Agent configuration stored as content (model, prompt, etc.)
        memory_artifact_id: Optional linked memory artifact
        access_contract_id: Access control contract (default: self_owned)

    Returns:
        Artifact configured as an agent

    Example:
        >>> agent = create_agent_artifact(
        ...     agent_id="agent_001",
        ...     created_by="agent_001",  # Self-owned
        ...     agent_config={"model": "gpt-4", "system_prompt": "You are helpful."}
        ... )
        >>> agent.is_agent
        True
        >>> agent.is_principal
        True
    """
    now = datetime.now(timezone.utc).isoformat()

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
        created_by=created_by,
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
    created_by: str,
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
        created_by: Who owns this memory (usually the agent)
        initial_content: Initial memory content (default: empty history/knowledge)

    Returns:
        Artifact configured as memory storage

    Example:
        >>> memory = create_memory_artifact(
        ...     memory_id="agent_001_memory",
        ...     created_by="agent_001",
        ... )
        >>> memory.is_agent
        False
        >>> memory.is_principal
        False
    """
    now = datetime.now(timezone.utc).isoformat()

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
        created_by=created_by,
        created_at=now,
        updated_at=now,
        executable=False,
        code="",
        policy=artifact_policy,
        has_standing=False,
        can_execute=False,
        memory_artifact_id=None,
    )


def create_config_artifact(
    config_id: str,
    created_by: str,
    config: dict[str, Any],
) -> Artifact:
    """Factory function to create a config artifact (Plan #160).

    Creates an artifact for storing agent configuration with:
    - artifact_type="config"
    - Self-owned access (only the agent can read/modify)
    - Callable interface for get/set operations

    This enables cognitive self-modification: agents can inspect and
    adjust their own configuration (temperature, max_tokens, etc.)
    during runtime.

    Args:
        config_id: Unique ID for the config artifact (e.g., "agent_001_config")
        created_by: Who owns this config (usually the agent)
        config: Initial configuration dict

    Returns:
        Artifact configured as config storage

    Example:
        >>> config = create_config_artifact(
        ...     config_id="agent_001_config",
        ...     created_by="agent_001",
        ...     config={"temperature": 0.7, "max_tokens": 1024}
        ... )
        >>> config.type
        'config'
    """
    now = datetime.now(timezone.utc).isoformat()

    # Self-owned policy: only owner can access
    artifact_policy = default_policy()
    artifact_policy["allow_read"] = []
    artifact_policy["allow_write"] = []
    artifact_policy["allow_invoke"] = []

    # Serialize content to string
    content = json.dumps(config)

    # Interface for invoking config operations
    interface = {
        "description": "Agent configuration. Invoke describe() first, then get/set values.",
        "tools": [
            {
                "name": "get",
                "description": "Get a configuration value by key",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "key": {"type": "string", "description": "Config key to retrieve"}
                    },
                    "required": ["key"]
                }
            },
            {
                "name": "set",
                "description": "Set a configuration value",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "key": {"type": "string", "description": "Config key to set"},
                        "value": {"description": "New value for the config key"}
                    },
                    "required": ["key", "value"]
                }
            },
            {
                "name": "list_keys",
                "description": "List all available config keys",
                "inputSchema": {
                    "type": "object",
                    "properties": {}
                }
            }
        ]
    }

    return Artifact(
        id=config_id,
        type="config",
        content=content,
        created_by=created_by,
        created_at=now,
        updated_at=now,
        executable=True,  # Invoke enabled for get/set
        code="",  # Uses genesis method dispatch
        policy=artifact_policy,
        has_standing=False,
        can_execute=False,
        memory_artifact_id=None,
        interface=interface,
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
        created_by: str,
        executable: bool = False,
        price: int = 0,
        code: str = "",
        policy: dict[str, Any] | None = None,
        depends_on: list[str] | None = None,
        depth_limit: int = 10,
        interface: dict[str, Any] | None = None,
        require_interface: bool = False,
        access_contract_id: str | None = None,
    ) -> Artifact:
        """Create or update an artifact. Returns the artifact.

        For executable artifacts, set executable=True and provide:
        - price: Service fee paid to owner on invocation (or use policy["invoke_price"])
        - code: Python code containing a run() function
        - interface: (Plan #114) Interface schema describing methods/inputs

        Policy dict controls access:
        - read_price: cost to read
        - invoke_price: cost to invoke (overrides price param)
        - allow_read, allow_write, allow_invoke: access lists

        Dependencies (Plan #63):
        - depends_on: List of artifact IDs this artifact depends on
        - depth_limit: Maximum transitive dependency depth (default 10)

        Interface requirement (Plan #114):
        - interface: JSON schema describing artifact's methods and inputs
        - require_interface: If True, raise error for executables without interface

        Access contract (Plan #100):
        - access_contract_id: Contract ID for permission checking (default: genesis_contract_freeware)
        """
        now = datetime.now(timezone.utc).isoformat()
        depends_on = depends_on or []

        # Plan #114: Validate interface requirement for executables
        if executable and require_interface and interface is None:
            raise ValueError(
                f"Interface schema required for executable artifact '{artifact_id}'. "
                "Provide an interface dict with 'description' and 'tools' keys describing "
                "the artifact's methods and their input schemas."
            )

        # Validate dependencies (Plan #63)
        if depends_on:
            self._validate_dependencies(artifact_id, depends_on, depth_limit)

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
            artifact.depends_on = depends_on
            if interface is not None:
                artifact.interface = interface
            if access_contract_id is not None:
                artifact.access_contract_id = access_contract_id
        else:
            # Create new - register with ID registry if available (Plan #7)
            if self.id_registry is not None:
                # Import here to avoid circular imports at module level
                from .id_registry import IDCollisionError, EntityType
                # Determine entity type for registry
                entity_type: EntityType = "genesis" if type == "genesis" else "artifact"
                self.id_registry.register(artifact_id, entity_type)
            # Determine access contract - use provided or default
            contract_id = access_contract_id if access_contract_id else "genesis_contract_freeware"
            artifact = Artifact(
                id=artifact_id,
                type=type,
                content=content,
                created_by=created_by,
                created_at=now,
                updated_at=now,
                executable=executable,
                code=code,
                policy=artifact_policy,
                depends_on=depends_on,
                interface=interface,
                access_contract_id=contract_id,
            )
            self.artifacts[artifact_id] = artifact

        return artifact

    def _validate_dependencies(
        self,
        artifact_id: str,
        depends_on: list[str],
        depth_limit: int,
    ) -> None:
        """Validate dependencies for an artifact.

        Raises ValueError if:
        - A dependency doesn't exist
        - Adding dependencies would create a cycle
        - Transitive dependency depth exceeds limit
        """
        # Check for self-reference (direct cycle)
        if artifact_id in depends_on:
            raise ValueError(
                f"Cycle detected: artifact '{artifact_id}' cannot depend on itself"
            )

        # Check all dependencies exist
        for dep_id in depends_on:
            if not self.exists(dep_id):
                raise ValueError(f"Dependency '{dep_id}' does not exist")

        # Check for cycles using DFS
        # Build temporary graph including the new artifact
        if self._would_create_cycle(artifact_id, depends_on):
            raise ValueError(
                f"Cycle detected: adding dependencies {depends_on} to '{artifact_id}' "
                "would create a dependency cycle"
            )

        # Check depth limit
        # max_depth is the depth of the deepest dependency
        # Adding this artifact would create depth max_depth + 1
        max_depth = self._calculate_max_depth(depends_on)
        new_depth = max_depth + 1
        if new_depth >= depth_limit:
            raise ValueError(
                f"Dependency depth limit exceeded: adding '{artifact_id}' would create "
                f"chain of depth {new_depth}, limit is {depth_limit}"
            )

    def _would_create_cycle(self, artifact_id: str, new_deps: list[str]) -> bool:
        """Check if adding new_deps to artifact_id would create a cycle.

        Uses DFS to detect if any transitive dependency of new_deps
        points back to artifact_id.
        """
        visited: set[str] = set()

        def dfs(current_id: str) -> bool:
            """Return True if we find artifact_id in transitive deps."""
            if current_id == artifact_id:
                return True
            if current_id in visited:
                return False
            visited.add(current_id)

            artifact = self.get(current_id)
            if artifact is None:
                return False

            for dep_id in artifact.depends_on:
                if dfs(dep_id):
                    return True
            return False

        # Check each new dependency
        for dep_id in new_deps:
            if dfs(dep_id):
                return True
        return False

    def _calculate_max_depth(self, depends_on: list[str]) -> int:
        """Calculate the maximum transitive dependency depth.

        Returns the depth of the deepest dependency chain.
        """
        if not depends_on:
            return 0

        memo: dict[str, int] = {}

        def depth(artifact_id: str) -> int:
            if artifact_id in memo:
                return memo[artifact_id]

            artifact = self.get(artifact_id)
            if artifact is None or not artifact.depends_on:
                memo[artifact_id] = 0
                return 0

            max_child_depth = 0
            for dep_id in artifact.depends_on:
                child_depth = depth(dep_id)
                max_child_depth = max(max_child_depth, child_depth)

            result = max_child_depth + 1
            memo[artifact_id] = result
            return result

        return max(depth(dep_id) for dep_id in depends_on)

    def get_owner(self, artifact_id: str) -> str | None:
        """Get owner of an artifact"""
        artifact = self.get(artifact_id)
        return artifact.created_by if artifact else None

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

    def get_owner_usage(self, created_by: str) -> int:
        """Get total disk usage for an owner in bytes.
        
        Deleted artifacts do not count toward disk usage (Plan #57).
        """
        total = 0
        for artifact in self.artifacts.values():
            if artifact.created_by == created_by and not artifact.deleted:
                total += len(artifact.content.encode("utf-8")) + len(
                    artifact.code.encode("utf-8")
                )
        return total

    def list_by_owner(self, created_by: str) -> list[dict[str, Any]]:
        """List all artifacts owned by a principal"""
        return [a.to_dict() for a in self.artifacts.values() if a.created_by == created_by]

    def get_artifacts_by_owner(
        self, created_by: str, include_deleted: bool = False
    ) -> list[str]:
        """Get artifact IDs owned by a principal.

        Args:
            created_by: Principal ID to query
            include_deleted: If True, include deleted artifacts (Plan #18)

        Returns:
            List of artifact IDs owned by the principal
        """
        result = []
        for artifact_id, artifact in self.artifacts.items():
            if artifact.created_by == created_by:
                if include_deleted or not artifact.deleted:
                    result.append(artifact_id)
        return result

    def transfer_ownership(
        self, artifact_id: str, from_id: str, to_id: str
    ) -> bool:
        """Transfer ownership of an artifact.

        Args:
            artifact_id: The artifact to transfer
            from_id: Current owner (must match artifact.created_by)
            to_id: New owner

        Returns:
            True if transfer succeeded, False otherwise
        """
        artifact = self.get(artifact_id)
        if not artifact:
            return False

        # Verify from_id is the current owner
        if artifact.created_by != from_id:
            return False

        # Transfer ownership
        artifact.created_by = to_id
        return True

    def write_artifact(
        self,
        artifact_id: str,
        artifact_type: str,
        content: str,
        created_by: str,
        executable: bool = False,
        price: int = 0,
        code: str = "",
        policy: dict[str, Any] | None = None,
        interface: dict[str, Any] | None = None,
        require_interface: bool = False,
        access_contract_id: str | None = None,
    ) -> WriteResult:
        """Write an artifact and return a standardized result.

        This is a higher-level wrapper around write() that returns a WriteResult
        with success status, message, and data. Used to deduplicate write logic
        in the world kernel.

        Args:
            artifact_id: Unique identifier for the artifact
            artifact_type: Type of artifact (e.g., "generic", "code")
            content: The artifact content
            created_by: Owner principal ID
            executable: Whether the artifact is executable
            price: Service fee for invocation (for executables)
            code: Python code with run() function (for executables)
            policy: Optional access control policy
            interface: (Plan #114) Interface schema for executables
            require_interface: (Plan #114) If True, require interface for executables
            access_contract_id: (Plan #100) Contract ID for permission checking

        Returns:
            WriteResult with success=True and artifact data, or success=False on error
        """
        try:
            self.write(
                artifact_id=artifact_id,
                type=artifact_type,
                content=content,
                created_by=created_by,
                executable=executable,
                price=price,
                code=code,
                policy=policy,
                interface=interface,
                require_interface=require_interface,
                access_contract_id=access_contract_id,
            )
        except ValueError as e:
            # Plan #114: Handle interface requirement validation
            return {
                "success": False,
                "message": str(e),
                "data": {"artifact_id": artifact_id, "error": str(e)},
            }

        # Plan #160: Improved success feedback with economic context
        content_size = len(content.encode('utf-8'))
        if executable:
            # Count interface methods if available
            method_count = 0
            if interface and "tools" in interface:
                method_count = len(interface.get("tools", []))
            method_info = f", {method_count} method(s)" if method_count else ""
            return {
                "success": True,
                "message": f"Wrote executable artifact {artifact_id} (price: {price} scrip{method_info}). Others pay you {price} scrip each time they invoke it.",
                "data": {"artifact_id": artifact_id, "executable": True, "price": price, "size": content_size},
            }
        else:
            return {
                "success": True,
                "message": f"Wrote artifact {artifact_id} ({content_size} bytes, type: {artifact_type})",
                "data": {"artifact_id": artifact_id, "size": content_size, "type": artifact_type},
            }

    def edit_artifact(
        self,
        artifact_id: str,
        old_string: str,
        new_string: str,
    ) -> WriteResult:
        """Edit an artifact using Claude Code-style string replacement.

        Plan #131: Enables precise, surgical edits without rewriting entire content.
        Uses old_string/new_string approach where old_string must be unique.

        Args:
            artifact_id: The artifact to edit
            old_string: The string to find and replace (must be unique in content)
            new_string: The string to replace it with

        Returns:
            WriteResult with success=True if edit applied, False on error

        Errors:
            - Artifact not found
            - Artifact is deleted
            - old_string not found in content
            - old_string appears multiple times (not unique)
            - old_string equals new_string (no-op)
        """
        # Get the artifact
        artifact = self.get(artifact_id)
        if artifact is None:
            return {
                "success": False,
                "message": f"Artifact '{artifact_id}' not found",
                "data": {"artifact_id": artifact_id, "error": "not_found"},
            }

        # Check if deleted
        if artifact.deleted:
            return {
                "success": False,
                "message": f"Artifact '{artifact_id}' has been deleted",
                "data": {"artifact_id": artifact_id, "error": "deleted"},
            }

        # Check if old_string equals new_string
        if old_string == new_string:
            return {
                "success": False,
                "message": "old_string and new_string must be different",
                "data": {"artifact_id": artifact_id, "error": "no_change"},
            }

        # Check for old_string in content
        count = artifact.content.count(old_string)
        if count == 0:
            return {
                "success": False,
                "message": f"old_string not found in artifact '{artifact_id}'",
                "data": {"artifact_id": artifact_id, "error": "not_found_in_content"},
            }

        if count > 1:
            return {
                "success": False,
                "message": f"old_string appears {count} times in artifact '{artifact_id}' (must be unique)",
                "data": {"artifact_id": artifact_id, "error": "not_unique", "count": count},
            }

        # Apply the edit
        artifact.content = artifact.content.replace(old_string, new_string, 1)
        artifact.updated_at = datetime.now(timezone.utc).isoformat()

        return {
            "success": True,
            "message": f"Edited artifact '{artifact_id}'",
            "data": {"artifact_id": artifact_id},
        }
