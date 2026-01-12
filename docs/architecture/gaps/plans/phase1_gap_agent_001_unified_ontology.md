# GAP-AGENT-001: Unified Ontology (Agents as Artifacts) Implementation Plan

**Gap ID:** GAP-AGENT-001
**Complexity:** XL (500+ lines, cross-component)
**Risk:** Medium
**Phase:** 1 - Foundations

---

## Summary

Transform agents from a separate entity type into artifacts with special properties. Agents become artifacts with `has_standing=true` (can own things, enter contracts) and `can_execute=true` (can run code). This enables agent trading, unified ownership model, and cleaner architecture.

---

## Current State

- Agents are a separate class from Artifacts
- Agent data stored separately from artifact store
- Cannot transfer agent ownership
- Dual tracking of agents vs artifacts
- Memory and agent state tightly coupled

---

## Target State

- Agents are artifacts with `has_standing=true` and `can_execute=true`
- Agent "definition" stored as artifact content
- Agent ownership transferable via standard artifact transfer
- Single ontology for all entities
- Memory as separate artifact (enables trading)

---

## Files to Modify

| File | Changes |
|------|---------|
| `src/world/artifacts.py` | Add `has_standing`, `can_execute` fields |
| `src/agents/agent.py` | Refactor to work with artifact storage |
| `src/agents/loader.py` | Load agents from artifacts |
| `src/world/world.py` | Unified agent/artifact management |
| `src/world/genesis.py` | Create agent artifacts |
| `config/schema.yaml` | Agent artifact configuration |
| `tests/test_agent_artifacts.py` | **NEW FILE** - Agent as artifact tests |

---

## Implementation Steps

### Step 1: Extend Artifact Model

Update `src/world/artifacts.py`:

```python
from dataclasses import dataclass, field
from typing import Any, Optional, Literal

@dataclass
class Artifact:
    """
    Universal artifact type.

    Special flags enable artifact-based entities:
    - has_standing=True: Can own things, enter contracts (principals)
    - can_execute=True: Can execute code, run autonomously (agents)
    """

    artifact_id: str
    artifact_type: str  # "agent", "contract", "data", "code", etc.
    owner_id: str
    content: Any

    # Access control
    access_contract_id: str = "genesis_contract_freeware"

    # Principal capabilities
    has_standing: bool = False  # Can own things, be party to contracts
    can_execute: bool = False   # Can execute code autonomously

    # Metadata
    created_at: float = field(default_factory=lambda: time.time())
    updated_at: float = field(default_factory=lambda: time.time())

    # For agents: link to memory artifact
    memory_artifact_id: Optional[str] = None

    @property
    def is_principal(self) -> bool:
        """Can this artifact own things and enter contracts?"""
        return self.has_standing

    @property
    def is_agent(self) -> bool:
        """Is this an autonomous agent?"""
        return self.has_standing and self.can_execute

    def to_dict(self) -> dict:
        """Serialize artifact."""
        return {
            "artifact_id": self.artifact_id,
            "artifact_type": self.artifact_type,
            "owner_id": self.owner_id,
            "content": self.content,
            "access_contract_id": self.access_contract_id,
            "has_standing": self.has_standing,
            "can_execute": self.can_execute,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "memory_artifact_id": self.memory_artifact_id,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "Artifact":
        """Deserialize artifact."""
        return cls(**data)


def create_agent_artifact(
    agent_id: str,
    owner_id: str,
    agent_config: dict,
    memory_artifact_id: Optional[str] = None,
    access_contract_id: str = "genesis_contract_self_owned",
) -> Artifact:
    """
    Factory function to create an agent artifact.

    Args:
        agent_id: Unique ID for the agent
        owner_id: Who owns this agent (can be self-owned)
        agent_config: Agent configuration (model, prompt, etc.)
        memory_artifact_id: Optional linked memory artifact
        access_contract_id: Access control contract

    Returns:
        Artifact configured as an agent
    """
    return Artifact(
        artifact_id=agent_id,
        artifact_type="agent",
        owner_id=owner_id,
        content=agent_config,
        access_contract_id=access_contract_id,
        has_standing=True,
        can_execute=True,
        memory_artifact_id=memory_artifact_id,
    )


def create_memory_artifact(
    memory_id: str,
    owner_id: str,  # Usually the agent
    initial_content: Optional[dict] = None,
) -> Artifact:
    """
    Factory function to create a memory artifact.

    Memory is private by default (self_owned contract).
    """
    return Artifact(
        artifact_id=memory_id,
        artifact_type="memory",
        owner_id=owner_id,
        content=initial_content or {"history": [], "knowledge": {}},
        access_contract_id="genesis_contract_self_owned",
        has_standing=False,
        can_execute=False,
    )
```

