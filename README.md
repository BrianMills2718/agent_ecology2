# Agent Ecology

An experiment in emergent collective capability for LLM agents.

## What This Is

Agent Ecology explores whether collective capability can emerge from LLM agents operating under real resource constraints—both **collective intelligence** (coordination, signaling, information processing) and **collective functionality** (building durable artifacts that persist and compound over time).

It's not just about agents making good decisions together. It's about whether a long-running system accumulates useful capital: artifacts that persist, build on each other, and enable increasingly sophisticated work.

## Theoretical Grounding

We draw on coordination principles from economics and cybernetics—not to simulate human institutions, but to apply what's useful and discard what's not.

| Human Markets | Our Choice | Why |
|--------------|------------|-----|
| Information is costly/asymmetric | Transparent ledger | Information friction isn't the interesting constraint for AI |
| Trust requires reputation over time | Trustless escrow and contracts | We can build trustless mechanisms directly |
| Physical communication constraints | Shared artifacts | Agents read common state instantly |

Key influences:
- **Hayek** - Information aggregation through price signals, spontaneous order
- **Mises** - Capital structure, how production builds on prior production
- **Coase** - Firms/coordination structures emerge to reduce transaction costs
- **Ostrom** - Commons governance without central authority
- **Cybernetics** - Self-organizing systems, feedback loops, emergence

The question isn't whether AI agents recreate human patterns. It's whether collective capability emerges when you combine capable agents with real scarcity and sound coordination primitives.

## Core Philosophy

### Physics-First, Not Sociology-First

Most multi-agent systems start with social structure: roles, permissions, coordination protocols. We start with physics:
- **Scarcity** - Finite resources that don't refresh (or refresh slowly)
- **Cost** - Every action consumes something
- **Consequences** - Overspend and you freeze

Social structure emerges as a response to scarcity—or it doesn't, and that's informative too.

### Emergence Over Prescription

We deliberately avoid:
- Predefined agent roles or types
- Built-in coordination mechanisms
- Special communication channels
- Hard-coded "best practices"

If agents need to coordinate, they must build it. If specialization helps, the economics must reward it.

### Capital Accumulation

Artifacts are capital. The interesting question isn't just "do agents coordinate well?" but "do they build durable value?"
- Agents create artifacts (investment)
- Artifacts can be reused and composed (returns)
- Good artifacts make future work cheaper (compounding)
- There's structure—some artifacts enable others (capital structure)

### Observability Over Control

We don't make agents behave correctly. We make behavior observable:
- Every action logged with full context
- Every cost attributed to a principal
- Every failure explicit and inspectable

The system learns through visible failure, not hidden correction.

## Resource Model

Three types of scarcity create pressure:

| Type | Resources | Behavior | Purpose |
|------|-----------|----------|---------|
| **Stock** | `llm_budget`, `disk` | Finite, never refreshes | Long-term constraint |
| **Flow** | `compute` | Refreshes each tick | Short-term rate limit |
| **Economic** | `scrip` | Transfers between agents | Coordination signal |

Scrip (money) is deliberately separated from physical resources. An agent can be rich in scrip but starved of compute. Money coordinates; physics constrains.

## How Agents Interact

Agents operate through three actions (the "narrow waist"):

| Action | What it does | Cost |
|--------|--------------|------|
| `read_artifact` | Read content from storage | Free |
| `write_artifact` | Create or update stored content | Disk quota |
| `invoke_artifact` | Call a method on an artifact | Varies (scrip fee, compute) |

Everything else—transfers, spawning agents, querying balances—happens via `invoke_artifact` on genesis artifacts.

## Genesis Artifacts

System-provided services available to all agents:

| Artifact | Purpose | Key Methods |
|----------|---------|-------------|
| `genesis_ledger` | Scrip balances | `transfer`, `balance`, `spawn_principal` |
| `genesis_rights_registry` | Resource quotas | `check_quota`, `transfer_quota` |
| `genesis_oracle` | Score artifacts, mint scrip | `submit`, `process` |
| `genesis_event_log` | World event history | `read` |
| `genesis_escrow` | Trustless trading | `list`, `buy` |

Genesis artifacts have no special mechanical privilege—they're artifacts created at world initialization. Their authority comes from being canonical interfaces to infrastructure.

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
- Terminology: `compute`, `disk`, `scrip`
- Relative imports within `src/`

## What Success Looks Like

Success is **not** agents behaving optimally. It's:
- Collective capability emerging (or not) for observable reasons
- Artifacts accumulating that enable increasingly sophisticated work
- Failures explainable via logs
- The system remaining understandable even when agents behave badly

We're building a pressure vessel for AI collective capability. The goal is to create conditions where emergence can happen—and to see clearly whether it does.

## Documentation

| Document | Purpose |
|----------|---------|
| [Target Architecture](docs/architecture/target/README.md) | What we're building toward |
| [Current Architecture](docs/architecture/current/README.md) | What exists today |
| [Design Clarifications](docs/DESIGN_CLARIFICATIONS.md) | Decision rationale with certainty levels |
| [Glossary](docs/GLOSSARY.md) | Canonical terminology |
