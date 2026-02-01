"""Simple artifact store - in-memory dict of artifacts"""

# --- GOVERNANCE START (do not edit) ---
# ADR-0001: Everything is an artifact
#
# Core artifact storage and management.
# Everything is an artifact - agents, contracts, data.
# --- GOVERNANCE END ---
from __future__ import annotations

import json
import re
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, TypedDict, TYPE_CHECKING


def extract_invoke_targets(code: str) -> list[str]:
    """Extract artifact IDs from invoke() calls in code (Plan #170).

    Args:
        code: Python source code to analyze

    Returns:
        List of unique artifact IDs found as first arguments to invoke() calls.
        Sorted alphabetically for deterministic output.

    Note:
        This uses regex pattern matching which has limitations:
        - May miss dynamic targets like invoke(variable, ...)
        - May have false positives from string literals containing invoke()
        These limitations are acceptable - we capture the common case.
    """
    if not code:
        return []

    # Match: invoke("artifact_id", ...) or invoke('artifact_id', ...)
    # Allows whitespace between invoke and opening paren
    pattern = r'invoke\s*\(\s*["\']([^"\']+)["\']'
    matches = re.findall(pattern, code)

    # Deduplicate and sort for deterministic output
    unique_targets = sorted(set(matches))
    return unique_targets

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
    - has_loop=True: Can execute code autonomously (agents)
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
    has_loop: bool = False  # Can execute code autonomously
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
    access_contract_id: str = "kernel_contract_freeware"
    # User-defined metadata for addressing/categorization (Plan #168)
    # Arbitrary key-value pairs for agent use (recipient, tags, priority, etc.)
    metadata: dict[str, Any] = field(default_factory=dict)
    # Plan #235 Phase 1: Kernel protection (system field, not metadata)
    # Once True, only kernel primitives can modify this artifact
    kernel_protected: bool = False

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

        Agents are artifacts with both has_standing=True AND has_loop=True.
        They are principals that can also:
        - Execute code autonomously
        - Make decisions via LLM
        - Take actions in the world

        A principal without has_loop (e.g., a DAO) can own things but
        cannot act autonomously - it requires external invocation.
        """
        return self.has_standing and self.has_loop

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
        if self.has_loop:
            result["has_loop"] = True
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
        # Include kernel_protected if set (Plan #235 Phase 1)
        if self.kernel_protected:
            result["kernel_protected"] = True
        # Include metadata if any (Plan #168)
        if self.metadata:
            result["metadata"] = self.metadata
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

        available = ["id", "type", "content", "created_by", "executable", "interface", "policy", "metadata"]

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
    access_contract_id: str = "kernel_contract_self_owned",
) -> Artifact:
    """Factory function to create an agent artifact.

    Creates an artifact configured as an autonomous agent with:
    - has_standing=True: Can own things, enter contracts
    - has_loop=True: Can execute code autonomously
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
    if access_contract_id == "kernel_contract_self_owned":
        # Self-owned: only owner/self can access
        artifact_policy["allow_read"] = []
        artifact_policy["allow_write"] = []
        artifact_policy["allow_invoke"] = []
    elif access_contract_id == "kernel_contract_private":
        # Private: only owner can access
        artifact_policy["allow_read"] = []
        artifact_policy["allow_write"] = []
        artifact_policy["allow_invoke"] = []
    elif access_contract_id == "kernel_contract_public":
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
        has_loop=True,
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
    - has_loop=False: Memory is passive storage

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
        has_loop=False,
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
        has_loop=False,
        memory_artifact_id=None,
        interface=interface,
    )