### Step 2: Refactor Agent Class

Update `src/agents/agent.py`:

```python
from dataclasses import dataclass, field
from typing import Optional, Any
from ..world.artifacts import Artifact

@dataclass
class Agent:
    """
    Runtime representation of an agent.

    Backed by an artifact with has_standing=True and can_execute=True.
    The artifact stores persistent state; this class handles runtime behavior.
    """

    # Reference to backing artifact
    artifact: Artifact

    # Runtime state (not persisted in artifact)
    alive: bool = True
    _memory_cache: Optional[dict] = field(default=None)

    @property
    def agent_id(self) -> str:
        return self.artifact.artifact_id

    @property
    def owner_id(self) -> str:
        return self.artifact.owner_id

    @property
    def config(self) -> dict:
        """Agent configuration from artifact content."""
        return self.artifact.content

    @property
    def memory_artifact_id(self) -> Optional[str]:
        return self.artifact.memory_artifact_id

    @classmethod
    def from_artifact(cls, artifact: Artifact) -> "Agent":
        """Create agent runtime from artifact."""
        if not artifact.is_agent:
            raise ValueError(
                f"Artifact {artifact.artifact_id} is not an agent "
                f"(has_standing={artifact.has_standing}, can_execute={artifact.can_execute})"
            )
        return cls(artifact=artifact)

    def to_artifact(self) -> Artifact:
        """Get the backing artifact."""
        return self.artifact

    async def get_memory(self, world: "World") -> dict:
        """Load memory from memory artifact."""
        if self._memory_cache is not None:
            return self._memory_cache

        if not self.memory_artifact_id:
            self._memory_cache = {"history": [], "knowledge": {}}
            return self._memory_cache

        memory_artifact = world.store.get(self.memory_artifact_id)
        if memory_artifact:
            self._memory_cache = memory_artifact.content
        else:
            self._memory_cache = {"history": [], "knowledge": {}}

        return self._memory_cache

    async def save_memory(self, world: "World") -> None:
        """Save memory to memory artifact."""
        if not self.memory_artifact_id or self._memory_cache is None:
            return

        memory_artifact = world.store.get(self.memory_artifact_id)
        if memory_artifact:
            memory_artifact.content = self._memory_cache
            memory_artifact.updated_at = time.time()
            world.store.update(memory_artifact)

    async def decide_action(self) -> Optional[dict]:
        """Decide what action to take."""
        if not self.alive:
            return None
        # ... existing decision logic ...
        return await self._generate_action()

    async def execute_action(self, action: dict) -> dict:
        """Execute a decided action."""
        # ... existing execution logic ...
        pass

    def shutdown(self) -> None:
        """Mark agent for shutdown."""
        self.alive = False
```

### Step 3: Update Agent Loader

Update `src/agents/loader.py`:

