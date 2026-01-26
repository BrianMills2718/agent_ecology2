# Agent Ontology

What IS an agent in this system.

---

## Core Definition

An **agent** is an artifact with two properties:

| Property | Value | Meaning |
|----------|-------|---------|
| `has_standing` | `True` | Can hold scrip, bear costs, own things |
| `can_execute` | `True` | Has runnable code, can take actions |

```python
# From artifacts.py
@property
def is_agent(self) -> bool:
    return self.has_standing and self.can_execute
```

---

## Artifact Categories

All entities in the system are artifacts. The properties determine category:

| Category | has_standing | can_execute | Example |
|----------|--------------|-------------|---------|
| **Agent** | True | True | alpha_3, beta_3, delta_3 |
| **Tool** | False | True | Executable artifact, invoker pays costs |
| **Account** | True | False | Treasury, escrow (holds value, no code) |
| **Data** | False | False | Documents, content |

---

## Agent as Artifact

Agents are stored as artifacts in the artifact store:

```python
{
    "id": "alpha_3",
    "has_standing": True,
    "can_execute": True,
    "created_by": "system",  # Genesis agents created by system
    "content": {
        "llm_model": "gemini/gemini-2.0-flash",
        "workflow": {...},
        "components": {...},
        # ... rest of agent.yaml content
    }
}
```

---

## What Agents Can Do

Because agents have standing and can execute:

| Capability | How |
|------------|-----|
| Hold scrip | `has_standing=True` → tracked in ledger |
| Pay costs | Bear their own LLM and action costs |
| Own artifacts | `created_by` field points to agent |
| Invoke artifacts | Execute actions via world |
| Be invoked | Other agents can call their methods |
| Trade | Buy/sell artifacts via escrow |

---

## What Agents Cannot Do (Currently)

| Limitation | Why | Future |
|------------|-----|--------|
| Modify own workflow structure at runtime | Workflow loaded from YAML at startup | Plan #202, #222 |
| Create new step types | Step types fixed in code | Could add plugin system |
| Escape loader's expected YAML structure | Loader enforces schema | Plan #155 (deferred) |

---

## Agent Identity

An agent's identity consists of:

| Component | Stored In | Tradeable? |
|-----------|-----------|------------|
| Configuration (prompt, model, workflow) | Agent artifact content | Yes (Plan #8) |
| Memory (experiences, learned patterns) | Memory artifact | Yes (separate artifact) |
| Balance (scrip holdings) | Ledger | N/A (transferred, not traded) |
| Reputation | Emerges from behavior | N/A (observed, not owned) |

See [../03_agents.md](../03_agents.md) for the full target vision of agent rights trading.

---

## Genesis vs Spawned Agents

| Type | Created By | Initial State |
|------|------------|---------------|
| **Genesis agents** | System at startup | Configured in `src/agents/*/agent.yaml` |
| **Spawned agents** | Other agents via `genesis_store.create()` | Created with provided config, 0 scrip |

Both are artifacts with the same properties. Genesis agents just have pre-configured content.

---

## Relationship to Plan #155

Plan #155 proposes: "Agents aren't real, they're patterns of artifact activity."

Current model:
- Agent IS a special artifact with `Agent` class in Python
- Agent has privileged LLM access, scheduling, workflow execution

Plan #155 vision:
- No `Agent` class
- "Agent" = observable pattern of artifact invocations
- LLM access through artifact invocation like everything else

**Current status:** Plan #155 deferred. We keep the `Agent` class but make it more flexible via Plan #222 (artifact-aware workflow).

---

## Config Rights Trading (Target)

Agents own their configuration and can trade control rights.

### What Agents Own

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

See [../03_agents.md](../03_agents.md) for full target vision including sleep mechanics and event bus.