class ArtifactStore:
    """In-memory artifact storage with O(1) index lookups (Plan #182)

    Args:
        id_registry: Optional IDRegistry for global ID collision prevention (Plan #7).
                     When provided, new artifact IDs are registered and collisions
                     raise IDCollisionError.
        indexed_metadata_fields: List of metadata field names to index for O(1) lookups.
                                 Supports dot notation for nested fields (e.g., "tags.priority").
    """

    artifacts: dict[str, Artifact]
    id_registry: "IDRegistry | None"
    # Plan #182: Indexes for O(1) lookups
    _index_by_type: dict[str, set[str]]  # type -> {artifact_ids}
    _index_by_creator: dict[str, set[str]]  # creator -> {artifact_ids}
    _index_by_metadata: dict[str, dict[Any, set[str]]]  # field -> {value -> {artifact_ids}}
    _indexed_metadata_fields: set[str]  # Which metadata fields to index

    def __init__(
        self,
        id_registry: "IDRegistry | None" = None,
        indexed_metadata_fields: list[str] | None = None,
    ) -> None:
        self.artifacts = {}
        self.id_registry = id_registry
        # Plan #182: Initialize indexes
        self._index_by_type = defaultdict(set)
        self._index_by_creator = defaultdict(set)
        self._index_by_metadata = {}
        self._indexed_metadata_fields = set(indexed_metadata_fields or [])

    # Plan #182: Index maintenance methods
    def _get_nested_value(self, data: dict[str, Any] | None, path: str) -> Any:
        """Get a value from a nested dict using dot notation.

        Returns None if path doesn't exist or data is None.
        """
        if not data:
            return None
        keys = path.split(".")
        value: Any = data
        for key in keys:
            if isinstance(value, dict) and key in value:
                value = value[key]
            else:
                return None
        return value

    def _add_to_index(self, artifact: Artifact) -> None:
        """Add artifact to all indexes."""
        artifact_id = artifact.id
        # Index by type
        self._index_by_type[artifact.type].add(artifact_id)
        # Index by owner
        self._index_by_creator[artifact.created_by].add(artifact_id)
        # Index configured metadata fields
        for field in self._indexed_metadata_fields:
            value = self._get_nested_value(artifact.metadata, field)
            if value is not None:
                if field not in self._index_by_metadata:
                    self._index_by_metadata[field] = defaultdict(set)
                self._index_by_metadata[field][value].add(artifact_id)

    def _remove_from_index(self, artifact: Artifact) -> None:
        """Remove artifact from all indexes."""
        artifact_id = artifact.id
        # Remove from type index
        self._index_by_type[artifact.type].discard(artifact_id)
        # Remove from owner index
        self._index_by_creator[artifact.created_by].discard(artifact_id)
        # Remove from metadata indexes
        for field in self._indexed_metadata_fields:
            value = self._get_nested_value(artifact.metadata, field)
            if value is not None and field in self._index_by_metadata:
                self._index_by_metadata[field][value].discard(artifact_id)

    def _update_index(self, old_artifact: Artifact, new_artifact: Artifact) -> None:
        """Update indexes when artifact changes."""
        artifact_id = old_artifact.id
        # Update type index if changed
        if old_artifact.type != new_artifact.type:
            self._index_by_type[old_artifact.type].discard(artifact_id)
            self._index_by_type[new_artifact.type].add(artifact_id)
        # Update owner index if changed
        if old_artifact.created_by != new_artifact.created_by:
            self._index_by_creator[old_artifact.created_by].discard(artifact_id)
            self._index_by_creator[new_artifact.created_by].add(artifact_id)
        # Update metadata indexes
        for field in self._indexed_metadata_fields:
            old_value = self._get_nested_value(old_artifact.metadata, field)
            new_value = self._get_nested_value(new_artifact.metadata, field)
            if old_value != new_value:
                # Remove old value
                if old_value is not None and field in self._index_by_metadata:
                    self._index_by_metadata[field][old_value].discard(artifact_id)
                # Add new value
                if new_value is not None:
                    if field not in self._index_by_metadata:
                        self._index_by_metadata[field] = defaultdict(set)
                    self._index_by_metadata[field][new_value].add(artifact_id)

    def query_by_type(self, artifact_type: str) -> list[Artifact]:
        """Query artifacts by type using O(1) index lookup (Plan #182)."""
        ids = self._index_by_type.get(artifact_type, set())
        return [self.artifacts[id] for id in ids if id in self.artifacts]

    def query_by_creator(self, creator: str) -> list[Artifact]:
        """Query artifacts by creator using O(1) index lookup (Plan #182).

        This queries by created_by (immutable). To query by current
        controller, use query_by_metadata("controller", controller_id).
        """
        ids = self._index_by_creator.get(creator, set())
        return [self.artifacts[id] for id in ids if id in self.artifacts]

    # Backwards compatibility alias (deprecated)
    def query_by_owner(self, owner: str) -> list[Artifact]:
        """Deprecated: Use query_by_creator() instead."""
        return self.query_by_creator(owner)

    def query_by_metadata(self, field: str, value: Any) -> list[Artifact]:
        """Query artifacts by metadata field using O(1) index lookup (Plan #182).

        Returns empty list if field is not indexed. Use add_indexed_field() first.
        """
        if field not in self._indexed_metadata_fields:
            return []  # Field not indexed
        ids = self._index_by_metadata.get(field, {}).get(value, set())
        return [self.artifacts[id] for id in ids if id in self.artifacts]

    def is_field_indexed(self, field: str) -> bool:
        """Check if a metadata field is indexed (Plan #182)."""
        return field in self._indexed_metadata_fields

    def add_indexed_field(self, field: str) -> None:
        """Add a metadata field to the index (Plan #182).

        This will index all existing artifacts for this field.
        """
        if field in self._indexed_metadata_fields:
            return  # Already indexed
        self._indexed_metadata_fields.add(field)
        self._index_by_metadata[field] = defaultdict(set)
        # Index all existing artifacts
        for artifact_id, artifact in self.artifacts.items():
            value = self._get_nested_value(artifact.metadata, field)
            if value is not None:
                self._index_by_metadata[field][value].add(artifact_id)

    def get_indexed_fields(self) -> set[str]:
        """Get the set of indexed metadata fields (Plan #182)."""
        return self._indexed_metadata_fields.copy()

    def rebuild_indexes(self) -> None:
        """Rebuild all indexes from existing artifacts (Plan #182).

        Use this after bulk-loading artifacts directly into self.artifacts
        without using write(). This ensures indexes are consistent.
        """
        # Clear existing indexes
        self._index_by_type.clear()
        self._index_by_creator.clear()
        self._index_by_metadata.clear()

        # Rebuild from all artifacts
        for artifact in self.artifacts.values():
            self._add_to_index(artifact)

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
        metadata: dict[str, Any] | None = None,
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
        - access_contract_id: Contract ID for permission checking (default: kernel_contract_freeware)

        Metadata (Plan #168):
        - metadata: User-defined key-value pairs for addressing/categorization
        """
        now = datetime.now(timezone.utc).isoformat()
        depends_on = depends_on or []
        metadata = metadata or {}

        # Plan #170: Auto-extract invoke targets for executable artifacts
        if executable and code:
            invokes = extract_invoke_targets(code)
            if invokes:
                metadata["invokes"] = invokes

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

            # Plan #235 Phase 1 (FM-1/FM-2): kernel_protected blocks all user modifications
            if artifact.kernel_protected:
                raise PermissionError(
                    f"Artifact '{artifact_id}' is kernel_protected: "
                    "modification only via kernel primitives"
                )

            # Plan #235 Phase 0 (FM-6): type is immutable after creation
            if type != artifact.type:
                raise ValueError(
                    f"Cannot change artifact type from '{artifact.type}' to '{type}'"
                )

            # Plan #235 Phase 0 (FM-7): Only creator can change access_contract_id
            if (access_contract_id is not None
                    and access_contract_id != artifact.access_contract_id
                    and created_by != artifact.created_by):
                raise PermissionError(
                    f"Only creator '{artifact.created_by}' can change access_contract_id"
                )

            # Plan #182: Capture old state for index update
            old_type = artifact.type
            old_owner = artifact.created_by
            old_metadata = artifact.metadata.copy() if artifact.metadata else {}

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
            # Plan #168: Update metadata (always replace, even with empty dict)
            artifact.metadata = metadata

            # Plan #182: Update indexes if relevant fields changed
            if old_type != type:
                self._index_by_type[old_type].discard(artifact_id)
                self._index_by_type[type].add(artifact_id)
            if old_owner != artifact.created_by:
                self._index_by_creator[old_owner].discard(artifact_id)
                self._index_by_creator[artifact.created_by].add(artifact_id)
            for field in self._indexed_metadata_fields:
                old_value = self._get_nested_value(old_metadata, field)
                new_value = self._get_nested_value(metadata, field)
                if old_value != new_value:
                    if old_value is not None and field in self._index_by_metadata:
                        self._index_by_metadata[field][old_value].discard(artifact_id)
                    if new_value is not None:
                        if field not in self._index_by_metadata:
                            self._index_by_metadata[field] = defaultdict(set)
                        self._index_by_metadata[field][new_value].add(artifact_id)
        else:
            # Plan #235 Phase 1 (FM-4): Reserved ID namespace enforcement
            if artifact_id.startswith("charge_delegation:"):
                expected_owner = artifact_id.split(":", 1)[1]
                if created_by != expected_owner:
                    raise PermissionError(
                        f"Cannot create charge_delegation artifact for another principal "
                        f"(caller='{created_by}', owner='{expected_owner}')"
                    )
            elif artifact_id.startswith("right:"):
                if created_by != "system":
                    raise PermissionError(
                        f"Cannot create right: artifact - only system/kernel can create rights "
                        f"(caller='{created_by}')"
                    )

            # Create new - register with ID registry if available (Plan #7)
            if self.id_registry is not None:
                # Import here to avoid circular imports at module level
                from .id_registry import IDCollisionError, EntityType
                # Determine entity type for registry
                entity_type: EntityType = "genesis" if type == "genesis" else "artifact"
                self.id_registry.register(artifact_id, entity_type)
            # Determine access contract - use provided or default
            contract_id = access_contract_id if access_contract_id else "kernel_contract_freeware"
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
                metadata=metadata,
            )
            self.artifacts[artifact_id] = artifact
            # Plan #182: Add new artifact to indexes
            self._add_to_index(artifact)

        return artifact

    def modify_protected_content(
        self,
        artifact_id: str,
        *,
        content: str | None = None,
        code: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> "Artifact":
        """Kernel-only: modify a kernel_protected artifact.

        Plan #235 Phase 1: This method bypasses kernel_protected checks.
        It is NOT exposed to user-facing action paths (write_artifact/edit_artifact).
        Only kernel primitives should call this method.

        Args:
            artifact_id: The artifact to modify
            content: New content (None = keep existing)
            code: New code (None = keep existing)
            metadata: New metadata (None = keep existing)

        Returns:
            The modified artifact

        Raises:
            KeyError: If artifact doesn't exist
        """
        artifact = self.artifacts[artifact_id]
        now = datetime.now(timezone.utc).isoformat()
        if content is not None:
            artifact.content = content
        if code is not None:
            artifact.code = code
        if metadata is not None:
            artifact.metadata = metadata
        artifact.updated_at = now
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

    def get_creator(self, artifact_id: str) -> str | None:
        """Get creator of an artifact (immutable historical fact).

        Per ADR-0016, created_by is immutable and records who originally
        created the artifact. Note that "ownership" is not a kernel concept -
        contracts decide access. Some genesis artifacts (like escrow) may use
        metadata["controller"] as their own convention.
        """
        artifact = self.get(artifact_id)
        return artifact.created_by if artifact else None

    # Backwards compatibility alias (deprecated)
    def get_owner(self, artifact_id: str) -> str | None:
        """Deprecated: Use get_creator() instead."""
        return self.get_creator(artifact_id)

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

    def get_creator_usage(self, creator: str) -> int:
        """Get total disk usage for artifacts created by a principal.

        Plan #182: Uses O(1) index lookup instead of O(n) scan.
        Deleted artifacts do not count toward disk usage (Plan #57).

        Note: This queries by created_by (immutable creator), not
        current controller.
        """
        total = 0
        artifact_ids = self._index_by_creator.get(creator, set())
        for artifact_id in artifact_ids:
            artifact = self.artifacts.get(artifact_id)
            if artifact and not artifact.deleted:
                total += len(artifact.content.encode("utf-8")) + len(
                    artifact.code.encode("utf-8")
                )
        return total

    # Backwards compatibility alias (deprecated)
    def get_owner_usage(self, created_by: str) -> int:
        """Deprecated: Use get_creator_usage() instead."""
        return self.get_creator_usage(created_by)

    def list_by_creator(self, creator: str) -> list[dict[str, Any]]:
        """List all artifacts created by a principal.

        Plan #182: Uses O(1) index lookup instead of O(n) scan.

        Note: This queries by created_by (immutable creator), not
        current controller.
        """
        artifact_ids = self._index_by_creator.get(creator, set())
        return [
            self.artifacts[id].to_dict()
            for id in artifact_ids
            if id in self.artifacts
        ]

    # Backwards compatibility alias (deprecated)
    def list_by_owner(self, created_by: str) -> list[dict[str, Any]]:
        """Deprecated: Use list_by_creator() instead."""
        return self.list_by_creator(created_by)

    def get_artifacts_by_creator(
        self, creator: str, include_deleted: bool = False
    ) -> list[str]:
        """Get artifact IDs created by a principal.

        Plan #182: Uses O(1) index lookup instead of O(n) scan.

        Note: This queries by created_by (immutable creator), not
        current controller.

        Args:
            creator: Principal ID to query
            include_deleted: If True, include deleted artifacts (Plan #18)

        Returns:
            List of artifact IDs created by the principal
        """
        artifact_ids = self._index_by_creator.get(creator, set())
        result = []
        for artifact_id in artifact_ids:
            artifact = self.artifacts.get(artifact_id)
            if artifact:
                if include_deleted or not artifact.deleted:
                    result.append(artifact_id)
        return result

    # Backwards compatibility alias (deprecated)
    def get_artifacts_by_owner(
        self, created_by: str, include_deleted: bool = False
    ) -> list[str]:
        """Deprecated: Use get_artifacts_by_creator() instead."""
        return self.get_artifacts_by_creator(created_by, include_deleted)

    def transfer_ownership(
        self, artifact_id: str, from_id: str, to_id: str
    ) -> bool:
        """Set metadata["controller"] on an artifact.

        NOTE: This is likely tech debt from before ADR-0016. It sets metadata
        but does NOT affect access control under standard genesis contracts
        (freeware, self_owned, private), which check created_by not controller.

        Per ADR-0016:
        - created_by is immutable (historical fact)
        - "Ownership" is not a kernel concept - contracts decide access
        - This method sets metadata["controller"] which custom contracts could use

        Args:
            artifact_id: The artifact to update
            from_id: Current controller (must match metadata["controller"] or created_by)
            to_id: New controller value to set in metadata

        Returns:
            True if metadata was updated, False otherwise
        """
        artifact = self.get(artifact_id)
        if not artifact:
            return False

        # Verify from_id matches current controller (or creator if no controller set)
        current_controller = artifact.metadata.get("controller", artifact.created_by)
        if current_controller != from_id:
            return False

        # Set metadata (note: doesn't affect access under freeware/self_owned/private)
        artifact.metadata["controller"] = to_id
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
        metadata: dict[str, Any] | None = None,
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
            metadata: (Plan #168) User-defined key-value pairs

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
                metadata=metadata,
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
