# Agent Cognitive Architecture

Detailed documentation of agent decision-making, memory, and learning systems.

**Last verified:** 2026-01-31 (TD-004: resource naming cleanup)

**Related:** [agents.md](agents.md) for lifecycle, [genesis_agents.md](genesis_agents.md) for default agents, [genesis_artifacts.md](genesis_artifacts.md) for services

---

## Overview

Agent cognition has multiple subsystems working together:

```
┌─────────────────────────────────────────────────────────────────┐
│                        AGENT COGNITION                          │
├─────────────────────────────────────────────────────────────────┤
│  Prompts & Workflows (90%)  │  State Machines (85%)            │
│  - 15+ prompt sections      │  - Configurable states           │
│  - CODE/LLM/TRANSITION      │  - Wildcard transitions          │
│  - Conditional execution    │  - LLM-informed decisions        │
├─────────────────────────────┴───────────────────────────────────┤
│  Memory Systems (80%)       │  Decision-Making (75%)           │
│  - Mem0 (semantic/episodic) │  - 4 action types                │
│  - Working memory (goals)   │  - Workflow vs propose_action    │
│  - ArtifactMemory (trade)   │  - OODA cognitive schema         │
├─────────────────────────────┴───────────────────────────────────┤
│  Loop Detection (75%)       │  Reflexes (60%)                  │
│  - Action history (15)      │  - Fast 0-cost decisions         │
│  - Pattern analysis         │  - Sandboxed Python              │
│  - Failure history (5)      │  - LLM fallback                  │
└─────────────────────────────────────────────────────────────────┘
```

---

## 1. Prompt Construction

### What Gets Injected (15+ sections)

`build_prompt()` in `src/agents/agent.py` constructs comprehensive prompts:

| Section | Source | Purpose |
|---------|--------|---------|
| System prompt | Agent config | Personality/instructions |
| Performance metrics | Agent state | Balance, success rate, revenue |
| Quota information | World state | Resource limits |
| Resource consumption | Plan #93 | Detailed usage metrics |
| Recent events | Action history | Last 15 actions with status |
| Working memory | Agent artifact | Goals, progress, lessons |
| Action history | Plan #156 | Compact loop detection format |
| Failure history | Plan #88 | Last 5 failures for learning |
| Mint submissions | World state | Pending auction bids |
| Available artifacts | World state | Discoverable artifacts + interfaces |
| Recent activity | World state | Filtered by relevance |
| Time remaining | Plan #157 | Progress %, time left |
| Economic context | Plan #160 | Solo vs multi-agent guidance |
| Action patterns | Plan #160 | Repeated patterns with success rates |

### Prompt Size Management

- Working memory truncated to `max_size_bytes` (default 2000)
- Action history limited to last 15 actions
- Failure history limited to last 5 failures
- **Concern:** No principled prioritization - all sections injected

---

## 2. Workflow Execution

### Step Types (`src/agents/workflow.py`)

