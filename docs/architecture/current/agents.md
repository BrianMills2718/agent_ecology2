# Current Agent Model

How agents work TODAY.

**Last verified:** 2026-01-12

**See target:** [../target/agents.md](../target/agents.md)

---

## Agent Lifecycle

Agents are passive. The system controls when they think and act.

```
Tick N:
  1. System calls agent.propose_action_async(world_state)
  2. Agent builds prompt (state + memory + history)
  3. Agent calls LLM
  4. Agent returns action proposal
  5. System deducts thinking cost
  6. System executes action (if resources available)
  7. Agent receives result for next tick

Tick N+1:
  ... repeat
```

---

## Agent Structure

**agent.py**

```python
class Agent:
    agent_id: str              # Unique identifier
    system_prompt: str         # Base instructions
    llm_model: str             # Model to use (e.g., "gemini/gemini-3-flash-preview")
    action_schema: str         # Action schema shown to LLM
    memory: AgentMemory        # RAG-based memory (Mem0/Qdrant)
    llm: LLMProvider           # LLM provider instance
    rag_config: RAGConfigDict  # Per-agent RAG settings
    last_action_result: str    # Feedback from previous action
```

---

## Thinking Process

### propose_action_async() (`Agent.propose_action_async()`)

1. **Build prompt** via `build_prompt(world_state)`
2. **Call LLM** with structured output schema
3. **Parse response** into action + thought_process
4. **Return** ActionResult or error

### Prompt Building (`Agent.build_prompt()`)

Prompt includes:

| Section | Source |
|---------|--------|
| System prompt | Agent config |
| Current tick | world_state["tick"] |
| Balances | world_state["balances"] |
| Quotas | world_state["quotas"] |
| Available artifacts | world_state["artifacts"] |
| Oracle submissions | world_state["oracle_submissions"] |
| Recent events | world_state["recent_events"] |
| Relevant memories | RAG search on current context |
| Last action result | self.last_action_result |

### LLM Response Schema

```python
class AgentResponse(BaseModel):
    thought_process: str
    action: Action  # noop, read_artifact, write_artifact, invoke_artifact
```

---

## Memory System

### AgentMemory (memory.py)

Uses Mem0 + Qdrant for persistent vector-based memory. Singleton shared by all agents.

**Agent wrapper methods** (hide agent_id):
```python
agent.record_action(action_type, details, success)
agent.record_observation(observation)
```

**Direct AgentMemory API** (requires agent_id):
```python
memory.record_action(agent_id, action_type, details, success)
memory.get_relevant_memories(agent_id, context, limit=5)
```

### What Gets Stored

| Event | Stored As |
|-------|-----------|
| Actions taken | "Agent {id} performed {action}: {details}" |
| Observations | Free-form text |
| Search is semantic | Vector similarity via Qdrant |

---

## Agent Configuration

### From agents/ directory (load_agents.py)

Each agent is a directory with `agent.yaml` and `system_prompt.md`:

```yaml
# agent.yaml
id: alice
starting_scrip: 100
enabled: true                              # Optional, default true
llm_model: gemini/gemini-3-flash-preview   # Optional, uses default
temperature: 0.7                           # Optional LLM override
max_tokens: 1000                           # Optional LLM override
rag:                                       # Optional per-agent RAG config
  enabled: true
  limit: 5
  query_template: "Tick {tick}. What should I do?"
```

System prompt is in separate `system_prompt.md` file.

### What Agents CAN'T Configure

- Their own resource quotas (managed by rights_registry)
- Their scrip balance (managed by ledger)
- Execution timing (controlled by runner)
- Other agents' state

---

## Action Types

Agents can only propose 4 action types:

| Action | Purpose |
|--------|---------|
| noop | Do nothing this tick |
| read_artifact | Read artifact content |
| write_artifact | Create/update artifact |
| invoke_artifact | Call method on executable artifact |

---

## Error Handling

### Thinking Failures

| Failure | Result |
|---------|--------|
| LLM timeout | Skip with "llm_error" |
| LLM parse error | Skip with "llm_error" |
| Insufficient compute | Skip with "insufficient_compute" |
| Invalid action | Skip with "intent_rejected" |

### Execution Failures

| Failure | Result |
|---------|--------|
| Artifact not found | ActionResult(success=False) |
| Permission denied | ActionResult(success=False) |
| Insufficient scrip | ActionResult(success=False) |
| Insufficient disk | ActionResult(success=False) |

Agent receives failure message in `last_action_result` for next tick.

---

## Key Files

| File | Key Functions | Description |
|------|---------------|-------------|
| `src/agents/agent.py` | `Agent.build_prompt()` | Prompt construction |
| `src/agents/agent.py` | `Agent.propose_action_async()` | LLM call and action parsing |
| `src/agents/agent.py` | `Agent.record_action()`, `record_observation()` | Memory recording |
| `src/agents/memory.py` | `AgentMemory` class | RAG-based memory |
| `src/agents/loader.py` | `load_agents()` | Agent loading from config |

---

## Implications

### No Autonomy
- Agents can't choose when to act
- Agents can't act more than once per tick
- Agents can't sleep (always asked to act)

### Uniform Execution
- All agents get same thinking opportunity
- All agents see same snapshot
- No fast/slow agent differentiation

### Memory is Passive
- Stored after actions
- Retrieved during prompt building
- No active memory management by agent
