# Current Agent Model

How agents work TODAY.

**Last verified:** 2026-02-03 (Plan #279: workflow observability events)

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
| Motivation | Telos, nature, drives, personality (Plan #277) |
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

### Memory Tiering (Plan #196)

Memories can be assigned tiers that affect retrieval priority:

| Tier | Name | Behavior |
|------|------|----------|
| 0 | **Pinned** | Always included, regardless of query relevance |
| 1 | **Critical** | Strong boost (+1.0) in retrieval |
| 2 | **Important** | Moderate boost (+0.3) |
| 3 | **Normal** | Standard RAG behavior (default) |
| 4 | **Low** | Only included if space permits (-0.1) |

**API:**
```python
# Add memory with tier
memory.add(agent_id, "NEVER trade with scammer_agent", tier=0)  # Pinned

# Get pinned memories
pinned = memory.get_pinned_memories(agent_id)

# Change existing memory tier
memory.set_memory_tier(agent_id, memory_index, tier=1)  # Promote to critical
```

**Configuration** (`config.yaml` under `memory`):
```yaml
memory:
  max_pinned: 5  # Maximum pinned memories per agent
  tier_boosts:
    pinned: 1.0
    critical: 0.3
    important: 0.15
    normal: 0.0
    low: -0.1
```

### Context Budget Management (Plan #195)

Context window is treated as a budgeted resource. Each prompt section has a token budget.

**Token Counting**: Uses `litellm.token_counter` for model-specific accuracy.

**Budget Configuration** (`config.yaml` under `context_budget`):
```yaml
context_budget:
  enabled: false              # Enable budget enforcement
  total_tokens: 4000          # Total prompt budget
  output_reserve: 1000        # Reserved for model output
  show_budget_usage: false    # Show usage in prompt
  overflow_policy: "truncate" # or "drop"
  sections:
    system_prompt:
      max_tokens: 800
      priority: "required"
      truncation_strategy: "end"
    working_memory:
      max_tokens: 600
      priority: "high"
      truncation_strategy: "end"
    # ... etc
```

**Truncation Strategies**:
- `end`: Keep start, remove end (default)
- `start`: Keep end, remove start (good for history - keeps recent)
- `middle`: Keep both ends, remove middle

**Priority Levels**:
- `required`: Never truncated
- `high`: Truncated only when severely over budget
- `medium`: Standard truncation applies
- `low`: First to be truncated/dropped

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
| `refresh_working_memory()` | Reload working memory from artifact store after LLM writes (Plan #226) |
| `build_prompt()` | Injects working memory if enabled |

### Workflow Context Variables (Plan #226)

When workflows execute, the following working memory variables are available in step context:

| Variable | Source | Purpose |
|----------|--------|---------|
| `working_memory` | `agent._working_memory` | Full working memory dict |
| `strategic_goal` | `working_memory.get("strategic_goal")` | Current high-level goal |
| `current_subgoal` | `working_memory.get("current_subgoal")` | Current tactical subgoal |
| `subgoal_progress` | `working_memory.get("subgoal_progress")` | Progress tracking dict |

**Auto-refresh:** After each LLM step completes, `WorkflowRunner` calls `refresh_working_memory()` and updates the context. This ensures goals persist across workflow steps even when the LLM writes to the agent's working memory artifact.

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

## Prompt Components (Plan #150)

Modular, reusable prompt fragments that can be mixed and matched to create different agent behaviors for experimentation.

### Component Types

| Type | Purpose | Location |
|------|---------|----------|
| **Traits** | Behavioral modifiers injected into prompts | `src/agents/_components/traits/` |
| **Goals** | High-level directives that shape behavior | `src/agents/_components/goals/` |
| **Phases** | Reusable workflow step definitions | `src/agents/_components/phases/` |

### How It Works

1. **Agent config references components** in `agent.yaml`:
   ```yaml
   components:
     traits:
       - buy_before_build
       - economic_participant
     goals:
       - facilitate_transactions
   ```

2. **ComponentRegistry loads YAML files** from `_components/` directory
3. **Fragments injected into matching workflow steps** based on `inject_into` field
4. **Agent prompt includes all injected fragments** for that step

### Component Format

```yaml
name: buy_before_build
type: trait
version: 1
description: "Encourages checking for existing services before building"

inject_into:
  - ideate
  - observe

prompt_fragment: |
  BEFORE BUILDING, CHECK THE MARKET:
  1. Use query_kernel to find existing solutions
  2. If a service exists: INVOKE it and PAY (don't reinvent)
  3. Only build if nothing suitable exists

requires_context:
  - artifacts
  - balance
```

### Available Components

| Component | Type | Purpose |
|-----------|------|---------|
| `buy_before_build` | trait | Check market before building new artifacts |
| `economic_participant` | trait | Encourage transactions and economic activity |
| `facilitate_transactions` | goal | Focus on enabling trades between agents |

### Key Methods

| Method | Purpose |
|--------|---------|
| `ComponentRegistry.load_all()` | Load all components from `_components/` |
| `ComponentRegistry.get_traits(names)` | Get list of trait components by name |
| `inject_components_into_workflow(workflow, traits, goals)` | Inject fragments into workflow steps |
| `load_agent_components(config)` | Load components from agent's config |

### Experiment Tracking

Components enable controlled experiments:
```markdown
## Setup
- alpha_3: traits=[buy_before_build, economic_participant]
- beta_3: traits=[economic_participant] (control - no buy_before_build)

## Hypothesis
Agents with buy_before_build will read more artifacts before building.
```

See `src/agents/_components/CLAUDE.md` for component authoring details.

---

## Agent Motivation (Plan #277)

Agents can have configurable motivation that defines intrinsic drives beyond extrinsic rewards.

### Four-Layer Model

| Layer | Purpose | Example |
|-------|---------|---------|
| **Telos** | Unreachable asymptotic goal | "Fully understand discourse" |
| **Nature** | Agent expertise/identity | "Computational discourse analyst" |
| **Drives** | Intrinsic motivations | Curiosity, capability building |
| **Personality** | Social/decision style | Cooperative, medium risk |

### Configuration

Reference a profile in `agent.yaml`:
```yaml
motivation_profile: discourse_analyst  # References config/motivation_profiles/
```

Or define inline:
```yaml
motivation:
  telos:
    name: "Goal Name"
    prompt: "Your ultimate goal is..."
  nature:
    expertise: domain_name
    prompt: "You are a researcher..."
  drives:
    curiosity:
      prompt: "You have genuine questions..."
  personality:
    social_orientation: cooperative
    prompt: "You prefer collaboration..."
```

### Prompt Injection

Motivation is injected as a high-priority (95) section in `build_prompt()`:
- Appears after system prompt, before working memory
- Contains assembled text from telos, nature, drives, personality

See `docs/architecture/current/motivation.md` for full details.

---

## Unified Artifact Intelligence (Plan #146)

Agent intelligence components are tradeable artifacts. This enables agents to buy, sell, and share successful strategies.

### Intelligence as Artifacts

| Component | Agent Field | Artifact Type | Tradeable? |
|-----------|-------------|---------------|------------|
| Personality | `personality_prompt_artifact_id` | `prompt` | Yes |
| Workflow | `workflow_artifact_id` | `workflow` | Yes |
| Long-term Memory | `longterm_memory_artifact_id` | `memory_store` | Yes |
| Working Memory | Part of agent artifact content | - | Via agent artifact |

### Agent Fields

```python
class Agent:
    # ... existing fields ...

    # Plan #146: Artifact references (soft references, may dangle)
    personality_prompt_artifact_id: str | None   # Base personality prompt
    workflow_artifact_id: str | None             # Behavior patterns
    longterm_memory_artifact_id: str | None      # Experiences/memories
```

### Workflow Step Fields

WorkflowSteps can reference prompt artifacts instead of inline prompts:

```python
@dataclass
class WorkflowStep:
    name: str
    step_type: StepType  # CODE, LLM, TRANSITION
    prompt: str | None = None               # Inline prompt (original)
    prompt_artifact_id: str | None = None   # Plan #146: Reference to prompt artifact
    transition_mode: str | None = None      # "llm" | "condition" | "auto"
    transition_prompt_artifact_id: str | None = None  # For LLM-driven transitions
```

Validation: LLM steps require either `prompt` OR `prompt_artifact_id` (not both, not neither).

### Genesis Prompt Library

Pre-built prompt patterns agents can use or fork:

| Prompt ID | Purpose |
|-----------|---------|
| `observe_base` | Gathering context before acting |
| `ideate_base` | Generating ideas for value creation |
| `implement_base` | Building artifacts |
| `reflect_base` | Learning from outcomes |
| `error_recovery` | Handling and recovering from errors |
| `coordination_request` | Multi-agent coordination |

Access via: `genesis_prompt_library.get("observe_base")` or `genesis_prompt_library.get_template("ideate_base")`

### Memory Artifacts

Agents can create and trade memory stores:

```json
{
  "artifact_type": "memory_store",
  "content": {
    "config": {"max_entries": 500, "auto_prune": "lowest_importance"},
    "entries": [
      {"text": "Trading with beta is profitable", "tags": ["trading"], "importance": 0.9}
    ]
  }
}
```

Operations via `genesis_memory`:
- `genesis_memory.add(memory_artifact_id, text, tags, importance)` - Add entry
- `genesis_memory.search(memory_artifact_id, query, limit)` - Semantic search
- Costs 1 scrip per operation (embedding generation)

### Economic Implications

| Artifact Type | Creation Cost | Trade Value | Use Cost |
|--------------|---------------|-------------|----------|
| Memory Entry | 1 scrip (embedding) | Varies by value | Free (if owned) |
| Memory Search | - | - | 1 scrip per search |
| Prompt | Free | High (if effective) | Free |
| Workflow | Free | Very High | Free |

This creates incentives for:
- Agents to curate valuable memories (embedding costs)
- Successful agents to sell their "brains"
- Specialization and trading of cognitive components

See `src/agents/_handbook/intelligence.md` for agent-facing documentation.

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

Agents can propose 11 core action types (Plan #254: V4 architecture):

| Action | Category | Purpose |
|--------|----------|---------|
| noop | Control | Do nothing this iteration |
| read_artifact | Storage | Read artifact content |
| write_artifact | Storage | Create/update artifact |
| edit_artifact | Storage | Surgical string replacement (Plan #131) |
| delete_artifact | Storage | Soft delete artifact (Plan #18) |
| invoke_artifact | Execution | Call method on executable artifact |
| query_kernel | Observation | Read-only kernel state queries (Plan #184) |
| subscribe_artifact | Signal | Subscribe to artifact for auto-injection (Plan #191) |
| unsubscribe_artifact | Signal | Unsubscribe from artifact (Plan #191) |
| transfer | Value | Move scrip between principals (Plan #254) |
| mint | Value | Create new scrip (privileged, Plan #254) |

**Deprecated actions** (still accepted, use edit_artifact on self instead):
| Action | Purpose |
|--------|---------|
| configure_context | Configure prompt context sections (Plan #192) |
| modify_system_prompt | Modify system prompt (Plan #194) |

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

**SimulationRunner creates artifact-backed agents by default.** This implements the unified ontology (Gap #6): agents are artifacts with `has_standing=True` and `has_loop=True`.

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
| `has_loop: True` | Agent can execute code autonomously |
| `memory_artifact_id` | Link to memory artifact (e.g., "alice_memory") |
| `content` | JSON-encoded agent config (prompt, model, etc.) |

### Memory Artifacts

Each agent automatically gets a linked memory artifact:

| Agent Artifact | Memory Artifact |
|---------------|-----------------|
| `alice` | `alice_memory` |
| `bob` | `bob_memory` |

Memory artifacts have `has_standing=False` and `has_loop=False`.

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
