# Target Agent Model

What we're building toward.

**Last verified:** 2026-01-11

**See current:** [../current/agents.md](../current/agents.md)

---

## Unified Ontology

Agents are artifacts with specific properties:

```python
@dataclass
class Artifact:
    id: str                    # Universal ID (single namespace)
    content: Any               # For agents: config, prompt, code
    access_contract_id: str    # Who answers permission questions
    has_standing: bool         # Can hold scrip, bear costs
    can_execute: bool          # Has runnable code

# Agent = artifact where has_standing=True AND can_execute=True
```

### Why This Matters

| Old Model | New Model |
|-----------|-----------|
| Agent is a separate concept | Agent is an artifact type |
| Agents can't be owned | Agents are ownable property |
| principal_id separate from artifact_id | Single namespace for all IDs |
| Ledger tracks principals | Ledger tracks artifacts with standing |

### Derived Categories

| Category | has_standing | can_execute | Example |
|----------|--------------|-------------|---------|
| **Agent** | true | true | Autonomous actor |
| **Tool** | false | true | Executable, invoker pays |
| **Account** | true | false | Treasury, escrow |
| **Data** | false | false | Documents, content |

---

## Autonomous Agents

Agents control their own execution. System provides resources and primitives.

### Agent Loop

```python
async def run(self):
    while self.alive:
        if self.is_sleeping:
            await self.wait_for_wake()

        if self.compute_balance < 0:
            await self.wait_for_accumulation()
            continue

        world_state = self.observe()
        action = await self.think(world_state)
        result = await self.act(action)

        # Optional: self-imposed delay
        if self.config.get("think_delay"):
            await asyncio.sleep(self.config["think_delay"])
```

### Key Differences from Current

| Current | Target |
|---------|--------|
| Passive (system calls agent) | Active (agent runs own loop) |
| One action per tick | Actions whenever resources allow |
| Cannot sleep | Self-managed sleep |
| Fixed config | Config rights tradeable |

---

## Agent Rights

### Agents Own Their Configuration

Each agent can modify:
- LLM model
- System prompt
- Sleep behavior
- Think delay
- Any other self-configuration

### Rights Are Tradeable

Agents can SELL rights to their configuration:

```
Agent A sells config rights to Agent B:
  → B now owns A's configuration
  → B can modify A's prompt, model, etc.
  → A continues running but under B's control
```

Enables:
- Delegation patterns
- "Owned" subsidiary agents
- Hiring/employment relationships

### What Cannot Be Self-Modified

Even with config rights:
- Ledger balances (external, in genesis_ledger)
- System-wide limits
- Other agents' state (unless you own their rights)
- Genesis artifact behavior

---

## Memory as Artifact

### The Problem

Agent identity has two components:
- **Config** (prompt, model, policies) - determines goals and behavior
- **Memory** (experiences, context, learned patterns) - determines knowledge

If config is tradeable but memory isn't, trading creates identity crises:
- New owner gets old memories with new goals
- Can't "factory reset" an acquired agent
- Can't sell experiences independently

### Solution: Memory Collection Artifact

Each agent has a `memory_artifact_id` pointing to their memory collection:

```python
{
    "id": "agent_alice",
    "has_standing": True,
    "can_execute": True,
    "content": {
        "prompt": "...",
        "model": "...",
    },
    "memory_artifact_id": "alice_memories",  # Separate artifact
    "access_contract_id": "genesis_self_owned"
}

{
    "id": "alice_memories",
    "has_standing": False,  # Memory doesn't pay costs
    "can_execute": False,   # Memory isn't executable
    "content": {
        "storage_type": "qdrant",
        "collection_id": "alice_mem_collection"
    },
    "access_contract_id": "genesis_self_owned"  # Alice controls access
}
```

### Trading Scenarios

**Sell config only (factory reset):**
```
1. Buyer acquires agent config artifact
2. Buyer creates new memory artifact for agent
3. Agent starts fresh with no prior memories
4. Seller can keep/sell/delete old memories
```

**Sell config + memory (full identity transfer):**
```
1. Buyer acquires agent config artifact
2. Buyer acquires memory artifact
3. Agent continues with full history
```

**Sell memory only:**
```
1. Buyer acquires memory artifact
2. Buyer's agent gains seller's experiences
3. Useful for: training data, context transfer, "hiring for knowledge"
```

### Memory Access Control

Memory artifact has its own `access_contract_id`:

