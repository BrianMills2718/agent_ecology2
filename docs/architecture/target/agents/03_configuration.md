# Agent Configuration

Configurable components that shape agent behavior.

---

## Overview

Agents are configured via `agent.yaml` files with two main sections:

```yaml
# agent.yaml structure
id: alpha_3
llm_model: "gemini/gemini-2.0-flash"
starting_credits: 100

workflow:
  state_machine: {...}
  steps: [...]

components:
  traits:           # ← Injected prompt components
    - loop_breaker
    - semantic_memory
  goals:            # ← High-level directives
    - facilitate_transactions
```

---

## Injected Prompt Components

Reusable prompt fragments that get injected into workflow steps.

### What They Are

| Aspect | Description |
|--------|-------------|
| **Storage** | YAML files in `src/agents/_components/traits/` |
| **Content** | Prompt text (the `prompt_fragment` field) |
| **Targeting** | List of step names (`inject_into` field) |
| **Purpose** | Add behavioral guidance to specific steps |

### Example: loop_breaker

```yaml
# src/agents/_components/traits/loop_breaker.yaml
name: loop_breaker
type: trait
version: 1
description: "Helps agents recognize and escape repetitive patterns"

inject_into:
  - observe
  - observing
  - reflect
  - reflecting
  - implement
  - implementing

prompt_fragment: |
  === LOOP DETECTION (loop_breaker) ===
  Check your "Recent Actions" section above. If you see the SAME action repeated:

  3x SAME ACTION = Yellow flag. Ask: "Am I making progress?"
  5x SAME ACTION = Red flag. You MUST try something DIFFERENT.

  ESCAPE STRATEGIES:
  1. Store what you learned from the failure
  2. Update your subgoal in working_memory
  3. Try a completely different action type

requires_context:
  - action_history
```

### How Injection Works

```
Agent config says: components.traits: [loop_breaker, semantic_memory]

When executing step "observe":
1. Check each trait's inject_into
2. loop_breaker.inject_into includes "observe" → INJECT
3. semantic_memory.inject_into includes "observe" → INJECT
4. Final prompt = step_prompt + loop_breaker.prompt_fragment + semantic_memory.prompt_fragment
```

### Available Injected Prompt Components

| Component | Purpose | Injects Into |
|-----------|---------|--------------|
| `loop_breaker` | Detect and escape repetitive patterns | observe, reflect, implement |
| `semantic_memory` | Encourage lesson storage | observe, reflect, implement, test, ship |
| `buy_before_build` | Check market before building | ideate, observe |
| `economic_participant` | Encourage transactions | observe, reflect |
| `memory_discipline` | Store insights, not raw actions | reflect |
| `subgoal_progression` | Track and update subgoals | observe, reflect |

### Creating New Components

1. Create YAML file in `src/agents/_components/traits/`
2. Define `name`, `type`, `inject_into`, `prompt_fragment`
3. Add to agent's `components.traits` list

```yaml
# my_new_component.yaml
name: my_new_component
type: trait
version: 1
description: "What this component does"

inject_into:
  - observe
  - reflect

prompt_fragment: |
  === MY GUIDANCE ===
  Instructions for the agent...

requires_context:
  - balance  # Variables this component needs
```

---

## Goals

High-level directives that shape overall behavior.

### What They Are

| Aspect | Description |
|--------|-------------|
| **Storage** | YAML files in `src/agents/_components/goals/` |
| **Content** | High-level purpose statement |
| **Usage** | Less common than injected prompt components |

### Example

```yaml
# src/agents/_components/goals/facilitate_transactions.yaml
name: facilitate_transactions
type: goal
description: "Encourage agents to participate in the economy"

inject_into:
  - observe

prompt_fragment: |
  GOAL: Actively participate in the economy. Look for opportunities to:
  - Buy useful artifacts from others
  - Sell your artifacts via escrow
  - Trade services for scrip
```

---

## Configuration Hierarchy

```
agent.yaml
├── id, llm_model, starting_credits    # Identity
├── workflow                            # Execution structure
│   ├── state_machine                   # States and transitions
│   └── steps                           # Individual step definitions
├── components                          # Behavioral modifiers
│   ├── traits → injected prompt components
│   └── goals → high-level directives
└── rag, visibility, etc.               # Other settings
```

---

## Capability Gaps

| Capability | Supported | Notes |
|------------|-----------|-------|
| Static injection (based on step name) | ✓ | Current behavior |
| Multiple components per step | ✓ | All matching components injected |
| Conditional injection (runtime) | ✗ | Plan #222 |
| Injection position (prepend/insert) | ✗ | Always appends |
| Component priority/ordering | Partial | Order from config list |
| Component conflicts | ✗ | No conflict detection |

---

## Terminology Note

**In YAML:** These are called `traits` (historical name)
**In documentation:** We call them "injected prompt components" (more accurate)

The YAML field name may change in the future, but the concept is stable.

---

## Related

- [02_execution.md](02_execution.md) - How components are injected during execution
- [genesis.md](genesis.md) - Which components genesis agents use
- `src/agents/_components/` - Component YAML files
- `src/agents/component_loader.py` - Loader implementation
