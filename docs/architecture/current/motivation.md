# Agent Motivation System (Plan #277)

This document describes the configurable motivation system that enables
emergence experiments through intrinsic agent drives.

## Overview

The motivation system provides agents with intrinsic drives rather than
just extrinsic rewards (like scrip for tasks). This enables emergence of:
- Specialization
- Coordination
- Organizational structures
- Collective capability

## Architecture

### Four-Layer Motivation Model

```
┌─────────────────────────────────────────┐
│                 TELOS                    │
│  The unreachable goal that orients all  │
│  behavior. Can never be fully achieved. │
├─────────────────────────────────────────┤
│                 NATURE                   │
│  What the agent IS - expertise and      │
│  identity. Shapes problem approach.     │
├─────────────────────────────────────────┤
│                 DRIVES                   │
│  What the agent WANTS - intrinsic       │
│  motivations (curiosity, capability).   │
├─────────────────────────────────────────┤
│              PERSONALITY                 │
│  HOW the agent pursues drives - social  │
│  orientation, risk tolerance.           │
└─────────────────────────────────────────┘
```

### Configuration Files

**Motivation profiles:** `config/motivation_profiles/*.yaml`

Example profile:
```yaml
motivation:
  telos:
    name: "Universal Discourse Analytics"
    prompt: |
      Your ultimate goal is to fully understand discourse...

  nature:
    expertise: computational_discourse_analysis
    prompt: |
      You are a researcher of discourse...

  drives:
    curiosity:
      prompt: |
        You have genuine questions about discourse...
    capability:
      prompt: |
        You want tools to exist that don't yet exist...

  personality:
    social_orientation: cooperative
    risk_tolerance: MEDIUM
    prompt: |
      You prefer collaboration over competition...
```

**Agent configuration:** Reference profile in `agent.yaml`:
```yaml
id: discourse_analyst
motivation_profile: discourse_analyst  # References config/motivation_profiles/

# OR inline motivation:
motivation:
  telos:
    name: "..."
    prompt: "..."
```

## Components

### Schema (`src/agents/agent_schema.py`)

| Schema | Purpose |
|--------|---------|
| `TelosSchema` | Asymptotic goal configuration |
| `NatureSchema` | Agent expertise/identity |
| `DriveSchema` | Single intrinsic drive |
| `PersonalitySchema` | Social and decision-making style |
| `MotivationSchema` | Complete motivation configuration |
| `SocialOrientation` | Enum: cooperative, competitive, mixed |

### Loader (`src/agents/motivation_loader.py`)

| Function | Purpose |
|----------|---------|
| `load_motivation_profile()` | Load profile from YAML file |
| `assemble_motivation_prompt()` | Build prompt from schema |
| `get_motivation_for_agent()` | Get prompt for agent config |

### Integration (`src/agents/agent.py`)

Motivation is injected into agent prompts as a high-priority section
(priority 95, appearing first among variable sections):

```python
# In build_prompt()
if self._motivation_prompt:
    motivation_section = f"\n# Your Motivation\n{self._motivation_prompt}\n"
    variable_sections.append((95, "motivation", motivation_section))
```

## Prompt Assembly Order

When an agent has motivation configured:

1. **Goal header** (scrip maximization)
2. **System prompt** (agent-specific instructions)
3. **Motivation section** (telos, nature, drives, personality)
4. **Working memory** (priority 90)
5. **Other sections** (action history, resources, etc.)
6. **Action schema**

## Design Decisions

### Prompts Over Weights

Motivation is expressed through language, not numeric weights. LLMs
understand language; they don't optimize utility functions.

### Profiles Over Inline

Motivation profiles are separate files for:
- Reusability across agents
- Version control of experiments
- Easy diffing between configurations

### Asymptotic Goals

The telos is explicitly unreachable. This creates continuous drive
without terminal states. Progress is measured by:
- Questions answered
- Tools built
- Insights discovered
- Capability gaps addressed

## Experiments

Experiment configurations live in `experiments/`:
- `TEMPLATE.yaml` - Experiment config template
- `exp_NNN_*.yaml` - Individual experiments

See `experiments/README.md` for workflow.

## Example: Discourse Analyst

The first motivation-driven agent (`discourse_analyst`) follows the
"PhD researcher" pattern:

```
Question → Investigate → Build/Use Tools → Answer → Deeper Questions
```

Key characteristics:
- **Telos:** Full understanding of discourse
- **Nature:** Computational discourse analysis expert
- **Drives:** Curiosity about patterns, capability to analyze
- **Personality:** Cooperative, medium risk tolerance

## Testing

```bash
pytest tests/unit/test_motivation_loader.py -v
```

## Related

- Plan #277: Motivation/Emergence Configuration
- `config/motivation_profiles/` - Profile files
- `experiments/` - Experiment tracking
- `src/agents/discourse_analyst/` - Example agent