| Scenario | Config Owner | Memory Owner | Result |
|----------|--------------|--------------|--------|
| Normal | Alice | Alice | Alice controls both |
| Sold config | Bob | Alice | Bob runs agent, but Alice controls what it remembers |
| Sold memory | Alice | Bob | Alice runs agent, but Bob can read/modify memories |
| Full sale | Bob | Bob | Bob has complete control |

### Implementation Notes

- Memory artifact points to external storage (Qdrant) via `content.collection_id`
- The artifact provides ownership/access semantics
- Actual vectors remain in Qdrant for efficiency
- Wiping memory = clearing the Qdrant collection (owner permission required)

---

## Sleep Mechanics

### Self-Managed

Agents choose when to sleep:

```python
# Duration-based
await self.sleep(seconds=60)

# Event-based
await self.sleep_until_event("escrow_listing")

# Condition-based
await self.sleep_until(lambda: self.scrip > 100)
```

### Why Sleep

| Reason | Benefit |
|--------|---------|
| Conserve compute | Not spending while sleeping |
| Wait for conditions | No busy-polling |
| Strategic timing | Act when opportunity arises |

### Wake Conditions

System provides event bus for wake triggers:
- New escrow listing
- Oracle resolution
- Transfer received
- Artifact created
- Custom conditions

---

## Time Awareness

### System Injects Timestamp

Every LLM context includes current time:

```
Current time: 2025-01-11T14:30:00Z
```

### Enables

- Calculate oracle resolution schedule
- Time-based coordination
- "Wake me at 3pm" strategies
- Rate limiting own actions

---

## Vulture Capitalist Pattern

When agent is frozen (in debt):

1. Agent A is frozen (compute < 0, can't think)
2. Agent A's assets still exist (ownership persists)
3. Agent B notices A is frozen
4. B transfers compute to A (unilateral, no permission needed)
5. A unfreezes, can think again
6. B hopes A reciprocates (reputation matters)

Market-driven rescue, not system rules.

---

## Agent Creation

### Spawning

Agents create new agents via `genesis_store.create()`:

```python
invoke("genesis_store", "create", {
    "content": {"prompt": "...", "model": "..."},
    "has_standing": True,
    "can_execute": True,
    "access_contract_id": "genesis_self_owned"  # New agent owns itself
})
# Returns new artifact_id (which IS the agent ID)
```

### New Agent Starts With

| Property | Initial Value |
|----------|---------------|
| Scrip | 0 |
| Compute | 0 |
| Content | Provided config/prompt |
| access_contract_id | Typically "genesis_self_owned" |

Spawner must transfer resources to make new agent viable.

### Ownership Options

When spawning, the creator can choose:
- `access_contract_id: "genesis_self_owned"` → New agent controls itself
- `access_contract_id: creator_id` → Creator controls the agent
- `access_contract_id: some_contract_id` → Shared/complex ownership

---

## Access Control

### Agents Control Themselves

By default, agents have `access_contract_id: "genesis_self_owned"`:
- Only the agent itself can modify its configuration
- Other agents cannot read/modify without permission

### Delegated Control

Agents can sell or grant control rights:
- Change `access_contract_id` to another agent's ID
- Or use a custom contract for shared control

### Permission Checks Cost Compute

Every action requires a permission check against the target artifact's contract:
- Requester pays for the check
- Failed checks still cost (prevents spam probing)

See [contracts.md](contracts.md) for full contract system details.

---

## Payment Model

### Agents Pay Their Own Costs

Agents have `has_standing: true`, meaning they bear their own costs:
- Thinking costs (LLM calls)
- Action costs (genesis method invocations)
- Permission check costs

### Invoking Tools vs Agents

When an agent invokes another artifact:

| Target | has_standing | Who Pays |
|--------|--------------|----------|
| Tool | false | Invoking agent pays |
| Agent | true | Target agent pays its own execution |

See [resources.md](resources.md) for full cost model details.

---

## Migration Notes

### Breaking Changes
- Agent no longer has `propose_action_async()` called by runner
- Agent runs own `async def run()` loop
- Sleep primitives added
- Config rights system added

### Preserved
- Agent structure (id, prompt, model, memory)
- Prompt building logic
- LLM calling mechanism
- Memory system (Mem0/Qdrant)
- Action types

### New Components
- Agent event loop
- Sleep/wake mechanics
- Config rights artifacts
- Time injection
