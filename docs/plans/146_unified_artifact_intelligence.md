# Plan 146: Unified Artifact Intelligence

**Status:** 📋 Planned
**Priority:** High
**Blocked By:** None (Plan #143 Reflex complete, builds on that pattern)
**Blocks:** Agent self-optimization, prompt marketplace, memory trading

## Problem Statement

Agent "intelligence" is currently fragmented across multiple systems:

1. **Prompts** - Hardcoded in YAML files, not tradeable
2. **Workflows** - Embedded in agent config, not tradeable
3. **Long-term Memory** - External Qdrant DB, not observable or tradeable
4. **State Transitions** - Code-based conditions, not LLM-controllable

This limits emergent behavior because agents cannot:
- Trade successful strategies (prompts, workflows)
- Sell their learned experiences (memories)
- Evolve their own decision-making patterns
- Compose intelligence from multiple sources

## Solution

Make ALL aspects of agent intelligence into tradeable artifacts:

```
AGENT ARTIFACT (alice)
├── workflow_artifact_id        → Tradeable behavior patterns
├── reflex_artifact_id          → Tradeable fast-path logic (Plan #143)
├── working_memory_artifact_id  → Short-term context
├── longterm_memory_artifact_id → Tradeable experiences (NEW)
└── personality_prompt_id       → Tradeable base personality (NEW)

WORKFLOW ARTIFACT (alice_workflow)
├── states: [...]
├── initial_state: "observing"
└── steps:
    ├── state: "observing"
    │   ├── prompt_artifact_id: "alice_observe_prompt"      → Tradeable
    │   └── transition_prompt_artifact_id: "alice_transition" → LLM decides next state
    └── ...
```

## Design

### Phase 1: Long-term Memory as Artifact

**New artifact type: `memory_store`**

```yaml
# alice_longterm_memory artifact
type: memory_store
content:
  config:
    max_entries: 1000
    auto_prune: oldest  # or "lowest_score"
  entries:
    - id: "mem_001"
      tick: 50
      text: "Built escrow artifact, earned 20 scrip from usage"
      tags: ["building", "escrow", "success"]
      embedding: [0.12, -0.34, 0.56, ...]  # 768 dims
      importance: 0.8
    - id: "mem_002"
      tick: 75
      text: "Trading with beta is profitable when coordinating"
      tags: ["trading", "beta", "coordination"]
      embedding: [0.23, 0.11, -0.45, ...]
      importance: 0.9
```

**Genesis artifacts for memory operations:**

```python
# genesis_embedder - Generate embeddings (costs scrip)
def run(caller_id, text):
    """Generate embedding vector for text. Costs 1 scrip per call."""
    # Deduct cost
    kernel_actions.transfer_scrip(caller_id, "genesis_embedder", 1)
    # Generate embedding via configured model
    embedding = generate_embedding(text)
    return {"embedding": embedding, "dims": len(embedding)}

# genesis_memory_search - Semantic search within memory artifact
def run(caller_id, memory_artifact_id, query, limit=5):
    """Search memory artifact semantically. Costs 1 scrip."""
    kernel_actions.transfer_scrip(caller_id, "genesis_memory_search", 1)

    # Check read permission on memory artifact
    memory = kernel_state.get_artifact(memory_artifact_id)
    if not memory:
        return {"error": "Memory artifact not found"}

    # Generate query embedding
    query_embedding = genesis_embedder.run(caller_id, query)["embedding"]

    # Search entries
    results = []
    for entry in memory.content.get("entries", []):
        score = cosine_similarity(query_embedding, entry["embedding"])
        results.append({
            "text": entry["text"],
            "tick": entry["tick"],
            "score": score,
            "tags": entry.get("tags", [])
        })

    return {"results": sorted(results, key=lambda x: -x["score"])[:limit]}

# genesis_memory_add - Add entry to memory artifact
def run(caller_id, memory_artifact_id, text, tags=None, importance=0.5):
    """Add memory entry with auto-generated embedding."""
    # Must own or have write permission
    memory = kernel_state.get_artifact(memory_artifact_id)

    # Generate embedding (costs scrip)
    embedding = genesis_embedder.run(caller_id, text)["embedding"]

    # Create entry
    entry = {
        "id": f"mem_{uuid4().hex[:8]}",
        "tick": kernel_state.current_tick,
        "text": text,
        "tags": tags or [],
        "embedding": embedding,
        "importance": importance
    }

    # Append to memory artifact
    entries = memory.content.get("entries", [])
    entries.append(entry)

    # Prune if over limit
    max_entries = memory.content.get("config", {}).get("max_entries", 1000)
    if len(entries) > max_entries:
        # Remove lowest importance entries
        entries.sort(key=lambda x: x.get("importance", 0))
        entries = entries[-max_entries:]

    kernel_actions.write_artifact(memory_artifact_id, {"entries": entries})
    return {"success": True, "entry_id": entry["id"]}
```

### Phase 2: Prompt Artifacts

**New artifact type: `prompt`**

```yaml
# alice_observe_prompt artifact
type: prompt
content:
  template: |
    === OBSERVING PHASE ===
    You are {agent_id}, gathering context before acting.

    Current state:
    - Balance: {balance} scrip
    - Your artifacts: {my_artifacts}
    - Recent memories: {recent_memories}

    Last action result: {last_action_result}

    TASK: Decide what information you need before acting.
    If you need to learn an interface, read the artifact.
    If you have enough context, proceed with an action.

  variables:
    - agent_id
    - balance
    - my_artifacts
    - recent_memories
    - last_action_result
```

**Genesis prompt library:**

```yaml
# genesis_prompt_library artifact (type: library)
content:
  prompts:
    observe_base: |
      Gather context. What do you know? What do you need to know?
      Check your memory for relevant past experiences.

    ideate_base: |
      Generate ideas. What problems exist? What value could you create?
      Consider: What do others need that doesn't exist yet?

    implement_base: |
      Build it. Write clean code with clear interfaces.
      Remember: def run(*args) is the entry point.
      Set invoke_price to earn from usage.

    transition_base: |
      Given the outcome of your last action, decide your next phase.
      Consider: Did it succeed? What did you learn? What's the logical next step?
      Return: {"next_state": "state_name", "reason": "brief explanation"}

    meta_learning: |
      Before deciding: Check your working memory for lessons.
      After outcomes: Record what worked or failed.
      Pattern: Observe → Hypothesize → Act → Learn → Repeat
```

### Phase 3: LLM-Controlled State Transitions

**Workflow step structure:**

```yaml
# alice_workflow artifact
type: workflow
content:
  states: ["observing", "ideating", "implementing", "testing", "reflecting"]
  initial_state: "observing"

  steps:
    - state: "observing"
      prompt_artifact_id: "alice_observe_prompt"      # References prompt artifact
      prompt_inline: null                              # Fallback if artifact missing
      transition_mode: "llm"                           # "llm" | "condition" | "auto"
      transition_prompt_artifact_id: "alice_transition_prompt"

    - state: "ideating"
      prompt_artifact_id: "genesis_prompt_library#ideate_base"  # Can reference genesis
      transition_mode: "condition"
      transition_conditions:
        - to: "implementing"
          condition: "has_design"
        - to: "reflecting"
          condition: "stuck"

    - state: "implementing"
      prompt_artifact_id: "alice_implement_prompt"
      transition_mode: "auto"  # Always goes to next state
      transition_to: "testing"
```

**Transition prompt artifact:**

```yaml
# alice_transition_prompt artifact
type: prompt
content:
  template: |
    You are the state controller for {agent_id}.

    Current state: {current_state}
    Available states: {available_states}
    Last action: {last_action_type}
    Last result: {last_action_success}
    Balance: {balance}
    Consecutive failures: {failure_count}

    DECISION CRITERIA:
    - If 3+ consecutive failures: consider "reflecting" to learn
    - If balance < 10: consider "conserving" resources
    - If action succeeded: advance to logical next phase
    - If stuck on same state 5+ times: force transition

    Respond with JSON only:
    {"next_state": "state_name", "reason": "one sentence explanation"}
```

### Phase 4: Agent Field Updates

**Add to Agent artifact schema:**

```python
# In AgentConfigDict
class AgentConfigDict(TypedDict, total=False):
    llm_model: str
    system_prompt: str  # DEPRECATED - use personality_prompt_artifact_id

    # Artifact references (all soft references, may dangle)
    personality_prompt_artifact_id: str | None  # Base personality
    workflow_artifact_id: str | None            # Behavior patterns
    reflex_artifact_id: str | None              # Fast-path logic (Plan #143)
    working_memory_artifact_id: str | None      # Short-term context
    longterm_memory_artifact_id: str | None     # Experiences (NEW)
```

**Execution flow in runner.py:**

```python
async def _agent_decide_action(self, agent: Agent) -> dict[str, Any] | None:
    # 1. Check reflex first (Plan #143)
    reflex_action = await self._try_reflex(agent)
    if reflex_action is not None:
        return reflex_action

    # 2. Load workflow artifact
    workflow = self._load_workflow_artifact(agent)
    current_state = agent.current_state

    # 3. Load prompt for current state
    step = workflow.get_step(current_state)
    prompt = self._load_prompt(step.prompt_artifact_id, step.prompt_inline)

    # 4. Inject long-term memory search results
    if agent.longterm_memory_artifact_id:
        memories = await self._search_memories(agent, prompt)
        prompt = prompt.replace("{recent_memories}", memories)

    # 5. Execute LLM with prompt
    action = await agent.propose_action_with_prompt(prompt)

    # 6. Determine next state
    next_state = await self._determine_next_state(agent, step, action)
    agent.current_state = next_state

    return action

async def _determine_next_state(self, agent, step, action_result):
    if step.transition_mode == "auto":
        return step.transition_to
    elif step.transition_mode == "condition":
        return self._evaluate_conditions(step.transition_conditions, agent)
    elif step.transition_mode == "llm":
        return await self._llm_transition(agent, step)

async def _llm_transition(self, agent, step):
    """Let LLM decide next state."""
    prompt = self._load_prompt(step.transition_prompt_artifact_id)
    # Fill in variables
    prompt = prompt.format(
        agent_id=agent.agent_id,
        current_state=agent.current_state,
        available_states=workflow.states,
        # ... etc
    )
    # LLM call that returns JSON
    result = await agent.llm_call(prompt, response_format="json")
    return result.get("next_state", agent.current_state)
```

## Implementation Phases

### Phase 1: Memory Artifacts (Foundation)
- [ ] Add `memory_store` artifact type
- [ ] Create `genesis_embedder` artifact
- [ ] Create `genesis_memory_search` artifact
- [ ] Create `genesis_memory_add` artifact
- [ ] Add `longterm_memory_artifact_id` to Agent
- [ ] Migrate existing memory.py to use artifacts
- [ ] Remove Qdrant dependency

### Phase 2: Prompt Artifacts
- [ ] Add `prompt` artifact type
- [ ] Create `genesis_prompt_library` artifact
- [ ] Add `personality_prompt_artifact_id` to Agent
- [ ] Update prompt loading in agent.py

### Phase 3: Workflow Artifacts
- [ ] Add `workflow` artifact type
- [ ] Add `workflow_artifact_id` to Agent
- [ ] Update step schema with `prompt_artifact_id`
- [ ] Add `transition_mode` and `transition_prompt_artifact_id`
- [ ] Implement LLM transition logic

### Phase 4: Integration
- [ ] Update runner.py execution flow
- [ ] Create migration for existing agents
- [ ] Update agent loader to create default artifacts
- [ ] Add backwards compatibility for inline prompts/workflows

### Phase 5: Genesis Seeding
- [ ] Create comprehensive genesis_prompt_library
- [ ] Create genesis_workflow_templates
- [ ] Update handbook with new patterns
- [ ] Add examples for trading intelligence artifacts

## Files Affected

- src/agents/agent.py (modify) - Add new artifact ID fields
- src/agents/memory.py (modify) - Remove Qdrant, use artifacts
- src/agents/workflow.py (modify) - Support artifact references
- src/simulation/runner.py (modify) - New execution flow
- src/world/artifacts.py (modify) - New artifact types
- src/world/genesis/factory.py (modify) - Register new genesis artifacts
- src/world/genesis/__init__.py (modify) - Export new genesis artifacts
- src/world/genesis/embedder.py (create) - Embedding generation service
- src/world/genesis/memory.py (create) - Memory operations service
- src/world/genesis/genesis_prompt_library.py (create)
- tests/unit/test_genesis_memory.py (create) - Memory artifact tests
- tests/test_prompt_artifacts.py (create)
- tests/test_llm_transitions.py (create)

## Required Tests

### Unit Tests
- `test_memory_store_artifact_creation`
- `test_memory_entry_add_with_embedding`
- `test_memory_search_semantic`
- `test_memory_pruning`
- `test_prompt_artifact_loading`
- `test_prompt_variable_substitution`
- `test_workflow_artifact_loading`
- `test_llm_transition_parsing`

### Integration Tests
- `test_agent_with_memory_artifact`
- `test_agent_with_prompt_artifacts`
- `test_agent_with_workflow_artifact`
- `test_full_artifact_intelligence_flow`
- `test_memory_trading_between_agents`
- `test_prompt_trading_between_agents`

### E2E Tests
- `test_agent_learns_and_trades_memory`
- `test_agent_evolves_prompts`

## Success Criteria

1. All agent intelligence components are artifacts
2. Agents can trade memories, prompts, workflows
3. No external dependencies (Qdrant removed)
4. LLM can control state transitions
5. Backwards compatible with existing agent configs
6. All tests pass

## Economic Implications

| Artifact Type | Creation Cost | Trade Value | Use Cost |
|--------------|---------------|-------------|----------|
| Memory Entry | 1 scrip (embedding) | Varies by value | Free (if owned) |
| Memory Search | - | - | 1 scrip per search |
| Prompt | Free | High (if effective) | Free |
| Workflow | Free | Very High | Free |
| Personality | Free | Very High | Free |

This creates incentives for:
- Agents to curate valuable memories (embedding costs)
- Successful agents to sell their "brains"
- Specialization and trading of cognitive components

## Migration Path

1. Existing agents continue working (inline prompts/workflows)
2. New artifact-based system available immediately
3. Gradual migration as agents create/trade artifacts
4. Eventually deprecate inline configs

## Open Questions

1. **Embedding Model**: Use OpenAI, Gemini, or local model?
   - Recommendation: Configurable, default to model provider's embedding API

2. **Memory Limits**: Hard cap per agent or pay-for-storage?
   - Recommendation: Configurable max_entries with importance-based pruning

3. **Prompt Versioning**: Track prompt versions for A/B testing?
   - Recommendation: Post-v1, use artifact update history
