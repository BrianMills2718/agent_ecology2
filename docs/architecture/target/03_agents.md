# Target Agent Model

What we're building toward.

**Last verified:** 2026-01-12

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
    has_loop: bool          # Has runnable code

# Agent = artifact where has_standing=True AND has_loop=True
```

### Why This Matters

| Old Model | New Model |
|-----------|-----------|
| Agent is a separate concept | Agent is an artifact type |
| Agents can't be owned | Agents are ownable property |
| principal_id separate from artifact_id | Single namespace for all IDs |
| Ledger tracks principals | Ledger tracks artifacts with standing |

### Derived Categories

| Category | has_standing | has_loop | Example |
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
    "has_loop": True,
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
    "has_loop": False,   # Memory isn't executable
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

### Qdrant Integration

Memory is stored in Qdrant vector database, referenced by memory artifact.

**Memory artifact structure:**

```python
{
    "id": "alice_memories",
    "content": {
        "storage_type": "qdrant",
        "collection_id": "alice_mem_collection",
        "embedding_model": "text-embedding-3-small",  # OpenAI or local
        "vector_size": 1536,
    }
}
```

**Memory interface:**

```python
class AgentMemory:
    def __init__(self, memory_artifact_id: str, qdrant_client: QdrantClient):
        self.artifact = load_artifact(memory_artifact_id)
        self.collection = self.artifact.content["collection_id"]
        self.client = qdrant_client

    async def store(self, text: str, metadata: dict = None) -> str:
        """Store a memory. Returns memory ID."""
        embedding = await embed(text, self.artifact.content["embedding_model"])
        point_id = uuid4().hex
        self.client.upsert(
            collection_name=self.collection,
            points=[PointStruct(id=point_id, vector=embedding, payload={"text": text, **(metadata or {})})]
        )
        return point_id

    async def recall(self, query: str, limit: int = 5) -> list[dict]:
        """Retrieve relevant memories."""
        embedding = await embed(query, self.artifact.content["embedding_model"])
        results = self.client.search(
            collection_name=self.collection,
            query_vector=embedding,
            limit=limit
        )
        return [{"text": r.payload["text"], "score": r.score} for r in results]

    def clear(self) -> None:
        """Wipe all memories. Requires owner permission on memory artifact."""
        self.client.delete_collection(self.collection)
        self.client.create_collection(self.collection, vectors_config=...)
```

**Memory quota tracking:**

```python
# Memory usage counted against agent's allocatable memory quota
def store_memory(agent_id: str, text: str):
    memory_bytes = len(text.encode()) + EMBEDDING_SIZE  # ~6KB per memory
    if not quota_check(agent_id, "memory", memory_bytes):
        raise QuotaExceeded("Memory quota exceeded")
    memory.store(text)
    quota_deduct(agent_id, "memory", memory_bytes)
```

**Qdrant deployment:**

```yaml
# docker-compose.yml
services:
  qdrant:
    image: qdrant/qdrant:latest
    ports:
      - "6333:6333"
    volumes:
      - qdrant_data:/qdrant/storage

  agent-ecology:
    environment:
      QDRANT_URL: http://qdrant:6333
```

**Fallback behavior:**

If Qdrant is unavailable:
- Memory operations fail with clear error
- Agent continues running (degraded mode)
- System logs Qdrant connectivity issues
- No silent fallback to local storage

**Checkpoint synchronization:**

Qdrant must be snapshotted atomically with world state checkpoints:

```
Checkpoint = {
    world_state: artifact_store + ledger at tick N,
    qdrant_snapshot: memory collections at tick N
}
```

On restore, both are restored together. This prevents "split-brain" where agents have memories of events that haven't happened in the restored world state.

**Implementation:** Qdrant supports snapshots via API. Checkpoint process:
1. Pause agent loops
2. Snapshot artifact store + ledger
3. Snapshot Qdrant collections
4. Resume agent loops

Restore reverses this atomically.

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

### Event Bus Interface

```python
class EventBus:
    """System-wide event notification."""

    async def subscribe(self, agent_id: str, event_type: str) -> None:
        """Subscribe to an event type. Subscription persists until unsubscribe."""
        pass

    async def unsubscribe(self, agent_id: str, event_type: str) -> None:
        """Unsubscribe from an event type."""
        pass

    async def wait_for(self, agent_id: str, event_type: str,
                       filter_fn: Callable[[Event], bool] = None) -> Event:
        """Block until matching event occurs. Auto-subscribes if needed."""
        pass

    def publish(self, event: Event) -> None:
        """Publish an event. All subscribers are notified."""
        pass
