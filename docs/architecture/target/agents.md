# Target Agent Model

What we're building toward.

**See current:** [../current/agents.md](../current/agents.md)

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

Agents can spawn new agents via `genesis_ledger.spawn_principal()`:

```python
invoke("genesis_ledger", "spawn_principal", [])
# Returns new principal_id
```

New agent starts with:
- 0 scrip
- 0 compute
- Default prompt (or none)

Spawner must transfer resources to make new agent viable.

### Inherited vs Default

| Property | Inherited? |
|----------|-----------|
| Scrip | No (starts at 0) |
| Compute | No (starts at 0) |
| Prompt | No (default or none) |
| Memory | No (fresh) |
| Config rights | Owned by new agent (can be sold) |

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