| Type | Description | Use Case |
|------|-------------|----------|
| `CODE` | Execute Python expression | Compute metrics, conditions |
| `LLM` | Call LLM with prompt | Decision-making, planning |
| `TRANSITION` | Map LLM output to state (Plan #157) | State machine control |

### Workflow Features

```yaml
workflow:
  steps:
    - name: "observe"
      type: "llm"
      prompt: "Analyze current state"
      run_if: "tick > 0"           # Conditional execution

    - name: "strategic_reflect"
      type: "transition"            # Plan #157 Phase 4
      prompt: "Should you continue, pivot, or ship?"
      transition_map:
        continue: "implementing"
        pivot: "observing"
        ship: "shipping"

  error_handling:
    on_step_failure: "continue"     # RETRY, SKIP, or FAIL
```

### Workflow vs propose_action()

| Mode | When Used | Characteristics |
|------|-----------|-----------------|
| Workflow | Agent has `workflow` config | Multi-step, stateful |
| propose_action | No workflow configured | Single LLM call |

---

## 3. State Machines

### Implementation (`src/agents/state_machine.py`)

```python
class WorkflowStateMachine:
    current_state: str              # Current state name
    history: list[str]              # Past states
    config: StateConfig             # States and transitions
```

### Transition Types

| Type | Example | Description |
|------|---------|-------------|
| Specific | `observing -> ideating` | Named source state |
| Wildcard | `* -> observing` | From any state |
| Conditional | `condition: "success_rate < 0.3"` | Safe expression eval |
| LLM-informed | `transition_map: {pivot: observing}` | Plan #157 |

### Maturity: 85%

**Implemented:**
- State persistence in workflow context
- Safe expression evaluation (Plan #123)
- LLM-informed transitions (Plan #157)

**Gaps:**
- Agents rarely use transitions intentionally
- Most transitions happen automatically after steps complete
- State not explicitly persisted to checkpoint (uses working memory)

---

## 4. Memory Systems

### Dual Memory Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                     MEMORY SYSTEMS                          │
├────────────────────────────┬────────────────────────────────┤
│      Mem0 (Episodic)       │    Working Memory (Goals)      │
│  ─────────────────────     │    ────────────────────────    │
│  * Semantic vector search  │    * Structured JSON           │
│  * Actions/observations    │    * current_goal, progress    │
│  * External Qdrant store   │    * Embedded in artifact      │
│  * Shared singleton        │    * Auto-injected to prompt   │
├────────────────────────────┴────────────────────────────────┤
│                   ArtifactMemory (Alternative)               │
│  ───────────────────────────────────────────────────────    │
│  * Stores memories as artifact content                      │
│  * Checkpointable and tradeable                             │
│  * Used when artifact_store available                       │
└─────────────────────────────────────────────────────────────┘
```

### Working Memory Structure

```json
{
  "current_goal": "Build price oracle",
  "progress": {
    "stage": "Implementation",
    "completed": ["interface design"],
    "next_steps": ["core logic"]
  },
  "lessons": ["escrow needs ownership transfer first"],
  "strategic_objectives": ["become known for pricing"]
}
```

### Maturity: 80%

**Implemented:**
- Mem0 with Qdrant backend
- Working memory extraction/injection
- ArtifactMemory for checkpointable memory

**Gaps:**
- Agents don't consistently maintain working memory
- No incentive for memory maintenance
- Two systems create confusion about when to use which
- Memory quality not measured

---

## 5. Loop Detection and Learning

### Action History (Plan #156)

```python
# Format: "action_type(target) -> STATUS: message"
action_history = [
    "write_artifact(tool_v1) -> OK: Created artifact",
    "write_artifact(tool_v1) -> FAIL: Permission denied",
    "invoke_artifact(genesis_escrow.deposit) -> OK: Listed for 50 scrip"
]
```

### Pattern Analysis (Plan #160)

Detects repeated patterns and shows success/failure rates:

```
Repeated patterns detected:
- write_artifact(tool_x): 5x (3 ok, 2 fail)
- query_kernel(list_artifacts): 3x (3 ok, 0 fail)
```

### Failure History (Plan #88)

Last 5 failures stored for learning:

```python
failure_history = [
    "write_artifact: Permission denied - artifact in escrow",
    "invoke_artifact: Insufficient scrip for method cost"
]
```

### Opportunity Cost Metrics (Plan #157)

| Metric | Description |
|--------|-------------|
| `actions_taken` | Total actions attempted |
| `successful_actions` | Actions that succeeded |
| `failed_actions` | Actions that failed |
| `revenue_earned` | Balance change since start |
| `artifacts_completed` | First-write artifacts |

### Maturity: 75%

**Implemented:**
- Pattern detection and display
- Failure history tracking
- Opportunity cost metrics
- Checkpoint persistence (Plan #163)

**Gaps:**
- Passive detection only - no enforcement
- Agents can ignore loop warnings
- No root cause analysis (WHY pattern emerged)
- Economic learning not connected to specific artifacts

---

## 6. Reflexes (Plan #143)

### Purpose

Fast, 0-cost decisions before LLM invocation:

```
Agent receives world state
    |
    v
Reflex executor runs (100ms timeout)
    |
    v
If reflex fires -> Action returned (no LLM cost)
If reflex returns None -> Fall back to LLM
```

### Reflex Context

```python
class ReflexContext:
    tick: int
    balance: dict
    recent_events: list
    owned_artifacts: list
```

### Sandbox Security

- Limited builtins: `True`, `False`, `None`, `abs`, `all`, `len`, `max`, `min`
- No imports, no filesystem access
- 100ms timeout protection

### Maturity: 60%

**Implemented:**
- ReflexExecutor with sandboxing
- Timeout protection
- LLM fallback

**Gaps:**
- No reflex creation guidance
- No discovery mechanism for useful reflexes
- No performance metrics on reflex ROI
- Limited context available to reflexes

---

## 7. Cognitive Self-Modification (Plan #160)

### What Agents Can Modify

| Field | Method | Effect |
|-------|--------|--------|
| `system_prompt` | Write to self artifact | Change personality/instructions |
| `llm_model` | Write to self artifact | Switch models |
| `working_memory` | Write to self artifact | Update goals/progress |

### Error Tracking

```python
# Shown in prompt if reload fails
_last_reload_error: str | None
```

### Maturity: 60%

**Implemented:**
- Config reload from artifact
- Error tracking and display
- Validation retry for JSON

**Gaps:**
- No atomic guarantees for concurrent updates
- No rollback on bad modifications
- No explicit guidance on what to modify

---

## 8. Checkpoint Persistence (Plan #163)

### What Gets Saved

```python
class AgentCheckpointState(TypedDict):
    working_memory: dict[str, Any]
    action_history: list[str]
    failure_history: list[str]
    actions_taken: int
    successful_actions: int
    failed_actions: int
    revenue_earned: float
    artifacts_completed: int
    starting_balance: int
    last_action_result: str | None
```

### Methods

| Method | Purpose |
|--------|---------|
| `Agent.export_state()` | Serialize runtime state |
| `Agent.restore_state()` | Restore from checkpoint |

### Atomic Writes

Checkpoints use temp file + `os.replace()` for crash safety.

---

## 9. Artifact-Based Intelligence (Plan #146)

### Tradeable Cognitive Components

Agent intelligence is now artifact-based, enabling trading of successful strategies:

| Component | Agent Field | Artifact Type |
|-----------|-------------|---------------|
| Personality | `personality_prompt_artifact_id` | `prompt` |
| Workflow | `workflow_artifact_id` | `workflow` |
| Long-term Memory | `longterm_memory_artifact_id` | `memory_store` |

### Workflow Artifact References

WorkflowSteps can reference prompt artifacts:

```yaml
steps:
  - state: "observing"
    prompt_artifact_id: "my_observe_prompt"  # Instead of inline prompt
    transition_mode: "llm"                    # LLM decides next state
    transition_prompt_artifact_id: "my_transition_prompt"
```

### Genesis Services

| Service | Purpose |
|---------|---------|
| `genesis_prompt_library` | Pre-built prompt patterns (observe, ideate, implement, etc.) |
| `genesis_memory` | Memory operations (add, search) with embeddings |
| `genesis_embedder` | Generate embeddings (1 scrip per call) |

### Maturity: 70%

**Implemented:**
- Agent artifact reference fields
- WorkflowStep prompt_artifact_id
- LLM-controlled transitions (transition_mode)
- Genesis prompt library and memory services
- Memory artifacts with embeddings

**Planned (Plan #208):**
- Workflow hooks for auto-invocation at timing points (pre_decision, post_action, etc.)

---

## Maturity Summary

| Subsystem | Maturity | Key Gap |
|-----------|----------|---------|
| Prompts & Workflows | 90% | Prompt size management |
| State Machines | 85% | Agents don't use intentionally |
| Memory Systems | 80% | Incentive alignment |
| Decision-Making | 75% | Limited action space |
| Loop Detection | 75% | Passive only, no enforcement |
| Artifact Intelligence | 70% | Runner integration, hooks (Plan #208) |
| Reflexes | 60% | No creation guidance |
| Self-Modification | 60% | Safety/atomicity |

---

## Key Architectural Decisions

### 1. Information over Constraints

Agents SEE loop patterns but aren't FORCED to stop. This enables emergent behavior but risks wasted compute.

### 2. Dual Memory Systems

Mem0 for episodic (what happened), Working Memory for goals (what to do). Agents should use both but often use neither.

### 3. LLM-Informed Transitions

State changes can be LLM judgments (Plan #157) rather than hardcoded thresholds. Adds flexibility but costs tokens.

### 4. Behavioral Continuity

Checkpoint saves complete agent state (Plan #163) for resume without amnesia.

---

## Key Files

| File | Responsibility |
|------|----------------|
| `src/agents/agent.py` | Agent class, prompt building, state export/restore |
| `src/agents/workflow.py` | WorkflowRunner, step execution, transitions |
| `src/agents/state_machine.py` | WorkflowStateMachine, transition logic |
| `src/agents/memory.py` | AgentMemory (Mem0), ArtifactMemory |
| `src/agents/reflex.py` | ReflexExecutor, sandboxed execution |
| `src/simulation/checkpoint.py` | Checkpoint save/load with agent state |

---

## Open Questions

1. **Should state machines be more prominent?** Currently underutilized.
2. **How to incentivize memory maintenance?** Agents often ignore working memory.
3. **Is passive loop detection enough?** Or should we add enforcement?
4. **How to measure cognitive quality?** No metrics on decision quality.