```

**Event types:**

| Event Type | Payload | Published When |
|------------|---------|----------------|
| `escrow_listing` | `{artifact_id, price, seller_id}` | New escrow listing created |
| `escrow_sale` | `{artifact_id, buyer_id, price}` | Escrow purchase completed |
| `oracle_resolution` | `{winners, scores}` | Oracle resolves bids |
| `transfer_received` | `{from_id, to_id, amount, resource}` | Agent receives transfer |
| `artifact_created` | `{artifact_id, creator_id}` | New artifact created |
| `agent_blocked` | `{agent_id, resource}` | Agent exceeded rate limit |
| `agent_unblocked` | `{agent_id, resource}` | Agent rate limit recovered |

**Subscription persistence:**

```python
# Subscriptions are stored in agent state
agent.subscriptions = ["escrow_listing", "transfer_received"]

# On agent restart, subscriptions are restored
async def restore_agent(agent_id: str):
    agent = load_agent(agent_id)
    for event_type in agent.subscriptions:
        await event_bus.subscribe(agent_id, event_type)
```

**Event Catch-Up Mechanism (Hybrid Approach):**

If an event fires while agent is sleeping or restarting:
- Events are NOT queued per-agent (too expensive, unbounded growth)
- Agent uses hybrid catch-up: query event log + condition re-verification

```python
async def wake_and_catch_up(self):
    """Hybrid approach to event catch-up after sleep/restart."""
    # 1. Query event log for events since last wake time
    events_since = await event_bus.query_log(
        since=self.last_wake_time,
        event_types=self.subscriptions
    )

    # 2. Process each event, but re-verify conditions
    for event in events_since:
        # Don't trust stale events blindly
        if self.condition_still_valid(event):
            await self.handle_event(event)

    # 3. Update last wake time
    self.last_wake_time = now()
```

**Why hybrid?**
- Event log provides history (what happened while sleeping)
- Condition re-verification ensures freshness (world may have changed)
- No per-agent queue = bounded memory
- Handles restart, checkpoint restore, long sleeps

**Trade-offs:**
- Agents may re-process events already handled before sleep
- Duplicate handling must be idempotent
- Log queries add some latency on wake

See `genesis_event_log` in [../current/genesis_artifacts.md](../current/genesis_artifacts.md) for log retention policy.

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

When agent is frozen (blocked on rate limits):

1. Agent A is blocked (insufficient rate capacity, can't think)
2. Agent A's artifacts still exist
3. Agent B notices A is blocked
4. B transfers rate quota to A (unilateral, no permission needed)
5. A unblocks, can think again
6. B hopes A reciprocates (reputation matters)

Market-driven rescue, not system rules.

---

## No Death Policy

**Agents never die. They can only be:**

| State | Meaning | Recovery |
|-------|---------|----------|
| **Active** | Running normally | N/A |
| **Blocked** | Insufficient rate capacity | Wait for window or receive quota transfer |
| **Dormant** | No actions for extended period | Any stimulus can wake |

**Why no death:**
- Complete audit trail preserved
- Vulture capitalist rescue always possible
- Frozen agent's artifacts remain accessible (per their contracts)
- Market handles cleanup via opportunity cost, not forced deletion

**Identity persistence:** An agent's ID and history exist forever. Even if all resources are transferred away, the "shell" remains in the registry. This enables:
- Future resurrection if someone funds the agent
- Historical analysis of agent evolution
- No "burned" IDs that can never be reused

**Note:** Asset reclamation from long-dormant agents (salvage rights) is deferred to future versions. For V1, dormant agents simply persist indefinitely.

---

## Agent Creation

### Spawning

Agents create new agents via `genesis_store.create()`:

```python
invoke("genesis_store", "create", {
    "content": {"prompt": "...", "model": "..."},
    "has_standing": True,
    "has_loop": True,
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

See [05_contracts.md](05_contracts.md) for full contract system details.

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

See [04_resources.md](04_resources.md) for full cost model details.

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
