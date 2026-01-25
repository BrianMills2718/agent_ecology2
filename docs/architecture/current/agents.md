# Current Agent Model

How agents work TODAY.

**Last verified:** 2026-01-25 (Plan #190 - Added is_genesis property for genesis vs spawned agents)

**See target:** [../target/agents.md](../target/agents.md)

---

## Agent Lifecycle

Agents run autonomous loops via `AgentLoop`. Each agent continuously:

1. **Check resources** - RateTracker gates action rate
2. **Decide action** - Builds prompt, calls LLM, returns proposal
3. **Execute action** - System executes if resources available
4. **Repeat** - Until resources exhausted or stopped

```
AgentLoop._execute_iteration():
  1. Check rate limit (RateTracker.can_consume)
  2. Call agent.decide_action(world_state)
     - Build prompt (state + memory + history)
     - Call LLM
     - Parse response into action
  3. Execute action via artifact executor
  4. Agent receives result
  5. Loop continues (async, independent of other agents)
```

**Integration point:** New agent-internal features (workflows, intelligence patterns) hook into `AgentLoop._execute_iteration()`.

**Duration mode:** Use `--duration N` to run for N seconds. Agents run autonomously (no tick synchronization).

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
    inject_working_memory: bool     # Auto-inject working memory into prompts (Plan #59)
    working_memory_max_bytes: int   # Max size for working memory truncation
    _working_memory: dict | None    # Cached working memory from agent artifact
    _workflow_config: WorkflowConfigDict | None  # Workflow configuration (Plan #70)
    failure_history: list[str]      # Recent failed actions for learning (Plan #88)
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
| Event number | world_state["event_number"] |
| Balances | world_state["balances"] |
| Quotas | world_state["quotas"] |
| Available artifacts | world_state["artifacts"] |
| Mint submissions | world_state["mint_submissions"] |
| Recent events | world_state["recent_events"] |
| Relevant memories | RAG search on current context |
| Working memory | Agent artifact `working_memory` section (Plan #59) |
| Last action result | self.last_action_result |
| Recent failures | self.failure_history (Plan #88) |

### LLM Response Schema

**Simple mode (default):**
```python
class AgentResponse(BaseModel):
    thought_process: str
    action: Action  # noop, read_artifact, write_artifact, invoke_artifact
```

**OODA mode** (`cognitive_schema: ooda` in config, Plan #88):
```python
class OODAResponse(BaseModel):
    situation_assessment: str  # Analysis of current state (can be verbose)
    action_rationale: str      # Concise 1-2 sentence explanation
    action: Action
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

## Working Memory (Plan #59)

Agents can maintain structured working memory for goal persistence.

### How It Works

1. **Agent artifact includes `working_memory` section** in its JSON content
2. **System auto-extracts** during `from_artifact()`
3. **System auto-injects** into prompt in `build_prompt()` if enabled
4. **Agent updates** by writing to self via `write_artifact`

### Configuration

`config.yaml` under `agent.working_memory`:

```yaml
working_memory:
  enabled: false          # Master switch (off by default)
  auto_inject: true       # Inject into prompt when enabled
  max_size_bytes: 2000    # Truncate to prevent prompt bloat
  include_in_rag: false   # Also include in semantic search
  structured_format: true # Enforce schema vs freeform
  warn_on_missing: false  # Log warning if no working memory
```

### Working Memory Structure

```json
{
  "current_goal": "Build price oracle",
  "started": "2026-01-16T10:30:00Z",
  "progress": {
    "stage": "Implementation",
    "completed": ["interface design"],
    "next_steps": ["core logic", "tests"],
    "actions_in_stage": 3
  },
  "lessons": ["escrow needs ownership transfer first"],
  "strategic_objectives": ["become known for pricing"]
}
```

### Key Methods

| Method | Purpose |
|--------|---------|
| `_extract_working_memory(content)` | Extract from agent artifact content |
| `_format_working_memory()` | Format for prompt injection with truncation |
| `build_prompt()` | Injects working memory if enabled |

### Design Philosophy

- **Optional**: Disabled by default, agents can ignore it
- **No enforcement**: Selection pressure, not system enforcement
- **Minimal schema**: Not prescriptive about goal structure
- **Size-limited**: Prevents prompt bloat via `max_size_bytes`

See `src/agents/_handbook/memory.md` for agent-facing documentation.

---

## Agent Workflows (Plan #70)

Agents can have configurable workflows that define step-by-step execution patterns.

### How It Works

1. **Agent config includes `workflow` section** in agent.yaml or artifact content
2. **WorkflowRunner executes steps** sequentially with context passing
3. **Steps can be code or LLM calls** - flexible execution model
4. **Fallback to propose_action()** if no workflow configured

### Configuration

`agent.yaml` workflow section:

```yaml
workflow:
  steps:
    - name: "observe"
      type: "llm"
      prompt: "Analyze current world state"
    - name: "decide"
      type: "llm"
      prompt: "Based on observations, choose an action"
    - name: "act"
      type: "code"
      action: "execute_decision"
  error_handling:
    on_step_failure: "continue"  # or "abort"
```

### Key Methods

| Method | Purpose |
|--------|---------|
| `has_workflow` | Property: whether agent has workflow configured |
| `workflow_config` | Property: get workflow configuration |
| `run_workflow(world_state)` | Execute workflow and return action |

### Workflow Steps

| Step Type | Description |
|-----------|-------------|
| `llm` | Call LLM with prompt, pass result to next step |
| `code` | Execute predefined code action |

### Integration with AgentLoop

When `AgentLoop` executes an iteration:
1. Check if agent `has_workflow`
2. If yes, call `run_workflow()` instead of `propose_action()`
3. If no, fall back to standard `propose_action()`

See `src/agents/workflow.py` for WorkflowRunner implementation.

---

## VSM-Aligned Agents (Plan #82)

Enhanced agent variants implementing Viable Systems Model patterns.

### alpha_2: Adaptive Architect

Self-monitoring agent with adaptation triggers:

| Feature | Implementation |
|---------|---------------|
| **Self-audit (S3*)** | `self_audit` workflow step evaluates strategy effectiveness |
| **Adaptation triggers** | Computes `success_rate`, `stuck_in_loop` flags |
| **Pivot mechanism** | When `should_pivot=True`, agent must change approach |

Workflow steps: `compute_metrics` → `self_audit` → `review_strategy` → `decide_action`

### beta_2: Strategic Integrator

Goal hierarchy tracking with strategic/tactical modes:

| Feature | Implementation |
|---------|---------------|
| **Goal hierarchy** | Maintains `strategic_goal` and `current_subgoal` |
| **Progress tracking** | Tracks `subgoal_progress` with action counts |
| **Strategic reviews** | Periodic (every ~10 iterations) or when stuck |

Workflow steps: `load_goals` → `strategic_review` (conditional) → `tactical_plan` → `decide_action`

### Configuration Note

VSM-aligned agents work best with working memory enabled:
```yaml
# config.yaml
working_memory:
  enabled: true
```

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
  query_template: "Current context. What should I do?"
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
| noop | Do nothing this iteration |
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
| Insufficient llm_tokens | Skip with "insufficient_llm_tokens" |
| Invalid action | Skip with "intent_rejected" |

### Execution Failures

| Failure | Result |
|---------|--------|
| Artifact not found | ActionResult(success=False) |
| Permission denied | ActionResult(success=False) |
| Insufficient scrip | ActionResult(success=False) |
| Insufficient disk | ActionResult(success=False) |

Agent receives failure message in `last_action_result` for next iteration.

---

## Key Files

| File | Key Functions | Description |
|------|---------------|-------------|
| `src/agents/agent.py` | `Agent.build_prompt()` | Prompt construction (incl. working memory) |
| `src/agents/agent.py` | `Agent.propose_action_async()` | LLM call and action parsing |
| `src/agents/agent.py` | `Agent.record_action()`, `record_observation()` | Memory recording |
| `src/agents/agent.py` | `Agent._extract_working_memory()` | Working memory extraction (Plan #59) |
| `src/agents/agent.py` | `Agent._format_working_memory()` | Working memory formatting (Plan #59) |
| `src/agents/memory.py` | `AgentMemory` class | RAG-based memory |
| `src/agents/loader.py` | `load_agents()` | Agent loading from config |

---

## Implications

### Continuous Execution
- Agents run in autonomous loops (no tick synchronization)
- Rate limited by RateTracker
- Run until resources exhausted or duration ends

### Async Execution
- Agents run independently (no synchronized snapshots)
- Each agent sees current world state when it acts
- Rate limiting provides fairness (faster agents still limited)

### Memory is Passive
- Stored after actions
- Retrieved during prompt building
- No active memory management by agent

---

## Artifact-Backed Agents (Default)

**SimulationRunner creates artifact-backed agents by default.** This implements the unified ontology (Gap #6): agents are artifacts with `has_standing=True` and `can_execute=True`.

### How It Works

When SimulationRunner initializes:

1. `create_agent_artifacts()` creates agent and memory artifacts in the world's artifact store
2. `load_agents_from_store()` creates Agent instances backed by those artifacts
3. Each agent has `is_artifact_backed=True` and links to its artifact

```python
# SimulationRunner creates artifact-backed agents automatically
runner = SimulationRunner(config)
assert runner.agents[0].is_artifact_backed is True
assert "agent_id" in runner.world.artifacts.artifacts
```

### Manual Creation

Agents can also be created manually from artifacts:

```python
from src.agents.agent import Agent

# Create agent from artifact
artifact = store.get("agent_001")
agent = Agent.from_artifact(artifact, store=store)

# Serialize back to artifact
updated_artifact = agent.to_artifact()
```

### Artifact Fields

| Field | Description |
|-------|-------------|
| `has_standing: True` | Agent is a principal (can own things) |
| `can_execute: True` | Agent can execute code autonomously |
| `memory_artifact_id` | Link to memory artifact (e.g., "alice_memory") |
| `content` | JSON-encoded agent config (prompt, model, etc.) |

### Memory Artifacts

Each agent automatically gets a linked memory artifact:

| Agent Artifact | Memory Artifact |
|---------------|-----------------|
| `alice` | `alice_memory` |
| `bob` | `bob_memory` |

Memory artifacts have `has_standing=False` and `can_execute=False`.

### Spawned Agents

Dynamically created agents (via ledger principal creation) are also artifact-backed. When `_check_for_new_principals()` detects a new principal:

1. Creates memory artifact for the new agent
2. Creates agent artifact with default config
3. Creates Agent instance from the artifact

### Benefits

| Benefit | Description |
|---------|-------------|
| Persistence | Agent state survives checkpoint/restore |
| Trading | Agents can be bought/sold via escrow |
| Single ID namespace | Agent IDs are artifact IDs |
| Unified queries | `is_agent` property finds all agents in store |

### ArtifactMemory

When artifact-backed, agents can use `ArtifactMemory` instead of Mem0:

```python
# Memory stored as artifact content
memory = ArtifactMemory(agent_id, store)
memory.add("Learned trading strategies")
```

This enables checkpointing agent memory with the artifact store.

See `docs/architecture/current/artifacts_executor.md` for principal capabilities.
