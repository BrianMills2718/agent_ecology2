# Agent Execution Model

How agents execute: state machines, steps, and transitions.

---

## Overview

Each agent turn:
1. Workflow engine checks current state
2. Finds step matching that state
3. Builds prompt (step + injected components)
4. Executes step (LLM call, code, or transition decision)
5. Transitions to next state

**One LLM call per turn** (for `type: llm` steps).

---

## State Machine

Defines the states an agent can be in and valid transitions.

```yaml
# From agent.yaml
workflow:
  state_machine:
    states: ["observing", "ideating", "implementing", "testing", "reflecting", "shipping"]
    initial_state: "observing"
    transitions:
      - from: "observing"
        to: "ideating"
        condition: "has_context"
      - from: "ideating"
        to: "implementing"
        condition: "has_idea"
      - from: "implementing"
        to: "testing"
        # No condition = always valid
      - from: "reflecting"
        to: "implementing"  # continue
      - from: "reflecting"
        to: "observing"     # pivot
      - from: "reflecting"
        to: "shipping"      # ship
      - from: "*"           # Wildcard: any state
        to: "observing"
        condition: "should_pivot"
```

### Transition Conditions

Conditions are evaluated against context variables:

| Condition Type | Example | Evaluated By |
|----------------|---------|--------------|
| Variable check | `"has_context"` | `safe_eval_condition()` |
| Always valid | (no condition) | Always true |
| Wildcard source | `from: "*"` | Matches any state |

**Limitation:** Conditions are static expressions. Cannot invoke artifacts.
**Future:** Plan #222 adds artifact invocation in conditions.

---

## Steps

Individual units of work within a workflow.

```yaml
workflow:
  steps:
    - name: observe
      type: llm
      in_state: "observing"
      prompt: |
        === GOAL: Maximize scrip ===
        You are {agent_id}. Balance: {balance}...
      transition_to: "ideating"
```

### Step Types

| Type | What It Does | LLM Call? |
|------|--------------|-----------|
| `llm` | Sends prompt to LLM, gets action | Yes |
| `code` | Executes Python code, sets context variables | No |
| `transition` | Asks LLM to choose next state | Yes |

### Step Fields

| Field | Required | Description |
|-------|----------|-------------|
| `name` | Yes | Unique identifier |
| `type` | Yes | `llm`, `code`, or `transition` |
| `in_state` | No | Only run when in these state(s) |
| `prompt` | For llm/transition | Prompt template with `{variables}` |
| `code` | For code | Python code to execute |
| `transition_to` | No | State to transition to after step |
| `transition_map` | For transition | Maps LLM decision → target state |
| `run_if` | No | Condition to check before running |
| `on_failure` | No | Error policy: `retry`, `skip`, `fail` |

### Code Steps

Execute Python code to set context variables:

```yaml
- name: compute_metrics
  type: code
  code: |
    success_rate = context.get('successes', 0) / max(context.get('total', 1), 1)
    should_pivot = success_rate < 0.3
    context['success_rate'] = success_rate
    context['should_pivot'] = should_pivot
```

**Security:** Code is evaluated via `safe_eval` - no arbitrary Python execution.

### Transition Steps

Ask LLM to choose next state:

```yaml
- name: strategic_reflect
  type: transition
  in_state: "reflecting"
  prompt: |
    Based on your performance, choose ONE:
    A) CONTINUE - keep working
    B) PIVOT - try something different
    C) SHIP - move on

    Respond with: continue, pivot, or ship
  transition_map:
    continue: "implementing"
    pivot: "observing"
    ship: "shipping"
```

---

## Prompt Building

For `type: llm` steps, the final prompt is built by:

1. **Start with step prompt** (from `workflow.steps[].prompt`)
2. **Inject matching components** (where `inject_into` includes step name)
3. **Substitute variables** (`{agent_id}`, `{balance}`, etc.)

```
Final Prompt = Step Prompt + Component1 + Component2 + ...
```

**Order:** Components are appended in the order they appear in `components.traits`.

**Limitation:** Always appends. Cannot prepend, insert at position, or replace.

---

## Context Variables

Available in prompts and conditions:

| Variable | Description |
|----------|-------------|
| `{agent_id}` | Agent's ID |
| `{balance}` | Current scrip balance |
| `{tick}` | Current event number |
| `{time_remaining}` | Time left in simulation |
| `{progress_percent}` | How far through simulation |
| `{artifacts}` | Available artifacts summary |
| `{my_artifacts}` | Artifacts created by this agent |
| `{action_history}` | Recent action results |
| `{last_action_result}` | Most recent action result |
| `{success_rate}` | Calculated success rate |
| `{economic_context}` | Economic summary |

Custom variables can be set by `type: code` steps.

---

## Error Handling

```yaml
workflow:
  default_on_failure: retry
  default_max_retries: 3

  steps:
    - name: risky_step
      type: llm
      on_failure: skip    # Override default for this step
      max_retries: 1
```

| Policy | Behavior |
|--------|----------|
| `retry` | Retry up to max_retries times |
| `skip` | Skip step, continue workflow |
| `fail` | Stop workflow execution |

---

## Execution Constraints

| Constraint | Current | Configurable? |
|------------|---------|---------------|
| One LLM call per turn | Yes | No (by design) |
| Step types | Fixed: llm, code, transition | No |
| Transition conditions | Static expressions | No (Plan #222 will add artifact invocation) |
| Injection timing | Static (based on inject_into list) | No (Plan #222 will add runtime conditions) |

---

## Related

- [03_configuration.md](03_configuration.md) - Injected prompt components
- [Plan #222](../../../plans/222_artifact_aware_workflow.md) - Artifact-aware workflow
- `src/agents/workflow.py` - Implementation
- `src/agents/state_machine.py` - State machine logic
