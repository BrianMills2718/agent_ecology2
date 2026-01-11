# Agent Ecology

A mechanism design substrate where LLM agents coordinate under real resource constraints.

## What This Is

Agent Ecology is **not a simulation**. It's a substrate for studying how heterogeneous AI agents interact when actions have real costs and consequences.

The goal is **emergence**: we don't define how agents should coordinate, specialize, or organize. We define scarcity and cost. Structure emerges—or doesn't—based on what works.

## The Problem

How do you get useful collective behavior from multiple AI agents without prescribing it?

Traditional approaches define roles, permissions, workflows, and coordination protocols upfront. This works when you know what you want. But for open-ended AI agent systems, you don't know what structures will be useful until agents discover them.

Agent Ecology takes a different approach: **constrain resources, not behavior**. Create real scarcity. Let agents figure out how to survive and thrive. Observe what emerges.

## Core Philosophy

### Physics-First, Not Sociology-First

Most multi-agent systems start with social structure: agent types, roles, organizations, permissions, coordination protocols. Then they simulate behavior within that structure.

We start with physics:
- **Scarcity** - Finite resources that don't refresh (or refresh slowly)
- **Cost** - Every action consumes something
- **Consequences** - Overspend and you freeze

Social structure (specialization, trade, cooperation) emerges as a response to scarcity—or it doesn't, and that's informative too.

### Emergence Over Prescription

We deliberately avoid:
- Predefined agent roles or types
- Built-in coordination mechanisms
- Special communication channels
- Hard-coded "best practices"

If agents need to coordinate, they must build coordination mechanisms from primitives (artifacts, contracts, transfers). If they need to specialize, the economics must reward it. Nothing is free.

### Real Constraints, Not Proxies

Resources in Agent Ecology map to real-world constraints:
- **llm_budget** = Actual dollars spent on API calls
- **disk** = Actual bytes stored
- **compute** = Rate limit on actions per time window

When the budget runs out, it's actually out. This grounds agent behavior in reality rather than abstract token economies.

### Observability Over Control

We don't try to make agents behave correctly. We make their behavior **observable**:
- Every action is logged with full context
- Every cost is attributed to a principal
- Every failure is explicit and inspectable

If agents behave badly, we see it. If they waste resources, we measure it. The system learns through visible failure, not hidden correction.

## Resource Model

Three types of scarcity create pressure:

| Type | Resources | Behavior | Purpose |
|------|-----------|----------|---------|
| **Stock** | `llm_budget`, `disk` | Finite, never refreshes | Long-term constraint |
| **Flow** | `compute` | Refreshes each tick | Short-term rate limit |
| **Economic** | `scrip` | Transfers between agents | Coordination signal |

**Key insight**: Scrip (money) is deliberately separated from physical resources. An agent can be rich in scrip but starved of compute, or vice versa. Money coordinates; physics constrains.

## How Agents Interact

Agents operate through three actions (the "narrow waist"):

| Action | What it does | Cost |
|--------|--------------|------|
| `read_artifact` | Read content from storage | Free |
| `write_artifact` | Create or update stored content | Disk quota |
| `invoke_artifact` | Call a method on an artifact | Varies (scrip fee, compute) |

Everything else—transfers, spawning agents, querying balances—happens via `invoke_artifact` on genesis artifacts. This keeps the action surface minimal and auditable.

## Genesis Artifacts

System-provided services available to all agents:

| Artifact | Purpose | Key Methods |
|----------|---------|-------------|
| `genesis_ledger` | Scrip balances | `transfer`, `balance`, `spawn_principal` |
| `genesis_rights_registry` | Resource quotas | `check_quota`, `transfer_quota` |
| `genesis_oracle` | Score artifacts, mint scrip | `submit`, `process` |
| `genesis_event_log` | World event history | `read` |
| `genesis_escrow` | Trustless trading | `list`, `buy` |

Genesis artifacts have no special mechanical privilege—they're just artifacts created at world initialization. Their authority comes from being the canonical interfaces to core infrastructure.

## Quick Start

```bash
# Install
pip install -e .

# Configure API keys
cp .env.example .env
# Edit .env with your LLM API credentials

# Run
python run.py                    # Run with defaults
python run.py --ticks 10         # Limit to 10 ticks
python run.py --agents 1         # Single agent
python run.py --dashboard        # With HTML dashboard
```

## Configuration

Key settings in `config/config.yaml`:

```yaml
resources:
  stock:
    llm_budget: { total: 1.00 }    # $ for API calls
    disk: { total: 50000 }         # bytes
  flow:
    compute: { per_tick: 1000 }    # actions per tick

scrip:
  starting_amount: 100             # initial currency

world:
  max_ticks: 100
```

## Architecture

```
agent_ecology/
  run.py              # Entry point
  config/
    config.yaml       # Runtime values
    schema.yaml       # Config documentation
  src/
    world/            # World state, ledger, executor
    agents/           # Agent loading, LLM interaction
    simulation/       # Runner, checkpointing
    dashboard/        # HTML dashboard
  tests/              # Test suite
  docs/
    architecture/     # Current and target architecture
```

### Execution Model

Each tick:
1. **Collect** - All agents submit actions simultaneously
2. **Execute** - Actions applied atomically (two-phase commit)

This prevents ordering advantages and enables fair concurrency.

### Security Model

- **No Python sandbox** - Agent code has full Python capabilities
- **Docker isolation** - Container is the security boundary
- **Intentional API access** - Agents can call external services

Agents are trusted within the container. The container is not trusted beyond its limits.

## Development

```bash
pip install -e .                              # Install
pytest tests/                                 # Run tests
python -m mypy src/ --ignore-missing-imports  # Type check
```

### Standards

- All functions require type hints
- No magic numbers—values come from config
- Terminology: `compute`, `disk`, `scrip` (not "credits" or "tokens")
- Relative imports within `src/`

## What Success Looks Like

Success is **not** agents behaving optimally. It's:
- Assumptions surfaced early through failure
- Failures explainable via logs
- Structure emerging (or not) for observable reasons
- The system remaining understandable even when agents behave badly

We're building a pressure vessel for AI coordination, not a solution. The goal is to make intelligence pay for its actions and make the results legible.

## Documentation

| Document | Purpose |
|----------|---------|
| [Target Architecture](docs/architecture/target/README.md) | What we're building toward |
| [Current Architecture](docs/architecture/current/README.md) | What exists today |
| [Design Clarifications](docs/DESIGN_CLARIFICATIONS.md) | Decision rationale with certainty levels |
| [Glossary](docs/GLOSSARY.md) | Canonical terminology |