```python
from typing import List, Optional
from ..world.artifacts import Artifact, create_agent_artifact, create_memory_artifact
from .agent import Agent

class AgentLoader:
    """Loads agents from artifacts."""

    def __init__(self, world: "World"):
        self.world = world

    def load_agent(self, agent_id: str) -> Optional[Agent]:
        """Load an agent from artifact store."""
        artifact = self.world.store.get(agent_id)

        if not artifact:
            return None

        if not artifact.is_agent:
            raise ValueError(f"{agent_id} is not an agent artifact")

        return Agent.from_artifact(artifact)

    def load_all_agents(self) -> List[Agent]:
        """Load all agents from artifact store."""
        agents = []

        for artifact in self.world.store.list_by_type("agent"):
            if artifact.is_agent:
                agents.append(Agent.from_artifact(artifact))

        return agents

    def create_agent(
        self,
        agent_id: str,
        owner_id: Optional[str] = None,
        agent_config: Optional[dict] = None,
        create_memory: bool = True,
    ) -> Agent:
        """
        Create a new agent with backing artifacts.

        Args:
            agent_id: Unique agent ID
            owner_id: Who owns the agent (defaults to self)
            agent_config: Agent configuration
            create_memory: Whether to create memory artifact
        """
        # Self-owned by default
        if owner_id is None:
            owner_id = agent_id

        # Default config
        if agent_config is None:
            agent_config = {
                "model": "default",
                "system_prompt": "",
            }

        # Create memory artifact first if requested
        memory_artifact_id = None
        if create_memory:
            memory_id = f"{agent_id}_memory"
            memory_artifact = create_memory_artifact(
                memory_id=memory_id,
                owner_id=agent_id,  # Memory owned by agent
            )
            self.world.store.create_artifact(memory_artifact)
            memory_artifact_id = memory_id

        # Create agent artifact
        agent_artifact = create_agent_artifact(
            agent_id=agent_id,
            owner_id=owner_id,
            agent_config=agent_config,
            memory_artifact_id=memory_artifact_id,
        )
        self.world.store.create_artifact(agent_artifact)

        # Return runtime agent
        return Agent.from_artifact(agent_artifact)

    def transfer_agent(self, agent_id: str, new_owner_id: str) -> None:
        """
        Transfer agent ownership.

        This is now just a standard artifact transfer.
        """
        artifact = self.world.store.get(agent_id)
        if not artifact or not artifact.is_agent:
            raise ValueError(f"Agent {agent_id} not found")

        # Use standard artifact transfer
        self.world.store.transfer(
            artifact_id=agent_id,
            from_owner=artifact.owner_id,
            to_owner=new_owner_id,
        )
```

### Step 4: Update World Class

Update `src/world/world.py`:

```python
class World:
    def __init__(self, ...):
        # ... existing init ...
        self.agent_loader = AgentLoader(self)
        self._running_agents: Dict[str, Agent] = {}

    def get_agent(self, agent_id: str) -> Optional[Agent]:
        """Get running agent by ID."""
        if agent_id in self._running_agents:
            return self._running_agents[agent_id]

        # Try to load from artifacts
        agent = self.agent_loader.load_agent(agent_id)
        if agent:
            self._running_agents[agent_id] = agent
        return agent

    def get_all_agents(self) -> List[Agent]:
        """Get all agents (running or loadable)."""
        # Load any agents not yet in running dict
        for agent in self.agent_loader.load_all_agents():
            if agent.agent_id not in self._running_agents:
                self._running_agents[agent.agent_id] = agent
        return list(self._running_agents.values())

    def is_principal(self, principal_id: str) -> bool:
        """Check if ID refers to a principal (agent or other standing artifact)."""
        artifact = self.store.get(principal_id)
        if artifact:
            return artifact.has_standing
        return principal_id == "genesis"  # Genesis is always a principal
```

### Step 5: Update Genesis Artifact Creation

Update `src/world/genesis.py`:

