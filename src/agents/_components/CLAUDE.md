# Prompt Components

Modular, reusable prompt fragments for composing agent behaviors.

## Quick Reference

```yaml
# In agent.yaml
components:
  behaviors:
    - buy_before_build    # Check market before building
    - economic_participant # Encourage transactions
  goals:
    - build_infrastructure
```

## Component Types

| Type | Purpose | Location |
|------|---------|----------|
| **Behaviors** | Behavioral modifiers injected into prompts | `behaviors/` |
| **Phases** | Reusable workflow step definitions | `phases/` |
| **Goals** | High-level directives that shape behavior | `goals/` |

## Component Format

```yaml
name: component_name
type: behavior | phase | goal
version: 1
description: "What this component does"

# Where to inject (for behaviors)
inject_into:
  - ideate
  - observe

# The prompt content
prompt_fragment: |
  Your prompt text here...

# Optional: context variables needed
requires_context:
  - artifacts
  - balance
```

## Creating Components

1. Create YAML file in appropriate subdirectory
2. Follow format above
3. Reference in agent's `components` section
4. Test with simulation

## How Injection Works

1. Agent config specifies components
2. Loader reads component files
3. For each workflow step matching `inject_into`, fragment is appended
4. Final prompt includes all injected fragments

## Experiment Tracking

Document experiments with component configurations:
```markdown
## Setup
- alpha_3: behaviors=[buy_before_build, economic_participant]
- beta_3: behaviors=[economic_participant] (control)
```
