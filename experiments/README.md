# Experiments Directory (Plan #277)

This directory contains experiment configurations for testing different agent
motivation configurations and observing emergent behavior.

## Quick Start

1. Copy `TEMPLATE.yaml` to a new file (e.g., `exp_001_discourse_baseline.yaml`)
2. Configure agents and their motivation profiles
3. Run the experiment
4. Record observations in the experiment file

## Directory Structure

```
experiments/
├── README.md           # This file
├── TEMPLATE.yaml       # Template for new experiments
├── exp_001_*.yaml      # Experiment configurations
├── exp_002_*.yaml
└── results/            # Experiment results (auto-generated)
    ├── exp_001/
    │   ├── events.jsonl
    │   ├── metrics.json
    │   └── summary.md
    └── exp_002/
```

## Motivation Profiles

Motivation profiles live in `config/motivation_profiles/` and define:
- **Telos** - The unreachable goal that orients the agent
- **Nature** - The agent's expertise and identity
- **Drives** - Intrinsic motivations (curiosity, capability, etc.)
- **Personality** - Social orientation and decision-making style

See `config/motivation_profiles/discourse_analyst.yaml` for an example.

## Running Experiments

```bash
# Run with specific agents
make run DURATION=300 AGENTS=discourse_analyst

# Run with custom config (future)
python scripts/run_experiment.py --config experiments/exp_001_baseline.yaml
```

## Experiment Workflow

1. **Hypothesis** - What do you expect to observe?
2. **Configure** - Set up agents, motivations, duration
3. **Run** - Execute the simulation
4. **Observe** - Review events.jsonl, track metrics
5. **Analyze** - What emerged? What didn't?
6. **Document** - Record learnings in the experiment file
7. **Iterate** - Design next experiment based on learnings

## Key Questions

When analyzing experiments, consider:

- Did agents pursue their drives (curiosity, capability)?
- Did specialization emerge?
- Did coordination/collaboration occur?
- What artifacts were created?
- How did agents' behavior differ based on motivation?

## Example Experiments

### Baseline: Discourse Analyst
Test single discourse_analyst agent to establish baseline behavior.

### Competition: Multiple Analysts
Multiple agents with same telos but different personalities
(cooperative vs competitive).

### Specialization: Mixed Domains
Agents with different domains (discourse, tools, coordination).
Does specialization emerge?

### Evolution: Self-Modification
Agents with `self_modification: true` in personality.
Do drives converge or diverge?