```python
from .artifacts import create_agent_artifact, create_memory_artifact

def create_genesis_agents(world: "World", agent_configs: List[dict]) -> None:
    """Create initial agents as artifacts."""

    for config in agent_configs:
        agent_id = config["id"]

        # Create memory artifact
        memory_id = f"{agent_id}_memory"
        memory_artifact = create_memory_artifact(
            memory_id=memory_id,
            owner_id=agent_id,
        )
        world.store.create_artifact(memory_artifact)

        # Create agent artifact
        agent_artifact = create_agent_artifact(
            agent_id=agent_id,
            owner_id=agent_id,  # Self-owned
            agent_config={
                "model": config.get("model", "default"),
                "system_prompt": config.get("system_prompt", ""),
                "initial_scrip": config.get("initial_scrip", 1000),
            },
            memory_artifact_id=memory_id,
        )
        world.store.create_artifact(agent_artifact)

        # Initialize balance
        world.ledger.set_balance(agent_id, config.get("initial_scrip", 1000))
```

### Step 6: Add Configuration

Update `config/schema.yaml`:

```yaml
agents:
  use_artifact_storage: true  # Feature flag
  default_access_contract: "genesis_contract_self_owned"
  create_memory_artifact: true
  initial_agents:
    - id: "agent_001"
      model: "default"
      initial_scrip: 1000
```

---

## Interface Definition

```python
@dataclass
class Artifact:
    artifact_id: str
    artifact_type: str
    owner_id: str
    content: Any
    access_contract_id: str
    has_standing: bool  # NEW
    can_execute: bool   # NEW
    memory_artifact_id: Optional[str]  # NEW

    @property
    def is_principal(self) -> bool: ...
    @property
    def is_agent(self) -> bool: ...

class Agent:
    artifact: Artifact
    alive: bool

    @classmethod
    def from_artifact(cls, artifact: Artifact) -> "Agent": ...
    def to_artifact(self) -> Artifact: ...
    async def get_memory(self, world: World) -> dict: ...
    async def save_memory(self, world: World) -> None: ...
```

---

## Migration Strategy

1. **Phase 1A:** Add `has_standing`, `can_execute` fields to Artifact (default False)
2. **Phase 1B:** Add `memory_artifact_id` field to Artifact
3. **Phase 1C:** Implement `Agent.from_artifact()` and factory functions
4. **Phase 1D:** Add feature flag `use_artifact_storage: false`
5. **Phase 1E:** Update AgentLoader to work with artifacts
6. **Phase 1F:** Run tests with both storage modes
7. **Phase 1G:** Enable `use_artifact_storage: true` by default
8. **Phase 2:** Remove legacy agent storage code

---

## Test Cases

| Test | Description | Expected |
|------|-------------|----------|
| `test_agent_is_artifact` | Agent stored as artifact | `artifact.is_agent == True` |
| `test_has_standing` | Agent has standing | `artifact.has_standing == True` |
| `test_can_execute` | Agent can execute | `artifact.can_execute == True` |
| `test_memory_artifact` | Memory stored separately | Memory artifact exists |
| `test_load_from_artifact` | Agent loads from store | Agent runtime works |
| `test_transfer_agent` | Agent ownership transfers | New owner owns agent |
| `test_agent_owns_memory` | Agent owns its memory | Memory ownership correct |
| `test_non_agent_artifact` | Regular artifact flags | `has_standing=False` |
| `test_factory_function` | Factory creates correct artifact | All fields set correctly |

---

## Acceptance Criteria

- [ ] Agents are stored as artifacts in artifact store
- [ ] Artifacts have `has_standing` and `can_execute` fields
- [ ] Agent ownership can be transferred via artifact transfer
- [ ] Memory is a separate artifact owned by agent
- [ ] `Agent.from_artifact()` creates runtime from artifact
- [ ] All existing agent functionality works
- [ ] Feature flag for migration
- [ ] All tests pass

---

## Rollback Plan

If issues arise:
1. Set `use_artifact_storage: false` in config
2. System falls back to legacy agent storage
3. Debug artifact-based agents in isolation
4. Fix and re-enable

---

## Dependencies

- **Requires:** GAP-GEN-001 (contract system for access_contract_id)
- **Required for:** GAP-AGENT-006 (memory as separate tradeable artifact)
- **Required for:** Agent trading via artifact transfer
- **Blocks:** Phase 2 agent stream
